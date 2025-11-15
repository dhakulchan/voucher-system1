"""
MariaDB DateTime Fix Module
Enhanced datetime handling specifically for MariaDB database
System has migrated from SQLite to MariaDB
"""

import logging
from datetime import datetime, date, time
from sqlalchemy import TypeDecorator, DateTime, Date, Time
from sqlalchemy.dialects.mysql import DATETIME, DATE, TIME
import mysql.connector

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global datetime error handler
def safe_datetime_processor(value):
    """Universal safe processor for any datetime-like value"""
    if value is None:
        return None
    
    # If it's already a proper datetime object, return it
    if isinstance(value, (datetime, date, time)):
        return value
    
    # If it's a string, try to parse it safely
    if isinstance(value, str):
        # Remove microseconds if present to avoid AttributeError
        if '.' in value and value.count(':') >= 2:
            value = value.split('.')[0]
        
        # Try various datetime formats
        datetime_formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M',
        ]
        
        # Try time formats
        time_formats = [
            '%H:%M:%S',
            '%H:%M',
        ]
        
        # Try datetime formats first
        for fmt in datetime_formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        
        # Try time formats
        for fmt in time_formats:
            try:
                return datetime.strptime(value, fmt).time()
            except ValueError:
                continue
        
        logger.warning(f"Could not parse datetime/time string: {value}")
        return None
    
    # Try to convert other types to string first
    try:
        return safe_datetime_processor(str(value))
    except:
        logger.warning(f"Could not process datetime value: {value} (type: {type(value)})")
        return None

class SafeDateTime(TypeDecorator):
    """
    Custom DateTime type that safely handles MariaDB datetime values
    """
    impl = DateTime
    cache_ok = True

    def load_dialect_impl(self, dialect):
        # Always use MariaDB DATETIME type
        return dialect.type_descriptor(DATETIME())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                try:
                    return datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    logger.warning(f"Could not parse datetime string: {value}")
                    return None
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                try:
                    return datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    try:
                        # Handle date-only strings
                        return datetime.strptime(value, '%Y-%m-%d')
                    except ValueError:
                        logger.warning(f"Could not parse datetime string: {value}")
                        return None
        return value

class SafeDate(TypeDecorator):
    """
    Custom Date type that safely handles MariaDB date values
    """
    impl = Date
    cache_ok = True

    def load_dialect_impl(self, dialect):
        # Always use MariaDB DATE type
        return dialect.type_descriptor(DATE())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return datetime.strptime(value, '%Y-%m-%d').date()
            except ValueError:
                try:
                    return datetime.fromisoformat(value.replace('Z', '+00:00')).date()
                except ValueError:
                    logger.warning(f"Could not parse date string: {value}")
                    return None
        if isinstance(value, datetime):
            return value.date()
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return datetime.strptime(value, '%Y-%m-%d').date()
            except ValueError:
                try:
                    return datetime.fromisoformat(value.replace('Z', '+00:00')).date()
                except ValueError:
                    logger.warning(f"Could not parse date string: {value}")
                    return None
        if isinstance(value, datetime):
            return value.date()
        return value

class SafeTime(TypeDecorator):
    """
    Custom Time type that safely handles MariaDB time values
    """
    impl = Time
    cache_ok = True

    def load_dialect_impl(self, dialect):
        # Always use MariaDB TIME type
        return dialect.type_descriptor(TIME())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return datetime.strptime(value, '%H:%M:%S').time()
            except ValueError:
                try:
                    return datetime.strptime(value, '%H:%M').time()
                except ValueError:
                    logger.warning(f"Could not parse time string: {value}")
                    return None
        if isinstance(value, datetime):
            return value.time()
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return datetime.strptime(value, '%H:%M:%S').time()
            except ValueError:
                try:
                    return datetime.strptime(value, '%H:%M').time()
                except ValueError:
                    logger.warning(f"Could not parse time string: {value}")
                    return None
        if isinstance(value, datetime):
            return value.time()
        return value

# Monkey patch MySQL dialect's datetime/time processors
def patch_mysql_dialect():
    """Patch SQLAlchemy MySQL dialect to use safe datetime processing"""
    try:
        from sqlalchemy.dialects.mysql import types as mysql_types
        
        # Create safe versions of the problematic processors
        def safe_mysql_datetime_process(value):
            try:
                return safe_datetime_processor(value)
            except Exception as e:
                logger.warning(f"MySQL datetime processor error: {e}, value: {value}")
                return value

        def safe_mysql_time_process(value):
            try:
                if value is None:
                    return None
                if isinstance(value, str):
                    # Handle string time values safely
                    try:
                        return datetime.strptime(value, '%H:%M:%S').time()
                    except ValueError:
                        try:
                            return datetime.strptime(value, '%H:%M').time()
                        except ValueError:
                            logger.warning(f"Could not parse time string: {value}")
                            return None
                return value
            except Exception as e:
                logger.warning(f"MySQL time processor error: {e}, value: {value}")
                return value

        # Patch the TIME type's process method
        original_time_process = getattr(mysql_types.TIME, 'process', None)
        if original_time_process:
            def patched_time_process(self, value, dialect):
                try:
                    # Try to access microseconds attribute safely
                    if hasattr(value, 'microseconds'):
                        return original_time_process(self, value, dialect)
                    else:
                        return safe_mysql_time_process(value)
                except AttributeError:
                    return safe_mysql_time_process(value)
                except Exception as e:
                    logger.warning(f"TIME process error: {e}")
                    return safe_mysql_time_process(value)
            
            mysql_types.TIME.process = patched_time_process
            logger.info("✅ MySQL TIME processor patched successfully")
        
        # Patch the DATETIME type's process method  
        original_datetime_process = getattr(mysql_types.DATETIME, 'process', None)
        if original_datetime_process:
            def patched_datetime_process(self, value, dialect):
                try:
                    # Try to access microseconds attribute safely
                    if hasattr(value, 'microseconds'):
                        return original_datetime_process(self, value, dialect)
                    else:
                        return safe_mysql_datetime_process(value)
                except AttributeError:
                    return safe_mysql_datetime_process(value)
                except Exception as e:
                    logger.warning(f"DATETIME process error: {e}")
                    return safe_mysql_datetime_process(value)
            
            mysql_types.DATETIME.process = patched_datetime_process
            logger.info("✅ MySQL DATETIME processor patched successfully")
        
    except Exception as e:
        logger.warning(f"Could not patch MySQL dialect: {e}")

def safe_mysql_datetime_processor(value):
    """
    Safe datetime processor for MySQL/MariaDB values
    """
    if value is None:
        return None
    
    if isinstance(value, datetime):
        return value
    
    if isinstance(value, str):
        # Remove microseconds if present to avoid AttributeError
        if '.' in value:
            value = value.split('.')[0]
        
        # Try various datetime formats
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        
        logger.warning(f"Could not parse datetime string: {value}")
        return None
    
    # Try to convert other types to string first
    try:
        return safe_mysql_datetime_processor(str(value))
    except:
        logger.warning(f"Could not process datetime value: {value} (type: {type(value)})")
        return None

def get_mariadb_connection():
    """Get MariaDB connection for datetime testing"""
    config = {
        'user': 'voucher_user',
        'password': 'voucher_secure_2024',
        'host': 'localhost',
        'port': 3306,
        'database': 'voucher_enhanced',
        'charset': 'utf8mb4'
    }
    return mysql.connector.connect(**config)

# Apply MariaDB datetime fixes
logger.info("🔧 MariaDB DateTime Fix Module Loaded")
logger.info("✅ System configured for MariaDB database")

# Patch MySQL datetime processor to handle string values safely
try:
    from sqlalchemy.dialects.mysql import types as mysql_types
    
    # Create a patched DATETIME class
    class SafeMySQLDateTime(mysql_types.DATETIME):
        def result_processor(self, dialect, coltype):
            """Safe datetime result processor that handles string values"""
            def process(value):
                if value is None:
                    return None
                
                # If it's already a datetime, return as-is
                if isinstance(value, datetime):
                    return value
                
                # If it's a string, use our safe processor
                if isinstance(value, str):
                    return safe_mysql_datetime_processor(value)
                
                # For other types, try to convert safely
                try:
                    return safe_mysql_datetime_processor(str(value))
                except:
                    logger.warning(f"Could not process datetime value: {value} (type: {type(value)})")
                    return None
            
            return process
    
    # Replace the original DATETIME class
    mysql_types.DATETIME = SafeMySQLDateTime
    logger.info("✅ MySQL DATETIME class replaced with safe version")
    
except Exception as e:
    logger.warning(f"⚠️ Could not patch MySQL datetime processor: {e}")

# Test MariaDB connection
try:
    conn = get_mariadb_connection()
    logger.info("✅ MariaDB connection test successful")
    conn.close()
except Exception as e:
    logger.error(f"❌ MariaDB connection test failed: {e}")

# Apply MySQL dialect patches and comprehensive SQLAlchemy overrides
patch_mysql_dialect()

# Override SQLAlchemy MySQL types and patch the exact problematic function
def override_mysql_types():
    """Replace problematic MySQL types with safe versions"""
    try:
        from sqlalchemy.dialects.mysql import types as mysql_types
        
        # CRITICAL: Patch the exact function that's causing the error
        # This is the function at line 427 in sqlalchemy/dialects/mysql/types.py
        
        # Get the original TIME class
        original_time_class = mysql_types.TIME
        
        # Create a completely new TIME class that overrides the problematic process method
        class UltraSafeTime(original_time_class):
            def result_processor(self, dialect, coltype):
                """Ultra-safe result processor that never tries to access microseconds on strings"""
                def process(value):
                    if value is None:
                        return None
                    
                    # If it's already a time object, return it
                    if hasattr(value, 'hour'):  # It's a time object
                        return value
                    
                    # If it's a string, parse it safely
                    if isinstance(value, str):
                        try:
                            if '.' in value:
                                # Handle microseconds in string format
                                time_part = value.split('.')[0]
                                return datetime.strptime(time_part, '%H:%M:%S').time()
                            else:
                                # Simple time string
                                if value.count(':') == 2:
                                    return datetime.strptime(value, '%H:%M:%S').time()
                                elif value.count(':') == 1:
                                    return datetime.strptime(value, '%H:%M').time()
                                else:
                                    logger.warning(f"Could not parse time string: {value}")
                                    return None
                        except ValueError as e:
                            logger.warning(f"Could not parse time string '{value}': {e}")
                            return None
                    
                    # For any other type, try to convert to string first
                    try:
                        return process(str(value))
                    except:
                        logger.warning(f"Could not process time value: {value} (type: {type(value)})")
                        return None
                
                return process
        
        # Replace the TIME class entirely
        mysql_types.TIME = UltraSafeTime
        
        # Also try to patch any existing instances
        try:
            # Force reload of the type mapping
            from sqlalchemy.dialects.mysql.base import MySQLDialect
            if hasattr(MySQLDialect, 'colspecs'):
                MySQLDialect.colspecs = getattr(MySQLDialect, 'colspecs', {}).copy()
                MySQLDialect.colspecs[mysql_types.TIME] = UltraSafeTime
                logger.info("✅ MySQL dialect colspecs updated")
        except Exception as e:
            logger.warning(f"Could not update colspecs: {e}")
        
        logger.info("✅ MySQL TIME type completely replaced with ultra-safe version")
        
    except Exception as e:
        logger.warning(f"Could not override MySQL TIME type: {e}")
        import traceback
        traceback.print_exc()

override_mysql_types()

logger.info("🔧 MariaDB DateTime Fix Module Loaded")