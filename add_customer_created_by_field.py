#!/usr/bin/env python3
"""
Migration: Add created_by field to customers table for tracking user ownership
Required for Internship and Freelance role filtering
"""

import pymysql
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_db_connection():
    """Create database connection from environment variables"""
    return pymysql.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'voucher_user'),
        password=os.getenv('DB_PASSWORD', 'voucher_secure_2024'),
        database=os.getenv('DB_NAME', 'voucher_enhanced'),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def add_customer_created_by_field():
    """Add created_by field to customers table"""
    conn = get_db_connection()
    
    try:
        with conn.cursor() as cursor:
            print("Adding created_by field to customers table...")
            
            # Check if column already exists
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = %s 
                AND TABLE_NAME = 'customers' 
                AND COLUMN_NAME = 'created_by'
            """, (os.getenv('DB_NAME', 'voucher_enhanced'),))
            
            has_created_by = cursor.fetchone()['count'] > 0
            
            if not has_created_by:
                sql = """
                    ALTER TABLE customers 
                    ADD COLUMN created_by INT NULL,
                    ADD CONSTRAINT fk_customers_created_by 
                    FOREIGN KEY (created_by) REFERENCES users(id) 
                    ON DELETE SET NULL
                """
                cursor.execute(sql)
                print(f"✓ {sql}")
            else:
                print("⚠ Column 'created_by' already exists in customers table")
            
            conn.commit()
            print("\n✅ Migration completed successfully!")
            print("Field 'created_by' added to customers table for user tracking")
            
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    add_customer_created_by_field()
