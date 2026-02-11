#!/usr/bin/env python3
"""
Add user_id field to customers table
"""
from extensions import db
from sqlalchemy import text

def add_user_id_field():
    """Add user_id column to customers table"""
    try:
        # Add user_id column
        db.session.execute(text("""
            ALTER TABLE customers 
            ADD COLUMN user_id INT NULL,
            ADD CONSTRAINT fk_customers_user_id 
            FOREIGN KEY (user_id) REFERENCES users(id),
            ADD UNIQUE INDEX idx_customers_user_id (user_id)
        """))
        db.session.commit()
        print("✓ Added user_id field to customers table")
        return True
    except Exception as e:
        db.session.rollback()
        if "Duplicate column name" in str(e) or "Duplicate key name" in str(e):
            print("✓ user_id field already exists")
            return True
        else:
            print(f"✗ Error adding user_id field: {e}")
            return False

if __name__ == '__main__':
    from app import app
    with app.app_context():
        add_user_id_field()
