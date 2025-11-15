#!/usr/bin/env python3
"""
Verify Quote Number Fix - Check booking 20 quote number
"""
import sys
import os
sys.path.append('.')

from app import create_app
from models.booking import Booking

def verify_quote_number():
    """Verify quote number is properly set"""
    app = create_app()
    
    with app.app_context():
        booking = Booking.query.get(20)
        if not booking:
            print("❌ Booking 20 not found")
            return False
        
        print(f"🔍 Booking {booking.id} - {booking.booking_reference}")
        print(f"Status: {booking.status}")
        print(f"Quote Number: '{booking.quote_number}'")
        
        # Test the quote number logic
        quote_number = booking.quote_number or f'QT{booking.id:06d}'
        print(f"Display Quote Number: {quote_number}")
        
        # Check if it meets the requirement
        if booking.status == 'quoted' and quote_number != 'N/A':
            print("✅ Quote Number Fix: SUCCESS")
            print(f"   - Status is 'quoted' ✅")
            print(f"   - Quote Number is '{quote_number}' (not N/A) ✅")
            return True
        else:
            print("❌ Quote Number Fix: FAILED")
            return False

if __name__ == '__main__':
    verify_quote_number()