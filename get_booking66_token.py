#!/usr/bin/env python3

from app import create_app
from models.booking import Booking

# Create app context
app = create_app()

with app.app_context():
    print("=== Getting public token for Booking 66 ===")
    
    # Get booking 66
    booking = Booking.query.get(66)
    if booking:
        print(f"Found booking: {booking.booking_reference}")
        
        # Try to get the share token
        try:
            token = booking.generate_secure_token()
            print(f"Share token: {token}")
            print(f"Public URL: http://localhost:5000/public/booking/{token}")
        except Exception as e:
            print(f"Error getting share token: {e}")
    else:
        print("Booking 66 not found")