#!/usr/bin/env python3
"""
Migration script to add share_token_version column to bookings table
This column is used to track token versions for invalidation when tokens need to be reset
"""

from app import create_app
from extensions import db
from sqlalchemy import text

def add_share_token_version_column():
    """Add share_token_version column to bookings table if it doesn't exist"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if column already exists
            result = db.session.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'bookings' 
                AND COLUMN_NAME = 'share_token_version'
            """))
            exists = result.scalar()
            
            if exists:
                print("✅ Column 'share_token_version' already exists in bookings table")
                return
            
            # Add the column with default value 1
            print("Adding share_token_version column to bookings table...")
            db.session.execute(text("""
                ALTER TABLE bookings 
                ADD COLUMN share_token_version INT NOT NULL DEFAULT 1
            """))
            db.session.commit()
            
            print("✅ Successfully added share_token_version column to bookings table")
            print("   All existing bookings will have share_token_version = 1")
            
        except Exception as e:
            print(f"❌ Error adding column: {e}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    add_share_token_version_column()
