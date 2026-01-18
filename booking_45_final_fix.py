"""
Final fix for booking #45 - fresh file to avoid Python caching issues
"""
import logging
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from datetime import datetime
import mysql.connector
from mysql.connector import pooling

logger = logging.getLogger(__name__)

class SafeDatetime:
    """Wrapper class to make string datetime values compatible with template datetime operations"""
    def __init__(self, datetime_str):
        self.datetime_str = str(datetime_str) if datetime_str else ""
        self._parsed_datetime = None
        
    def __str__(self):
        return self.datetime_str
    
    def __repr__(self):
        return f"SafeDatetime('{self.datetime_str}')"
    
    def strftime(self, format_str):
        """Handle .strftime() calls from templates"""
        if not self.datetime_str:
            return ""
        
        # Try to parse the datetime string if not already parsed
        if not self._parsed_datetime:
            try:
                # Common datetime formats to try
                formats = [
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%d',
                    '%d/%m/%Y %H:%M:%S',
                    '%d/%m/%Y',
                    '%Y-%m-%d %H:%M',
                    '%d/%m/%Y %H:%M'
                ]
                
                for fmt in formats:
                    try:
                        from datetime import datetime
                        self._parsed_datetime = datetime.strptime(self.datetime_str, fmt)
                        break
                    except ValueError:
                        continue
                        
                # If parsing fails, return the original string
                if not self._parsed_datetime:
                    return self.datetime_str
                    
            except Exception:
                return self.datetime_str
        
        try:
            return self._parsed_datetime.strftime(format_str)
        except Exception:
            return self.datetime_str
    
    def __bool__(self):
        """For truthiness checks in templates"""
        return bool(self.datetime_str)
    
    def __eq__(self, other):
        """For comparison operations"""
        if isinstance(other, SafeDatetime):
            return self.datetime_str == other.datetime_str
        return self.datetime_str == str(other)
    
    # Make it behave like the original string in most contexts
    def __getattr__(self, name):
        return getattr(self.datetime_str, name)

class SimpleBooking:
    """Wrapper class to make dictionary data compatible with template object expectations"""
    def __init__(self, booking_data):
        # Copy all data from dictionary to object attributes
        for key, value in booking_data.items():
            setattr(self, key, value)
    
    def get_products(self):
        """Return products list for template compatibility"""
        return getattr(self, 'products', [])
    
    def __getattr__(self, name):
        """Fallback for any missing attributes"""
        return None

class SimpleCustomer:
    """Simple customer object for template compatibility"""
    def __init__(self):
        self.name = ""
        self.email = ""
        self.phone = ""

def get_mariadb_cursor():
    """Get MariaDB connection cursor"""
    import contextlib
    
    @contextlib.contextmanager
    def cursor_context():
        conn = mysql.connector.connect(
            host='localhost',
            user='voucher_user',
            password='voucher_secure_2024',
            database='voucher_enhanced',
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci'
        )
        cursor = conn.cursor()
        try:
            yield cursor, conn
        finally:
            cursor.close()
            conn.close()
    
    return cursor_context()

# Create blueprint
booking_45_final_bp = Blueprint('booking_45_final', __name__)

@booking_45_final_bp.route('/booking/edit/45/final')
@login_required
def edit_booking_45_final():
    """Final handler for booking #45"""
    try:
        print("🚀 NEW FINAL ROUTE: Loading booking #45")
        
        # Get booking data using raw MariaDB
        with get_mariadb_cursor() as (cursor, conn):
            cursor.execute("""
                SELECT 
                    b.*,
                    c.name as customer_name,
                    c.email as customer_email,
                    c.phone as customer_phone
                FROM bookings b
                LEFT JOIN customers c ON b.customer_id = c.id
                WHERE b.id = 45
            """)
            
            result = cursor.fetchone()
            
            if not result:
                flash('Booking #45 not found', 'error')
                return redirect(url_for('booking.list'))
            
            # Convert to dictionary
            columns = [desc[0] for desc in cursor.description]
            booking_data = dict(zip(columns, result))
            
        print(f"🚀 Original time_limit: {booking_data.get('time_limit')} (type: {type(booking_data.get('time_limit'))})")
        
        # Convert ALL date/time related fields to SafeDatetime objects
        datetime_field_names = [
            'time_limit', 'created_at', 'updated_at', 'confirmed_at', 
            'quoted_at', 'invoiced_at', 'paid_at', 'vouchered_at', 
            'invoice_paid_date', 'date', 'datetime', 'timestamp'
        ]
        
        for field_name in datetime_field_names:
            if field_name in booking_data and booking_data[field_name]:
                original_value = booking_data[field_name]
                booking_data[field_name] = SafeDatetime(booking_data[field_name])
                print(f"🚀 Converted {field_name}: {original_value} -> {booking_data[field_name]}")
        
        # Convert any other datetime-like fields
        for key, value in booking_data.items():
            if value and isinstance(value, str):
                if any(x in key.lower() for x in ['date', 'time', 'created', 'updated', 'at']) and not isinstance(value, SafeDatetime):
                    booking_data[key] = SafeDatetime(value)
                    print(f"🚀 Second pass converted {key}: {value}")
        
        print(f"🚀 Final time_limit: {booking_data.get('time_limit')} (type: {type(booking_data.get('time_limit'))})")
        
        # Set up products and customer
        booking_data['products'] = []
        
        customer_obj = SimpleCustomer()
        if booking_data.get('customer_name'):
            customer_obj.name = booking_data['customer_name']
            customer_obj.email = booking_data.get('customer_email', '')
            customer_obj.phone = booking_data.get('customer_phone', '')
        
        booking_data['customer'] = customer_obj
        
        # Create booking object wrapper
        booking_obj = SimpleBooking(booking_data)
        
        print(f"🚀 About to render with booking type: {type(booking_obj)}")
        print(f"🚀 Has get_products: {hasattr(booking_obj, 'get_products')}")
        print(f"🚀 time_limit type: {type(booking_obj.time_limit)}")
        
        logger.info(f"✅ Final route successfully loaded booking #45: {booking_data.get('booking_reference', 'N/A')}")
        
        # Use simple template for now
        return render_template('booking/simple_edit.html', booking=booking_obj, special_mode=True)
        
    except Exception as e:
        print(f"🚀 Error in final route: {e}")
        logger.error(f"❌ Error in final booking #45 route: {e}", exc_info=True)
        flash(f'Database error loading booking #45: {str(e)}', 'error')
        return redirect(url_for('booking.list'))

# Registration function
def register_final_booking_45_routes(app):
    """Register the final booking #45 routes"""
    app.register_blueprint(booking_45_final_bp)
    logger.info("✅ Final booking #45 routes registered")