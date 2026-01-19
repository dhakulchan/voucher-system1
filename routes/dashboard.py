from flask import Blueprint, render_template, request, jsonify, current_app, session
from flask_login import login_required, current_user
from models.customer import Customer
from models.user import User
from extensions import db
from datetime import datetime, timedelta
from sqlalchemy import func, text
import pymysql

dashboard_bp = Blueprint('dashboard', __name__)

class CustomerDisplay:
    """Simple class to hold customer data for template display"""
    def __init__(self, name):
        self.name = name

class BookingDisplay:
    """Simple class to hold booking data for template display"""
    def __init__(self, id, booking_reference, status, total_amount, currency, created_at, customer_name):
        self.id = id
        self.booking_code = booking_reference  # Keep booking_code for template compatibility
        self.status = status  
        # Convert total_amount to float for template formatting
        try:
            self.total_amount = float(total_amount or 0)
        except (ValueError, TypeError):
            self.total_amount = 0.0
        self.currency = currency
        # Parse created_at string to datetime for template formatting
        try:
            if isinstance(created_at, str):
                self.created_at = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
            else:
                self.created_at = created_at
        except Exception:
            self.created_at = datetime.now()
        
        # Create customer object for template compatibility
        self.customer = CustomerDisplay(customer_name or 'No Customer')

@dashboard_bp.route('/')
@login_required
def index():
    try:
        # Use direct database connection to bypass SQLAlchemy datetime processor
        connection = pymysql.connect(
            host='localhost',
            user='voucher_user',
            password='VoucherSecure2026!',
            database='voucher_enhanced',
            charset='utf8mb4'
        )
        
        with connection.cursor() as cursor:
            # Total customers
            cursor.execute("SELECT COUNT(*) FROM customers")
            total_customers = cursor.fetchone()[0]
            
            # Total bookings
            cursor.execute("SELECT COUNT(*) FROM bookings")  
            total_bookings = cursor.fetchone()[0]
            
            # Bookings by status
            cursor.execute("SELECT COUNT(*) FROM bookings WHERE status = 'draft'")
            draft_bookings = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM bookings WHERE status = 'pending'")
            pending_bookings = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM bookings WHERE status = 'confirmed'")
            confirmed_bookings = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM bookings WHERE status = 'cancelled'")
            cancelled_bookings = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM bookings WHERE status = 'vouchered'")
            vouchered_bookings = cursor.fetchone()[0]
            
            # Recent bookings with customer names
            cursor.execute("""
                SELECT b.id, b.booking_reference, b.status, b.total_amount, b.currency, b.created_at, c.name as customer_name
                FROM bookings b
                LEFT JOIN customers c ON b.customer_id = c.id
                ORDER BY b.id DESC 
                LIMIT 10
            """)
            recent_bookings_data = cursor.fetchall()
            recent_bookings = [BookingDisplay(*row) for row in recent_bookings_data]
            
            # Monthly revenue
            cursor.execute("""
                SELECT COALESCE(SUM(total_amount), 0) 
                FROM bookings 
                WHERE status = 'confirmed' 
                AND created_at >= DATE_FORMAT(NOW(), '%Y-%m-01')
            """)
            monthly_revenue = cursor.fetchone()[0] or 0
            
            # Booking types distribution  
            cursor.execute("""
                SELECT booking_type, COUNT(*) 
                FROM bookings 
                GROUP BY booking_type
            """)
            booking_types = cursor.fetchall()
            
        connection.close()
        
    except Exception as e:
        current_app.logger.error(f"Database error: {e}")
        # Return minimal dashboard if database fails
        total_customers = 0
        total_bookings = 0
        draft_bookings = 0
        pending_bookings = 0
        confirmed_bookings = 0
        cancelled_bookings = 0
        vouchered_bookings = 0
        recent_bookings = []
        monthly_revenue = 0
        booking_types = []
    
    # Determine template based on user language preference
    user_lang = session.get('language', 'en')
    if user_lang == 'th':
        template_name = 'dashboard/index_th.html'
    else:
        template_name = 'dashboard/index_en.html'
    
    try:
        return render_template(template_name,
                             total_customers=total_customers,
                             total_bookings=total_bookings,
                             draft_bookings=draft_bookings,
                             pending_bookings=pending_bookings,
                             confirmed_bookings=confirmed_bookings,
                             cancelled_bookings=cancelled_bookings,
                             vouchered_bookings=vouchered_bookings,
                             recent_bookings=recent_bookings,
                             monthly_revenue=monthly_revenue,
                             booking_types=booking_types)
    except Exception as e:
        current_app.logger.error(f"Template error: {e}")
        # Fallback to Thai template
        return render_template('dashboard/index_th.html',
                             total_customers=total_customers,
                             total_bookings=total_bookings,
                             draft_bookings=draft_bookings,
                             pending_bookings=pending_bookings,
                             confirmed_bookings=confirmed_bookings,
                             cancelled_bookings=cancelled_bookings,
                             vouchered_bookings=vouchered_bookings,
                             recent_bookings=recent_bookings,
                             monthly_revenue=monthly_revenue,
                             booking_types=booking_types)