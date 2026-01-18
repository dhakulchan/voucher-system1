#!/usr/bin/env python3
"""
Migration: Add company-related fields to customers table and invoices table
- type (Visitor-Individual, Corporate-Company, Travel Agent)
- company_name
- company_address
- company_tel
- company_taxid
- company_contact
"""

from app import app
from extensions import db
from sqlalchemy import text

def add_customer_company_fields():
    """Add company-related fields to customers and invoices tables"""
    with app.app_context():
        try:
            # Get connection
            conn = db.engine.connect()
            trans = conn.begin()
            
            print("Adding company fields to customers table...")
            
            # Add fields to customers table
            customer_fields = [
                "ALTER TABLE customers ADD COLUMN IF NOT EXISTS type VARCHAR(50) DEFAULT 'Visitor-Individual'",
                "ALTER TABLE customers ADD COLUMN IF NOT EXISTS company_name VARCHAR(255) NULL",
                "ALTER TABLE customers ADD COLUMN IF NOT EXISTS company_address TEXT NULL",
                "ALTER TABLE customers ADD COLUMN IF NOT EXISTS company_tel VARCHAR(50) NULL",
                "ALTER TABLE customers ADD COLUMN IF NOT EXISTS company_taxid VARCHAR(50) NULL",
                "ALTER TABLE customers ADD COLUMN IF NOT EXISTS company_contact VARCHAR(255) NULL"
            ]
            
            for sql in customer_fields:
                try:
                    conn.execute(text(sql))
                    print(f"✓ {sql}")
                except Exception as e:
                    print(f"⚠ Warning: {sql}")
                    print(f"  Error: {e}")
            
            print("\nAdding company fields to invoices table...")
            
            # Add fields to invoices table
            invoice_fields = [
                "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS type VARCHAR(50) NULL",
                "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS company_name VARCHAR(255) NULL",
                "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS company_address TEXT NULL",
                "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS company_tel VARCHAR(50) NULL",
                "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS company_taxid VARCHAR(50) NULL",
                "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS company_contact VARCHAR(255) NULL"
            ]
            
            for sql in invoice_fields:
                try:
                    conn.execute(text(sql))
                    print(f"✓ {sql}")
                except Exception as e:
                    print(f"⚠ Warning: {sql}")
                    print(f"  Error: {e}")
            
            trans.commit()
            print("\n✅ Migration completed successfully!")
            print("\nFields added:")
            print("- type: Customer/Company type selection")
            print("- company_name: Company name")
            print("- company_address: Company address")
            print("- company_tel: Company telephone")
            print("- company_taxid: Company tax ID")
            print("- company_contact: Company contact person")
            
        except Exception as e:
            trans.rollback()
            print(f"\n❌ Migration failed: {e}")
            raise
        finally:
            conn.close()

if __name__ == '__main__':
    add_customer_company_fields()
