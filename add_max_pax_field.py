#!/usr/bin/env python3
"""
Add max_pax field to group_buy_campaigns table
(จำนวนผู้เดินทางสูงสุดรวมทั้งหมด - นับจากทุกกลุ่ม)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db

def add_max_pax_field():
    """Add max_pax field"""
    app = create_app()
    
    with app.app_context():
        connection = db.engine.raw_connection()
        cursor = connection.cursor()
        
        print("=" * 80)
        print("Adding max_pax field to group_buy_campaigns table")
        print("=" * 80)
        
        try:
            cursor.execute("""
                ALTER TABLE group_buy_campaigns 
                ADD COLUMN max_pax INT NULL 
                COMMENT 'จำนวนผู้เดินทางสูงสุด (รวมทุกกลุ่ม) - Pax'
            """)
            print("✅ Added max_pax column")
        except Exception as e:
            if 'Duplicate column' in str(e):
                print("⚠️  max_pax column already exists")
            else:
                print(f"❌ Error adding max_pax: {e}")
        
        connection.commit()
        cursor.close()
        connection.close()
        
        print("\n" + "=" * 80)
        print("✅ Migration completed!")
        print("=" * 80)
        print("\nNew field added:")
        print("  • max_pax (INT) - จำนวนผู้เดินทางสูงสุด (Pax)")
        print("=" * 80)

if __name__ == '__main__':
    add_max_pax_field()
