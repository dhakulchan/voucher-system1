"""
Migration script to add booking sync fields to invoices table
Adds: quote_number, customer_id, cust_name, booking_type, total_pax, 
      arrival_date, departure_date, guest_list, flight_info
"""
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from sqlalchemy import text

def add_invoice_booking_sync_fields():
    """Add booking sync fields to invoices table"""
    app = create_app()
    
    with app.app_context():
        print("🔄 Adding booking sync fields to invoices table...")
        
        # List of columns to add with their SQL definitions
        columns_to_add = [
            ("quote_number", "VARCHAR(100)", "Quote number from booking"),
            ("customer_id", "INTEGER", "Customer ID reference"),
            ("cust_name", "VARCHAR(255)", "Customer name"),
            ("booking_type", "VARCHAR(50)", "Booking type (tour/hotel/transport)"),
            ("total_pax", "INTEGER", "Total number of passengers"),
            ("arrival_date", "DATE", "Arrival date"),
            ("departure_date", "DATE", "Departure date"),
            ("guest_list", "TEXT", "Guest list (JSON)"),
            ("flight_info", "TEXT", "Flight information")
        ]
        
        for column_name, column_type, description in columns_to_add:
            try:
                # Check if column already exists
                check_query = text(f"""
                    SELECT COUNT(*) 
                    FROM information_schema.COLUMNS 
                    WHERE TABLE_SCHEMA = DATABASE() 
                    AND TABLE_NAME = 'invoices' 
                    AND COLUMN_NAME = '{column_name}'
                """)
                
                result = db.session.execute(check_query)
                exists = result.scalar() > 0
                
                if exists:
                    print(f"⏭️  Column '{column_name}' already exists - skipping")
                    continue
                
                # Add the column
                alter_query = text(f"ALTER TABLE invoices ADD COLUMN {column_name} {column_type}")
                db.session.execute(alter_query)
                db.session.commit()
                print(f"✅ Added column '{column_name}' ({column_type}) - {description}")
                
            except Exception as e:
                print(f"❌ Error adding column '{column_name}': {str(e)}")
                db.session.rollback()
                continue
        
        print("\n✅ Migration completed successfully!")
        print("\nNew fields added to invoices table:")
        print("  - quote_number: Quote number from booking")
        print("  - customer_id: Customer ID reference")
        print("  - cust_name: Customer name")
        print("  - booking_type: Booking type (tour/hotel/transport)")
        print("  - total_pax: Total number of passengers")
        print("  - arrival_date: Arrival date")
        print("  - departure_date: Departure date")
        print("  - guest_list: Guest list (JSON)")
        print("  - flight_info: Flight information")

if __name__ == '__main__':
    add_invoice_booking_sync_fields()
