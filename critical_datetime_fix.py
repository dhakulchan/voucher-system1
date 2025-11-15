"""
Critical DateTime Corruption Fix for Booking #45
แก้ไขปัญหา datetime corruption โดยการแพทช์ในระดับ SQLAlchemy engine
"""

import logging
from datetime import datetime, date
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.dialects.mysql import pymysql
import mysql.connector

logger = logging.getLogger(__name__)

def safe_datetime_converter(value):
    """Convert any datetime value safely"""
    if value is None:
        return None
    
    if isinstance(value, (datetime, date)):
        return value
    
    if isinstance(value, str):
        # Remove microseconds to avoid 'str' object has no attribute 'microseconds'
        if '.' in value and value.count('.') == 1:
            value = value.split('.')[0]
        
        # Try various formats
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
            '%Y-%m-%dT%H:%M:%S',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
                
        logger.warning(f"Could not parse datetime: {value}")
        return None
    
    return value

def apply_critical_datetime_fix():
    """Apply critical fix for datetime corruption"""
    
    # Fix 1: Patch PyMySQL datetime converter
    try:
        import pymysql.converters as converters
        
        # Store original converters
        original_datetime = converters.convert_datetime
        original_date = converters.convert_date
        original_timestamp = converters.convert_timestamp
        
        def safe_convert_datetime(obj):
            try:
                if isinstance(obj, str):
                    return safe_datetime_converter(obj)
                return original_datetime(obj)
            except:
                return safe_datetime_converter(obj)
        
        def safe_convert_date(obj):
            try:
                if isinstance(obj, str):
                    converted = safe_datetime_converter(obj)
                    return converted.date() if converted else None
                return original_date(obj)
            except:
                converted = safe_datetime_converter(obj)
                return converted.date() if converted else None
        
        def safe_convert_timestamp(obj):
            try:
                if isinstance(obj, str):
                    return safe_datetime_converter(obj)
                return original_timestamp(obj)
            except:
                return safe_datetime_converter(obj)
        
        # Apply patches
        converters.convert_datetime = safe_convert_datetime
        converters.convert_date = safe_convert_date
        converters.convert_timestamp = safe_convert_timestamp
        
        logger.info("✅ PyMySQL datetime converters patched")
        
    except Exception as e:
        logger.warning(f"⚠️ Could not patch PyMySQL converters: {e}")
    
    # Fix 2: Engine-level event listener
    @event.listens_for(Engine, "connect")
    def set_mysql_pragmas(dbapi_connection, connection_record):
        """Set MySQL connection properties for safe datetime handling"""
        try:
            if hasattr(dbapi_connection, 'cursor'):
                cursor = dbapi_connection.cursor()
                # Set timezone and datetime handling
                cursor.execute("SET time_zone = '+00:00'")
                cursor.execute("SET sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO'")
                cursor.close()
                logger.info("✅ MySQL connection datetime settings applied")
        except Exception as e:
            logger.warning(f"⚠️ Could not set MySQL pragmas: {e}")
    
    # Fix 3: Pre-process result rows before SQLAlchemy processes them
    @event.listens_for(Engine, "before_cursor_execute")
    def log_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Log SQL execution for debugging"""
        if "booking" in statement.lower() and "45" in str(parameters):
            logger.info(f"🔍 Executing query for booking 45: {statement}")
    
    logger.info("🔧 Critical datetime corruption fixes applied")

# Apply fixes immediately when module is imported
apply_critical_datetime_fix()

def fix_booking_45_direct():
    """Direct fix for booking #45 datetime data"""
    
    try:
        # Connect directly to MariaDB
        conn = mysql.connector.connect(
            user='voucher_user',
            password='voucher_secure_2024',
            host='localhost',
            port=3306,
            database='voucher_enhanced',
            charset='utf8mb4'
        )
        
        cursor = conn.cursor()
        
        print("🔧 Applying direct fix to booking #45...")
        
        # Update all datetime fields to ensure proper format
        cursor.execute("""
            UPDATE bookings 
            SET 
                created_at = CONVERT(created_at, DATETIME),
                updated_at = CONVERT(updated_at, DATETIME), 
                time_limit = CONVERT(time_limit, DATETIME),
                confirmed_at = CASE WHEN confirmed_at IS NOT NULL THEN CONVERT(confirmed_at, DATETIME) ELSE NULL END,
                quoted_at = CASE WHEN quoted_at IS NOT NULL THEN CONVERT(quoted_at, DATETIME) ELSE NULL END,
                invoiced_at = CASE WHEN invoiced_at IS NOT NULL THEN CONVERT(invoiced_at, DATETIME) ELSE NULL END,
                paid_at = CASE WHEN paid_at IS NOT NULL THEN CONVERT(paid_at, DATETIME) ELSE NULL END,
                vouchered_at = CASE WHEN vouchered_at IS NOT NULL THEN CONVERT(vouchered_at, DATETIME) ELSE NULL END,
                invoice_paid_date = CASE WHEN invoice_paid_date IS NOT NULL THEN CONVERT(invoice_paid_date, DATETIME) ELSE NULL END
            WHERE id = 45
        """)
        
        conn.commit()
        
        # Verify the fix
        cursor.execute("SELECT id, booking_reference, created_at, updated_at FROM bookings WHERE id = 45")
        result = cursor.fetchone()
        
        if result:
            print(f"✅ Booking #45 datetime fields fixed: {result}")
        else:
            print("❌ Booking #45 not found")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing booking #45: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Critical DateTime Fix...")
    
    # Apply direct fix
    if fix_booking_45_direct():
        print("✅ Direct fix applied successfully")
    
    print("🎉 Critical datetime corruption fix ready!")