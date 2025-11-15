#!/usr/bin/env python3
"""
Clear SQLAlchemy cache and force reload booking data
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from models.booking import Booking

app = create_app()

with app.app_context():
    print("🔄 Clearing SQLAlchemy cache...")
    
    # Clear SQLAlchemy session
    db.session.remove()
    
    # Clear metadata cache
    db.metadata.clear()
    
    # Force reload metadata
    db.metadata.reflect(bind=db.engine)
    
    # Test booking 19 data
    print("🔍 Testing booking 19 data after cache clear...")
    
    # Raw SQL test
    raw_result = db.session.execute(db.text("SELECT id, quote_number, quote_id FROM bookings WHERE id = 19")).fetchone()
    if raw_result:
        print(f"📋 Raw SQL: id={raw_result[0]}, quote_number={raw_result[1]}, quote_id={raw_result[2]}")
    
    # SQLAlchemy test
    booking = Booking.query.filter_by(id=19).first()
    if booking:
        print(f"📋 SQLAlchemy: id={booking.id}, quote_number={booking.quote_number}, quote_id={booking.quote_id}")
    
    print("✅ SQLAlchemy cache cleared successfully!")