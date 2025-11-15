"""
Quick fix for MySQL microseconds issue
"""
from sqlalchemy.dialects.mysql import types as mysql_types
from datetime import datetime, time
import logging

logger = logging.getLogger(__name__)

def patch_mysql_time_type():
    """Patch MySQL TIME type to prevent microseconds error"""
    
    # Get the original TIME class
    original_time_class = mysql_types.TIME
    
    class SafeTime(original_time_class):
        def result_processor(self, dialect, coltype):
            """Safe result processor that handles string values properly"""
            def process(value):
                if value is None:
                    return None
                
                # If it's already a time object, return it
                if hasattr(value, 'hour'):
                    return value
                
                # If it's a string, parse it safely without accessing microseconds
                if isinstance(value, str):
                    try:
                        # Remove microseconds part if present
                        if '.' in value:
                            value = value.split('.')[0]
                        
                        # Parse time string
                        if value.count(':') == 2:
                            return datetime.strptime(value, '%H:%M:%S').time()
                        elif value.count(':') == 1:
                            return datetime.strptime(value, '%H:%M').time()
                        else:
                            return None
                    except ValueError:
                        return None
                
                return value
            
            return process
    
    # Replace the TIME class
    mysql_types.TIME = SafeTime
    logger.info("MySQL TIME type patched successfully")

# Apply the patch immediately
patch_mysql_time_type()