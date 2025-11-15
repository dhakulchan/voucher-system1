"""
Minimal Test Route for Booking #45 Template
ทดสอบ template โดยใช้ data ง่ายๆ
"""

from flask import Blueprint, render_template
from flask_login import login_required
import logging

logger = logging.getLogger(__name__)

# Create minimal test blueprint
minimal_45_bp = Blueprint('minimal_45', __name__)

class SimpleCustomer:
    """Simple customer object for template"""
    def __init__(self, name=None, email=None, phone=None):
        self.name = name
        self.email = email
        self.phone = phone

@minimal_45_bp.route('/minimal/booking/edit/45')
@login_required
def minimal_edit_booking_45():
    """Minimal test with hardcoded data"""
    try:
        # Create simple test data
        booking_data = {
            'id': 45,
            'booking_reference': 'BK20250930ZBO0',
            'customer_id': 2,
            'adults': 2,
            'children': 1,
            'total_pax': 3,
            'total_amount': '21000',
            'currency': None,
            'created_at': '2025-09-30 07:39:07',
            'updated_at': '2025-09-30 07:53:01',
            'products': []
        }
        
        # Create customer object
        customer = SimpleCustomer()
        customer.name = 'Test Customer'
        customer.email = 'test@example.com'
        customer.phone = '123-456-7890'
        
        booking_data['customer'] = customer
        
        logger.info("✅ Minimal handler - Rendering simple template")
        return render_template('booking/simple_edit.html', booking=booking_data, minimal_mode=True)
        
    except Exception as e:
        logger.error(f"❌ Minimal handler error: {e}", exc_info=True)
        return f"Minimal handler error: {str(e)}", 500

def register_minimal_45_routes(app):
    """Register minimal test routes"""
    app.register_blueprint(minimal_45_bp)
    logger.info("✅ Minimal booking #45 routes registered")

if __name__ == "__main__":
    print("🧪 Minimal Booking #45 Template Test...")
    print("✅ Route: GET /minimal/booking/edit/45")
    print("📋 Hardcoded data - no database required")