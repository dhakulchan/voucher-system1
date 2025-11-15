#!/usr/bin/env python3
"""
Update flight info for booking 174 with clear line breaks for testing
"""

import sys
sys.path.insert(0, '/Applications/python/voucher-ro_v1.0')

from app import create_app
from models.booking import Booking
from app import db

def update_flight_info_test():
    """Update flight info with very clear line breaks"""
    
    app = create_app()
    with app.app_context():
        # Get booking 174
        booking = Booking.query.get(174)
        if not booking:
            print("Booking 174 not found!")
            return
        
        print(f"Current flight info: {repr(booking.flight_info)}")
        
        # Set clear test content
        new_flight_info = "Line 1: First flight number\nLine 2: Second flight number\nLine 3: Third flight number"
        
        # Convert to HTML format (like our route would do)
        html_flight_info = new_flight_info.replace('\n', '<br>')
        html_flight_info = f'<p>{html_flight_info}</p>'
        
        print(f"Setting new flight info: {repr(html_flight_info)}")
        
        booking.flight_info = html_flight_info
        db.session.commit()
        
        print("✅ Updated flight info for booking 174")
        print("Test the edit page now!")

if __name__ == '__main__':
    update_flight_info_test()
