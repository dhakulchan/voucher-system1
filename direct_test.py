#!/usr/bin/env python3

import sys
import os
sys.path.append('/Applications/python/voucher-ro_v1.0')

from app import app, db
from models.booking import Booking

with app.app_context():
    print("🔍 Testing Booking 8 in Flask context")
    
    # Get booking directly
    booking = Booking.query.get(8)
    if booking:
        print(f"✅ Booking found: {booking.id}")
        print(f"   booking_reference: {booking.booking_reference}")
        print(f"   quote_number: {booking.quote_number}")
        print(f"   quote_id: {booking.quote_id}")
        print(f"   quote_status: {booking.quote_status}")
        
        # Check if fields are actually accessible
        try:
            print(f"   Direct access quote_number: '{booking.quote_number}'")
            print(f"   Type of quote_number: {type(booking.quote_number)}")
            print(f"   Is None? {booking.quote_number is None}")
            print(f"   Is empty string? {booking.quote_number == ''}")
            print(f"   Truthiness: {bool(booking.quote_number)}")
        except Exception as e:
            print(f"   ❌ Error accessing quote_number: {e}")
            
        # Refresh and check again
        db.session.refresh(booking)
        print(f"   After refresh quote_number: '{booking.quote_number}'")
        
    else:
        print("❌ Booking 8 not found")
        
    # Check all bookings with quotes
    print("\n📋 All bookings with quotes:")
    bookings = Booking.query.filter(Booking.quote_number.isnot(None)).all()
    for b in bookings:
        print(f"   Booking {b.id}: {b.quote_number} (quote_id={b.quote_id})")
        
    print("✅ Test complete")