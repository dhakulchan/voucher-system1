#!/usr/bin/env python3
import json
from app import app
from models.booking import Booking
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_booking_55():
    with app.app_context():
        try:
            # Query for booking 55
            booking = Booking.query.filter_by(id=55).first()
            
            if not booking:
                logger.error("❌ Booking 55 not found")
                return
            
            logger.info(f"✅ Found booking: {booking.booking_reference}")
            
            # Update guest_list with clean data
            clean_guest_list = [
                "รายชื่อลูกค้า",
                "คุณสมชาย ใจดี", 
                "คุณสมหญิง สวยงาม",
                "นายจอห์น สมิธ",
                "Mrs. Jane Smith",
                "Mr. Robert Johnson"
            ]
            
            booking.guest_list = json.dumps(clean_guest_list, ensure_ascii=False)
            
            # Update flight_info with clean data
            clean_flight_info = """เที่ยวบิน
TG123 Bangkok (BKK) → Hong Kong (HKG) 08:30 - 12:15
TG456 Hong Kong (HKG) → Bangkok (BKK) 14:30 - 16:45

Airline: Thai Airways International
Confirmation Code: ABC123XYZ"""
            
            booking.flight_info = clean_flight_info
            
            # Update timestamp
            booking.updated_at = datetime.now()
            
            # Save changes
            from app import db
            db.session.commit()
            
            logger.info("✅ Successfully updated booking 55 with clean data")
            
            print("📊 Updated guest list:")
            for guest in clean_guest_list:
                print(f"  - {guest}")
                
            print("\n📊 Updated flight info:")
            print(clean_flight_info)
            
        except Exception as e:
            logger.error(f"❌ Error updating booking: {e}")
            from app import db
            db.session.rollback()

if __name__ == "__main__":
    update_booking_55()