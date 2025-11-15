#!/usr/bin/env python3
"""
Add missing quote_id and invoice_id fields to bookings table
"""
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from sqlalchemy import text

def add_missing_fields():
    """Add missing quote_id and invoice_id fields to bookings table"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if fields already exist
            result = db.session.execute(text("DESCRIBE bookings"))
            columns = [row[0] for row in result.fetchall()]
            
            print("Current bookings table columns:")
            for col in columns:
                print(f"  - {col}")
            
            # Add quote_id if missing
            if 'quote_id' not in columns:
                print("\n➕ Adding quote_id column...")
                db.session.execute(text("ALTER TABLE bookings ADD COLUMN quote_id INT NULL"))
                print("✅ Added quote_id column")
            else:
                print("\n✅ quote_id column already exists")
            
            # Add invoice_id if missing  
            if 'invoice_id' not in columns:
                print("\n➕ Adding invoice_id column...")
                db.session.execute(text("ALTER TABLE bookings ADD COLUMN invoice_id INT NULL"))
                print("✅ Added invoice_id column")
            else:
                print("\n✅ invoice_id column already exists")
            
            db.session.commit()
            print("\n🎉 Migration completed successfully!")
            
            # Show updated table structure
            result = db.session.execute(text("DESCRIBE bookings"))
            columns = [row[0] for row in result.fetchall()]
            
            print("\nUpdated bookings table columns:")
            for col in columns:
                if col in ['quote_id', 'invoice_id']:
                    print(f"  - {col} ✨ (newly added)")
                else:
                    print(f"  - {col}")
                    
        except Exception as e:
            print(f"❌ Error during migration: {e}")
            db.session.rollback()
            return False
            
    return True

if __name__ == '__main__':
    success = add_missing_fields()
    if success:
        print("\n✅ Migration completed successfully!")
        print("You can now use quote_id and invoice_id fields in bookings.")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)