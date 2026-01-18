#!/usr/bin/env python3
"""
Add quote_id and quote_number columns to bookings table
Date: 2025-11-26
"""

import sys
from extensions import db
from app import create_app

def add_quote_columns():
    """Add quote_id and quote_number columns to bookings table"""
    
    app = create_app()
    
    with app.app_context():
        try:
            from sqlalchemy import text
            print("🔧 Adding quote columns to bookings table...")
            
            # Check if columns already exist
            result = db.session.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'bookings' 
                AND COLUMN_NAME IN ('quote_id', 'quote_number')
            """))
            existing_columns = [row[0] for row in result.fetchall()]
            
            if 'quote_id' not in existing_columns:
                # Add quote_id column
                db.session.execute(text("""
                    ALTER TABLE bookings 
                    ADD COLUMN quote_id INT NULL
                """))
                print("✅ Added quote_id column")
                
                # Add foreign key constraint
                db.session.execute(text("""
                    ALTER TABLE bookings 
                    ADD CONSTRAINT fk_bookings_quote 
                        FOREIGN KEY (quote_id) REFERENCES quotes(id) 
                        ON DELETE SET NULL
                """))
                print("✅ Added foreign key constraint")
            else:
                print("ℹ️ quote_id column already exists")
            
            if 'quote_number' not in existing_columns:
                # Add quote_number column
                db.session.execute(text("""
                    ALTER TABLE bookings 
                    ADD COLUMN quote_number VARCHAR(50) NULL
                """))
                print("✅ Added quote_number column")
            else:
                print("ℹ️ quote_number column already exists")
            
            # Commit changes
            db.session.commit()
            print("✅ Database migration completed successfully!")
            
            # Update existing bookings with their latest quote
            print("\n🔄 Updating existing bookings with quote data...")
            result = db.session.execute(text("""
                UPDATE bookings b
                INNER JOIN (
                    SELECT booking_id, id, quote_number
                    FROM quotes
                    WHERE (booking_id, created_at) IN (
                        SELECT booking_id, MAX(created_at)
                        FROM quotes
                        GROUP BY booking_id
                    )
                ) q ON b.id = q.booking_id
                SET b.quote_id = q.id,
                    b.quote_number = q.quote_number
                WHERE b.quote_id IS NULL
            """))
            db.session.commit()
            print(f"✅ Updated {result.rowcount} bookings with quote data")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            sys.exit(1)

if __name__ == '__main__':
    add_quote_columns()
