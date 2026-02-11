#!/usr/bin/env python3
"""
Migration Script: Add customer_id to users table
Adds customer_id column and links existing users to their customer records
"""

print("🔧 Adding customer_id column to users table...")

# First, add the column via SQL
import os
import sys

# Change to app directory
os.chdir('/var/www/booking')
sys.path.insert(0, '/var/www/booking')

from app import app, db

with app.app_context():
    # Add column
    try:
        db.session.execute(db.text("""
            ALTER TABLE users 
            ADD COLUMN customer_id INT NULL,
            ADD CONSTRAINT fk_users_customers 
                FOREIGN KEY (customer_id) 
                REFERENCES customers(id)
        """))
        db.session.commit()
        print("✅ customer_id column added successfully")
    except Exception as e:
        if 'Duplicate column name' in str(e):
            print("⚠️  customer_id column already exists")
            db.session.rollback()
        else:
            print(f"❌ Error adding column: {e}")
            db.session.rollback()
            sys.exit(1)
    
    # Link users to customers by email
    print("\n🔗 Linking users to customers...")
    try:
        result = db.session.execute(db.text("""
            UPDATE users u
            INNER JOIN customers c ON u.email = c.email
            SET u.customer_id = c.id
            WHERE u.role = 'Customer' AND u.customer_id IS NULL
        """))
        db.session.commit()
        print(f"✅ Linked {result.rowcount} users to customer records")
    except Exception as e:
        print(f"❌ Error linking users: {e}")
        db.session.rollback()
        sys.exit(1)

print("\n✅ Migration completed successfully!")
