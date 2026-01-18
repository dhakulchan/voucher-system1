#!/usr/bin/env python3
"""
Direct SQL migration: Add company-related fields to customers and invoices tables
This script runs raw SQL without importing the full app to avoid dependency issues.
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

def add_customer_company_fields():
    """Add company-related fields to customers and invoices tables"""
    conn = get_db_connection()
    
    try:
        with conn.cursor() as cursor:
            print("Adding company fields to customers table...")
            
            # Add fields to customers table
            customer_fields = [
                "ALTER TABLE customers ADD COLUMN type VARCHAR(50) DEFAULT 'Visitor-Individual'",
                "ALTER TABLE customers ADD COLUMN company_name VARCHAR(255) NULL",
                "ALTER TABLE customers ADD COLUMN company_address TEXT NULL",
                "ALTER TABLE customers ADD COLUMN company_tel VARCHAR(50) NULL",
                "ALTER TABLE customers ADD COLUMN company_taxid VARCHAR(50) NULL",
                "ALTER TABLE customers ADD COLUMN company_contact VARCHAR(255) NULL"
            ]
            
            for sql in customer_fields:
                try:
                    cursor.execute(sql)
                    print(f"✓ {sql}")
                except pymysql.err.OperationalError as e:
                    if "Duplicate column name" in str(e):
                        print(f"⚠ Column already exists: {sql}")
                    else:
                        raise
            
            print("\nAdding company fields to invoices table...")
            
            # Add fields to invoices table
            invoice_fields = [
                "ALTER TABLE invoices ADD COLUMN type VARCHAR(50) NULL",
                "ALTER TABLE invoices ADD COLUMN company_name VARCHAR(255) NULL",
                "ALTER TABLE invoices ADD COLUMN company_address TEXT NULL",
                "ALTER TABLE invoices ADD COLUMN company_tel VARCHAR(50) NULL",
                "ALTER TABLE invoices ADD COLUMN company_taxid VARCHAR(50) NULL",
                "ALTER TABLE invoices ADD COLUMN company_contact VARCHAR(255) NULL"
            ]
            
            for sql in invoice_fields:
                try:
                    cursor.execute(sql)
                    print(f"✓ {sql}")
                except pymysql.err.OperationalError as e:
                    if "Duplicate column name" in str(e):
                        print(f"⚠ Column already exists: {sql}")
                    else:
                        raise
            
            conn.commit()
            print("\n✅ Migration completed successfully!")
            print("\nFields added:")
            print("- type: Customer/Company type selection")
            print("- company_name: Company name")
            print("- company_address: Company address")
            print("- company_tel: Company telephone")
            print("- company_taxid: Company tax ID")
            print("- company_contact: Company contact person")
            
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    add_customer_company_fields()
