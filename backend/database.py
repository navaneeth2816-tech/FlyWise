import queue
import threading
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

def _create_raw_connection():
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
        'connect_timeout': 8
    }
    if Config.DB_SSL:
        kwargs['ssl'] = {'ssl_mode': 'REQUIRED'}
    return pymysql.connect(**kwargs)

class MySQLConnectionPool:
    """Thread-safe connection pool for reusing database connections."""
    def __init__(self, maxsize=15):
        self.pool = queue.Queue(maxsize=maxsize)
        self.maxsize = maxsize
        self._lock = threading.Lock()

    def acquire(self):
        """Acquires a healthy connection from the pool or creates a new one."""
        while not self.pool.empty():
            try:
                conn = self.pool.get_nowait()
                if conn and conn.open:
                    try:
                        conn.ping()
                        return conn
                    except Exception:
                        try:
                            conn.close()
                        except Exception:
                            pass
            except queue.Empty:
                break
        return _create_raw_connection()

    def release(self, conn):
        """Returns an active connection back to the pool."""
        if not conn:
            return
        try:
            if conn.open:
                try:
                    conn.rollback()
                except Exception:
                    pass
                self.pool.put_nowait(conn)
            else:
                try:
                    conn.close()
                except Exception:
                    pass
        except queue.Full:
            try:
                conn.close()
            except Exception:
                pass
        except Exception:
            try:
                conn.close()
            except Exception:
                pass

_db_pool = MySQLConnectionPool(maxsize=15)

def get_connection():
    """Creates or acquires a MySQL connection."""
    return _db_pool.acquire()

@contextmanager
def get_db_cursor(commit=False):
    """Context manager for single operations or auto-commit queries using connection pooling."""
    conn = _db_pool.acquire()
    try:
        with conn.cursor() as cursor:
            yield cursor
        if commit:
            conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        _db_pool.release(conn)

@contextmanager
def transaction():
    """
    ACID Transaction context manager:
    Begins transaction, yields (conn, cursor).
    On successful block exit, commits changes.
    On exception, rolls back immediately.
    Releases connection back to the pool.
    """
    conn = _db_pool.acquire()
    try:
        conn.begin()
        with conn.cursor() as cursor:
            yield cursor
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        _db_pool.release(conn)

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
