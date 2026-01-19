from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from models.customer import Customer
# from models.booking import Booking  # Temporarily disabled to avoid datetime processor issues
from models.user import User
from extensions import db
from datetime import datetime, timedelta
from sqlalchemy import func, text

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required  
def index():
    """Dashboard with raw SQL to bypass MariaDB datetime processor issues"""
    
    # Get customer count (works fine)
    total_customers = Customer.query.count()
    
    # Use direct database connection to bypass SQLAlchemy ORM datetime processing
    import pymysql
    try:
        # Direct MySQL connection bypassing SQLAlchemy's datetime processors
        connection = pymysql.connect(
            host='localhost',
            user='voucher_user', 
            password='VoucherSecure2026!',
            database='voucher_enhanced',
            charset='utf8mb4'
        )
        
        with connection.cursor() as cursor:
            # Get booking statistics
            cursor.execute("SELECT COUNT(*) FROM bookings")
            total_bookings = cursor.fetchone()[0]
            
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
            
            # Get recent bookings
            cursor.execute("""
                SELECT b.id, b.booking_reference, b.status, b.customer_id, c.name as customer_name
                FROM bookings b 
                LEFT JOIN customers c ON b.customer_id = c.id
                ORDER BY b.id DESC 
                LIMIT 10
            """)
            recent_bookings_data = cursor.fetchall()
            
            # Convert to simple objects for template
class CustomerDisplay:
    """Simple class to hold customer data for template display"""
    def __init__(self, name):
        self.name = name

class BookingDisplay:
    """Simple class to hold booking data for template display"""
    def __init__(self, booking_code, status, total_amount, currency, created_at, customer_name):
        self.booking_code = booking_code
        self.status = status  
        self.total_amount = total_amount
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
        total_bookings = draft_bookings = pending_bookings = confirmed_bookings = 0
        cancelled_bookings = vouchered_bookings = monthly_revenue = 0
        recent_bookings = []
        booking_types = []
    
    # Use language-specific template
    from flask import session
    current_language = session.get('language', 'en')
    template_name = f'dashboard/index_{current_language}.html'
    
    # Fallback to Thai template if language-specific template doesn't exist
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

@dashboard_bp.route('/customers')
@login_required
def customers():
    """Customer management page"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    
    query = Customer.query
    
    if search:
        query = query.filter(
            Customer.name.contains(search) | 
            Customer.email.contains(search) | 
            Customer.phone.contains(search)
        )
    
    # Use ID instead of created_at to avoid datetime conversion issues  
    try:
        customers = query.order_by(Customer.id.desc()).paginate(
            page=page, per_page=20, error_out=False
        )
    except Exception as e:
        current_app.logger.error(f"Error fetching customers for dashboard: {e}")
        customers = query.order_by(Customer.id.desc()).paginate(
            page=1, per_page=20, error_out=False
        )
    
    return render_template('dashboard/customers.html', 
                         customers=customers, 
                         search=search)

@dashboard_bp.route('/bookings')
@login_required
def bookings():
    """Booking management page"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '', type=str)
    booking_type = request.args.get('type', '', type=str)
    search = request.args.get('search', '', type=str)
    
    query = Booking.query
    
    if status_filter:
        query = query.filter(Booking.status == status_filter)
    
    if booking_type:
        query = query.filter(Booking.booking_type == booking_type)
    
    if search:
        query = query.filter(
            Booking.booking_reference.contains(search)
        )
    
    # Use ID instead of created_at to avoid datetime conversion issues
    try:
        bookings = query.order_by(Booking.id.desc()).paginate(
            page=page, per_page=20, error_out=False
        )
    except Exception as e:
        current_app.logger.error(f"Error fetching bookings for dashboard: {e}")
        bookings = query.order_by(Booking.id.desc()).paginate(
            page=1, per_page=20, error_out=False
        )
    
    return render_template('dashboard/bookings.html', 
                         bookings=bookings, 
                         status_filter=status_filter,
                         booking_type=booking_type,
                         search=search)

@dashboard_bp.route('/reports')
@login_required
def reports():
    """Reports and analytics page"""
    
    # Date range from request or default to last 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    if request.args.get('start_date'):
        start_date = datetime.strptime(request.args.get('start_date'), '%Y-%m-%d')
    if request.args.get('end_date'):
        end_date = datetime.strptime(request.args.get('end_date'), '%Y-%m-%d')
    
    # Bookings by date
    daily_bookings = db.session.query(
        func.date(Booking.created_at).label('date'),
        func.count(Booking.id).label('count'),
        func.sum(Booking.total_amount).label('revenue')
    ).filter(
        Booking.created_at >= start_date,
        Booking.created_at <= end_date
    ).group_by(func.date(Booking.created_at)).all()
    
    # Top customers
    top_customers = db.session.query(
        Customer.name,
        func.count(Booking.id).label('booking_count'),
        func.sum(Booking.total_amount).label('total_spent')
    ).join(Booking).filter(
        Booking.created_at >= start_date,
        Booking.created_at <= end_date
    ).group_by(Customer.id).order_by(
        func.sum(Booking.total_amount).desc()
    ).limit(10).all()
    
    return render_template('dashboard/reports.html',
                         daily_bookings=daily_bookings,
                         top_customers=top_customers,
                         start_date=start_date,
                         end_date=end_date)

@dashboard_bp.route('/api/dashboard-stats')
@login_required
def dashboard_stats():
    """API endpoint for dashboard statistics"""
    
    # Today's stats
    today = datetime.now().date()
    today_bookings = Booking.query.filter(func.date(Booking.created_at) == today).count()
    today_revenue = db.session.query(func.sum(Booking.total_amount)).filter(
        func.date(Booking.created_at) == today,
        Booking.status == 'confirmed'
    ).scalar() or 0
    
    # This week's stats
    week_start = today - timedelta(days=today.weekday())
    week_bookings = Booking.query.filter(Booking.created_at >= week_start).count()
    week_revenue = db.session.query(func.sum(Booking.total_amount)).filter(
        Booking.created_at >= week_start,
        Booking.status == 'confirmed'
    ).scalar() or 0
    
    return jsonify({
        'today': {
            'bookings': today_bookings,
            'revenue': float(today_revenue)
        },
        'this_week': {
            'bookings': week_bookings,
            'revenue': float(week_revenue)
        }
    })
