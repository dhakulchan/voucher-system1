"""
MariaDB Connection Helper
ฟังก์ชันช่วยสำหรับเชื่อมต่อ MariaDB ที่ใช้แทน SQLite
"""

import mysql.connector
from contextlib import contextmanager

def get_mariadb_config():
    """Get MariaDB configuration"""
    return {
        'user': 'voucher_user',
        'password': 'voucher_secure_2024',
        'host': 'localhost',
        'port': 3306,
        'database': 'voucher_enhanced',
        'charset': 'utf8mb4'
    }

@contextmanager
def get_mariadb_connection():
    """Context manager for MariaDB connection"""
    conn = None
    try:
        config = get_mariadb_config()
        conn = mysql.connector.connect(**config)
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()

@contextmanager 
def get_mariadb_cursor():
    """Context manager for MariaDB cursor"""
    with get_mariadb_connection() as conn:
        cursor = conn.cursor()
        try:
            yield cursor, conn
        finally:
            cursor.close()

def execute_mariadb_query(query, params=None, fetch_one=False, fetch_all=False):
    """Execute MariaDB query with automatic connection handling"""
    with get_mariadb_cursor() as (cursor, conn):
        cursor.execute(query, params or ())
        
        if fetch_one:
            return cursor.fetchone()
        elif fetch_all:
            return cursor.fetchall()
        else:
            conn.commit()
            return cursor.lastrowid

def convert_sqlite_to_mariadb_query(sqlite_query):
    """Convert SQLite query syntax to MariaDB syntax"""
    # Replace ? placeholders with %s placeholders
    mariadb_query = sqlite_query.replace('?', '%s')
    
    # Convert common SQLite functions to MariaDB equivalents
    replacements = {
        'datetime(': 'STR_TO_DATE(',
        'strftime(': 'DATE_FORMAT(',
        'substr(': 'SUBSTRING(',
        'length(': 'LENGTH(',
        'ifnull(': 'IFNULL(',
    }
    
    for sqlite_func, mariadb_func in replacements.items():
        mariadb_query = mariadb_query.replace(sqlite_func, mariadb_func)
    
    return mariadb_query

# Legacy SQLite connection replacement
def sqlite3_connect_replacement(database_path):
    """
    Replacement function for sqlite3.connect() calls
    Returns MariaDB connection instead
    """
    import warnings
    warnings.warn(
        f"sqlite3.connect('{database_path}') is deprecated. Use MariaDB connection instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    config = get_mariadb_config()
    return mysql.connector.connect(**config)

# Monkey patch for legacy code
try:
    import sqlite3
    sqlite3.connect_original = sqlite3.connect
    sqlite3.connect = sqlite3_connect_replacement
except ImportError:
    pass