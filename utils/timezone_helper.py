"""
Timezone Helper - Thailand Timezone Utilities (UTC+7)
"""
from datetime import datetime
from config import Config
import pytz

def now_thailand():
    """
    Get current datetime in Thailand timezone (Asia/Bangkok, UTC+7)
    Returns timezone-naive datetime for database compatibility
    """
    return datetime.now(Config.TIMEZONE).replace(tzinfo=None)

def to_thailand_time(dt):
    """
    Convert any datetime to Thailand timezone
    If datetime is naive, assumes it's UTC
    Returns timezone-naive datetime
    """
    if dt is None:
        return None
    
    if dt.tzinfo is None:
        # Assume UTC if naive
        dt = pytz.utc.localize(dt)
    
    # Convert to Thailand timezone
    thailand_dt = dt.astimezone(Config.TIMEZONE)
    
    # Return naive datetime for database
    return thailand_dt.replace(tzinfo=None)

def format_thai_datetime(dt, format_str='%d/%m/%Y %H:%M'):
    """
    Format datetime in Thailand timezone
    If datetime is naive, assumes it's UTC (from database)
    """
    if dt is None:
        return ''
    
    if dt.tzinfo is None:
        # Assume UTC if naive (from database)
        dt = pytz.utc.localize(dt)
    
    # Convert to Thailand timezone
    thailand_dt = dt.astimezone(Config.TIMEZONE)
    return thailand_dt.strftime(format_str)

def get_thailand_timestamp():
    """
    Get current timestamp string in Thailand timezone
    Format: YYYYMMDD_HHMMSS
    """
    return now_thailand().strftime('%Y%m%d_%H%M%S')
