"""API route for generating secure share URLs"""

from flask import Blueprint, jsonify, request, url_for
from flask_login import login_required, current_user
from models.booking import Booking

api_share_bp = Blueprint('api_share', __name__, url_prefix='/api/share')

# DEPRECATED: This route moved to api_share_enhanced.py for better token management
# @api_share_bp.route('/booking/<int:booking_id>/url', methods=['GET'])
@api_share_bp.route('/booking/<int:booking_id>/url_old', methods=['GET'])
@login_required
def get_secure_share_url(booking_id):
    """Generate secure share URL for booking - LEGACY VERSION"""
    print(f"⚠️ WARNING: Using OLD api_share.py route for booking {booking_id} - should use api_share_enhanced.py instead!")
    # Check if user is authenticated
    if not current_user.is_authenticated:
        return jsonify({
            'success': False,
            'error': 'Authentication required'
        }), 401
    
    booking = Booking.query.get_or_404(booking_id)
    
    # สร้าง secure URL - Use production URL or current request URL
    from config import Config
    
    # Check if we're in development mode
    base_url = request.url_root.rstrip('/')
    current_host = request.headers.get('Host', '').lower()
    
    if hasattr(Config, 'DEVELOPMENT_MODE') and Config.DEVELOPMENT_MODE and 'localhost' in current_host:
        # Development mode: use current localhost URL
        base_url = request.url_root.rstrip('/')
    elif hasattr(Config, 'PUBLIC_BASE_URL') and Config.PUBLIC_BASE_URL:
        # Production mode: use configured public URL
        force_domains = getattr(Config, 'FORCE_HTTPS_DOMAINS', ['service.dhakulchan.net'])
        
        if any(domain in current_host for domain in force_domains):
            base_url = Config.PUBLIC_BASE_URL
        else:
            # Force HTTPS for known production domains
            if base_url.startswith('http://') and any(domain in base_url for domain in force_domains):
                base_url = base_url.replace('http://', 'https://')
    
    secure_url = booking.get_secure_share_url(base_url)
    
    return jsonify({
        'success': True,
        'secure_url': secure_url,
        'share_url': secure_url,  # For compatibility
        'booking_reference': booking.booking_reference,
        'expires_in_days': 30
    })

@api_share_bp.route('/booking/<int:booking_id>/png', methods=['GET'])
@login_required
def get_booking_png_url(booking_id):
    """Generate PNG URL for booking Service Proposal"""
    # Check if user is authenticated
    if not current_user.is_authenticated:
        return jsonify({
            'success': False,
            'error': 'Authentication required'
        }), 401
        
    booking = Booking.query.get_or_404(booking_id)
    
    # สร้าง Service Proposal PNG URL (ไม่ใช่ tour voucher)
    png_url = url_for('booking.generate_booking_png', booking_id=booking_id, _external=True)
    
    return jsonify({
        'success': True,
        'png_url': png_url,
        'booking_reference': booking.booking_reference,
        'type': 'service_proposal'
    })

@api_share_bp.route('/booking/<int:booking_id>/public', methods=['GET'])
@login_required
def get_public_booking_info(booking_id):
    """Generate public share URL and PNG URL for booking"""
    booking = Booking.query.get_or_404(booking_id)
    
    # สร้าง secure public URL - Force HTTPS in production
    base_url = request.url_root.rstrip('/')
    if base_url.startswith('http://') and 'booking.dhakulchan.net' in base_url:
        base_url = base_url.replace('http://', 'https://')
    public_url = booking.get_secure_share_url(base_url)
    
    # สร้าง public PNG URL (ใช้ tour voucher PNG ที่ไม่ต้อง login)
    public_png_url = url_for('booking.generate_service_proposal_png', booking_id=booking_id, _external=True)
    
    return jsonify({
        'success': True,
        'public_url': public_url,
        'public_png_url': public_png_url,
        'booking_reference': booking.booking_reference,
        'type': 'public_share'
    })

@api_share_bp.route('/booking/<int:booking_id>/lock', methods=['POST'])
@login_required
def lock_booking_token(booking_id):
    """Lock the sharing token for a booking to prevent further access"""
    if not current_user.is_authenticated:
        return jsonify({
            'success': False,
            'error': 'Authentication required'
        }), 401
    
    booking = Booking.query.get_or_404(booking_id)
    
    try:
        # Lock token by setting expiry to past date
        from datetime import datetime, timedelta
        booking.share_token_expiry = datetime.utcnow() - timedelta(days=1)
        booking.save()
        
        return jsonify({
            'success': True,
            'message': 'Token locked successfully',
            'booking_id': booking_id
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to lock token: {str(e)}'
        }), 500

@api_share_bp.route('/booking/<int:booking_id>/reset', methods=['POST'])
@login_required
def reset_booking_token(booking_id):
    """Reset the sharing token for a booking with new 120-day expiry"""
    if not current_user.is_authenticated:
        return jsonify({
            'success': False,
            'error': 'Authentication required'
        }), 401
    
    booking = Booking.query.get_or_404(booking_id)
    
    try:
        # Generate new token with departure_date + 120 days expiry
        from datetime import datetime, timedelta
        
        # Reset token (this will generate a new one)
        booking.share_token = None
        booking.share_token_expiry = None
        
        # Force regeneration with new expiry
        new_token = booking.generate_secure_token()
        
        # Calculate new expiry based on departure_date + 120 days
        if booking.departure_date:
            new_expiry = booking.departure_date + timedelta(days=120)
        else:
            new_expiry = datetime.utcnow() + timedelta(days=120)
            
        booking.share_token_expiry = new_expiry
        booking.save()
        
        return jsonify({
            'success': True,
            'message': 'Token reset successfully',
            'booking_id': booking_id,
            'new_expiry': new_expiry.strftime('%Y-%m-%d %H:%M:%S'),
            'new_token': new_token[:12] + '...'  # Only show partial token for security
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to reset token: {str(e)}'
        }), 500
