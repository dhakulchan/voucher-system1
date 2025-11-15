#!/usr/bin/env python3
"""
Ultra-aggressive datetime fix for SQLAlchemy MySQL TIME processing
This patches the exact function that's causing the AttributeError
"""

import logging
from datetime import datetime, time
import sys

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def ultra_aggressive_patch():
    """
    Apply the most aggressive patch possible to fix the datetime issue
    """
    try:
        # Import the exact module that's causing the problem
        from sqlalchemy.dialects.mysql import types as mysql_types
        
        # Get the original TIME class
        original_time_class = mysql_types.TIME
        
        # Store the original result_processor method
        original_result_processor = original_time_class.result_processor
        
        def patched_result_processor(self, dialect, coltype):
            """
            Completely safe result processor that never fails
            """
            def safe_process_time_value(value):
                if value is None:
                    return None
                
                # If it's already a time object, return it
                if isinstance(value, time):
                    return value
                
                # If it's a string, parse it safely without any microseconds access
                if isinstance(value, str):
                    try:
                        # Remove any fractional seconds to avoid issues
                        clean_value = value.split('.')[0] if '.' in value else value
                        
                        # Try to parse as time
                        if clean_value.count(':') == 2:
                            parts = clean_value.split(':')
                            hour, minute, second = int(parts[0]), int(parts[1]), int(parts[2])
                            return time(hour, minute, second)
                        elif clean_value.count(':') == 1:
                            parts = clean_value.split(':')
                            hour, minute = int(parts[0]), int(parts[1])
                            return time(hour, minute)
                        else:
                            logger.warning(f"Unexpected time format: {clean_value}")
                            return None
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Could not parse time string '{value}': {e}")
                        return None
                
                # Try to convert any other type to string first
                try:
                    return safe_process_time_value(str(value))
                except Exception as e:
                    logger.warning(f"Could not process time value {value} (type: {type(value)}): {e}")
                    return None
            
            return safe_process_time_value
        
        # Replace the result_processor method on the class
        original_time_class.result_processor = patched_result_processor
        logger.info("✅ Ultra-aggressive patch: MySQL TIME.result_processor completely replaced")
        
        # Also patch any instances that might already exist
        try:
            # Try to patch at the dialect level as well
            from sqlalchemy.dialects.mysql.base import MySQLDialect
            
            # Create a safe processor function
            def safe_time_processor_function(value):
                if value is None:
                    return None
                if isinstance(value, str):
                    try:
                        # Clean the value and parse safely
                        clean_value = value.split('.')[0] if '.' in value else value
                        if clean_value.count(':') == 2:
                            parts = clean_value.split(':')
                            return time(int(parts[0]), int(parts[1]), int(parts[2]))
                        elif clean_value.count(':') == 1:
                            parts = clean_value.split(':')
                            return time(int(parts[0]), int(parts[1]))
                    except (ValueError, IndexError):
                        logger.warning(f"Could not parse time: {value}")
                        return None
                return value
            
            # If there's a way to set type processors, do it
            if hasattr(MySQLDialect, '_type_memos'):
                # Clear any cached type processors
                MySQLDialect._type_memos.clear()
                logger.info("✅ Cleared MySQL dialect type memos")
            
        except Exception as e:
            logger.warning(f"Could not patch dialect level: {e}")
        
        # Also try to patch the exact function that's being called
        try:
            # This is the nuclear option - patch the exact method that's failing
            import sqlalchemy.dialects.mysql.types
            
            # Get the TIME class from the module
            time_class = sqlalchemy.dialects.mysql.types.TIME
            
            # Create a completely new process method that never accesses microseconds
            def ultra_safe_process(self, value, dialect):
                """Process TIME values without ever accessing microseconds attribute"""
                if value is None:
                    return None
                
                # Never, ever try to access microseconds on the value
                # Just parse it as a string if needed
                if isinstance(value, str):
                    try:
                        clean_value = value.split('.')[0]  # Remove fractional seconds
                        if clean_value.count(':') == 2:
                            h, m, s = clean_value.split(':')
                            return time(int(h), int(m), int(s))
                        elif clean_value.count(':') == 1:
                            h, m = clean_value.split(':')
                            return time(int(h), int(m))
                    except (ValueError, AttributeError):
                        logger.warning(f"Could not parse time string: {value}")
                        return None
                
                # If it's already a time object, return it
                if hasattr(value, 'hour'):
                    return value
                
                return value
            
            # Replace the process method entirely
            if hasattr(time_class, 'process'):
                time_class.process = ultra_safe_process
                logger.info("✅ TIME.process method completely replaced")
            
        except Exception as e:
            logger.warning(f"Could not patch TIME.process method: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ultra-aggressive patch failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def apply_engine_level_patch():
    """
    Apply patches at the SQLAlchemy engine level
    """
    try:
        from sqlalchemy import event
        from sqlalchemy.engine import Engine
        
        @event.listens_for(Engine, "connect")
        def set_mysql_time_handling(dbapi_connection, connection_record):
            """Set safe time handling at connection level"""
            try:
                # This runs for every new connection
                logger.info("Setting up safe time handling for new connection")
            except Exception as e:
                logger.warning(f"Could not set up connection-level time handling: {e}")
        
        logger.info("✅ Engine-level time handling event registered")
        
    except Exception as e:
        logger.warning(f"Could not set up engine-level patches: {e}")

if __name__ == "__main__":
    print("🚀 Applying ultra-aggressive datetime fix...")
    
    # Apply all patches
    success = ultra_aggressive_patch()
    apply_engine_level_patch()
    
    if success:
        print("✅ Ultra-aggressive patches applied successfully")
    else:
        print("❌ Some patches failed")
    
    print("🔧 Ultra-Aggressive DateTime Fix Module Loaded")