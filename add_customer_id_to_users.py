#!/usr/bin/env python3
"""Add customer_id field to users table"""

from app import app, db
from sqlalchemy import text

with app.app_context():
    try:
        # Check if column already exists
        result = db.session.execute(text("SHOW COLUMNS FROM users LIKE 'customer_id'"))
        if result.fetchone():
            print("✅ customer_id column already exists")
        else:
            print("🔧 Adding customer_id column to users table...")
            db.session.execute(text("""
                ALTER TABLE users 
                ADD COLUMN customer_id INT NULL,
                ADD FOREIGN KEY (customer_id) REFERENCES customers(id)
            """))
            db.session.commit()
            print("✅ customer_id column added successfully")
        
        # Now link existing Customer role users to their customer records
        print("\n🔗 Linking users to customers...")
        result = db.session.execute(text("""
            UPDATE users u
            INNER JOIN customers c ON u.email = c.email
            SET u.customer_id = c.id
            WHERE u.role = 'Customer' AND u.customer_id IS NULL
        """))
        db.session.commit()
        
        print(f"✅ Linked {result.rowcount} users to customer records")
        
        # Verify customer005
        result = db.session.execute(text("""
            SELECT u.id, u.username, u.email, u.customer_id, c.id as actual_customer_id
            FROM users u
            LEFT JOIN customers c ON u.email = c.email
            WHERE u.email = 'customer005@dcts.com'
        """))
        row = result.fetchone()
        if row:
            print(f"\n✅ Verified customer005:")
            print(f"   User ID: {row[0]}")
            print(f"   Username: {row[1]}")
            print(f"   Email: {row[2]}")
            print(f"   Linked customer_id: {row[3]}")
            print(f"   Actual customer_id: {row[4]}")
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
