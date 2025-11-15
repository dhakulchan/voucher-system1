#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create a test booking with Thai customer name
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models.booking import Booking
from models.customer import Customer  
from app import db
from datetime import datetime, timezone

def create_thai_booking():
    app = create_app()
    
    with app.app_context():
        # Create Thai customer
        thai_customer = Customer(
            name="วันใหม่ ใจดี",  # Required name field
            first_name="วันใหม่",
            last_name="ใจดี", 
            email="wanmai@email.com",
            phone="+66-2-234-5678"
        )
        
        db.session.add(thai_customer)
        db.session.flush()  # Get customer ID
        
        print(f"✅ Created Thai customer: {thai_customer.first_name} {thai_customer.last_name}")
        
        # Create booking
        booking = Booking(
            customer_id=thai_customer.id,
            booking_reference=f"TH{datetime.now().strftime('%Y%m%d%H%M%S')}",
            booking_type="tour",
            adults=2,
            children=1,
            infants=0,
            total_amount=5500.00,
            time_limit=datetime.now(timezone.utc),  # Required field
            internal_note="ทดสอบการจองทัวร์สำหรับลูกค้าไทย",
            admin_notes="Customer prefers Thai communication",
            manager_memos="VIP customer - handle with care"
        )
        
        db.session.add(booking)
        db.session.flush()
        
        print(f"✅ Created booking ID: {booking.id}")
        
        # Add a simple booking without products
        print(f"✅ Booking created without products (will add manually later)")
        
        db.session.commit()
        
        print(f"\n🎯 Test booking created!")
        print(f"   Customer: {thai_customer.first_name} {thai_customer.last_name}")
        print(f"   Email: {thai_customer.email}")
        print(f"   Phone: {thai_customer.phone}")
        print(f"   Booking ID: {booking.id}")
        print(f"   Notes: {booking.internal_note}")
        
        return booking.id

if __name__ == "__main__":
    booking_id = create_thai_booking()
    print(f"\n📋 Now test with: python debug_booking.py {booking_id}")
