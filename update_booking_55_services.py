#!/usr/bin/env python3
"""
Update booking 55 with sample daily_services data
"""
import sys
import os
import json
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import Flask app and models
from app import create_app
from models.booking import Booking
from extensions import db

def update_booking_daily_services():
    """Update booking 55 with sample daily_services"""
    app = create_app()
    
    with app.app_context():
        try:
            # Sample daily services data
            daily_services = [
                {
                    'date': '02/10/2025',
                    'arrival_date': '02/10/2025', 
                    'departure_date': '05/10/2025',
                    'description': 'Hotel Accommodation - Luxury Resort Bangkok',
                    'supplier_name': 'Bangkok Luxury Resort',
                    'service_details': 'Superior Room with Breakfast',
                    'type': 'Accommodation',
                    'service_type': 'Hotel',
                    'room_type': '2 Adults, Superior Room'
                },
                {
                    'date': '03/10/2025',
                    'arrival_date': '03/10/2025',
                    'departure_date': '03/10/2025', 
                    'description': 'City Tour Bangkok with Temple Visit',
                    'supplier_name': 'Amazing Thailand Tours',
                    'service_details': 'Full day city tour including Grand Palace',
                    'type': 'Tour',
                    'service_type': 'Sightseeing',
                    'room_type': '4 Pax'
                },
                {
                    'date': '04/10/2025',
                    'arrival_date': '04/10/2025',
                    'departure_date': '04/10/2025',
                    'description': 'Airport Transfer',
                    'supplier_name': 'VIP Transfer Service', 
                    'service_details': 'Private car from hotel to airport',
                    'type': 'Transfer',
                    'service_type': 'Transportation',
                    'room_type': 'Private Car'
                }
            ]
            
            # Get booking 55
            booking = db.session.get(Booking, 55)
            if not booking:
                print("❌ Booking 55 not found")
                return False
                
            print(f"✅ Found booking: {booking.booking_reference}")
            
            # Update daily_services
            booking.daily_services = json.dumps(daily_services)
            
            # Commit changes
            db.session.commit()
            
            print("✅ Successfully updated booking 55 with daily_services")
            print(f"📊 Added {len(daily_services)} services:")
            for i, service in enumerate(daily_services, 1):
                print(f"   {i}. {service['description']} ({service['type']})")
                
            return True
            
        except Exception as e:
            print(f"❌ Error updating booking: {e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    update_booking_daily_services()