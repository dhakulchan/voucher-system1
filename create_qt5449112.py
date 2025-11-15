#!/usr/bin/env python3
"""Create test quote with QT5449112 to test sequence"""

from app import create_app, db
from models.quote import Quote
from models.booking import Booking

app = create_app()

with app.app_context():
    print("🔍 Creating test quote with QT5449112")
    
    # Create a new quote with QT5449112 to establish the new sequence
    try:
        # Check if booking 8 exists
        booking = Booking.query.get(8)
        if not booking:
            print("❌ Booking 8 not found")
            exit(1)
        
        # Create new quote with manual quote number
        from datetime import datetime, timedelta
        
        test_quote = Quote(
            booking_id=8,
            quote_number="QT5449112",
            title="Test Quote Starting New Sequence",
            subtotal=10000,
            total_amount=10000,
            status="draft",
            valid_until=datetime.utcnow() + timedelta(days=30)  # Add valid_until
        )
        
        db.session.add(test_quote)
        db.session.commit()
        
        print(f"✅ Created quote: {test_quote.quote_number} (ID: {test_quote.id})")
        
        # Now test generation of next quote
        next_quote = Quote(booking_id=8)
        next_number = next_quote._generate_quote_number()
        print(f"📋 Next generated quote number: {next_number}")
        
        print("\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.session.rollback()
        import traceback
        traceback.print_exc()