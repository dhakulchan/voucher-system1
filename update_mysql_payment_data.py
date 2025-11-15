#!/usr/bin/env python3
"""
Update Booking #9 payment information in MySQL database
"""

import sys
import os
sys.path.append('/Applications/python/voucher-ro_v1.0')

from app import create_app
from models.booking import Booking
from extensions import db
from datetime import date
from decimal import Decimal

def update_mysql_payment_data():
    """Update payment data in MySQL database"""
    app = create_app()
    
    with app.app_context():
        print("=== UPDATING BOOKING #9 PAYMENT DATA IN MYSQL ===")
        
        try:
            # Get booking #9
            booking = Booking.query.get(9)
            if not booking:
                print("❌ Booking #9 not found in MySQL")
                return
                
            print(f"✅ Found booking #9: Status={booking.status}, Is_Paid={booking.is_paid}")
            
            # Update payment fields
            booking.bank_received = "กสิกรไทย"
            booking.received_date = date(2025, 9, 27)
            booking.received_amount = Decimal('3500.00')
            booking.product_type = "Tour Package"
            booking.notes = "Payment received and confirmed"
            
            # Commit changes
            db.session.commit()
            print("✅ Payment data updated successfully!")
            
            # Verify the update
            booking = Booking.query.get(9)
            print(f"\n=== VERIFICATION ===")
            print(f"Bank Received: {booking.bank_received}")
            print(f"Received Date: {booking.received_date}")
            print(f"Received Amount: {booking.received_amount}")
            print(f"Product Type: {booking.product_type}")
            print(f"Notes: {booking.notes}")
            
        except Exception as e:
            print(f"❌ Error updating MySQL: {e}")
            db.session.rollback()

if __name__ == "__main__":
    update_mysql_payment_data()