"""
Admin routes for Booking Auto Completion Management
"""

from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_login import login_required, current_user
from services.booking_auto_completion import BookingAutoCompletionService
from datetime import datetime
import logging

# Create blueprint
auto_completion_bp = Blueprint('auto_completion', __name__, url_prefix='/admin/auto-completion')

@auto_completion_bp.route('/')
@login_required
def index():
    """Main auto completion management page"""
    # Check if user has admin privileges (implement your own auth check)
    # if not current_user.is_admin:
    #     flash('Access denied. Admin privileges required.', 'error')
    #     return redirect(url_for('main.index'))
    
    return render_template('admin/auto_completion_dashboard.html')

@auto_completion_bp.route('/preview')
@login_required
def preview():
    """Preview upcoming completions"""
    days = request.args.get('days', 7, type=int)
    
    try:
        candidates = BookingAutoCompletionService.get_completion_candidates(days)
        
        return jsonify({
            'success': True,
            'data': candidates,
            'total_candidates': sum(len(c['bookings']) for c in candidates)
        })
        
    except Exception as e:
        logging.error(f"Error previewing auto completions: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@auto_completion_bp.route('/run', methods=['POST'])
@login_required
def run_completion():
    """Run auto completion process manually"""
    try:
        results = BookingAutoCompletionService.process_auto_completion()
        
        flash(f'Auto completion completed: {results["successful"]} successful, {results["failed"]} failed', 
              'success' if results['failed'] == 0 else 'warning')
        
        return jsonify({
            'success': True,
            'data': results
        })
        
    except Exception as e:
        logging.error(f"Error running auto completion: {str(e)}")
        flash(f'Error running auto completion: {str(e)}', 'error')
        
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@auto_completion_bp.route('/eligible')
@login_required
def eligible_bookings():
    """Get currently eligible bookings"""
    try:
        bookings = BookingAutoCompletionService.get_eligible_bookings()
        
        booking_data = []
        for booking in bookings:
            booking_data.append({
                'id': booking.id,
                'booking_reference': booking.booking_reference,
                'customer_id': booking.customer_id,
                'status': booking.status,
                'departure_date': booking.departure_date.strftime('%Y-%m-%d') if booking.departure_date else None,
                'total_amount': float(booking.total_amount) if booking.total_amount else 0,
                'currency': booking.currency or 'THB'
            })
        
        return jsonify({
            'success': True,
            'data': booking_data,
            'count': len(booking_data)
        })
        
    except Exception as e:
        logging.error(f"Error getting eligible bookings: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@auto_completion_bp.route('/status')
@login_required
def status():
    """Get auto completion system status"""
    try:
        # Get today's eligible bookings
        eligible_today = BookingAutoCompletionService.get_eligible_bookings()
        
        # Get upcoming completions
        upcoming = BookingAutoCompletionService.get_completion_candidates(7)
        
        status_info = {
            'current_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'eligible_today': len(eligible_today),
            'upcoming_7_days': sum(len(c['bookings']) for c in upcoming),
            'system_active': True,  # Could be based on actual system checks
            'last_run': 'Not implemented yet'  # Could store last run timestamp
        }
        
        return jsonify({
            'success': True,
            'data': status_info
        })
        
    except Exception as e:
        logging.error(f"Error getting system status: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500