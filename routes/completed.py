"""
Completed Bookings routes for listing and managing completed bookings
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models.booking import Booking
from extensions import db
import logging

completed_bp = Blueprint('completed', __name__, url_prefix='/completed')
logger = logging.getLogger(__name__)

@completed_bp.route('/')
@login_required
def list_completed_bookings():
    """List all bookings with status='completed'"""
    try:
        # Get bookings with status 'completed' using raw SQL to avoid datetime issues
        from sqlalchemy import text
        
        query = text("""
            SELECT id, booking_reference, party_name, agency_reference, hotel_name,
                   arrival_date, pickup_time, adults, children, infants,
                   total_amount, status, created_at, updated_at, voucher_image_path,
                   party_code, description, pickup_point, destination
            FROM bookings 
            WHERE status = 'completed' 
            ORDER BY updated_at DESC, id DESC
        """)
        
        result = db.session.execute(query)
        booking_data = result.fetchall()
        
        # Convert to list of dictionaries
        bookings = []
        total_amount = 0
        
        for row in booking_data:
            booking_dict = {
                'id': row[0],
                'booking_reference': row[1],
                'party_name': row[2],  # เปลี่ยนเป็น party_name
                'agency_reference': row[3],
                'hotel_name': row[4],
                'arrival_date': str(row[5]) if row[5] else None,  # Convert to string
                'pickup_time': row[6],
                'adults': row[7] or 0,  # เปลี่ยนเป็น adults
                'children': row[8] or 0,  # เปลี่ยนเป็น children
                'infants': row[9] or 0,
                'total_amount': row[10],
                'status': row[11],
                'created_at': str(row[12]) if row[12] else None,  # Convert to string
                'updated_at': str(row[13]) if row[13] else None,  # Convert to string
                'voucher_image_path': row[14],
                'party_code': row[15],
                'description': row[16],
                'pickup_point': row[17],
                'destination': row[18]
            }
            bookings.append(booking_dict)
            
            # Calculate total amount safely
            if row[10]:  # total_amount
                try:
                    total_amount += float(row[10])
                except (ValueError, TypeError):
                    pass
        
        logger.info(f"Successfully loaded {len(bookings)} completed bookings")
        return render_template('completed/list_bookings.html', 
                             bookings=bookings, 
                             total_completed_amount=total_amount)
                             
    except Exception as e:
        import traceback
        logger.error(f"Error listing completed bookings: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        flash(f'Error loading completed bookings: {str(e)}', 'error')
        return redirect(url_for('dashboard.index'))