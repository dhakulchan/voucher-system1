"""
MySQL DateTime compatibility fix for SQLAlchemy
Handles string to datetime conversion issues
"""

from sqlalchemy import TypeDecorator, DateTime
from sqlalchemy.dialects.mysql import DATETIME
from datetime import datetime
import dateutil.parser

class MySQLDateTime(TypeDecorator):
    """Custom DateTime type that handles string conversion"""
    
    impl = DATETIME
    cache_ok = True
    
    def process_result_value(self, value, dialect):
        """Convert database value to Python datetime"""
        if value is None:
            return None
        
        if isinstance(value, str):
            try:
                # Parse string datetime to datetime object
                return dateutil.parser.parse(value)
            except (ValueError, TypeError):
                return None
        
        return value
    
    def process_bind_param(self, value, dialect):
        """Convert Python value to database format"""
        if value is None:
            return None
            
        if isinstance(value, str):
            try:
                return dateutil.parser.parse(value)
            except (ValueError, TypeError):
                return None
                
        return value

# Alternative approach using raw SQL queries
def safe_datetime_query(model_class, order_by_field='created_at', limit=10):
    """Safe datetime query that converts strings to datetime"""
    from extensions import db
    from sqlalchemy import text
    
    # Use raw SQL to handle datetime conversion
    table_name = model_class.__tablename__
    query = text(f"""
        SELECT * FROM {table_name} 
        ORDER BY COALESCE({order_by_field}, '1970-01-01') DESC 
        LIMIT :limit
    """)
    
    result = db.session.execute(query, {'limit': limit})
    return result.fetchall()