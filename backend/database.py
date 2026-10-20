import pymysql
import pymysql.cursors
from contextlib import contextmanager
from decimal import Decimal
from datetime import datetime, date, timedelta
from config import Config

def clean_row(row):
    """Recursively converts Decimals, datetimes, dates to JSON serializable formats."""
    if row is None:
        return None
    if isinstance(row, list):
        return [clean_row(item) for item in row]
    if isinstance(row, dict):
        new_dict = {}
        for k, v in row.items():
            if isinstance(v, Decimal):
                new_dict[k] = float(v)
            elif isinstance(v, (datetime, date)):
                new_dict[k] = v.isoformat()
            elif isinstance(v, timedelta):
                new_dict[k] = str(v)
            elif isinstance(v, (dict, list)):
                new_dict[k] = clean_row(v)
            else:
                new_dict[k] = v
        return new_dict
    return row

def get_connection():
    """Creates a raw MySQL connection."""
    kwargs = {
        'host': Config.DB_HOST,
        'port': Config.DB_PORT,
        'user': Config.DB_USER,
        'password': Config.DB_PASSWORD,
        'database': Config.DB_NAME,
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor,
        'autocommit': False,
        'connect_timeout': 10
    }
    if Config.DB_SSL:
        kwargs['ssl'] = {'ssl_mode': 'REQUIRED'}
    return pymysql.connect(**kwargs)

@contextmanager
def get_db_cursor(commit=False):
    """Context manager for single operations or auto-commit queries."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            yield cursor
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

@contextmanager
def transaction():
    """
    ACID Transaction context manager:
    Begins transaction, yields (conn, cursor).
    On successful block exit, commits changes.
    On exception, rolls back immediately.
    """
    conn = get_connection()
    try:
        conn.begin()
        with conn.cursor() as cursor:
            yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def query_all(query, params=None):
    """Executes SELECT and returns list of dicts."""
    with get_db_cursor() as cursor:
        cursor.execute(query, params or ())
        results = cursor.fetchall()
        return clean_row(results)

def query_one(query, params=None):
    """Executes SELECT and returns a single dict or None."""
    with get_db_cursor() as cursor:
        cursor.execute(query, params or ())
        result = cursor.fetchone()
        return clean_row(result)

def execute_commit(query, params=None):
    """Executes an INSERT/UPDATE/DELETE query and commits."""
    with get_db_cursor(commit=True) as cursor:
        cursor.execute(query, params or ())
        return cursor.lastrowid
