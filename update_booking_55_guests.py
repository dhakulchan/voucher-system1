#!/usr/bin/env python3
"""
Update booking 55 guest_list with proper Thai characters
"""
import sys
import os
import json

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import Flask app and models
from app import create_app
from models.booking import Booking
from extensions import db

def update_booking_guest_list():
    """Update booking 55 with proper guest_list"""
    app = create_app()
    
    with app.app_context():
        try:
            # Proper guest list data with Thai characters
            guest_list = [
                "รายชื่อลูกค้า",
                "คุณสมชาย ใจดี", 
                "คุณสมหญิง สวยงาม",
                "นายจอห์น สมิธ",
                "Mrs. Jane Smith",
                "Mr. Robert Johnson"
            ]
            
            # Get booking 55
            booking = db.session.get(Booking, 55)
            if not booking:
                print("❌ Booking 55 not found")
                return False
                
            print(f"✅ Found booking: {booking.booking_reference}")
            
            # Update guest_list
            booking.guest_list = json.dumps(guest_list, ensure_ascii=False)
            
            # Commit changes
            db.session.commit()
            
            print("✅ Successfully updated booking 55 with guest_list")
            print(f"📊 Added {len(guest_list)} guests:")
            for i, guest in enumerate(guest_list, 1):
                print(f"   {i}. {guest}")
                
            return True
            
        except Exception as e:
            print(f"❌ Error updating booking: {e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    update_booking_guest_list()