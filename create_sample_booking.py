#!/usr/bin/env python3
"""Create test booking matching the sample image format"""

from app import create_app, db
from models.booking import Booking
from models.customer import Customer
from datetime import datetime, timedelta

def create_sample_format_booking():
    app = create_app()
    
    with app.app_context():
        # Create or get test customer matching sample
        customer = Customer.query.filter_by(name="PMMC MM").first()
        if not customer:
            customer = Customer(
                name="PMMC MM",
                email="pmmc@example.com",
                phone="08123456789",
                address="Sample Address"
            )
            db.session.add(customer)
            db.session.commit()
        
        # Create test booking exactly matching the sample image
        arrival_date = datetime(2025, 10, 11)
        departure_date = datetime(2025, 10, 15)
        
        # Use unique booking reference
        unique_ref = f"BK2025081799AQ"  # Use exact reference from sample
        
        # Check if this booking already exists, update it instead
        existing_booking = Booking.query.filter_by(booking_reference=unique_ref).first()
        if existing_booking:
            # Update existing booking
            existing_booking.description = "26DEC : From Macao Airport To Chimelong Spaceship Hotel (NX995 ETA 14:25)\n29DEC : Pick up Time 11:30am From Chimelong Spaceship Hotel To Grand Lisboa (**Pending Hotel TBD)"
            existing_booking.party_name = "PMC251011-15"
            existing_booking.special_request = "Request new car"
            db.session.commit()
            print(f"✅ Updated existing booking: {existing_booking.booking_reference}")
            return existing_booking
        
        booking = Booking(
            customer_id=customer.id,
            booking_reference=unique_ref,
            booking_type='tour',
            description="26DEC : From Macao Airport To Chimelong Spaceship Hotel (NX995 ETA 14:25)\n29DEC : Pick up Time 11:30am From Chimelong Spaceship Hotel To Grand Lisboa (**Pending Hotel TBD)",
            arrival_date=arrival_date,
            departure_date=departure_date,
            adults=2,
            children=1,
            infants=1,
            total_pax=3,
            party_name="PMC251011-15",
            special_request="Request new car"
        )
        
        db.session.add(booking)
        db.session.commit()
        
        print(f"✅ Sample format booking created: {booking.booking_reference}")
        print(f"   Customer: {customer.name}")
        print(f"   Party Name: {booking.party_name}")
        print(f"   Travel Period: {booking.arrival_date} to {booking.departure_date}")
        print(f"   PAX: {booking.total_pax} (Adult {booking.adults} / Child {booking.children} / Infant {booking.infants})")
        
        return booking

if __name__ == '__main__':
    create_sample_format_booking()
