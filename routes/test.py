#!/usr/bin/env python3
"""Simple test route for quote number display"""

from flask import Blueprint, render_template, current_app as app
from models.booking import Booking
from extensions import db

# Create test blueprint
test_bp = Blueprint('test', __name__, url_prefix='/test')

@test_bp.route('/booking/<int:id>')
def test_booking_view(id):
    """Test route for booking view without authentication"""
    try:
        # Debug: Check database configuration
        app.logger.info(f"🔍 Starting test route for booking {id}")
        app.logger.info(f"📂 Database URI: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
        
        # Method 1: Simple query
        booking = Booking.query.get_or_404(id)
        app.logger.info(f"📋 Method 1 - Booking {id}: quote_number={booking.quote_number}, quote_id={booking.quote_id}")
        
        # Method 2: Direct SQL query
        result = db.session.execute(db.text("SELECT quote_number, quote_id FROM bookings WHERE id = :id"), {"id": id}).fetchone()
        if result:
            app.logger.info(f"📋 Method 2 - Direct SQL: quote_number={result[0]}, quote_id={result[1]}")
        
        # Method 3: Check all bookings to see if there's data at all
        all_bookings = db.session.execute(db.text("SELECT COUNT(*) FROM bookings")).fetchone()
        app.logger.info(f"📋 Total bookings in database: {all_bookings[0]}")
        
        # Method 4: Check if booking 8 exists at all
        exists = db.session.execute(db.text("SELECT id FROM bookings WHERE id = :id"), {"id": id}).fetchone()
        app.logger.info(f"📋 Booking {id} exists: {exists is not None}")
        
        return render_template('booking/view_en.html', booking=booking)
        
    except Exception as e:
        app.logger.error(f"❌ Test route error: {e}")
        import traceback
        traceback.print_exc()
        return f"Error: {e}", 500