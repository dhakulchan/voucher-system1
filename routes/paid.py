"""
Paid Bookings routes for listing and managing paid bookings
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models.booking import Booking
from extensions import db
import logging

paid_bp = Blueprint('paid', __name__, url_prefix='/paid')
logger = logging.getLogger(__name__)

@paid_bp.route('/')
@login_required
def list_paid_bookings():
    """List all bookings with status='paid'"""
    try:
        # Get bookings with status 'paid'
        bookings = Booking.query.filter_by(status='paid').order_by(Booking.created_at.desc()).all()
        
        # Calculate total amount safely
        total_amount = 0
        for booking in bookings:
            if booking.total_amount:
                try:
                    total_amount += float(booking.total_amount)
                except (ValueError, TypeError):
                    pass  # Skip invalid amounts
        
        return render_template('paid/list_bookings.html', bookings=bookings, total_paid_amount=total_amount)
    except Exception as e:
        import traceback
        logger.error(f"Error listing paid bookings: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        flash(f'Error loading paid bookings: {str(e)}')
        return redirect(url_for('dashboard.index'))

@paid_bp.route('/receipts')
@login_required
def list_receipts():
    """Alternative route name for receipts"""
    return redirect(url_for('paid.list_paid_bookings'))