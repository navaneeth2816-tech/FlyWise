import os
import queue
import threading
from contextlib import contextmanager
from decimal import Decimal
from datetime import datetime, date, timedelta
from config import Config

# Primary MySQL Driver: MySQL Connector/Python
# Fallback Driver: PyMySQL
HAVE_MYSQL_CONNECTOR = False
HAVE_PYMYSQL = False

try:
    import mysql.connector
    HAVE_MYSQL_CONNECTOR = True
except ImportError:
    pass

try:
    import pymysql
    import pymysql.cursors
    HAVE_PYMYSQL = True
except ImportError:
    pass

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

def _wrap_mysql_connector_conn(conn):
    """Wraps mysql.connector connection for unified API compatibility without breaking internal callers."""
    if not hasattr(conn, 'open'):
        type(conn).open = property(lambda self: self.is_connected())
    if not hasattr(conn, 'begin'):
        type(conn).begin = lambda self: self.start_transaction()
    return conn

def _create_raw_connection():
    """Creates a raw MySQL connection using MySQL Connector/Python or PyMySQL."""
    if HAVE_MYSQL_CONNECTOR:
        kwargs = {
            'host': Config.DB_HOST,
            'port': Config.DB_PORT,
            'user': Config.DB_USER,
            'password': Config.DB_PASSWORD,
            'database': Config.DB_NAME,
            'charset': 'utf8mb4',
            'autocommit': False,
            'connection_timeout': 10
        }
        if Config.DB_SSL:
            kwargs['ssl_disabled'] = False
        else:
            kwargs['ssl_disabled'] = True
        conn = mysql.connector.connect(**kwargs)
        return _wrap_mysql_connector_conn(conn)
    elif HAVE_PYMYSQL:
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
            try:
                import ssl
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                kwargs['ssl'] = ctx
            except Exception:
                kwargs['ssl'] = {'ssl_mode': 'REQUIRED'}
        return pymysql.connect(**kwargs)
    else:
        raise RuntimeError("No MySQL driver installed. Please run: pip install mysql-connector-python")

def _is_connection_alive(conn):
    """Checks whether the connection is currently open and healthy."""
    if not conn:
        return False
    try:
        if hasattr(conn, 'is_connected'):
            if not conn.is_connected():
                return False
        elif hasattr(conn, 'open'):
            if not conn.open:
                return False
        if hasattr(conn, 'ping'):
            conn.ping(reconnect=True)
        return True
    except Exception:
        return False

class MySQLConnectionPool:
    """Thread-safe connection pool for reusing MySQL connections."""
    def __init__(self, maxsize=15):
        self.pool = queue.Queue(maxsize=maxsize)
        self.maxsize = maxsize
        self._lock = threading.Lock()

    def acquire(self):
        """Acquires a healthy connection from the pool or creates a new one."""
        while not self.pool.empty():
            try:
                conn = self.pool.get_nowait()
                if _is_connection_alive(conn):
                    return conn
                else:
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
            if _is_connection_alive(conn):
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
        if HAVE_MYSQL_CONNECTOR and isinstance(conn, (mysql.connector.pooling.PooledMySQLConnection, mysql.connector.MySQLConnection)):
            cursor = conn.cursor(dictionary=True, buffered=True)
        else:
            cursor = conn.cursor()
        try:
            yield cursor
        finally:
            try:
                cursor.close()
            except Exception:
                pass
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
    Begins transaction, yields dictionary cursor.
    On successful block exit, commits changes.
    On exception, rolls back immediately.
    Releases connection back to the pool.
    """
    conn = _db_pool.acquire()
    try:
        conn.begin()
        if HAVE_MYSQL_CONNECTOR and isinstance(conn, (mysql.connector.pooling.PooledMySQLConnection, mysql.connector.MySQLConnection)):
            cursor = conn.cursor(dictionary=True, buffered=True)
        else:
            cursor = conn.cursor()
        try:
            yield cursor
        finally:
            try:
                cursor.close()
            except Exception:
                pass
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
