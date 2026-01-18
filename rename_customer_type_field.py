#!/usr/bin/env python3
"""
Direct SQL migration: Rename 'type' to 'customer_type' in customers table
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

def rename_customer_type_field():
    """Rename type field to customer_type in customers table"""
    conn = get_db_connection()
    
    try:
        with conn.cursor() as cursor:
            print("Renaming 'type' to 'customer_type' in customers table...")
            
            # Check if old column exists
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = %s 
                AND TABLE_NAME = 'customers' 
                AND COLUMN_NAME = 'type'
            """, (os.getenv('DB_NAME', 'voucher_enhanced'),))
            
            has_type = cursor.fetchone()['count'] > 0
            
            # Check if new column exists
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = %s 
                AND TABLE_NAME = 'customers' 
                AND COLUMN_NAME = 'customer_type'
            """, (os.getenv('DB_NAME', 'voucher_enhanced'),))
            
            has_customer_type = cursor.fetchone()['count'] > 0
            
            if has_type and not has_customer_type:
                # Rename column
                sql = "ALTER TABLE customers CHANGE COLUMN type customer_type VARCHAR(50) DEFAULT 'Visitor-Individual'"
                cursor.execute(sql)
                print(f"✓ {sql}")
            elif has_customer_type:
                print("⚠ Column 'customer_type' already exists")
            elif not has_type:
                # Create new column if neither exists
                sql = "ALTER TABLE customers ADD COLUMN customer_type VARCHAR(50) DEFAULT 'Visitor-Individual'"
                cursor.execute(sql)
                print(f"✓ {sql}")
            
            conn.commit()
            print("\n✅ Migration completed successfully!")
            print("Field 'type' renamed to 'customer_type' in customers table")
            
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    rename_customer_type_field()
