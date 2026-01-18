#!/usr/bin/env python3
"""
Migration script to add assigned_counter column to users table
"""
from app import app, db
from sqlalchemy import text

def add_assigned_counter_column():
    """Add assigned_counter column to users table"""
    with app.app_context():
        try:
            # Check if column already exists
            result = db.session.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'users' 
                AND COLUMN_NAME = 'assigned_counter'
            """))
            exists = result.scalar() > 0
            
            if exists:
                print("✓ Column 'assigned_counter' already exists")
                return
            
            # Add the column
            print("Adding assigned_counter column to users table...")
            db.session.execute(text("""
                ALTER TABLE users 
                ADD COLUMN assigned_counter INT NULL 
                COMMENT 'Counter number assigned to this user'
            """))
            db.session.commit()
            print("✓ Successfully added assigned_counter column")
            
        except Exception as e:
            db.session.rollback()
            print(f"✗ Error: {e}")
            raise

if __name__ == '__main__':
    print("=" * 50)
    print("Adding assigned_counter to users table")
    print("=" * 50)
    add_assigned_counter_column()
    print("\n✓ Migration completed successfully!")
