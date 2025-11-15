#!/usr/bin/env python3
"""
Update booking 55 flight_info with proper format
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import Flask app and models
from app import create_app
from models.booking import Booking
from extensions import db

def update_booking_flight_info():
    """Update booking 55 with proper flight_info"""
    app = create_app()
    
    with app.app_context():
        try:
            # Proper flight info data
            flight_info = """เที่ยวบิน
TG123 Bangkok (BKK) → Hong Kong (HKG) 08:30 - 12:15
TG456 Hong Kong (HKG) → Bangkok (BKK) 14:30 - 16:45

Airline: Thai Airways International
Confirmation Code: ABC123XYZ"""
            
            # Get booking 55
            booking = db.session.get(Booking, 55)
            if not booking:
                print("❌ Booking 55 not found")
                return False
                
            print(f"✅ Found booking: {booking.booking_reference}")
            
            # Update flight_info
            booking.flight_info = flight_info
            
            # Commit changes
            db.session.commit()
            
            print("✅ Successfully updated booking 55 with flight_info")
            print(f"📊 Flight info:")
            print(flight_info)
                
            return True
            
        except Exception as e:
            print(f"❌ Error updating booking: {e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    update_booking_flight_info()