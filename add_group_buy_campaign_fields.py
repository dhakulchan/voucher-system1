#!/usr/bin/env python3
"""
Add new fields to group_buy_campaigns table:
- travel_date_from (วันที่เดินทางไป)
- travel_date_to (วันที่เดินทางกลับ)
- product_image (รูปภาพสินค้า)
- Update product_type to support more types
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db

def add_campaign_fields():
    """Add new fields to group_buy_campaigns table"""
    app = create_app()
    
    with app.app_context():
        connection = db.engine.raw_connection()
        cursor = connection.cursor()
        
        print("=" * 80)
        print("Adding new fields to group_buy_campaigns table")
        print("=" * 80)
        
        # 1. Add travel_date_from
        try:
            cursor.execute("""
                ALTER TABLE group_buy_campaigns 
                ADD COLUMN travel_date_from DATE NULL 
                COMMENT 'วันที่เดินทางไป'
            """)
            print("✅ Added travel_date_from column")
        except Exception as e:
            if 'Duplicate column' in str(e):
                print("⚠️  travel_date_from column already exists")
            else:
                print(f"❌ Error adding travel_date_from: {e}")
        
        # 2. Add travel_date_to
        try:
            cursor.execute("""
                ALTER TABLE group_buy_campaigns 
                ADD COLUMN travel_date_to DATE NULL 
                COMMENT 'วันที่เดินทางกลับ'
            """)
            print("✅ Added travel_date_to column")
        except Exception as e:
            if 'Duplicate column' in str(e):
                print("⚠️  travel_date_to column already exists")
            else:
                print(f"❌ Error adding travel_date_to: {e}")
        
        # 3. Add product_image
        try:
            cursor.execute("""
                ALTER TABLE group_buy_campaigns 
                ADD COLUMN product_image VARCHAR(500) NULL 
                COMMENT 'Path to product image (1:1 ratio)'
            """)
            print("✅ Added product_image column")
        except Exception as e:
            if 'Duplicate column' in str(e):
                print("⚠️  product_image column already exists")
            else:
                print(f"❌ Error adding product_image: {e}")
        
        connection.commit()
        cursor.close()
        connection.close()
        
        print("\n" + "=" * 80)
        print("✅ Migration completed successfully!")
        print("=" * 80)
        print("\nNew fields added:")
        print("  • travel_date_from (DATE) - วันที่เดินทางไป")
        print("  • travel_date_to (DATE) - วันที่เดินทางกลับ")
        print("  • product_image (VARCHAR) - รูปภาพสินค้า (1:1)")
        print("\nProduct types now support:")
        print("  • Package")
        print("  • Tour")
        print("  • Collective Groups")
        print("  • Air Ticket")
        print("  • Hotel")
        print("  • Transport")
        print("  • Park Ticket")
        print("  • F.I.T.")
        print("  • Others")
        print("=" * 80)

if __name__ == '__main__':
    add_campaign_fields()
