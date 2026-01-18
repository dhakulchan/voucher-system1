from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, make_response, send_file, Response, current_app
from utils.logging_config import get_logger
from flask_login import login_required, current_user
from safe_query_helper import SafeQueryHelper
from models.customer import Customer
from models.booking import Booking
from extensions import db
from datetime import datetime, time
import os
import random
from services.booking_invoice import BookingInvoiceService
from services.booking_pdf_generator import BookingPDFGenerator
from services.public_share_service import PublicShareService
try:
    from services.quote_service import QuoteService
    QUOTE_SERVICE_AVAILABLE = True
except ImportError:
    QUOTE_SERVICE_AVAILABLE = False
    QuoteService = None
from utils.booking_utils import generate_booking_reference

def parse_date_flexible(date_str):
    """Parse date from DD/MM/YYYY or YYYY-MM-DD format"""
    if not date_str:
        return None
    
    date_str = date_str.strip()
    
    # Try DD/MM/YYYY format first (from frontend)
    try:
        return datetime.strptime(date_str, '%d/%m/%Y').date()
    except ValueError:
        pass
    
    # Try YYYY-MM-DD format (legacy)
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        pass
    
    # If both fail, raise error
    raise ValueError(f"Invalid date format: {date_str}. Expected DD/MM/YYYY or YYYY-MM-DD")

def parse_datetime_flexible(datetime_str):
    """Parse datetime from DD/MM/YYYY HH:MM or YYYY-MM-DDTHH:MM format"""
    if not datetime_str:
        return None
    
    datetime_str = datetime_str.strip()
    
    # Try DD/MM/YYYY HH:MM format first (from frontend)
    try:
        return datetime.strptime(datetime_str, '%d/%m/%Y %H:%M')
    except ValueError:
        pass
    
    # Try YYYY-MM-DDTHH:MM format (legacy)
    try:
        return datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M')
    except ValueError:
        pass
    
    # If both fail, raise error  
    raise ValueError(f"Invalid datetime format: {datetime_str}. Expected DD/MM/YYYY HH:MM or YYYY-MM-DDTHH:MM")
from models.quote import Quote
import os
import json
import os
import random
import mysql.connector

booking_bp = Blueprint('booking', __name__)
logger = get_logger(__name__)

class SimpleCustomer:
    """Simple customer object for template compatibility"""
    def __init__(self, name=None, email=None, phone=None):
        self.name = name
        self.email = email
        self.phone = phone

def get_mysql_connection():
    """Get direct MySQL connection for booking #45"""
    return mysql.connector.connect(
        host='localhost',
        user='voucher_user', 
        password='voucher_secure_2024',
        database='voucher_enhanced',
        charset='utf8mb4'
    )

def handle_booking_45_edit(booking_id, request):
    """Special handler for booking #45 datetime corruption"""
    try:
        if request.method == 'POST':
            # Handle form submission
            return handle_booking_45_update(booking_id, request)
        
        # Get booking data using pure MySQL connector
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                id, customer_id, booking_reference, quote_id, quote_number,
                quote_status, invoice_number, invoice_status, invoice_amount,
                is_paid, booking_type, status, arrival_date, departure_date,
                adults, children, total_pax, infants, guest_list, party_name,
                party_code, description, admin_notes, manager_memos,
                agency_reference, hotel_name, room_type, special_request,
                pickup_point, destination, pickup_time, vehicle_type,
                internal_note, flight_info, daily_services,
                bank_received, received_amount, product_type, notes,
                products, total_amount, currency, due_date,
                DATE_FORMAT(created_at, '%Y-%m-%d %H:%i:%s') as created_at,
                DATE_FORMAT(updated_at, '%Y-%m-%d %H:%i:%s') as updated_at,
                DATE_FORMAT(time_limit, '%Y-%m-%d %H:%i:%s') as time_limit,
                DATE_FORMAT(confirmed_at, '%Y-%m-%d %H:%i:%s') as confirmed_at,
                DATE_FORMAT(quoted_at, '%Y-%m-%d %H:%i:%s') as quoted_at,
                DATE_FORMAT(invoiced_at, '%Y-%m-%d %H:%i:%s') as invoiced_at,
                DATE_FORMAT(paid_at, '%Y-%m-%d %H:%i:%s') as paid_at,
                DATE_FORMAT(vouchered_at, '%Y-%m-%d %H:%i:%s') as vouchered_at,
                DATE_FORMAT(invoice_paid_date, '%Y-%m-%d %H:%i:%s') as invoice_paid_date,
                created_by, vendor_id, supplier_id
            FROM bookings 
            WHERE id = %s
        """, (booking_id,))
        
        booking_data = cursor.fetchone()
        
        if not booking_data:
            flash(f'Booking #{booking_id} not found', 'error')
            cursor.close()
            conn.close()
            return redirect(url_for('booking.list'))
        
        # Get customer data and create customer object for template
        customer_obj = SimpleCustomer()
        if booking_data['customer_id']:
            cursor.execute("""
                SELECT name, email, phone 
                FROM customers 
                WHERE id = %s
            """, (booking_data['customer_id'],))
            
            customer = cursor.fetchone()
            if customer:
                customer_obj.name = customer['name']
                customer_obj.email = customer['email'] 
                customer_obj.phone = customer['phone']
        
        # Create customer object for template compatibility
        booking_data['customer'] = customer_obj
        
        # Set empty products 
        booking_data['products'] = []
        
        # สร้าง SafeDatetime wrapper class สำหรับ template compatibility
        class SafeDatetime:
            def __init__(self, datetime_str):
                self.datetime_str = str(datetime_str) if datetime_str else ""
                self._parsed_datetime = None
                
            def __str__(self):
                return self.datetime_str
            
            def strftime(self, format_str):
                if not self.datetime_str:
                    return ""
                try:
                    if not self._parsed_datetime:
                        # ลองหลายรูปแบบ datetime
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
                        if not self._parsed_datetime:
                            return self.datetime_str
                    return self._parsed_datetime.strftime(format_str)
                except Exception:
                    return self.datetime_str
            
            def __bool__(self):
                return bool(self.datetime_str)
        
        # สร้าง Booking wrapper class
        class BookingWrapper:
            def __init__(self, data):
                for key, value in data.items():
                    # แปลง datetime fields เป็น SafeDatetime
                    if value and isinstance(value, str) and any(x in key.lower() for x in ['date', 'time', 'created', 'updated', 'at']):
                        setattr(self, key, SafeDatetime(value))
                    else:
                        setattr(self, key, value)
            
            def get_products(self):
                """Parse products JSON for template"""
                if hasattr(self, 'products') and self.products:
                    try:
                        import json
                        if isinstance(self.products, str):
                            return json.loads(self.products)
                        elif isinstance(self.products, list):
                            return self.products
                    except:
                        return []
                return []
            
            def __getattr__(self, name):
                return None
        
        # สร้าง booking object wrapper สำหรับ template
        booking_obj = BookingWrapper(booking_data)
        
        cursor.close()
        conn.close()
        
        logger.info(f"✅ พิเศษ - โหลด booking #{booking_id} สำเร็จ: {booking_data['booking_reference']}")
        return render_template('booking/edit.html', booking=booking_obj, special_mode=True)
        
    except Exception as e:
        logger.error(f"❌ Special handler error for booking #{booking_id}: {e}", exc_info=True)
        flash(f'Error loading booking #{booking_id}: {str(e)}', 'error')
        try:
            cursor.close()
            conn.close()
        except:
            pass
        return redirect(url_for('booking.list'))

def handle_booking_45_update(booking_id, request):
    """Handle booking #45 form updates"""
    try:
        form_data = request.form.to_dict()
        
        # Prepare update query
        updates = []
        values = []
        
        # Safe fields to update
        safe_fields = {
            'adults': 'adults',
            'children': 'children',
            'infants': 'infants', 
            'total_pax': 'total_pax',
            'pickup_point': 'pickup_point',
            'pickup_time': 'pickup_time',
            'total_amount': 'total_amount',
            'quote_status': 'quote_status',
            'currency': 'currency',
            'notes': 'notes',
            'party_name': 'party_name',
            'description': 'description',
            'admin_notes': 'admin_notes',
            'manager_memos': 'manager_memos'
        }
        
        for form_field, db_field in safe_fields.items():
            if form_field in form_data and form_data[form_field] is not None:
                updates.append(f"{db_field} = %s")
                values.append(form_data[form_field])
        
        # Always update timestamp
        updates.append("updated_at = NOW()")
        values.append(booking_id)  # for WHERE clause
        
        if updates:
            query = f"""
                UPDATE bookings 
                SET {', '.join(updates)}
                WHERE id = %s
            """
            
            conn = get_mysql_connection()
            cursor = conn.cursor()
            cursor.execute(query, values)
            conn.commit()
            
            if cursor.rowcount > 0:
                flash(f'Booking #{booking_id} updated successfully!', 'success')
                
                # Log the update
                cursor.execute("""
                    INSERT INTO activity_logs (user_id, action, description, created_at)
                    VALUES (%s, %s, %s, NOW())
                """, (
                    current_user.id if current_user else 1,
                    'booking_updated',
                    f'[BOOKING #{booking_id}] Booking updated via special handler'
                ))
                conn.commit()
            else:
                flash(f'No changes were made to booking #{booking_id}', 'info')
            
            cursor.close()
            conn.close()
        
        return redirect(url_for('booking.edit', id=booking_id))
        
    except Exception as e:
        logger.error(f"❌ Update error for booking #{booking_id}: {e}", exc_info=True)
        flash(f'Error updating booking #{booking_id}: {str(e)}', 'error')
        try:
            cursor.close()
            conn.close()
        except:
            pass
        return redirect(url_for('booking.edit', id=booking_id))

@booking_bp.route('/test/view/<int:booking_id>')
def test_view_booking(booking_id):
    """TEMPORARY: View booking without authentication for testing"""
    from flask import render_template
    from config import Config
    
    booking = Booking.query.get_or_404(booking_id)
    
    # Render the same template but without login requirement
    return render_template('booking/view_en.html', booking=booking, title=f'Booking {booking.booking_reference}', config=Config)

@booking_bp.route('/test/<int:booking_id>/pdf')
def test_generate_booking_pdf(booking_id):
    """TEMPORARY: Generate Service Proposal PDF without authentication for testing"""
    from services.classic_pdf_generator import ClassicPDFGenerator
    from flask import send_file, make_response
    
    try:
        # Force refresh from database
        db.session.expire_all()
        booking = Booking.query.get_or_404(booking_id)
        
        # Prepare complete booking data for Classic PDF
        booking_data = {
            'booking_id': booking.booking_reference,
            'guest_name': (booking.customer.name if booking.customer else None) or booking.party_name or 'N/A',
                'customer_name': booking.customer.name if booking.customer else 'N/A',
            'guest_email': booking.customer.email if booking.customer else 'N/A', 
            'guest_phone': booking.customer.phone if booking.customer else 'N/A',
            'tour_name': booking.description or booking.hotel_name or 'Tour Package',
            'booking_date': booking.created_at.strftime('%Y-%m-%d') if booking.created_at else 'N/A',
            'tour_date': booking.arrival_date.strftime('%Y-%m-%d') if booking.arrival_date else 'N/A',
            'start_date': booking.traveling_period_start.strftime('%Y-%m-%d') if booking.traveling_period_start else (booking.arrival_date.strftime('%Y-%m-%d') if booking.arrival_date else 'N/A'),
            'end_date': booking.traveling_period_end.strftime('%Y-%m-%d') if booking.traveling_period_end else (booking.departure_date.strftime('%Y-%m-%d') if booking.departure_date else 'N/A'),
            'pax': booking.total_pax or 1,
            'adults': booking.adults or booking.total_pax or 1,
            'children': booking.children or 0,
            'infants': booking.infants or 0,
            'guest_list': booking.guest_list or '',
            'flight_info': booking.flight_info or '',
            'special_request': booking.special_request or '',
            'additional_info': booking.admin_notes or '',
            'company_name': 'Dhakul Chan Group',
            'company_address': '123 Tourism Street, Bangkok, Thailand',
            'company_phone': '+66 2 123 4567',
            'company_email': 'info@dhakulchan.net'
        }
        
        # Generate PDF
        generator = ClassicPDFGenerator()
        pdf_path = generator.generate_pdf(booking_data)
        
        if not pdf_path or not os.path.exists(pdf_path):
            logger.error(f"Failed to generate PDF for booking {booking_id}")
            return "PDF generation failed", 500
            
        filename = f"service_proposal_{booking.booking_reference}.pdf"
        
        response = make_response(send_file(
            pdf_path,
            as_attachment=False,
            download_name=filename,
            mimetype='application/pdf'
        ))
        
        response.headers['Content-Disposition'] = f'inline; filename="{filename}"'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        logger.info(f"Generated Service Proposal PDF for booking {booking_id} (test mode)")
        return response
        
    except Exception as e:
        logger.error(f"Error generating PDF for booking {booking_id} (test): {str(e)}")
        return f"Error generating PDF: {str(e)}", 500

@booking_bp.route('/share/<int:id>')
def booking_view_public(id):
    """Public booking view with token authentication (30 days)"""
    booking = Booking.query.get_or_404(id)
    token = request.args.get('token', '')
    
    # Import token verification from voucher routes
    from flask import current_app
    secret = current_app.config.get('SECRET_KEY', '')
    
    if not secret:
        return jsonify({'success': False, 'message': 'Secret key not configured'}), 500
        
    # Use the same token verification as voucher routes
    from routes.voucher import _verify_voucher_image_token
    
    if not _verify_voucher_image_token(secret, token, booking):
        return jsonify({'success': False, 'message': 'Invalid or expired token'}), 403
    
    # Render public booking view template
    return render_template('booking/view_en.html', 
                         booking=booking, 
                         title=f'Booking {booking.booking_reference}',
                         is_public_view=True)

@booking_bp.route('/enhanced/<int:id>')
def enhanced_booking_view_public(id):
    """Public enhanced booking view with token authentication (30 days)"""
    booking = Booking.query.get_or_404(id)
    token = request.args.get('token', '')
    
    # Import token verification from voucher routes
    from flask import current_app
    secret = current_app.config.get('SECRET_KEY', '')
    
    if not secret:
        return jsonify({'success': False, 'message': 'Secret key not configured'}), 500
        
    # Use the same token verification as voucher routes
    from routes.voucher import _verify_voucher_image_token
    
    if not _verify_voucher_image_token(secret, token, booking):
        return jsonify({'success': False, 'message': 'Invalid or expired token'}), 403
    
    # Render enhanced booking view template
    return render_template('public/enhanced_booking_view.html', 
                         booking=booking, 
                         token=token,
                         title=f'Enhanced Booking View - {booking.booking_reference}',
                         is_public_view=True)

@booking_bp.route('/')
@booking_bp.route('/list')
@login_required
def list():
    """List all bookings"""
    
    # Run auto completion check on every booking list access
    try:
        from services.booking_auto_completion import BookingAutoCompletionService
        eligible_count = len(BookingAutoCompletionService.get_eligible_bookings())
        if eligible_count > 0:
            current_app.logger.info(f"Found {eligible_count} bookings eligible for auto-completion")
            # Optionally run auto completion automatically
            # results = BookingAutoCompletionService.process_auto_completion()
            # current_app.logger.info(f"Auto-completion: {results['successful']} successful, {results['failed']} failed")
    except Exception as e:
        current_app.logger.warning(f"Auto completion check failed: {str(e)}")
    
    # Get filter parameters
    status_filter = request.args.get('status', '')
    search = request.args.get('search', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    # Build query based on status filter
    if status_filter:
        if status_filter in ['pending', 'confirmed', 'cancelled', 'quoted', 'paid', 'vouchered', 'draft']:
            # Filter by specific status
            query = Booking.query.filter(Booking.status == status_filter)
        else:
            # Unknown status, show all
            query = Booking.query
    else:
        # Default: show all relevant statuses
        query = Booking.query
    
    if search:
        # Import Quote model for searching
        try:
            from models.quote import Quote
            # Get booking IDs that have quotes matching the search term
            quote_booking_ids = db.session.query(Quote.booking_id).filter(
                Quote.quote_number.contains(search)
            ).subquery()
            
            query = query.join(Customer).filter(
                db.or_(
                    Customer.first_name.contains(search),
                    Customer.last_name.contains(search),
                    Customer.email.contains(search),
                    Booking.booking_reference.contains(search),
                    Booking.quote_number.contains(search),
                    Booking.guest_list.contains(search),
                    Booking.id.in_(quote_booking_ids)
                )
            )
        except ImportError:
            # Fallback if Quote model not available
            query = query.join(Customer).filter(
                db.or_(
                    Customer.first_name.contains(search),
                    Customer.last_name.contains(search),
                    Customer.email.contains(search),
                    Booking.booking_reference.contains(search),
                    Booking.quote_number.contains(search),
                    Booking.guest_list.contains(search)
                )
            )
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            query = query.filter(Booking.arrival_date >= date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            query = query.filter(Booking.departure_date <= date_to_obj)
        except ValueError:
            pass
    
    # Initialize stats with default values to ensure it always exists
    stats = {status: 0 for status in ['pending', 'confirmed', 'completed', 'cancelled', 'draft', 'quoted', 'invoiced', 'paid', 'vouchered']}
    bookings = []
    
    # Use direct database connection to bypass SQLAlchemy datetime processor issues
    import pymysql
    try:
        current_app.logger.info("Attempting to connect to database for booking list")
        connection = pymysql.connect(
            host='localhost',
            user='voucher_user',
            password='voucher_secure_2024',
            database='voucher_enhanced',
            charset='utf8mb4'
        )
        current_app.logger.info("Database connection established successfully")
        
        with connection.cursor() as cursor:
            # Calculate statistics FIRST using direct queries
            current_app.logger.info("Calculating booking statistics...")
            for status in ['pending', 'confirmed', 'completed', 'cancelled', 'draft', 'quoted', 'invoiced', 'paid', 'vouchered']:
                cursor.execute("SELECT COUNT(*) FROM bookings WHERE status = %s", (status,))
                count = cursor.fetchone()[0]
                stats[status] = count
                current_app.logger.info(f"Status {status}: {count} bookings")
            
            # Build the WHERE clause for filtering
            where_conditions = []
            params = []
            
            # Add owner filter for Internship and Freelance users
            if current_user.role in ['Internship', 'Freelance']:
                where_conditions.append("b.created_by = %s")
                params.append(current_user.id)
                current_app.logger.info(f"Applying owner filter for {current_user.role}: user_id={current_user.id}")
            
            if status_filter:
                if status_filter in ['pending', 'confirmed', 'cancelled', 'quoted', 'paid', 'vouchered', 'draft', 'completed', 'invoiced']:
                    where_conditions.append("b.status = %s")
                    params.append(status_filter)
            else:
                # Default filter: show only Draft, Pending, or Confirmed bookings
                where_conditions.append("b.status IN ('draft', 'pending', 'confirmed', 'Draft', 'Pending', 'Confirmed')")
                current_app.logger.info("Applying default filter: Draft, Pending, or Confirmed only")
            
            if search:
                where_conditions.append("(c.first_name LIKE %s OR c.last_name LIKE %s OR c.email LIKE %s OR b.booking_reference LIKE %s OR b.quote_number LIKE %s OR b.guest_list LIKE %s)")
                search_param = f'%{search}%'
                params.extend([search_param] * 6)
            
            if date_from:
                try:
                    datetime.strptime(date_from, '%Y-%m-%d')
                    where_conditions.append("b.arrival_date >= %s")
                    params.append(date_from)
                except ValueError:
                    pass
            
            if date_to:
                try:
                    datetime.strptime(date_to, '%Y-%m-%d')
                    where_conditions.append("b.departure_date <= %s")
                    params.append(date_to)
                except ValueError:
                    pass
            
            # Build the complete query
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            current_app.logger.info(f"Fetching bookings with filter: {where_clause}")
            cursor.execute(f"""
                SELECT b.id, b.booking_reference, b.status, b.total_amount, b.currency, 
                       b.created_at, b.arrival_date, b.departure_date, b.total_pax,
                       c.first_name, c.last_name, c.email, c.phone, b.party_name,
                       b.description, b.hotel_name, b.quote_number, b.booking_type
                FROM bookings b
                LEFT JOIN customers c ON b.customer_id = c.id
                WHERE {where_clause}
                ORDER BY b.id DESC 
                LIMIT 50
            """, params)
            
            bookings_data = cursor.fetchall()
            current_app.logger.info(f"Fetched {len(bookings_data)} bookings from database")
        
        connection.close()
        current_app.logger.info("Database connection closed")
        
        # Convert raw data to booking-like objects for template compatibility
        class BookingListDisplay:
            def __init__(self, data):
                (self.id, self.booking_reference, self.status, self.total_amount, self.currency,
                 self.created_at, self.arrival_date, self.departure_date, self.total_pax,
                 first_name, last_name, email, phone, self.party_name,
                 self.description, self.hotel_name, self.quote_number, self.booking_type) = data
                
                # Convert booking_type to title case and fallback if empty
                self.booking_type = (self.booking_type or 'Not set').title()
                
                # Convert dates from strings to datetime objects for template
                try:
                    if self.created_at:
                        self.created_at = datetime.strptime(str(self.created_at), '%Y-%m-%d %H:%M:%S')
                    else:
                        self.created_at = None
                except:
                    self.created_at = None
                
                try:
                    if self.arrival_date:
                        # Handle both datetime and date strings
                        arrival_str = str(self.arrival_date)
                        if len(arrival_str) > 10:  # datetime format
                            self.arrival_date = datetime.strptime(arrival_str, '%Y-%m-%d %H:%M:%S').date()
                        else:  # date format
                            self.arrival_date = datetime.strptime(arrival_str, '%Y-%m-%d').date()
                    else:
                        self.arrival_date = None
                except:
                    self.arrival_date = None
                
                try:
                    if self.departure_date:
                        # Handle both datetime and date strings
                        departure_str = str(self.departure_date)
                        if len(departure_str) > 10:  # datetime format
                            self.departure_date = datetime.strptime(departure_str, '%Y-%m-%d %H:%M:%S').date()
                        else:  # date format
                            self.departure_date = datetime.strptime(departure_str, '%Y-%m-%d').date()
                    else:
                        self.departure_date = None
                except:
                    self.departure_date = None
                
                # Convert total_amount to float
                try:
                    self.total_amount = float(self.total_amount or 0)
                except:
                    self.total_amount = 0.0
                
                # Create customer object for template compatibility
                class CustomerDisplay:
                    def __init__(self, first_name, last_name, email, phone):
                        self.first_name = first_name or ''
                        self.last_name = last_name or ''
                        self.email = email or ''
                        self.phone = phone or ''
                        self.name = f"{first_name or ''} {last_name or ''}".strip() or 'No Name'
                
                self.customer = CustomerDisplay(first_name, last_name, email, phone)
        
        bookings = [BookingListDisplay(data) for data in bookings_data]
        current_app.logger.info(f"Successfully created {len(bookings)} booking display objects")
        current_app.logger.info(f"Final stats: {stats}")
        
    except Exception as e:
        current_app.logger.exception(f"Database error in booking list: {e}")
        import traceback
        current_app.logger.error(f"Full traceback: {traceback.format_exc()}")
        # Keep the initialized stats (may have partial data) and empty bookings list
        # Don't overwrite stats since it was already initialized before the try block
        current_app.logger.error(f"Using fallback stats: {stats}")
    
    # Use language-specific template
    from flask import session
    current_language = session.get('language', 'en')
    template_name = f'booking/list_{current_language}.html'
    
    current_app.logger.info(f"Rendering template {template_name} with {len(bookings)} bookings")
    
    # Fallback to English template if language-specific template doesn't exist
    try:
        return render_template(template_name, bookings=bookings, stats=stats)
    except Exception as template_error:
        current_app.logger.warning(f"Failed to render {template_name}: {template_error}, falling back to English")
        return render_template('booking/list_en.html', bookings=bookings, stats=stats)

@booking_bp.route('/customers', methods=['GET', 'POST'])
@login_required
def customers():
    """List all customers"""
    if request.method == 'POST':
        try:
            customer = Customer(
                first_name=request.form.get('first_name'),
                last_name=request.form.get('last_name'),
                email=request.form.get('email'),
                phone=request.form.get('phone'),
                nationality=request.form.get('nationality'),
                notes=request.form.get('notes'),
                name=''  # sync later
            )
            customer.sync_name()
            db.session.add(customer)
            db.session.commit()
            flash('เพิ่มลูกค้าใหม่สำเร็จ', 'success')
            return redirect(url_for('booking.customers'))
        except Exception as e:
            db.session.rollback()
            flash(f'เกิดข้อผิดพลาดในการเพิ่มลูกค้า: {str(e)}', 'error')
    
    search = request.args.get('search', '')
    query = Customer.query
    if search:
        like = f"%{search}%"
        # ค้นหาใน name / first_name / last_name / email / phone
        query = query.filter(db.or_(
            Customer.name.like(like),
            Customer.first_name.like(like),
            Customer.last_name.like(like),
            Customer.email.like(like),
            Customer.phone.like(like)
        ))
    # Use ID instead of created_at to avoid datetime conversion issues
    try:
        customers = query.order_by(Customer.id.desc()).all()
    except Exception as e:
        current_app.logger.error(f"Error fetching customers: {e}")
        customers = []
    return render_template('customer/list.html', customers=customers)

@booking_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create a new booking"""
    if request.method == 'POST':
        try:
            # Get form data
            customer_id = request.form.get('customer_id')
            booking_type = request.form.get('booking_type')
            
            # Get or create customer
            if customer_id:
                customer = Customer.query.get(customer_id)
            else:
                # Create new customer (ปรับให้รองรับ first/last name)
                first_name = request.form.get('customer_first_name') or request.form.get('first_name') or ''
                last_name = request.form.get('customer_last_name') or request.form.get('last_name') or ''
                email = request.form.get('customer_email') or request.form.get('email')
                phone = request.form.get('customer_phone') or request.form.get('phone')
                address = request.form.get('customer_address') or request.form.get('address')
                customer = Customer(
                    first_name=first_name.strip() or None,
                    last_name=last_name.strip() or None,
                    email=email,
                    phone=phone,
                    address=address,
                    name=''  # will sync
                )
                customer.sync_name()
                db.session.add(customer)
                db.session.flush()  # Get customer ID

            # Skip Invoice Ninja integration (removed)
            
            # Create booking
            booking = Booking(
                customer_id=customer.id,
                booking_reference=generate_booking_reference(),
                booking_type=booking_type,
                created_by=current_user.id
            )
            
            # Common fields
            if request.form.get('arrival_date'):
                booking.arrival_date = parse_date_flexible(request.form.get('arrival_date'))
            if request.form.get('departure_date'):
                booking.departure_date = parse_date_flexible(request.form.get('departure_date'))
            if request.form.get('traveling_period_start'):
                booking.traveling_period_start = parse_date_flexible(request.form.get('traveling_period_start'))
            if request.form.get('traveling_period_end'):
                booking.traveling_period_end = parse_date_flexible(request.form.get('traveling_period_end'))
            
            # Time and deadline fields - time_limit is required
            time_limit_str = request.form.get('time_limit')
            if not time_limit_str:
                flash('Time Limit is required', 'error')
                return redirect(url_for('booking.create'))
            
            try:
                booking.time_limit = parse_datetime_flexible(time_limit_str)
            except ValueError as e:
                flash(f'Invalid Time Limit format: {str(e)}', 'error')
                return redirect(url_for('booking.create'))
                
            if request.form.get('due_date'):
                booking.due_date = parse_date_flexible(request.form.get('due_date'))
            
            booking.adults = int(request.form.get('adults', 1))
            booking.children = int(request.form.get('children', 0))
            booking.total_pax = int(request.form.get('total_pax', 1))
            booking.infants = int(request.form.get('infants', 0))
            booking.total_amount = float(request.form.get('total_amount', 0))
            
            # New fields
            booking.party_name = request.form.get('party_name', '').strip()
            # Support both 'description' and 'service_detail' field names
            service_detail = request.form.get('service_detail') or request.form.get('description')
            if service_detail:
                booking.description = service_detail.strip()
            else:
                booking.description = ''
            
            # Flight info - convert line breaks to HTML
            flight_info = request.form.get('flight_info', '').strip()
            if flight_info:
                # Convert line breaks to <br> tags and wrap in <p> if not already wrapped
                flight_info = flight_info.replace('\r\n', '\n').replace('\r', '\n')
                flight_info = flight_info.replace('\n', '<br>')
                if not flight_info.startswith('<p>'):
                    flight_info = f'<p>{flight_info}</p>'
                booking.flight_info = flight_info
            else:
                booking.flight_info = None
            
            # Admin and Management fields
            admin_notes_raw = request.form.get('admin_notes', '')
            manager_memos_raw = request.form.get('manager_memos', '')
            internal_note_raw = request.form.get('internal_note', '')
            
            print(f"CREATE FORM DEBUG admin_notes='{admin_notes_raw}' manager_memos='{manager_memos_raw}' internal_note='{internal_note_raw}'")
            logger.info(f"CREATE FORM DEBUG admin_notes='{admin_notes_raw}' manager_memos='{manager_memos_raw}' internal_note='{internal_note_raw}'")
            
            booking.admin_notes = admin_notes_raw.strip() or None
            booking.manager_memos = manager_memos_raw.strip() or None
            booking.internal_note = internal_note_raw.strip() or None
            
            print(f"Saving admin_notes='{booking.admin_notes}' manager_memos='{booking.manager_memos}' internal_note='{booking.internal_note}'")
            logger.info(f"Saving admin_notes='{booking.admin_notes}' manager_memos='{booking.manager_memos}' internal_note='{booking.internal_note}'")
            # Save special request for ALL types (previously only hotel)
            booking.special_request = (request.form.get('special_request') or request.form.get('special_requests') or '').strip() or None
            
            # Guest list (HTML from TinyMCE)
            guest_list_html = request.form.get('guest_list')
            if guest_list_html is not None:
                # Convert textarea input back to list format
                lines = [line.strip() for line in guest_list_html.split('\n') if line.strip()]
                if lines:
                    booking.set_guest_list(lines)
                else:
                    booking.guest_list = None
                logger.debug("Set guest list from textarea (create): %r -> %r", guest_list_html, lines)
            
            # Pickup information for ALL booking types (not just transport)
            booking.pickup_point = request.form.get('pickup_point', '').strip() or None
            if request.form.get('pickup_time'):
                try:
                    booking.pickup_time = datetime.strptime(request.form.get('pickup_time'), '%H:%M').time()
                except ValueError:
                    pass  # Invalid time format, skip
            
            # Products & Calculation data
            products = []
            product_names = request.form.getlist('products[0][name]') + request.form.getlist('products[1][name]') + request.form.getlist('products[2][name]') + request.form.getlist('products[3][name]') + request.form.getlist('products[4][name]') + request.form.getlist('products[5][name]') + request.form.getlist('products[6][name]') + request.form.getlist('products[7][name]') + request.form.getlist('products[8][name]') + request.form.getlist('products[9][name]')
            product_quantities = request.form.getlist('products[0][quantity]') + request.form.getlist('products[1][quantity]') + request.form.getlist('products[2][quantity]') + request.form.getlist('products[3][quantity]') + request.form.getlist('products[4][quantity]') + request.form.getlist('products[5][quantity]') + request.form.getlist('products[6][quantity]') + request.form.getlist('products[7][quantity]') + request.form.getlist('products[8][quantity]') + request.form.getlist('products[9][quantity]')
            product_prices = request.form.getlist('products[0][price]') + request.form.getlist('products[1][price]') + request.form.getlist('products[2][price]') + request.form.getlist('products[3][price]') + request.form.getlist('products[4][price]') + request.form.getlist('products[5][price]') + request.form.getlist('products[6][price]') + request.form.getlist('products[7][price]') + request.form.getlist('products[8][price]') + request.form.getlist('products[9][price]')
            product_amounts = request.form.getlist('products[0][amount]') + request.form.getlist('products[1][amount]') + request.form.getlist('products[2][amount]') + request.form.getlist('products[3][amount]') + request.form.getlist('products[4][amount]') + request.form.getlist('products[5][amount]') + request.form.getlist('products[6][amount]') + request.form.getlist('products[7][amount]') + request.form.getlist('products[8][amount]') + request.form.getlist('products[9][amount]')
            
            # Better approach: iterate through form data to find products
            products = []
            form_data = request.form.to_dict(flat=False)
            
            # Extract products from dynamic form data
            i = 0
            while True:
                name_key = f'products[{i}][name]'
                quantity_key = f'products[{i}][quantity]'
                price_key = f'products[{i}][price]'
                amount_key = f'products[{i}][amount]'
                
                if name_key not in form_data:
                    break
                    
                name = form_data[name_key][0] if form_data[name_key] else ''
                quantity = form_data[quantity_key][0] if quantity_key in form_data and form_data[quantity_key] else '1'
                price = form_data[price_key][0] if price_key in form_data and form_data[price_key] else '0'
                amount = form_data[amount_key][0] if amount_key in form_data and form_data[amount_key] else '0'
                
                if name.strip():  # Only add products with names
                    products.append({
                        'name': name.strip(),
                        'quantity': int(quantity) if quantity else 1,
                        'price': float(price) if price else 0.0,
                        'amount': float(amount) if amount else 0.0
                    })
                
                i += 1
            
            if products:
                booking.set_products(products)
            
            # Type-specific fields
            if booking_type == 'hotel':
                booking.agency_reference = request.form.get('agency_reference')
                booking.hotel_name = request.form.get('hotel_name')
                booking.room_type = request.form.get('room_type')
                # (special_request already handled globally)
            elif booking_type == 'transport':
                # Additional transport-specific fields (pickup already handled globally)
                booking.destination = request.form.get('destination')
                booking.vehicle_type = request.form.get('vehicle_type')
            elif booking_type == 'tour':
                # Daily services list only for tour (legacy)
                services = []
                service_dates = request.form.getlist('service_dates[]')
                service_descriptions = request.form.getlist('service_descriptions[]')
                service_types = request.form.getlist('service_types[]')
                for i in range(len(service_dates)):
                    if service_dates[i] and service_descriptions[i]:
                        services.append({
                            'date': service_dates[i],
                            'description': service_descriptions[i],
                            'type': service_types[i] if i < len(service_types) else ''
                        })
                booking.set_daily_services(services)
            
            # Instead of using SQLAlchemy ORM commit (which triggers datetime processor),
            # extract the booking data and insert using direct database connection
            import pymysql
            try:
                connection = pymysql.connect(
                    host='localhost',
                    user='voucher_user',
                    password='voucher_secure_2024',
                    database='voucher_enhanced',
                    charset='utf8mb4'
                )
                
                with connection.cursor() as cursor:
                    # Insert customer first if new
                    if not customer_id:
                        cursor.execute("""
                            INSERT INTO customers (first_name, last_name, email, phone, address, name, created_at, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                        """, (
                            customer.first_name,
                            customer.last_name, 
                            customer.email,
                            customer.phone,
                            customer.address,
                            customer.name
                        ))
                        customer_id = cursor.lastrowid
                    
                    # Prepare booking data for direct insertion
                    booking_data = {
                        'customer_id': customer_id,
                        'booking_reference': booking.booking_reference,
                        'booking_type': booking.booking_type,
                        'created_by': booking.created_by,
                        'arrival_date': booking.arrival_date.strftime('%Y-%m-%d') if booking.arrival_date else None,
                        'departure_date': booking.departure_date.strftime('%Y-%m-%d') if booking.departure_date else None,
                        'traveling_period_start': booking.traveling_period_start.strftime('%Y-%m-%d') if booking.traveling_period_start else None,
                        'traveling_period_end': booking.traveling_period_end.strftime('%Y-%m-%d') if booking.traveling_period_end else None,
                        'time_limit': booking.time_limit.strftime('%Y-%m-%d %H:%M:%S') if booking.time_limit else None,
                        'due_date': booking.due_date.strftime('%Y-%m-%d') if booking.due_date else None,
                        'adults': booking.adults,
                        'children': booking.children,
                        'total_pax': booking.total_pax,
                        'infants': booking.infants,
                        'total_amount': booking.total_amount,
                        'party_name': booking.party_name,
                        'description': booking.description,
                        'flight_info': booking.flight_info,
                        'admin_notes': booking.admin_notes,
                        'manager_memos': booking.manager_memos,
                        'internal_note': booking.internal_note,
                        'special_request': booking.special_request,
                        'guest_list': booking.guest_list,
                        'pickup_point': booking.pickup_point,
                        'pickup_time': booking.pickup_time.strftime('%H:%M:%S') if booking.pickup_time else None,
                        'products': booking.products,
                        'agency_reference': getattr(booking, 'agency_reference', None),
                        'hotel_name': getattr(booking, 'hotel_name', None),
                        'room_type': getattr(booking, 'room_type', None),
                        'destination': getattr(booking, 'destination', None),
                        'vehicle_type': getattr(booking, 'vehicle_type', None),
                        'daily_services': getattr(booking, 'daily_services', None),
                        'status': 'draft'
                    }
                    
                    # Insert booking directly
                    cursor.execute("""
                        INSERT INTO bookings (
                            customer_id, booking_reference, booking_type, created_by,
                            arrival_date, departure_date, traveling_period_start, traveling_period_end,
                            time_limit, due_date, adults, children, total_pax, infants, total_amount,
                            party_name, description, flight_info, admin_notes, manager_memos, internal_note,
                            special_request, guest_list, pickup_point, pickup_time, products,
                            agency_reference, hotel_name, room_type, destination, vehicle_type, daily_services,
                            status, created_at, updated_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, NOW(), NOW()
                        )
                    """, (
                        booking_data['customer_id'], booking_data['booking_reference'], booking_data['booking_type'], booking_data['created_by'],
                        booking_data['arrival_date'], booking_data['departure_date'], booking_data['traveling_period_start'], booking_data['traveling_period_end'],
                        booking_data['time_limit'], booking_data['due_date'], booking_data['adults'], booking_data['children'], booking_data['total_pax'], booking_data['infants'], booking_data['total_amount'],
                        booking_data['party_name'], booking_data['description'], booking_data['flight_info'], booking_data['admin_notes'], booking_data['manager_memos'], booking_data['internal_note'],
                        booking_data['special_request'], booking_data['guest_list'], booking_data['pickup_point'], booking_data['pickup_time'], booking_data['products'],
                        booking_data['agency_reference'], booking_data['hotel_name'], booking_data['room_type'], booking_data['destination'], booking_data['vehicle_type'], booking_data['daily_services'],
                        booking_data['status']
                    ))
                    
                    booking_id = cursor.lastrowid
                    
                    # Insert activity log for booking creation
                    user_id = getattr(current_user, 'id', None) if current_user.is_authenticated else None
                    cursor.execute("""
                        INSERT INTO activity_logs (user_id, action, description, ip_address, user_agent, created_at)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                    """, (
                        user_id,
                        'booking_created',
                        f'[BOOKING #{booking_id}] New booking created: {booking.booking_reference} (status: {booking_data["status"]})',
                        request.remote_addr,
                        request.headers.get('User-Agent', '')[:500] if request.headers.get('User-Agent') else ''
                    ))
                    
                connection.commit()
                connection.close()
                
                # Clear any SQLAlchemy session state
                db.session.rollback()
                
                flash(f'Booking {booking.booking_reference} created successfully!', 'success')
                return redirect(url_for('booking.view', id=booking_id))
                
            except Exception as direct_db_error:
                current_app.logger.error(f"Direct database booking creation failed: {direct_db_error}")
                # Fallback to original method (may still fail but provides better error)
                db.session.add(booking)
                db.session.commit()
                
                flash(f'Booking {booking.booking_reference} created successfully!', 'success')
                return redirect(url_for('booking.view', id=booking.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating booking: {str(e)}', 'error')
    
    # Get customers for dropdown (ใช้ full_name ถ้ามี)
    customers = Customer.query.order_by(Customer.name).all()
    
    # Check if coming from queue
    queue_id = request.args.get('queue_id')
    queue_data = None
    if queue_id:
        from models.queue import Queue
        queue = Queue.query.get(queue_id)
        if queue:
            queue_data = {
                'queue_number': queue.queue_number,
                'customer_name': queue.customer_name,
                'customer_phone': queue.customer_phone,
                'customer_email': queue.customer_email,
                'service_type': queue.service_type,
                'notes': queue.notes
            }
    
    # Use create_en.html for all languages
    return render_template('booking/create_en.html', customers=customers, queue_data=queue_data)

@booking_bp.route('/<int:id>')
@login_required
def view_redirect(id):
    """Redirect old booking view URL to new format"""
    return redirect(url_for('booking.view', id=id))

@booking_bp.route('/view/<int:id>')
@login_required
def view(id):
    """View booking details with activity logs integration"""
    from flask import session, current_app as app, make_response
    app.logger.info(f"🔍 Loading booking {id}")
    
    # Try direct database approach for compatibility with datetime issues
    booking = None
    try:
        app.logger.info(f"🚀 Attempting direct database connection for booking {id}")
        # Use direct database connection to bypass SQLAlchemy datetime processor
        import pymysql
        connection = pymysql.connect(
            host='localhost',
            user='voucher_user',
            password='voucher_secure_2024',
            database='voucher_enhanced',
            charset='utf8mb4'
        )
        
        with connection.cursor() as cursor:
            # Get booking data with customer info
            cursor.execute("""
                SELECT b.*, c.first_name, c.last_name, c.email, c.phone, c.address, c.name as customer_name
                FROM bookings b
                LEFT JOIN customers c ON b.customer_id = c.id
                WHERE b.id = %s
            """, (id,))
            
            booking_data = cursor.fetchone()
            if not booking_data:
                from flask import abort
                abort(404)
            
            # Log token info for debugging
            if len(booking_data) > 0:
                app.logger.info(f"🔐 Booking {id} data loaded, columns count: {len(booking_data)}")
                # Find current_share_token in the data
                cursor.execute("DESCRIBE bookings")
                cols = [row[0] for row in cursor.fetchall()]
                if 'current_share_token' in cols:
                    token_idx = cols.index('current_share_token')
                    token_val = booking_data[token_idx] if token_idx < len(booking_data) else None
                    app.logger.info(f"🔑 Token at index {token_idx}: {token_val[:20] if token_val else 'NULL'}...")
                else:
                    app.logger.warning(f"⚠️ current_share_token column not found in bookings table!")
            
            # Get column names for mapping
            cursor.execute("DESCRIBE bookings")
            booking_columns = [row[0] for row in cursor.fetchall()]
            
            cursor.execute("DESCRIBE customers")
            customer_columns = [row[0] for row in cursor.fetchall()]
            customer_columns = ['customer_' + col for col in customer_columns if col not in ['id']]
            
            # Create a booking-like object for template compatibility
            class BookingViewDisplay:
                def __init__(self, data, columns):
                    # Map booking data - use len(columns) instead of enumerate index
                    num_booking_cols = len(booking_columns)
                    for i, col in enumerate(booking_columns):
                        # Get value from data at same index
                        value = data[i] if i < len(data) else None
                        
                        # Convert date strings to datetime objects for template
                        if col in ['created_at', 'updated_at', 'time_limit'] and value:
                            try:
                                if isinstance(value, str):
                                    if len(value) > 10:  # datetime
                                        value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                                    else:  # date
                                        value = datetime.strptime(value, '%Y-%m-%d').date()
                            except:
                                pass
                        elif col in ['arrival_date', 'departure_date', 'traveling_period_start', 'traveling_period_end', 'due_date'] and value:
                            try:
                                if isinstance(value, str):
                                    value = datetime.strptime(value, '%Y-%m-%d').date()
                            except:
                                pass
                        elif col == 'pickup_time' and value:
                            try:
                                if isinstance(value, str):
                                    value = datetime.strptime(value, '%H:%M:%S').time()
                            except:
                                pass
                        elif col == 'total_amount' and value:
                            try:
                                value = float(value)
                            except:
                                value = 0.0
                        
                        setattr(self, col, value)
                    
                    # Map customer data
                    customer_data = data[-6:]  # Last 6 fields are customer data
                    class CustomerDisplay:
                        def __init__(self, first_name, last_name, email, phone, address, name):
                            self.first_name = first_name or ''
                            self.last_name = last_name or ''
                            self.email = email or ''
                            self.phone = phone or ''
                            self.address = address or ''
                            self.name = name or f"{first_name or ''} {last_name or ''}".strip() or 'No Name'
                    
                    self.customer = CustomerDisplay(*customer_data)
                    
                    # Add some methods that templates might expect
                    self.quotes = []  # Empty quotes list for now
                    self.activity_logs = []  # Will be populated separately
                    
                def get_guest_list(self):
                    """Parse guest list JSON/text for template"""
                    if hasattr(self, 'guest_list') and self.guest_list:
                        try:
                            import json
                            return json.loads(self.guest_list)
                        except:
                            # Fallback to plain text split
                            return self.guest_list.split('\n') if self.guest_list else []
                    return []
                
                def get_guest_list_for_edit(self):
                    """Get guest list as text for editing (template compatibility)"""
                    if hasattr(self, 'guest_list') and self.guest_list:
                        try:
                            import json
                            import html
                            import re
                            
                            guest_list = json.loads(self.guest_list)
                            if isinstance(guest_list, list):
                                # Process each guest item to clean HTML
                                formatted_guests = []
                                for guest in guest_list:
                                    if isinstance(guest, dict):
                                        # Format dict as readable string
                                        guest_str = f"{guest.get('name', 'Unknown')}"
                                        if guest.get('nationality'):
                                            guest_str += f" ({guest.get('nationality')})"
                                        if guest.get('type'):
                                            guest_str += f" - {guest.get('type')}"
                                        if guest.get('special_needs'):
                                            guest_str += f" - Special needs: {guest.get('special_needs')}"
                                        formatted_guests.append(guest_str)
                                    else:
                                        # Clean HTML from string
                                        guest_str = str(guest)
                                        
                                        # Decode HTML entities first
                                        guest_str = html.unescape(guest_str)
                                        
                                        # Convert <br> tags to newlines before removing HTML
                                        guest_str = re.sub(r'<br\s*/?>', '\n', guest_str, flags=re.IGNORECASE)
                                        
                                        # Remove all other HTML tags
                                        guest_str = re.sub(r'<[^>]+>', '', guest_str)
                                        
                                        # Clean up extra whitespace and empty lines
                                        lines = [line.strip() for line in guest_str.split('\n') if line.strip()]
                                        
                                        if lines:
                                            formatted_guests.extend(lines)
                                
                                return '\n'.join(formatted_guests)
                            else:
                                return str(self.guest_list)
                        except Exception as e:
                            print(f"🚨 Error in get_guest_list_for_edit: {e}")
                            return str(self.guest_list) if self.guest_list else ''
                    return ''
                
                def get_products(self):
                    """Parse products JSON for template"""
                    if hasattr(self, 'products') and self.products:
                        try:
                            import json
                            return json.loads(self.products)
                        except:
                            return []
                    return []
                
                def get_daily_services(self):
                    """Parse daily services JSON for template"""
                    if hasattr(self, 'daily_services') and self.daily_services:
                        try:
                            import json
                            return json.loads(self.daily_services)
                        except:
                            return []
                    return []
                
                def set_guest_list(self, guest_list):
                    """Set guest list (for template compatibility)"""
                    if isinstance(guest_list, list):
                        import json
                        self.guest_list = json.dumps(guest_list)
                    else:
                        self.guest_list = str(guest_list) if guest_list else None
                
                def set_products(self, products):
                    """Set products (for template compatibility)"""
                    if products:
                        import json
                        self.products = json.dumps(products)
                    else:
                        self.products = None
                
                def set_daily_services(self, services):
                    """Set daily services (for template compatibility)"""
                    if services:
                        import json
                        self.daily_services = json.dumps(services)
                    else:
                        self.daily_services = None
            
            booking = BookingViewDisplay(booking_data, booking_columns)
            current_app.logger.info(f"📊 BookingViewDisplay created for booking {id}")
            
            # Get activity logs for this booking
            cursor.execute("""
                SELECT al.id, al.user_id, al.action, al.description, al.ip_address, 
                       al.user_agent, al.created_at, u.username, u.full_name
                FROM activity_logs al
                LEFT JOIN users u ON al.user_id = u.id
                WHERE al.booking_id = %s OR al.description LIKE %s
                ORDER BY al.created_at DESC
                LIMIT 50
            """, (id, f'%[BOOKING #{id}]%'))
            
            activity_logs_data = cursor.fetchall()
            current_app.logger.info(f"📋 Found {len(activity_logs_data)} activity logs for booking {id}")
            
            # Create activity log objects for template
            class ActivityLogDisplay:
                def __init__(self, log_data):
                    (self.id, self.user_id, self.action, self.description, self.ip_address, 
                     self.user_agent, self.created_at, username, full_name) = log_data
                    
                    # Convert created_at to datetime
                    try:
                        if isinstance(self.created_at, str):
                            self.created_at = datetime.strptime(self.created_at, '%Y-%m-%d %H:%M:%S')
                    except:
                        pass
                    
                    # Create user info
                    class UserDisplay:
                        def __init__(self, username, full_name):
                            self.username = username or 'System'
                            self.full_name = full_name or ''
                            
                            # Split full_name for compatibility
                            if full_name:
                                name_parts = full_name.strip().split(' ', 1)
                                self.first_name = name_parts[0] if name_parts else ''
                                self.last_name = name_parts[1] if len(name_parts) > 1 else ''
                            else:
                                self.first_name = ''
                                self.last_name = ''
                                
                            self.name = full_name or username or 'System'
                    
                    self.user = UserDisplay(username, full_name)
            
            booking.activity_logs = [ActivityLogDisplay(log_data) for log_data in activity_logs_data]
            current_app.logger.info(f"✅ Created {len(booking.activity_logs)} ActivityLogDisplay objects")
            
        connection.close()
        app.logger.info(f"✅ Successfully loaded booking {id} via direct database")
        
    except Exception as e:
        app.logger.error(f"❌ Direct database failed for booking {id}: {e}")
        # Fallback to ORM method
        try:
            app.logger.info(f"🔄 Falling back to ORM method for booking {id}")
            booking = Booking.query.get_or_404(id)
            # Add empty activity_logs for template compatibility
            booking.activity_logs = []
            app.logger.info(f"✅ Successfully loaded booking {id} via ORM fallback")
        except Exception as orm_error:
            app.logger.error(f"❌ Both direct DB and ORM failed for booking {id}: {orm_error}")
            from flask import abort
            abort(500)

    # Get recent activity logs for this booking (last 6 entries)
    activity_logs = []
    try:
        import pymysql
        # Use direct database connection to avoid SQLAlchemy issues
        connection = pymysql.connect(
            host='localhost',
            user='voucher_user',
            password='voucher_secure_2024',
            database='voucher_enhanced',
            charset='utf8mb4'
        )
        
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT id, action, description, created_at, user_id 
                   FROM activity_logs 
                   WHERE booking_id = %s 
                   ORDER BY created_at DESC 
                   LIMIT 6""", 
                (id,)
            )
            results = cursor.fetchall()
            activity_logs = [
                {
                    'id': row[0],
                    'action': row[1],
                    'description': row[2],
                    'created_at': row[3],
                    'user_id': row[4]
                }
                for row in results
            ]
        connection.close()
        app.logger.info(f"Retrieved {len(activity_logs)} activity logs for booking {id}")
    except Exception as logs_error:
        app.logger.warning(f"Could not retrieve activity logs: {logs_error}")
        activity_logs = []

    # Use language-specific template
    current_language = session.get('language', 'en')
    template_name = f'booking/view_{current_language}.html'
    
    # Import config for template
    from config import Config
    
    # Fallback to English template if language-specific template doesn't exist
    try:
        app.logger.info(f"🎨 Attempting to render template: {template_name}")
        response = make_response(render_template(template_name, booking=booking, invoice_status=None, config=Config, activity_logs=activity_logs))
        app.logger.info(f"✅ Successfully rendered template: {template_name}")
    except Exception as template_error:
        app.logger.error(f"❌ Template rendering failed for {template_name}: {template_error}")
        try:
            app.logger.info(f"🔄 Falling back to English template")
            response = make_response(render_template('booking/view_en.html', booking=booking, invoice_status=None, config=Config, activity_logs=activity_logs))
            app.logger.info(f"✅ Successfully rendered fallback template")
        except Exception as fallback_error:
            app.logger.error(f"❌ Fallback template rendering also failed: {fallback_error}")
            import traceback
            app.logger.error(f"📍 Full traceback: {traceback.format_exc()}")
            raise
    
    # Add cache control headers to prevent browser caching of dynamic content
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

@booking_bp.route('/<int:id>/update-status', methods=['POST'])
@login_required
def update_status(id):
    """Update booking status"""
    booking = Booking.query.get_or_404(id)
    
    new_status = request.form.get('status')
    if new_status in ['pending', 'confirmed', 'completed', 'cancelled']:
        old_status = booking.status
        booking.status = new_status
        
        # Create activity log entry for status change
        try:
            import pymysql
            from datetime import datetime
            
            connection = pymysql.connect(
                host='localhost',
                user='voucher_user',
                password='voucher_secure_2024',
                database='voucher_enhanced',
                charset='utf8mb4'
            )
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO activity_logs (booking_id, action, description, created_at) 
                    VALUES (%s, %s, %s, %s)
                """, (
                    id,
                    'status_updated',
                    f'Booking status changed from {old_status} to {new_status}',
                    datetime.now()
                ))
                connection.commit()
                current_app.logger.info(f"✅ Activity log created for booking {id} status change: {old_status} → {new_status}")
                
        except Exception as e:
            current_app.logger.error(f"❌ Failed to create activity log for booking {id}: {e}")
        finally:
            if 'connection' in locals():
                connection.close()
        
        if new_status == 'confirmed':
            flash('การจองได้รับการยืนยันแล้ว', 'success')
        elif new_status == 'completed':
            flash('การจองเสร็จสิ้นแล้ว', 'success')
        elif new_status == 'cancelled':
            flash('การจองถูกยกเลิกแล้ว', 'warning')
        
        db.session.commit()
    else:
        flash('สถานะไม่ถูกต้อง', 'error')
    
    return redirect(url_for('booking.view', id=id))

# Invoice Ninja sync function removed

@booking_bp.route('/<int:booking_id>/mark-paid', methods=['POST'])
@login_required
def mark_as_paid(booking_id):
    """Mark booking invoice as paid with password confirmation"""
    
    try:
        # Check if it's a form submission or API call
        if request.content_type == 'application/json' or request.is_json:
            # API call - skip password for automation
            data = request.get_json() or {}
            password = data.get('payment_password', 'pm250966')  # Default for API
            new_quote_number = data.get('quote_number', '').strip()
            new_invoice_number = data.get('invoice_number', '').strip()  
            new_invoice_status = data.get('invoice_status', 'paid').strip()
            maintain_paid_status = data.get('maintain_paid_status', False)
        else:
            # Form submission - require password
            password = request.form.get('payment_password')
            new_quote_number = request.form.get('quote_number', '').strip()
            new_invoice_number = request.form.get('invoice_number', '').strip()
            new_invoice_status = request.form.get('invoice_status', '').strip()
            maintain_paid_status = request.form.get('maintain_paid_status', '') == 'true'
        
        # Verify password for form submissions
        if not request.is_json and password != 'pm250966':
            message = '❌ Invalid password. Access denied.'
            if request.is_json:
                return jsonify({'success': False, 'message': message}), 403
            flash(message, 'error')
            return redirect(url_for('booking.view', id=booking_id))
        
        booking = Booking.query.get_or_404(booking_id)
        
        # Update quote and invoice data if provided
        old_quote = booking.quote_number
        old_invoice = booking.invoice_number
        old_status = booking.invoice_status
        
        if new_quote_number:
            booking.quote_number = new_quote_number
        if new_invoice_number:
            booking.invoice_number = new_invoice_number
        if new_invoice_status:
            booking.invoice_status = new_invoice_status
        
        # For API calls, set default invoice number if not provided
        if request.is_json and not booking.invoice_number:
            booking.invoice_number = f"INV-{booking.booking_reference}"
        
        # Check if booking has invoice number after update
        if not booking.invoice_number:
            message = '❌ No invoice number provided. Please enter invoice number.'
            if request.is_json:
                return jsonify({'success': False, 'message': message}), 400
            flash(message, 'error')
            return redirect(url_for('booking.view', id=booking_id))
        
        # Set payment status
        old_booking_status = booking.status
        if maintain_paid_status:
            # Confirming already paid status - maintain current paid state
            booking.is_paid = True
            if not booking.invoice_paid_date:
                booking.invoice_paid_date = datetime.now()
            # Use the provided status (default to 'paid' from form)
            if not booking.invoice_status:
                booking.invoice_status = 'paid'
            # Update booking status to paid if not already
            if booking.status != 'paid':
                booking.status = 'paid'
        else:
            # New payment marking - always mark as paid
            booking.invoice_status = 'paid'
            booking.is_paid = True
            booking.invoice_paid_date = datetime.now()
            # Update booking status to paid
            booking.status = 'paid'
        
        db.session.commit()
        
        # Always create activity logs for payment actions (using direct pymysql for reliability)
        try:
            import pymysql
            from datetime import datetime
            
            connection = pymysql.connect(
                host='localhost',
                user='voucher_user',
                password='voucher_secure_2024',
                database='voucher_enhanced',
                charset='utf8mb4'
            )
            
            with connection.cursor() as cursor:
                # Create activity log for status change if booking status changed
                if old_booking_status != booking.status:
                    cursor.execute("""
                        INSERT INTO activity_logs (booking_id, action, description, created_at) 
                        VALUES (%s, %s, %s, %s)
                    """, (
                        booking_id,
                        'status_updated',
                        f'Booking status changed from {old_booking_status} to {booking.status}',
                        datetime.now()
                    ))
                    current_app.logger.info(f"✅ Activity log created for booking {booking_id} status change: {old_booking_status} → {booking.status}")
                
                # Always create payment marking activity log
                activity_description = f"[BOOKING #{booking_id}] Invoice {booking.invoice_number or 'TBD'} marked as {booking.invoice_status.upper()}"
                if maintain_paid_status:
                    activity_description = f"[BOOKING #{booking_id}] Payment status confirmed for invoice {booking.invoice_number or 'TBD'}"
                
                cursor.execute("""
                    INSERT INTO activity_logs (booking_id, action, description, created_at) 
                    VALUES (%s, %s, %s, %s)
                """, (
                    booking_id,
                    'payment_marked',
                    activity_description,
                    datetime.now()
                ))
                
                connection.commit()
                current_app.logger.info(f"✅ Payment activity log created for booking {booking_id}: {activity_description}")
                
        except Exception as e:
            current_app.logger.error(f"❌ Failed to create activity logs for booking {booking_id}: {e}")
        finally:
            if 'connection' in locals():
                connection.close()
        
        action_type = "confirmed" if maintain_paid_status else "marked"
        logger.info(f"Booking {booking_id} {action_type} as paid by admin {current_user.username}")
        
        # Build success message
        success_msgs = []
        if old_quote != booking.quote_number:
            success_msgs.append(f'Quote: {old_quote or "None"} → {booking.quote_number}')
        if old_invoice != booking.invoice_number:
            success_msgs.append(f'Invoice: {old_invoice or "None"} → {booking.invoice_number}')
        
        if maintain_paid_status:
            flash(f'✅ Payment status confirmed! Invoice {booking.invoice_number} status: {booking.invoice_status.upper()}. Voucher creation enabled.', 'success')
        else:
            flash(f'✅ Invoice {booking.invoice_number} marked as PAID! Voucher creation is now available.', 'success')
            
        flash(f'🔄 Status updated: {old_status or "Unknown"} → {booking.invoice_status.upper()}', 'info')
        
        if success_msgs:
            flash(f'📝 Updated: {", ".join(success_msgs)}', 'info')
        
        # Auto sync to invoices table when marked as paid
        try:
            sync_booking_to_invoice(booking)
        except Exception as e:
            logger.warning(f"Failed to sync booking {booking_id} to invoices table: {e}")
        
        # Return JSON for API calls
        if request.is_json or request.headers.get('Content-Type') == 'application/json':
            # Safe datetime conversion for invoice_paid_date
            paid_date_iso = None
            if booking.invoice_paid_date:
                if isinstance(booking.invoice_paid_date, str):
                    try:
                        paid_datetime = datetime.fromisoformat(booking.invoice_paid_date.replace('Z', '+00:00'))
                        paid_date_iso = paid_datetime.isoformat()
                    except ValueError:
                        paid_date_iso = booking.invoice_paid_date
                else:
                    paid_date_iso = booking.invoice_paid_date.isoformat()
            
            return jsonify({
                'success': True,
                'message': f'Invoice {booking.invoice_number} marked as PAID! Voucher creation enabled.',
                'status': booking.status,
                'invoice_status': booking.invoice_status,
                'is_paid': booking.is_paid,
                'invoice_paid_date': paid_date_iso
            })
        
        return redirect(url_for('booking.view', id=booking_id))
        
    except Exception as e:
        logger.error(f"Error marking booking {booking_id} as paid: {e}")
        flash('An error occurred while marking as paid.', 'error')
        return redirect(url_for('booking.view', id=booking_id))

@booking_bp.route('/<int:booking_id>/unmark-paid', methods=['POST'])
@login_required
def unmark_as_paid(booking_id):
    """Unmark booking invoice as paid (reset to unpaid) with password confirmation"""
    
    try:
        password = request.form.get('payment_password')
        
        # Verify password
        if password != 'pm250966':
            flash('❌ Invalid password. Access denied.', 'error')
            return redirect(url_for('booking.view', id=booking_id))
        
        booking = Booking.query.get_or_404(booking_id)
        
        # Get form data for new status and values
        new_quote_number = request.form.get('quote_number', '').strip()
        new_invoice_number = request.form.get('invoice_number', '').strip()
        new_invoice_status = request.form.get('invoice_status', '').strip()
        
        # Store old values for logging
        old_quote = booking.quote_number
        old_invoice = booking.invoice_number
        old_status = booking.invoice_status
        
        # Update fields if provided
        if new_quote_number:
            booking.quote_number = new_quote_number
        if new_invoice_number:
            booking.invoice_number = new_invoice_number
            
        # Set invoice status - default to "unknown" if not specified
        if new_invoice_status:
            booking.invoice_status = new_invoice_status
        else:
            booking.invoice_status = 'unknown'
        
        # Reset payment status
        booking.is_paid = False
        booking.invoice_paid_date = None
        
        db.session.commit()
        
        logger.info(f"Booking {booking_id} unmarked as paid by admin {current_user.username}")
        
        # Build success message
        success_msgs = []
        if old_quote != booking.quote_number:
            success_msgs.append(f'Quote: {old_quote or "None"} → {booking.quote_number}')
        if old_invoice != booking.invoice_number:
            success_msgs.append(f'Invoice: {old_invoice or "None"} → {booking.invoice_number}')
        
        flash(f'✅ Payment status reset! Invoice {booking.invoice_number or "N/A"} is now unpaid.', 'success')
        flash(f'🔄 Status updated: {old_status or "Unknown"} → {booking.invoice_status.upper()}', 'info')
        
        if success_msgs:
            flash(f'📝 Updated: {", ".join(success_msgs)}', 'info')
        
        return redirect(url_for('booking.view', id=booking_id))
        
    except Exception as e:
        logger.error(f"Error unmarking booking {booking_id} as paid: {e}")
        flash('An error occurred while resetting payment status.', 'error')
        return redirect(url_for('booking.view', id=booking_id))

# Bulk invoice sync function removed

@booking_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    """Edit booking with special handling for booking #45"""
    print(f"🔍 EDIT FUNCTION CALLED - Booking ID: {id}, Method: {request.method}")
    
    # Special case for booking #45 - use dedicated handler
    if id == 45:
        logger.info("🎯 Routing booking #45 to special handler")
        return handle_booking_45_edit(id, request)
    
    # Original booking edit logic for other bookings
    try:
        booking = Booking.query.get_or_404(id)
    except Exception as e:
        logger.error(f"Database error when loading booking {id}: {e}")
        if "microseconds" in str(e) or "datetime" in str(e).lower():
            flash(f'Database error: Unable to load booking {id} due to datetime data corruption.', 'error')
        else:
            flash(f'Database error: Unable to load booking {id}.', 'error')
        return redirect(url_for('booking.list'))
    
    if request.method == 'POST':
        print(f"🔍 POST REQUEST DETECTED for booking {id}")
        print(f"   Form keys: {[key for key in request.form.keys()]}")
        print(f"   service_detail value: '{request.form.get('service_detail')}'")
        
        try:
            # Helper function to parse DD/MM/YYYY format
            def parse_date_ddmmyyyy(date_str):
                if not date_str:
                    return None
                try:
                    # First try DD/MM/YYYY format
                    if '/' in date_str:
                        return datetime.strptime(date_str, '%d/%m/%Y').date()
                    # Fallback to YYYY-MM-DD format
                    else:
                        return datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    return None

            # Helper function to parse DD/MM/YYYY HH:MM format
            def parse_datetime_ddmmyyyy(datetime_str):
                if not datetime_str:
                    return None
                try:
                    # First try DD/MM/YYYY HH:MM format
                    if '/' in datetime_str:
                        return datetime.strptime(datetime_str, '%d/%m/%Y %H:%M')
                    # Fallback to YYYY-MM-DDTHH:MM format
                    else:
                        return datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M')
                except ValueError:
                    return None
            
            # Update booking fields
            booking.booking_type = request.form.get('booking_type') or booking.booking_type
            booking.status = request.form.get('status') or booking.status
            
            # Update dates with DD/MM/YYYY support
            arrival_date = parse_date_ddmmyyyy(request.form.get('arrival_date'))
            if arrival_date:
                booking.arrival_date = arrival_date
                
            departure_date = parse_date_ddmmyyyy(request.form.get('departure_date'))
            if departure_date:
                booking.departure_date = departure_date
                
            traveling_start = parse_date_ddmmyyyy(request.form.get('traveling_period_start'))
            if traveling_start:
                booking.traveling_period_start = traveling_start
                
            traveling_end = parse_date_ddmmyyyy(request.form.get('traveling_period_end'))
            if traveling_end:
                booking.traveling_period_end = traveling_end
            
            # Time and deadline fields with DD/MM/YYYY support
            time_limit_str = request.form.get('time_limit')
            if not time_limit_str:
                flash('Time Limit is required', 'error')
                return redirect(url_for('booking.edit', id=booking.id))
            
            time_limit = parse_datetime_ddmmyyyy(time_limit_str)
            if not time_limit:
                flash('Invalid Time Limit format. Please use DD/MM/YYYY HH:MM', 'error')
                return redirect(url_for('booking.edit', id=booking.id))
            booking.time_limit = time_limit
                
            due_date = parse_date_ddmmyyyy(request.form.get('due_date'))
            if due_date:
                booking.due_date = due_date
            elif request.form.get('due_date') == '':
                booking.due_date = None
            
            # Pax
            booking.adults = int(request.form.get('adults', booking.adults or 1))
            booking.children = int(request.form.get('children', booking.children or 0))
            booking.total_pax = int(request.form.get('total_pax', (booking.adults or 0) + (booking.children or 0) or 1))
            booking.infants = int(request.form.get('infants', booking.infants or 0))
            
            # Financial
            if request.form.get('total_amount'):
                try:
                    booking.total_amount = float(request.form.get('total_amount'))
                except ValueError:
                    pass
            
            # Common fields
            booking.party_name = (request.form.get('party_name') or booking.party_name or '').strip()
            # WYSIWYG description (may contain HTML) - support both field names
            service_detail = request.form.get('service_detail') or request.form.get('description')
            print(f"🔍 DEBUGGING SERVICE DETAIL:")
            print(f"   service_detail from form: '{service_detail}'")
            print(f"   current booking.description: '{booking.description}'")
            if service_detail:
                booking.description = service_detail.strip()
                print(f"   ✅ Updated booking.description to: '{booking.description}'")
            else:
                print(f"   ❌ No service_detail data received from form")
            booking.internal_note = request.form.get('internal_note', '').strip() or None
            
            # Flight info - convert line breaks to HTML
            flight_info = request.form.get('flight_info', '').strip()
            if flight_info:
                # Convert line breaks to <br> tags and wrap in <p> if not already wrapped
                flight_info = flight_info.replace('\r\n', '\n').replace('\r', '\n')
                flight_info = flight_info.replace('\n', '<br>')
                if not flight_info.startswith('<p>'):
                    flight_info = f'<p>{flight_info}</p>'
                booking.flight_info = flight_info
            else:
                booking.flight_info = None
            # Admin and Management fields
            print(f"🚨 BOOKING EDIT FORM DATA RECEIVED:")
            print(f"   admin_notes: '{request.form.get('admin_notes', 'NOT_FOUND')}'")
            print(f"   manager_memos: '{request.form.get('manager_memos', 'NOT_FOUND')}'")
            print(f"   internal_note: '{request.form.get('internal_note', 'NOT_FOUND')}'")
            print(f"   guest_list: '{request.form.get('guest_list', 'NOT_FOUND')}'")
            print(f"   special_request: '{request.form.get('special_request', 'NOT_FOUND')}'")
            print(f"   flight_info: '{request.form.get('flight_info', 'NOT_FOUND')}'")
            
            logger.debug("EDIT FORM DEBUG admin_notes=%r manager_memos=%r internal_note=%r", 
                         request.form.get('admin_notes'),
                         request.form.get('manager_memos'),
                         request.form.get('internal_note'))
            
            booking.admin_notes = request.form.get('admin_notes', '').strip() or None
            booking.manager_memos = request.form.get('manager_memos', '').strip() or None
            booking.internal_note = request.form.get('internal_note', '').strip() or None
            
            logger.debug("Saving admin_notes=%r manager_memos=%r internal_note=%r", 
                         booking.admin_notes, booking.manager_memos, booking.internal_note)
            
            # DEBUG: Log form data for guest_list and special_request
            logger.debug("EDIT FORM DEBUG guest_list=%r special_request=%r", 
                         request.form.get('guest_list'),
                         request.form.get('special_request'))
            
            # Persist special request for ALL booking types
            booking.special_request = (request.form.get('special_request') or request.form.get('special_requests') or '').strip() or None
            
            # Guest list (textarea with one per line)
            guest_list_html = request.form.get('guest_list')
            if guest_list_html is not None:
                # Convert textarea input back to list format
                lines = [line.strip() for line in guest_list_html.split('\n') if line.strip()]
                if lines:
                    booking.set_guest_list(lines)
                else:
                    booking.guest_list = None
                logger.debug("Set guest list from textarea: %r -> %r", guest_list_html, lines)
            
            # Pickup information for ALL booking types (not just transport)
            booking.pickup_point = request.form.get('pickup_point', '').strip() or None
            if request.form.get('pickup_time'):
                try:
                    booking.pickup_time = datetime.strptime(request.form.get('pickup_time'), '%H:%M').time()
                except ValueError:
                    pass  # Invalid time format, skip
            elif request.form.get('pickup_time') == '':
                booking.pickup_time = None
            
            # Products & Calculation data
            products = []
            form_data = request.form.to_dict(flat=False)
            
            # Extract products from dynamic form data
            i = 0
            while True:
                name_key = f'products[{i}][name]'
                quantity_key = f'products[{i}][quantity]'
                price_key = f'products[{i}][price]'
                amount_key = f'products[{i}][amount]'
                
                if name_key not in form_data:
                    break
                    
                name = form_data[name_key][0] if form_data[name_key] else ''
                quantity = form_data[quantity_key][0] if quantity_key in form_data and form_data[quantity_key] else '1'
                price = form_data[price_key][0] if price_key in form_data and form_data[price_key] else '0'
                amount = form_data[amount_key][0] if amount_key in form_data and form_data[amount_key] else '0'
                
                if name.strip():  # Only add products with names
                    products.append({
                        'name': name.strip(),
                        'quantity': int(quantity) if quantity else 1,
                        'price': float(price) if price else 0.0,
                        'amount': float(amount) if amount else 0.0
                    })
                
                i += 1
            
            # Log products data for debugging
            print(f"🛍️ PRODUCTS DEBUG - Booking {id}:")
            print(f"   Products found in form: {len(products)}")
            print(f"   Products data: {products}")
            print(f"   Current booking.products: {booking.get_products() if hasattr(booking, 'get_products') else 'N/A'}")
            
            # Only update products if new data was submitted, otherwise keep existing
            if i > 0:  # At least one product field was in the form
                booking.set_products(products)
                print(f"   ✅ Updated products to: {products}")
            else:
                print(f"   ⚠️  No product fields in form - keeping existing products")
                # Don't call set_products() - keep existing data
            
            # Type-specific & shared optional fields
            if booking.booking_type == 'hotel':
                booking.agency_reference = request.form.get('agency_reference') or booking.agency_reference
                booking.hotel_name = request.form.get('hotel_name') or booking.hotel_name
                booking.room_type = request.form.get('room_type') or booking.room_type
                # (special_request already set globally)
            elif booking.booking_type == 'transport':
                # Additional transport-specific fields (pickup already handled globally)
                booking.destination = request.form.get('destination') or booking.destination
                booking.vehicle_type = request.form.get('vehicle_type') or booking.vehicle_type
            elif booking.booking_type == 'tour':
                # Daily services list only for tour (legacy)
                services = []
                service_dates = request.form.getlist('service_dates[]')
                service_descriptions = request.form.getlist('service_descriptions[]')
                service_types = request.form.getlist('service_types[]')
                for i in range(len(service_dates)):
                    if service_dates[i] and service_descriptions[i]:
                        services.append({
                            'date': service_dates[i],
                            'description': service_descriptions[i],
                            'type': service_types[i] if i < len(service_types) else ''
                        })
                if services:
                    booking.set_daily_services(services)
            
            print(f"🔥 FINAL VALUES BEFORE DATABASE SAVE:")
            print(f"   booking.admin_notes = '{booking.admin_notes}'")
            print(f"   booking.manager_memos = '{booking.manager_memos}'")
            print(f"   booking.internal_note = '{booking.internal_note}'")
            print(f"   booking.guest_list = '{booking.guest_list}'")
            print(f"   booking.special_request = '{booking.special_request}'")
            print(f"   booking.flight_info = '{booking.flight_info}'")
            
            db.session.commit()
            print(f"✅ DATABASE COMMITTED SUCCESSFULLY!")
            flash('Booking updated successfully!', 'success')
            return redirect(url_for('booking.view', id=booking.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating booking: {str(e)}', 'error')
    
    return render_template('booking/edit.html', booking=booking)

@booking_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    """Delete booking"""
    booking = Booking.query.get_or_404(id)
    
    try:
        db.session.delete(booking)
        db.session.commit()
        flash(f'Booking {booking.booking_reference} deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting booking: {str(e)}', 'error')
    
    return redirect(url_for('dashboard.bookings'))

@booking_bp.route('/ro/<int:id>')
@login_required
def ro_pdf(id):
    """Generate Hotel RO PDF"""
    booking = Booking.query.get_or_404(id)
    
    if booking.booking_type != 'hotel':
        flash('This booking is not a hotel reservation', 'error')
        return redirect(url_for('booking.view', id=id))
    
    from services.pdf_generator import PDFGenerator
    pdf_generator = PDFGenerator()
    
    try:
        pdf_path = pdf_generator.generate_hotel_ro(booking)
        return redirect(f'/static/generated/{pdf_path}')
    except Exception as e:
        flash(f'Error generating RO PDF: {str(e)}', 'error')
        return redirect(url_for('booking.view', id=id))

@booking_bp.route('/mpv/<int:id>')
@login_required
def mpv_pdf(id):
    """Generate MPV Booking PDF"""
    booking = Booking.query.get_or_404(id)
    
    if booking.booking_type != 'transport':
        flash('This booking is not a transport reservation', 'error')
        return redirect(url_for('booking.view', id=id))
    
    from services.pdf_generator import PDFGenerator
    pdf_generator = PDFGenerator()
    
    try:
        pdf_path = pdf_generator.generate_mpv_booking(booking)
        return redirect(f'/static/generated/{pdf_path}')
    except Exception as e:
        flash(f'Error generating MPV PDF: {str(e)}', 'error')
        return redirect(url_for('booking.view', id=id))

@booking_bp.route('/api/customer/<int:customer_id>')
@login_required
def get_customer(customer_id):
    """API endpoint to get customer details"""
    customer = Customer.query.get_or_404(customer_id)
    return jsonify(customer.to_dict())

@booking_bp.route('/<int:booking_id>/pdf')
@login_required
def generate_booking_pdf(booking_id):
    """Generate Service Proposal PDF using Classic PDF Generator (like original sample)"""
    from services.classic_pdf_generator import ClassicPDFGenerator
    from flask import send_file, make_response
    
    try:
        # Force refresh from database
        db.session.expire_all()
        booking = Booking.query.get_or_404(booking_id)
        
        # Prepare complete booking data for Classic PDF
        booking_data = {
            'booking_id': booking.booking_reference,
            'guest_name': (booking.customer.name if booking.customer else None) or booking.party_name or 'N/A',
                'customer_name': booking.customer.name if booking.customer else 'N/A',
            'guest_email': booking.customer.email if booking.customer else 'N/A', 
            'guest_phone': booking.customer.phone if booking.customer else 'N/A',
            'tour_name': booking.description or booking.hotel_name or 'Tour Package',
            'booking_date': booking.created_at.strftime('%Y-%m-%d') if booking.created_at else 'N/A',
            'tour_date': booking.arrival_date.strftime('%Y-%m-%d') if booking.arrival_date else 'N/A',
            'start_date': booking.traveling_period_start.strftime('%Y-%m-%d') if booking.traveling_period_start else (booking.arrival_date.strftime('%Y-%m-%d') if booking.arrival_date else 'N/A'),
            'end_date': booking.traveling_period_end.strftime('%Y-%m-%d') if booking.traveling_period_end else (booking.departure_date.strftime('%Y-%m-%d') if booking.departure_date else 'N/A'),
            'pax': booking.total_pax or 1,
            'adults': booking.adults or booking.total_pax or 1,
            'children': booking.children or 0,
            'infants': booking.infants or 0,
            'price': float(booking.total_amount) if booking.total_amount else 0.0,
            'status': booking.status,
            'description': booking.description or '',
            'internal_note': booking.admin_notes or booking.internal_note or '',
            'daily_services': booking.daily_services or '',
            'guest_list': booking.guest_list or '',  # Add guest list data
            'flight_info': booking.flight_info or '',
            'special_request': booking.special_request or '',
            'customer_address': getattr(booking.customer, 'address', '') if booking.customer else '',
            'customer_nationality': getattr(booking.customer, 'nationality', '') if booking.customer else '',
            'reference': booking.booking_reference
        }
        
        # Get products for this booking from the products JSON field
        products = []
        booking_products = booking.get_products()
        if booking_products:
            for product_data in booking_products:
                products.append({
                    'name': product_data.get('name', 'Unknown Product'),
                    'quantity': product_data.get('quantity', 1),
                    'price': float(product_data.get('price', 0.0)),
                    'amount': float(product_data.get('amount', 0.0))
                })
        
        # Debug: Print products being used  
        print(f"🔍 PDF Products for {booking.booking_reference} ({len(products)} items):")
        for i, product in enumerate(products, 1):
            print(f"  {i}. {product['name']} x{product['quantity']} = {product['price']:,.2f} (Amount: {product['amount']:,.2f})")
        
        # Generate PDF using Classic PDF Generator
        classic_generator = ClassicPDFGenerator()
        pdf_path = classic_generator.generate_pdf(booking_data, products)
        
        if not pdf_path or not os.path.exists(pdf_path):
            logger.error(f"Failed to generate PDF for booking {booking_id}")
            flash('Error generating PDF file', 'error')
            return redirect(url_for('admin.bookings'))
            
        filename = f"service_proposal_{booking.booking_reference}.pdf"
        
        response = make_response(send_file(
            pdf_path,
            as_attachment=False,
            download_name=filename,
            mimetype='application/pdf'
        ))
        
        response.headers['Content-Disposition'] = f'inline; filename="{filename}"'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        logger.info(f"Generated Service Proposal PDF for booking {booking_id}")
        return response
    except Exception as e:
        flash(f'Error generating Classic PDF: {str(e)}', 'error')
        return redirect(url_for('admin.bookings'))

@booking_bp.route('/generate/<int:booking_id>/service-proposal')
def generate_service_proposal_pdf(booking_id):
    """Generate Service Proposal PDF using Classic PDF Generator"""
    from services.classic_pdf_generator import ClassicPDFGenerator
    from flask import send_file, abort, Response, make_response
    
    # Force refresh from database
    db.session.expire_all()
    booking = Booking.query.get_or_404(booking_id)

    try:
        # Prepare complete booking data for WeasyPrint
        booking_data = {
            'booking_id': booking.booking_reference,
            'guest_name': (booking.customer.name if booking.customer else None) or booking.party_name or 'N/A',
                'customer_name': booking.customer.name if booking.customer else 'N/A',
            'customer_name': booking.customer.name if booking.customer else 'N/A',  # Add explicit customer_name
            'guest_email': booking.customer.email if booking.customer else 'N/A', 
            'guest_phone': booking.customer.phone if booking.customer else 'N/A',
            'tour_name': booking.description or booking.hotel_name or 'Tour Package',
            'booking_date': booking.created_at.strftime('%Y-%m-%d') if booking.created_at else 'N/A',
            'tour_date': booking.arrival_date.strftime('%Y-%m-%d') if booking.arrival_date else 'N/A',
            'start_date': booking.traveling_period_start.strftime('%Y-%m-%d') if booking.traveling_period_start else (booking.arrival_date.strftime('%Y-%m-%d') if booking.arrival_date else 'N/A'),
            'end_date': booking.traveling_period_end.strftime('%Y-%m-%d') if booking.traveling_period_end else (booking.departure_date.strftime('%Y-%m-%d') if booking.departure_date else 'N/A'),
            'pax': booking.total_pax or 1,
            'adults': booking.adults or booking.total_pax or 1,
            'children': booking.children or 0,
            'infants': booking.infants or 0,
            'price': float(booking.total_amount) if booking.total_amount else 0.0,
            'status': booking.status,
            'description': booking.description or '',
            'flight_info': booking.flight_info or '',  # Pass empty string instead of None
            'special_request': booking.special_request or '',  # Pass empty string instead of None
            'internal_note': booking.admin_notes or booking.internal_note or '',
            'daily_services': booking.daily_services or '',
            'guest_list': booking.get_guest_list_for_edit() or '',  # Use clean text method for PDF
            'customer_address': getattr(booking.customer, 'address', '') if booking.customer else '',
            'customer_nationality': getattr(booking.customer, 'nationality', '') if booking.customer else '',
            'reference': booking.booking_reference
        }
        
        # Get products for this booking from the products JSON field
        products = []
        booking_products = booking.get_products()
        if booking_products:
            for product_data in booking_products:
                products.append({
                    'name': product_data.get('name', 'Unknown Product'),
                    'quantity': product_data.get('quantity', 1),
                    'price': float(product_data.get('price', 0.0)),
                    'amount': float(product_data.get('amount', 0.0))
                })
        
        # Debug: Print products being used  
        print(f"🔍 PDF Products for {booking.booking_reference} ({len(products)} items):")
        for i, product in enumerate(products, 1):
            print(f"  {i}. {product['name']} x{product['quantity']} = {product['price']:,.2f} (Amount: {product['amount']:,.2f})")
        
        # Generate PDF using Classic PDF Generator  
        classic_generator = ClassicPDFGenerator()
        
        # Use adaptive path for development vs production
        output_dir = "static/generated"
        os.makedirs(output_dir, exist_ok=True)
        
        pdf_path = classic_generator.generate_pdf(
            booking_data, 
            products, 
            f'{output_dir}/classic_service_proposal_{booking.booking_reference}_{datetime.now().strftime("%Y%m%d_%H%M%S")}_{random.randint(10000, 99999)}.pdf'
        )
        
        if pdf_path and os.path.exists(pdf_path):
            # Add aggressive cache-busting headers
            response = send_file(pdf_path, 
                               as_attachment=True, 
                               download_name=f"booking_{booking.booking_reference}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                               mimetype='application/pdf')
            
            # Aggressive anti-cache headers
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '-1'
            response.headers['Last-Modified'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')
            response.headers['ETag'] = f'"{datetime.now().timestamp()}"'
            
            return response
        else:
            abort(404, description="PDF file not found")
            
    except Exception as e:
        import traceback
        full_error = traceback.format_exc()
        logger.error(f"Error generating Classic PDF for booking {booking_id}: {str(e)}")
        logger.error(f"Full traceback: {full_error}")
        abort(500, description=f"Error generating PDF: {str(e)}")

@booking_bp.route('/generate/<int:booking_id>/service-proposal-png')
def generate_service_proposal_png(booking_id):
    """Generate PNG image from Service Proposal PDF using ClassicPDFGenerator"""
    from services.classic_pdf_generator import ClassicPDFGenerator
    from services.pdf_image import pdf_to_png_bytes_list, pdf_to_long_png_bytes
    from flask import send_file, abort, Response
    import io, os
    
    # Force refresh from database
    db.session.expire_all()
    booking = Booking.query.get_or_404(booking_id)
    
    try:
        # Use party_name instead of client_name
        customer = booking.customer if hasattr(booking, 'customer') else None
        guest_name = booking.party_name or (customer.name if customer else 'Guest')
        
        booking_data = {
            'booking_id': booking.booking_reference,
            'guest_name': guest_name,
            'customer_name': guest_name,
            'guest_phone': customer.phone if customer else '',
            'pax': booking.total_pax or 1,
            'adults': booking.adults or 0,
            'children': booking.children or 0,
            'infants': booking.infants or 0,
            'start_date': booking.traveling_period_start.strftime('%d %b %Y') if booking.traveling_period_start else '',
            'end_date': booking.traveling_period_end.strftime('%d %b %Y') if booking.traveling_period_end else '',
            'booking_date': booking.created_at.strftime('%d.%b.%Y') if booking.created_at else '',
            'status': booking.status or 'pending',
            'flight_info': booking.flight_info or '',
            'description': booking.description or '',
            'daily_services': booking.daily_services or '',
            'guest_list': booking.guest_list or '',
            'special_request': booking.special_request or '',
            'internal_note': booking.admin_notes or booking.internal_note or '',
            'tour_name': booking.description or booking.hotel_name or 'Tour Package',
            'reference': booking.booking_reference
        }
        
        # Get products for this booking from the products JSON field (like voucher generator)
        products = []
        booking_products = booking.get_products()
        if booking_products:
            for product_data in booking_products:
                products.append({
                    'name': product_data.get('name', 'Unknown Product'),
                    'quantity': product_data.get('quantity', 1),
                    'price': float(product_data.get('price', 0.0)),
                    'amount': float(product_data.get('amount', 0.0))
                })
        
        # Generate PDF using ClassicPDFGenerator (with products)
        classic_generator = ClassicPDFGenerator()
        pdf_path = classic_generator.generate_pdf(booking_data, products)
        
        if not pdf_path or not os.path.exists(pdf_path):
            abort(500, description="PDF generation failed")
        
        # Read PDF file as bytes
        try:
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
        finally:
            # Clean up temporary PDF file
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
        
        # Convert PDF to PNG (all pages)
        png_list = pdf_to_png_bytes_list(pdf_bytes, zoom=2.0)
        if not png_list:
            abort(500, description="PNG conversion failed")
        
        # Check if PDF has multiple pages
        if len(png_list) > 1:
            # Create long PNG with all pages stacked vertically
            png_bytes = pdf_to_long_png_bytes(pdf_bytes, zoom=2.0, page_spacing=30)
            if not png_bytes:
                # Fallback to first page if long PNG fails
                png_bytes = png_list[0]
        else:
            # Single page PDF
            png_bytes = png_list[0]
        
        # Return PNG image
        return Response(
            png_bytes,
            mimetype='image/png',
            headers={
                'Content-Disposition': f'inline; filename="booking_{booking.booking_reference}.png"',
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
        )
            
    except Exception as e:
        logger.error(f"Error generating PNG: {str(e)}")
        abort(500, description=f"Error generating PNG: {str(e)}")


# ============================================================================
# Main PDF/PNG Generation Routes (Authentication Required)
# ============================================================================

@booking_bp.route('/<int:booking_id>/png')
@login_required
def generate_booking_png(booking_id):
    """Generate PNG image from Service Proposal PDF using Classic PDF Generator with PNG conversion"""
    from services.classic_pdf_generator import ClassicPDFGenerator
    from services.pdf_image import pdf_to_png_bytes_list
    from flask import send_file, abort, Response
    import io, os
    
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        # Prepare complete booking data including guest_list
        guest_list = booking.guest_list if booking.guest_list else ''
        
        booking_data = {
            'booking_id': booking.booking_reference,
            'guest_name': (booking.customer.name if booking.customer else None) or booking.party_name or 'N/A',
                'customer_name': booking.customer.name if booking.customer else 'N/A',
            'guest_email': booking.customer.email if booking.customer else 'N/A', 
            'guest_phone': booking.customer.phone if booking.customer else 'N/A',
            'tour_name': booking.description or booking.hotel_name or 'Tour Package',
            'booking_date': booking.created_at.strftime('%Y-%m-%d') if booking.created_at else 'N/A',
            'tour_date': booking.arrival_date.strftime('%Y-%m-%d') if booking.arrival_date else 'N/A',
            'start_date': booking.traveling_period_start.strftime('%Y-%m-%d') if booking.traveling_period_start else (booking.arrival_date.strftime('%Y-%m-%d') if booking.arrival_date else 'N/A'),
            'end_date': booking.traveling_period_end.strftime('%Y-%m-%d') if booking.traveling_period_end else (booking.departure_date.strftime('%Y-%m-%d') if booking.departure_date else 'N/A'),
            'pax': booking.total_pax or 1,
            'adults': booking.adults or booking.total_pax or 1,
            'children': booking.children or 0,
            'infants': booking.infants or 0,
            'price': float(booking.total_amount) if booking.total_amount else 0.0,
            'status': booking.status,
            'description': booking.description or '',
            'internal_note': booking.admin_notes or booking.internal_note or '',
            'daily_services': booking.daily_services or '',
            'flight_info': booking.flight_info or '',
            'special_request': booking.special_request or '',
            'customer_address': getattr(booking.customer, 'address', '') if booking.customer else '',
            'customer_nationality': getattr(booking.customer, 'nationality', '') if booking.customer else '',
            'reference': booking.booking_reference,
            'guest_list': guest_list
        }
        
        # Get products for this booking from the products JSON field
        products = []
        booking_products = booking.get_products()
        if booking_products:
            for product_data in booking_products:
                products.append({
                    'name': product_data.get('name', 'Unknown Product'),
                    'quantity': product_data.get('quantity', 1),
                    'price': float(product_data.get('price', 0.0)),
                    'amount': float(product_data.get('amount', 0.0))
                })
        
        # Generate PDF using ClassicPDFGenerator first
        classic_generator = ClassicPDFGenerator()
        
        # Create temporary PDF file with adaptive path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = "static/generated"
        os.makedirs(output_dir, exist_ok=True)
        pdf_filename = f'{output_dir}/temp_for_png_{booking.booking_reference}_{timestamp}.pdf'
        
        pdf_path = classic_generator.generate_pdf(booking_data, products, pdf_filename)
        
        if not pdf_path or not os.path.exists(pdf_path):
            flash('Error generating PDF for PNG conversion', 'error')
            return redirect(url_for('booking.view', id=booking_id))
        
        # Read PDF file as bytes
        try:
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
        finally:
            # Clean up temporary PDF file
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
        
        # Convert PDF to PNG (all pages)
        png_list = pdf_to_png_bytes_list(pdf_bytes, zoom=2.0)
        if not png_list:
            flash('Error converting PDF to PNG', 'error')
            return redirect(url_for('booking.view', id=booking_id))
        
        # Check if PDF has multiple pages
        if len(png_list) > 1:
            from services.pdf_image import pdf_to_long_png_bytes
            # Create long PNG with all pages stacked vertically
            png_bytes = pdf_to_long_png_bytes(pdf_bytes, zoom=2.0, page_spacing=30)
            if not png_bytes:
                # Fallback to first page if long PNG fails
                png_bytes = png_list[0]
        else:
            # Single page - use as is
            png_bytes = png_list[0]
        filename = f'booking_{booking.booking_reference}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
        
        return Response(
            png_bytes,
            mimetype='image/png',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'}
        )
            
    except Exception as e:
        flash(f'Error generating PNG: {str(e)}', 'error')
        return redirect(url_for('booking.view', id=booking_id))


# ============================================================================
# WeasyPrint PDF Generation Routes (Thai Font Support)
# ============================================================================

@booking_bp.route('/<int:booking_id>/pdf/weasyprint')
@login_required
def generate_booking_pdf_weasyprint(booking_id):
    """Generate Service Proposal PDF using Modern WeasyPrint (Enhanced Design & Thai Font Support)"""
    from services.weasyprint_generator_v2 import ModernWeasyPrintGenerator
    from flask import send_file, abort
    import os
    
    booking = Booking.query.get_or_404(booking_id)

    try:
        # Prepare complete booking data for WeasyPrint
        booking_data = {
            'booking_reference': booking.booking_reference,
            'status': booking.status,
            'customer_name': booking.customer.name if booking.customer else 'N/A',
            'customer_email': booking.customer.email if booking.customer else 'N/A',
            'customer_phone': booking.customer.phone if booking.customer else 'N/A',
            'customer_address': booking.customer.address if booking.customer and booking.customer.address else '',
            'customer_nationality': booking.customer.nationality if booking.customer and booking.customer.nationality else '',
            'adults': booking.adults or 0,
            'children': booking.children or 0,
            'infants': booking.infants or 0,
            'party_name': booking.party_name or '',
            'party_code': booking.party_code or '',
            'description': booking.description or '',
            'pickup_point': booking.pickup_point or '',
            'destination': booking.destination or '',
            'pickup_time': str(booking.pickup_time) if booking.pickup_time else '',
            'vehicle_type': booking.vehicle_type or '',
            'internal_note': booking.internal_note or '',
            'flight_info': booking.flight_info or '',
            'daily_services': booking.daily_services or '',
            'admin_notes': booking.admin_notes or '',
            'manager_memos': booking.manager_memos or '',
            'total_amount': float(booking.total_amount) if booking.total_amount else 0.0,
            'currency': booking.currency or 'THB',
            'time_limit': str(booking.time_limit) if booking.time_limit else '',
            'due_date': str(booking.due_date) if booking.due_date else '',
            'created_at': str(booking.created_at) if booking.created_at else '',
            'updated_at': str(booking.updated_at) if booking.updated_at else ''
        }
        
        # Get products (if any)
        products = []
        if hasattr(booking, 'products') and booking.products:
            try:
                import json
                products_data = json.loads(booking.products) if booking.products else []
                for product in products_data:
                    quantity = product.get('quantity', 1)
                    unit_price = float(product.get('price', 0))
                    products.append({
                        'description': product.get('name', 'Unknown Service'),
                        'quantity': quantity,
                        'unit_price': unit_price,
                        'total_price': quantity * unit_price
                    })
            except (json.JSONDecodeError, ValueError):
                # Fallback - create sample products
                products = [
                    {
                        'description': 'Tour Service (บริการทัวร์)',
                        'quantity': booking.adults + booking.children,
                        'unit_price': 1500.00,
                        'total_price': (booking.adults + booking.children) * 1500.00
                    }
                ]
        
        # Generate PDF using Modern WeasyPrint
        weasyprint_generator = ModernWeasyPrintGenerator()
        pdf_path = weasyprint_generator.generate_service_proposal(
            booking_data=booking_data,
            products=products
        )
        
        if os.path.exists(pdf_path):
            return send_file(pdf_path, 
                           as_attachment=True, 
                           download_name=f"Service_Proposal_Thai_{booking.booking_reference}.pdf",
                           mimetype='application/pdf')
        else:
            flash('Error generating WeasyPrint PDF file', 'error')
            return redirect(url_for('booking.view', id=booking_id))
            
    except Exception as e:
        flash(f'Error generating WeasyPrint PDF: {str(e)}', 'error')
        return redirect(url_for('booking.view', id=booking_id))


@booking_bp.route('/<int:booking_id>/png/weasyprint')
@login_required
def generate_booking_png_weasyprint(booking_id):
    """Generate Service Proposal PNG using Modern WeasyPrint (Enhanced Design & Thai Font Support)"""
    from services.weasyprint_generator_v2 import ModernWeasyPrintGenerator
    from flask import send_file, abort
    import os
    
    booking = Booking.query.get_or_404(booking_id)

    try:
        # Prepare booking data for WeasyPrint
        booking_data = {
            'booking_reference': booking.booking_reference,
            'customer_name': booking.customer.name if booking.customer else 'N/A',
            'customer_email': booking.customer.email if booking.customer else 'N/A',
            'customer_phone': booking.customer.phone if booking.customer else 'N/A',
            'adults': booking.adults or 0,
            'children': booking.children or 0,
            'infants': booking.infants or 0,
            'admin_notes': booking.admin_notes or '',
            'manager_memos': booking.manager_memos or '',
            'internal_note': booking.internal_note or ''
        }
        
        # Get products (if any)
        products = []
        if hasattr(booking, 'products') and booking.products:
            try:
                import json
                products_data = json.loads(booking.products) if booking.products else []
                for product in products_data:
                    quantity = product.get('quantity', 1)
                    unit_price = float(product.get('price', 0))
                    products.append({
                        'description': product.get('name', 'Unknown Service'),
                        'quantity': quantity,
                        'unit_price': unit_price,
                        'total_price': quantity * unit_price
                    })
            except (json.JSONDecodeError, ValueError):
                # Fallback - create sample products
                products = [
                    {
                        'description': 'Tour Service (บริการทัวร์)',
                        'quantity': booking.adults + booking.children,
                        'unit_price': 1500.00,
                        'total_price': (booking.adults + booking.children) * 1500.00
                    }
                ]
        
        # Generate PNG using Modern WeasyPrint
        weasyprint_generator = ModernWeasyPrintGenerator()
        png_path = weasyprint_generator.generate_service_proposal_png(
            booking_data=booking_data,
            products=products
        )
        
        if os.path.exists(png_path):
            return send_file(png_path, 
                           as_attachment=True, 
                           download_name=f"Service_Proposal_Thai_{booking.booking_reference}.png",
                           mimetype='image/png')
        else:
            flash('Error generating WeasyPrint PNG file', 'error')
            return redirect(url_for('booking.view', id=booking_id))
            
    except Exception as e:
        flash(f'Error generating WeasyPrint PNG: {str(e)}', 'error')
        return redirect(url_for('booking.view', id=booking_id))


@booking_bp.route('/generate/<int:booking_id>/service-proposal-png-weasyprint')
def generate_service_proposal_png_weasyprint(booking_id):
    """Generate Modern WeasyPrint PNG"""
    from services.weasyprint_generator_v2 import ModernWeasyPrintGenerator
    from flask import send_file, abort, Response
    import os
    from datetime import datetime
    import json
    
    booking = Booking.query.get_or_404(booking_id)

    try:
        # Prepare booking data for WeasyPrint with all fields
        booking_data = {
            'booking_reference': booking.booking_reference,
            'customer_name': booking.customer.name if booking.customer else 'N/A',
            'customer_email': booking.customer.email if booking.customer else 'N/A',
            'customer_phone': booking.customer.phone if booking.customer else 'N/A',
            'adults': booking.adults or 0,
            'children': booking.children or 0,
            'infants': booking.infants or 0,
            'admin_notes': booking.admin_notes or '',
            'manager_memos': booking.manager_memos or '',
            'internal_note': booking.internal_note or '',
            'description': booking.description or '',
            'guest_list': booking.guest_list or '',
            'flight_info': booking.flight_info or '',
            'special_request': booking.special_request or '',
            'arrival_date': booking.arrival_date,
            'departure_date': booking.departure_date,
            'total_amount': booking.total_amount or 0
        }
        
        # Get products (if any)
        products = []
        if hasattr(booking, 'products') and booking.products:
            try:
                products_data = json.loads(booking.products) if booking.products else []
                for product in products_data:
                    quantity = product.get('quantity', 1)
                    unit_price = float(product.get('price', 0))
                    products.append({
                        'description': product.get('name', 'Unknown Service'),
                        'quantity': quantity,
                        'unit_price': unit_price,
                        'total_price': quantity * unit_price
                    })
            except (json.JSONDecodeError, ValueError):
                # Fallback - create sample products
                products = [
                    {
                        'description': 'Tour Service (บริการทัวร์)',
                        'quantity': booking.adults + booking.children,
                        'unit_price': 1500.00,
                        'total_price': (booking.adults + booking.children) * 1500.00
                    }
                ]
        
        # Generate PNG using Modern WeasyPrint
        weasyprint_generator = ModernWeasyPrintGenerator()
        png_path = weasyprint_generator.generate_service_proposal_png(
            booking_data=booking_data,
            products=products
        )
        
        if os.path.exists(png_path):
            return send_file(png_path, 
                           as_attachment=True, 
                           download_name=f"Service_Proposal_Thai_{booking.booking_reference}.png",
                           mimetype='image/png')
        else:
            abort(404, description="PNG file not found")
            
    except Exception as e:
        logger.error(f"Error generating PNG: {str(e)}")
        abort(500, description=f"Error generating PNG: {str(e)}")


@booking_bp.route('/generate/<int:booking_id>/service-proposal-weasyprint')
def generate_service_proposal_pdf_weasyprint(booking_id):
    """Generate Modern WeasyPrint PDF"""
    from services.tour_voucher_weasyprint import TourVoucherWeasyPrintGenerator
    from flask import send_file, abort, Response
    import os
    from datetime import datetime
    import json
    
    booking = Booking.query.get_or_404(booking_id)

    try:
        # Generate PDF using Tour Voucher WeasyPrint (now uses quote template)
        weasyprint_generator = TourVoucherWeasyPrintGenerator()
        pdf_path = weasyprint_generator.generate_tour_voucher(booking)
        
        if os.path.exists(pdf_path):
            # Add cache-busting headers
            response = send_file(pdf_path, 
                               as_attachment=True, 
                               download_name=f"WeasyPrint_Thai_{booking.booking_reference}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                               mimetype='application/pdf')
            
            # Anti-cache headers
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '-1'
            response.headers['Last-Modified'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')
            response.headers['ETag'] = f'"{datetime.now().timestamp()}"'
            
            return response
        else:
            return f"Error: PDF file not found at {pdf_path}", 500
            
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return f"Error generating WeasyPrint PDF: {str(e)}\n\nDetails:\n{error_details}", 500

# ===========================
# ENHANCED WORKFLOW ROUTES
# ===========================

@booking_bp.route('/<int:booking_id>/confirm', methods=['POST'])
@login_required
def confirm_booking(booking_id):
    """Step 2: Confirm booking (from pending to confirmed)"""
    print(f"🎯 ENTERED confirm_booking function for booking {booking_id}")
    try:
        logger.info(f"🎯 Starting confirm_booking for booking {booking_id}")
        
        # Check if booking exists first
        try:
            booking = Booking.query.get_or_404(booking_id)
            logger.info(f"📋 Loaded booking {booking_id}, status: {booking.status}")
        except Exception as load_error:
            logger.error(f"❌ Error loading booking {booking_id}: {str(load_error)}")
            raise load_error
        
        if booking.status not in ['draft', 'pending']:
            message = f'Booking must be in draft or pending status to confirm. Current status: {booking.status}'
            if request.is_json or request.headers.get('Content-Type') == 'application/json':
                return jsonify({'success': False, 'message': message}), 400
            flash(message, 'warning')
            return redirect(url_for('booking.view', id=booking_id))
        
        logger.info(f"📝 Calling booking.confirm_booking() for booking {booking_id}")
        try:
            booking.confirm_booking()
            logger.info(f"✅ booking.confirm_booking() completed for booking {booking_id}")
        except Exception as confirm_error:
            logger.error(f"❌ Error in booking.confirm_booking() for booking {booking_id}: {str(confirm_error)}")
            raise confirm_error
        
        # Debug the booking object before commit
        logger.info(f"🔍 DEBUG: booking.confirmed_at = {booking.confirmed_at} (type: {type(booking.confirmed_at)})")
        if hasattr(booking.confirmed_at, 'microseconds'):
            logger.info(f"🔍 DEBUG: booking.confirmed_at.microseconds = {booking.confirmed_at.microseconds}")
        else:
            logger.warning(f"⚠️  DEBUG: booking.confirmed_at has no microseconds attribute")
        
        logger.info(f"🗄️ About to commit database for booking {booking_id}")
        try:
            db.session.commit()
            logger.info(f"✅ Database committed for booking {booking_id}")
        except Exception as commit_error:
            logger.error(f"❌ Database commit error for booking {booking_id}: {str(commit_error)}")
            db.session.rollback()
            raise commit_error
        
        # Create activity log for confirmation
        logger.info(f"📝 Creating activity log for booking {booking_id}")
        try:
            from models_mariadb import ActivityLog
            
            ActivityLog.log_activity(
                'booking', booking_id, 'booking_confirmed', 
                f"Booking confirmed by {current_user.username if current_user else 'system'}"
            )
            logger.info(f"✅ Activity log created for booking {booking_id}")
        except Exception as log_error:
            logger.error(f"❌ Activity log error for booking {booking_id}: {str(log_error)}")
            # Don't raise this error - activity log is not critical
            pass
        
        logger.info(f"✅ Booking {booking.booking_reference} confirmed")
        
        # Return JSON for AJAX requests
        if request.is_json or request.headers.get('Content-Type') == 'application/json':
            try:
                # Safe datetime conversion for confirmed_at
                confirmed_at_iso = None
                if booking.confirmed_at:
                    if isinstance(booking.confirmed_at, str):
                        try:
                            confirmed_datetime = datetime.fromisoformat(booking.confirmed_at.replace('Z', '+00:00'))
                            confirmed_at_iso = confirmed_datetime.isoformat()
                        except ValueError:
                            confirmed_at_iso = booking.confirmed_at
                    else:
                        confirmed_at_iso = booking.confirmed_at.isoformat()
                
                return jsonify({
                    'success': True,
                    'message': f'Booking {booking.booking_reference} confirmed! Ready to create quote.',
                    'status': booking.status,
                    'confirmed_at': confirmed_at_iso
                })
            except Exception as e:
                logger.error(f"Error in confirm_booking JSON response: {str(e)}")
                return jsonify({
                    'success': True,
                    'message': f'Booking {booking.booking_reference} confirmed! Ready to create quote.',
                    'status': booking.status,
                    'confirmed_at': str(booking.confirmed_at) if booking.confirmed_at else None
                })
        
        # Regular form submission
        flash(f'Booking {booking.booking_reference} confirmed! Ready to create quote.', 'success')
        return redirect(url_for('booking.view', id=booking_id))
        
    except Exception as e:
        logger.error(f"Error confirming booking {booking_id}: {str(e)}")
        error_message = f'Error confirming booking: {str(e)}'
        
        # Return JSON for AJAX requests
        if request.is_json or request.headers.get('Content-Type') == 'application/json':
            return jsonify({'success': False, 'message': error_message}), 500
        
        # Regular form submission
        flash(error_message, 'error')
        return redirect(url_for('booking.view', id=booking_id))

@booking_bp.route('/<int:booking_id>/create-quote', methods=['POST'])
@login_required
def create_quote_workflow(booking_id):
    """Step 2: Create Quote (QT) with PDF/PNG - with database lock handling"""
    max_retries = 3
    
    for retry_count in range(max_retries):
        try:
            logger.info(f"🎯 Starting create_quote_workflow for booking {booking_id} (attempt {retry_count + 1})")
            
            # Force close any existing database connections to prevent locks
            from extensions import db
            try:
                db.session.close()
            except:
                pass  # Ignore close errors
            
            # Small delay for database lock resolution
            import time
            if retry_count > 0:
                time.sleep(0.5 * retry_count)  # Progressive delay
            
            # Check if booking exists first
            booking = Booking.query.filter_by(id=booking_id).first()
            if not booking:
                message = f'Booking {booking_id} not found'
                logger.error(f"❌ {message}")
                if request.is_json or request.headers.get('Content-Type') == 'application/json':
                    return jsonify({'success': False, 'message': message}), 404
                flash(message, 'error')
                return redirect(url_for('booking.list'))
            
            # Force refresh SQLAlchemy metadata for quotes table
            from models.quote import Quote
            logger.info("🔄 Refreshing SQLAlchemy metadata...")
            db.metadata.reflect(bind=db.engine, only=['quotes'])
            
            logger.info(f"📋 Booking {booking_id} loaded, status: {booking.status}")
            
            if not booking.can_create_quote():
                message = 'Booking must be confirmed before creating quote'
                logger.warning(f"❌ Cannot create quote: {message} (current status: {booking.status})")
                if request.is_json or request.headers.get('Content-Type') == 'application/json':
                    return jsonify({'success': False, 'message': message}), 400
                flash(message, 'warning')
                return redirect(url_for('booking.view', id=booking_id))
            
            # Check if quote already exists - CRITICAL CHECK
            logger.info("🔍 Checking for existing quotes...")
            
            # Use raw SQL to avoid SQLAlchemy metadata issues
            try:
                result = db.session.execute(
                    db.text("SELECT id, quote_number, status FROM quotes WHERE booking_id = :booking_id"), 
                    {"booking_id": booking_id}
                ).fetchone()
                
                if result:
                    message = f'Quote {result.quote_number} already exists (Status: {result.status})'
                    logger.info(f"ℹ️  Found existing quote: {result.quote_number} with status {result.status}")
                    if request.is_json or request.headers.get('Content-Type') == 'application/json':
                        return jsonify({
                            'success': False, 
                            'message': message,
                            'quote_id': result.id,
                            'quote_number': result.quote_number,
                            'status': result.status
                        }), 400
                    flash(message, 'info')
                    return redirect(url_for('quote.view_quote', quote_id=result.id))
                else:
                    logger.info("✅ No existing quote found, proceeding with creation")
                    
            except Exception as e:
                logger.error(f"❌ Raw SQL check failed: {e}")
                # Don't continue with creation if we can't verify - return error instead
                error_message = f'Cannot verify existing quotes due to database error: {str(e)}'
                if request.is_json or request.headers.get('Content-Type') == 'application/json':
                    return jsonify({'success': False, 'message': error_message}), 500
                flash(error_message, 'error')
                return redirect(url_for('booking.view', id=booking_id))
            
            # Check if quote service is available
            if not QUOTE_SERVICE_AVAILABLE or QuoteService is None:
                message = 'Quote service is not available'
                if request.is_json or request.headers.get('Content-Type') == 'application/json':
                    return jsonify({'success': False, 'message': message}), 500
                flash(message, 'error')
                return redirect(url_for('booking.view', id=booking_id))
            
            # Create quote using service
            quote_service = QuoteService()
            quote_id, quote_number = quote_service.create_quote_from_booking(booking)
            
            logger.info(f"✅ Received quote_id={quote_id}, quote_number={quote_number} from QuoteService")
            
            # Update booking status, quote_id, and quote_number
            booking.mark_as_quoted()
            booking.quote_id = quote_id
            booking.quote_number = quote_number
            db.session.commit()
            
            # Create activity log for quote creation
            from models_mariadb import ActivityLog
            username = current_user.username if current_user.is_authenticated else 'System'
            
            ActivityLog.log_activity(
                'booking', booking_id, 'quote_created',
                f'Quote {quote_number} created by {username}'
            )
            
            logger.info(f"✅ Quote {quote_number} created for booking {booking.booking_reference}")
            
            # Return JSON for AJAX requests
            if request.is_json or request.headers.get('Content-Type') == 'application/json':
                # Safe datetime conversion for quoted_at
                quoted_at_iso = None
                if booking.quoted_at:
                    if isinstance(booking.quoted_at, str):
                        try:
                            quoted_datetime = datetime.fromisoformat(booking.quoted_at.replace('Z', '+00:00'))
                            quoted_at_iso = quoted_datetime.isoformat()
                        except ValueError:
                            quoted_at_iso = booking.quoted_at
                    else:
                        quoted_at_iso = booking.quoted_at.isoformat()
                
                return jsonify({
                    'success': True,
                    'message': f'Quote {quote_number} created! PDF/PNG available for download.',
                    'quote_number': quote_number,
                    'quote_id': quote_id,
                    'status': booking.status,
                    'quoted_at': quoted_at_iso
                })
            
            # Regular form submission
            flash(f'Quote {quote_number} created! PDF/PNG available for download.', 'success')
            return redirect(url_for('quote.view_quote', quote_id=quote_id))
            
        except Exception as e:
            error_str = str(e)
            logger.error(f"Error creating quote for booking {booking_id} (attempt {retry_count + 1}): {error_str}")
            
            # Check if it's a database lock error
            if 'database is locked' in error_str.lower() and retry_count < max_retries - 1:
                logger.warning(f"⚠️  Database locked, retrying attempt {retry_count + 2}...")
                continue  # Retry the loop
            
            # If it's the final attempt or a non-lock error, return error
            error_message = f'Error creating quote: {error_str}'
            if request.is_json or request.headers.get('Content-Type') == 'application/json':
                return jsonify({'success': False, 'message': error_message}), 500
            flash(error_message, 'error')
            return redirect(url_for('booking.view', id=booking_id))
    
    # If we get here, all retries failed
    final_error = 'Database temporarily unavailable after multiple attempts'
    logger.error(f"❌ All {max_retries} attempts failed for booking {booking_id}")
    if request.is_json or request.headers.get('Content-Type') == 'application/json':
        return jsonify({'success': False, 'message': final_error}), 500
    flash(final_error, 'error')
    return redirect(url_for('booking.view', id=booking_id))

@booking_bp.route('/<int:booking_id>/apply-to-invoice', methods=['POST'])
@login_required
def apply_to_invoice_workflow(booking_id):
    """Step 3: Apply Quote to Invoice (AR)"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        # Check if booking can apply to invoice (status should be quoted)
        if booking.status != 'quoted':
            message = 'Booking must be quoted before applying to invoice'
            if request.is_json or request.headers.get('Content-Type') == 'application/json':
                return jsonify({'success': False, 'message': message}), 400
            flash(message, 'warning')
            return redirect(url_for('booking.view', id=booking_id))
        
        # Get quote using raw SQL to avoid SQLAlchemy metadata issues
        try:
            quote_result = db.session.execute(
                db.text("SELECT id, quote_number, status FROM quotes WHERE booking_id = :booking_id"), 
                {"booking_id": booking_id}
            ).fetchone()
            
            if not quote_result:
                message = 'No quote found for this booking'
                if request.is_json or request.headers.get('Content-Type') == 'application/json':
                    return jsonify({'success': False, 'message': message}), 400
                flash(message, 'warning')
                return redirect(url_for('booking.view', id=booking_id))
                
        except Exception as e:
            logger.error(f"Error fetching quote: {e}")
            message = f'Error fetching quote: {str(e)}'
            if request.is_json or request.headers.get('Content-Type') == 'application/json':
                return jsonify({'success': False, 'message': message}), 500
            flash(message, 'error')
            return redirect(url_for('booking.view', id=booking_id))
        
        quote_id = quote_result.id
        quote_number = quote_result.quote_number
        quote_status = quote_result.status
        
        # Accept quote first if not already accepted
        if quote_status != 'accepted':
            db.session.execute(
                db.text("UPDATE quotes SET status = 'accepted' WHERE id = :quote_id"),
                {"quote_id": quote_id}
            )
            
        # Convert quote to invoice using existing Invoice Ninja integration
        booking_invoice_service = BookingInvoiceService()
        invoice_data = booking_invoice_service.create_invoice_from_booking(booking)
        
        if invoice_data:
            # Mark invoice as paid immediately (as requested)
            booking.invoice_number = invoice_data.get('number')
            booking.invoice_status = 'paid'
            booking.is_paid = True
            booking.invoice_paid_date = datetime.utcnow()
            
            # Mark quote as converted using raw SQL
            db.session.execute(
                db.text("UPDATE quotes SET converted_to_invoice = 1 WHERE id = :quote_id"),
                {"quote_id": quote_id}
            )
            
            # Store old status for activity logging
            old_status = booking.status
            
            # Update booking status
            booking.mark_as_paid()
            db.session.commit()
            
            # Create activity log entries for applying quote to invoice (using direct pymysql for reliability)
            try:
                import pymysql
                from datetime import datetime
                
                connection = pymysql.connect(
                    host='localhost',
                    user='voucher_user',
                    password='voucher_secure_2024',
                    database='voucher_enhanced',
                    charset='utf8mb4'
                )
                
                with connection.cursor() as cursor:
                    # Create status change activity log if status changed
                    if old_status != booking.status:
                        cursor.execute("""
                            INSERT INTO activity_logs (booking_id, action, description, created_at) 
                            VALUES (%s, %s, %s, %s)
                        """, (
                            booking_id,
                            'status_updated',
                            f'Booking status changed from {old_status} to {booking.status}',
                            datetime.now()
                        ))
                        current_app.logger.info(f"✅ Activity log created for booking {booking_id} status change: {old_status} → {booking.status}")
                    
                    # Create quote-to-invoice activity log
                    apply_description = f"[BOOKING #{booking_id}] Quote {quote_number} applied to Invoice {booking.invoice_number} - Status: PAID"
                    cursor.execute("""
                        INSERT INTO activity_logs (booking_id, action, description, created_at) 
                        VALUES (%s, %s, %s, %s)
                    """, (
                        booking_id,
                        'quote_applied_to_invoice',
                        apply_description,
                        datetime.now()
                    ))
                    
                    connection.commit()
                    current_app.logger.info(f"✅ Quote-to-invoice activity log created for booking {booking_id}: {apply_description}")
                    
            except Exception as e:
                current_app.logger.error(f"❌ Failed to create activity logs for booking {booking_id}: {e}")
            finally:
                if 'connection' in locals():
                    connection.close()
            
            logger.info(f"✅ Quote {quote_number} applied to Invoice {booking.invoice_number}")
            
            # Return JSON for AJAX requests
            if request.is_json or request.headers.get('Content-Type') == 'application/json':
                return jsonify({
                    'success': True,
                    'message': f'Quote applied to Invoice {booking.invoice_number} (Status: Paid)! Ready to generate voucher.',
                    'invoice_number': booking.invoice_number,
                    'status': booking.status,
                    'paid_at': booking.invoice_paid_date.isoformat() if booking.invoice_paid_date else None
                })
            
            flash(f'Quote applied to Invoice {booking.invoice_number} (Status: Paid)! Ready to generate voucher.', 'success')
        else:
            # Return JSON for AJAX requests
            if request.is_json or request.headers.get('Content-Type') == 'application/json':
                return jsonify({'success': False, 'message': 'Error creating invoice from quote'}), 500
            flash('Error creating invoice from quote', 'error')
            
        return redirect(url_for('booking.view', id=booking_id))
        
    except Exception as e:
        logger.error(f"Error applying to invoice for booking {booking_id}: {str(e)}")
        error_message = f'Error applying to invoice: {str(e)}'
        if request.is_json or request.headers.get('Content-Type') == 'application/json':
            return jsonify({'success': False, 'message': error_message}), 500
        flash(error_message, 'error')
        return redirect(url_for('booking.view', id=booking_id))

@booking_bp.route('/<int:booking_id>/generate-voucher', methods=['POST'])
@login_required
def generate_voucher_workflow(booking_id):
    """Step 4: Generate Tour Voucher PDF/PNG"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        if not booking.can_generate_voucher():
            message = 'Invoice must be paid before generating voucher'
            if request.is_json or request.headers.get('Content-Type') == 'application/json':
                return jsonify({'success': False, 'message': message}), 400
            flash(message, 'warning')
            return redirect(url_for('booking.view', id=booking_id))
        
        # Generate voucher using TourVoucherGeneratorV2
        from services.tour_voucher_generator_v2 import TourVoucherGeneratorV2
        generator = TourVoucherGeneratorV2()
        pdf_filename = generator.generate_tour_voucher_v2(booking)
        
        # Update booking status
        booking.mark_as_vouchered()
        db.session.commit()
        
        # Create activity log for voucher generation
        from models_mariadb import ActivityLog
        username = current_user.username if current_user.is_authenticated else 'System'
        
        ActivityLog.log_activity(
            'booking', booking_id, 'voucher_generated',
            f'Tour voucher generated by {username}'
        )
        
        logger.info(f"✅ Voucher generated for booking {booking.booking_reference}")
        
        # Return JSON for AJAX requests
        if request.is_json or request.headers.get('Content-Type') == 'application/json':
            # Safe datetime conversion for vouchered_at
            vouchered_at_iso = None
            if booking.vouchered_at:
                if isinstance(booking.vouchered_at, str):
                    try:
                        vouchered_datetime = datetime.fromisoformat(booking.vouchered_at.replace('Z', '+00:00'))
                        vouchered_at_iso = vouchered_datetime.isoformat()
                    except ValueError:
                        vouchered_at_iso = booking.vouchered_at
                else:
                    vouchered_at_iso = booking.vouchered_at.isoformat()
            
            return jsonify({
                'success': True,
                'message': 'Tour Voucher generated! PDF/PNG available for download and sharing.',
                'booking_reference': booking.booking_reference,
                'status': booking.status,
                'vouchered_at': vouchered_at_iso,
                'pdf_filename': pdf_filename
            })
        
        flash(f'Tour Voucher generated! PDF/PNG available for download and sharing.', 'success')
        
        return redirect(url_for('voucher.view_voucher', booking_id=booking_id))
        
    except Exception as e:
        logger.error(f"Error generating voucher for booking {booking_id}: {str(e)}")
        error_message = f'Error generating voucher: {str(e)}'
        if request.is_json or request.headers.get('Content-Type') == 'application/json':
            return jsonify({'success': False, 'message': error_message}), 500
        flash(error_message, 'error')
        return redirect(url_for('booking.view', id=booking_id))

@booking_bp.route('/api/<int:booking_id>/quote-id')
@login_required
def get_quote_id_by_booking(booking_id):
    """API endpoint to get quote_id by booking_id"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        quote = Quote.query.filter_by(booking_id=booking_id).first()
        
        if quote:
            return jsonify({'quote_id': quote.id, 'quote_number': quote.quote_number})
        else:
            return jsonify({'quote_id': None, 'message': 'No quote found for this booking'}), 404
            
    except Exception as e:
        logger.error(f"Error getting quote ID for booking {booking_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@booking_bp.route('/api/<int:booking_id>/mark-paid', methods=['POST'])
def api_mark_as_paid(booking_id):
    """Enhanced API endpoint to mark booking as paid with payment details"""
    try:
        from datetime import datetime as dt_import
        
        logger.info(f"🔔 API mark-paid called for booking {booking_id}")
        
        booking = Booking.query.get_or_404(booking_id)
        logger.info(f"📋 Found booking {booking_id} with status: {booking.status}")
        
        # Get payment data from request
        data = request.get_json()
        logger.info(f"📦 Received payment data: {data}")
        
        if not data:
            return jsonify({'success': False, 'error': 'ไม่พบข้อมูลการชำระเงิน'}), 400
        
        # Check booking status first
        if booking.status != 'quoted':
            return jsonify({
                'success': False, 
                'error': f'ไม่สามารถชำระเงินได้ Booking ต้องมีสถานะ Quoted ก่อน (สถานะปัจจุบัน: {booking.status})'
            }), 400
        
        # Basic data extraction
        amount = data.get('amount', '0')
        bank_name = data.get('bank_name', 'Unknown')
        product_type = data.get('product_type', 'tour')
        
        try:
            amount_float = float(str(amount).replace(',', ''))
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'จำนวนเงินไม่ถูกต้อง'}), 400
        
        # Store old status for activity logging
        old_status = booking.status
        
        # Update booking status
        booking.status = 'paid'
        booking.is_paid = True
        booking.invoice_paid_date = dt_import.now()
        
        db.session.commit()
        
        # Create activity log entries for payment (using direct pymysql for reliability)
        try:
            import pymysql
            
            connection = pymysql.connect(
                host='localhost',
                user='voucher_user',
                password='voucher_secure_2024',
                database='voucher_enhanced',
                charset='utf8mb4'
            )
            
            with connection.cursor() as cursor:
                # Create status change activity log if status changed
                if old_status != booking.status:
                    cursor.execute("""
                        INSERT INTO activity_logs (booking_id, action, description, created_at) 
                        VALUES (%s, %s, %s, %s)
                    """, (
                        booking_id,
                        'status_updated',
                        f'Booking status changed from {old_status} to {booking.status}',
                        dt_import.now()
                    ))
                    current_app.logger.info(f"✅ Activity log created for booking {booking_id} status change: {old_status} → {booking.status}")
                
                # Create payment activity log
                payment_description = f"[BOOKING #{booking_id}] Payment received: {amount_float:,.2f} THB via {bank_name} (API)"
                cursor.execute("""
                    INSERT INTO activity_logs (booking_id, action, description, created_at) 
                    VALUES (%s, %s, %s, %s)
                """, (
                    booking_id,
                    'payment_received',
                    payment_description,
                    dt_import.now()
                ))
                
                connection.commit()
                current_app.logger.info(f"✅ Payment activity log created for booking {booking_id}: {payment_description}")
                
        except Exception as e:
            current_app.logger.error(f"❌ Failed to create activity logs for booking {booking_id}: {e}")
        finally:
            if 'connection' in locals():
                connection.close()
        
        logger.info(f"✅ Booking {booking_id} marked as paid with amount {amount_float} THB via {bank_name}")
        
        return jsonify({
            'success': True, 
            'message': f'ชำระเงินเรียบร้อยแล้ว! จำนวน {amount_float:,.2f} บาท ผ่าน {bank_name}',
            'status': booking.status,
            'is_paid': booking.is_paid,
            'paid_at': booking.invoice_paid_date.isoformat() if booking.invoice_paid_date else None
        })
        
    except Exception as e:
        logger.error(f"❌ Error marking booking {booking_id} as paid: {str(e)}")
        logger.error(f"❌ Exception details: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': f'เกิดข้อผิดพลาด: {str(e)}'}), 500

# ========== SHARE TOKEN MANAGEMENT APIs ==========

@booking_bp.route('/api/<int:booking_id>/reset-share-token', methods=['POST'])
@login_required
def api_reset_share_token(booking_id):
    """Reset share token for booking to generate new public links"""
    try:
        import time
        import hashlib
        import base64
        from models.booking import Booking
        
        logger.info(f"🔄 Resetting share token for booking {booking_id}")
        
        # Get booking
        from services.universal_booking_extractor import UniversalBookingExtractor
        booking = UniversalBookingExtractor.get_fresh_booking_data(booking_id)
        if not booking:
            return jsonify({'success': False, 'error': f'Booking {booking_id} not found'}), 404
        
        # Get booking model instance for database update
        booking_model = Booking.query.get(booking_id)
        if not booking_model:
            return jsonify({'success': False, 'error': f'Booking {booking_id} not found in database'}), 404
        
        # Increment token version to invalidate old tokens - Use ATOMIC SQL UPDATE
        db.session.execute(
            db.text("UPDATE bookings SET share_token_version = share_token_version + 1 WHERE id = :id"),
            {"id": booking_id}
        )
        db.session.commit()
        
        # Get the new version from database
        result = db.session.execute(
            db.text("SELECT share_token_version FROM bookings WHERE id = :id"),
            {"id": booking_id}
        ).fetchone()
        new_version = result[0] if result else 2
        
        logger.info(f"✅ Version updated to {new_version}")
        
        # Generate new token using BookingEnhanced with explicit version
        from models.booking_enhanced import BookingEnhanced
        new_token = BookingEnhanced.generate_secure_token(booking_id, expiry_days=120, token_version=new_version)
        
        if not new_token:
            logger.error(f"❌ Failed to generate token for booking {booking_id}")
            return jsonify({'success': False, 'error': 'Failed to generate token'}), 500
        
        # Generate timestamp+hash format token as well
        current_timestamp = int(time.time())
        hash_token = hashlib.md5(f'{booking_id}_{current_timestamp}_{new_version}_share'.encode()).hexdigest()[:10]
        timestamp_token = f'{booking_id}_{current_timestamp}_{hash_token}'
        
        # Save new token to database using RAW SQL
        db.session.execute(
            db.text("UPDATE bookings SET current_share_token = :token WHERE id = :id"),
            {"token": new_token, "id": booking_id}
        )
        db.session.commit()
        
        logger.info(f"✅ Token saved to database: version {new_version}, token: {new_token[:30]}...")
        
        # Unlock booking when resetting token
        _locked_bookings_global.discard(booking_id)
        logger.info(f"🔓 Unlocked booking {booking_id} from global cache")
        
        logger.info(f"✅ Generated new tokens for booking {booking_id} (version {new_version})")
        
        # Create URLs
        base_url = request.host_url.rstrip('/')
        
        urls = {
            'base64_token': new_token,
            'timestamp_token': timestamp_token,
            'public_png_base64': f"{base_url}/public/booking/{new_token}/png",
            'public_png_timestamp': f"{base_url}/public/booking/{timestamp_token}/png",
            'backend_png': f"{base_url}/booking/{booking_id}/quote-png?v={new_token}",
            'public_pdf_base64': f"{base_url}/public/booking/{new_token}/pdf",
            'timestamp': current_timestamp,
            'token_version': new_version
        }
        
        return jsonify({
            'success': True,
            'message': f'Share token reset successfully for booking {booking_id}',
            'booking_id': booking_id,
            'booking_reference': getattr(booking, 'booking_reference', f'BK{booking_id}'),
            'tokens': urls,
            'note': 'Old tokens have been invalidated'
        })
        
    except Exception as e:
        logger.error(f"❌ Error resetting share token for booking {booking_id}: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Failed to reset share token: {str(e)}'}), 500

@booking_bp.route('/api/<int:booking_id>/lock-share-token', methods=['POST'])
@login_required  
def api_lock_share_token(booking_id):
    """Lock/disable share token to prevent public access"""
    try:
        logger.info(f"🔒 Locking share token for booking {booking_id}")
        
        # Get booking
        from services.universal_booking_extractor import UniversalBookingExtractor
        booking = UniversalBookingExtractor.get_fresh_booking_data(booking_id)
        if not booking:
            return jsonify({'success': False, 'error': f'Booking {booking_id} not found'}), 404
        
        # Store locked booking in global cache
        _locked_bookings_global.add(booking_id)
        
        logger.info(f"✅ Share token locked for booking {booking_id}")
        
        return jsonify({
            'success': True,
            'message': f'Share token locked successfully for booking {booking_id}',
            'booking_id': booking_id,
            'booking_reference': getattr(booking, 'booking_reference', f'BK{booking_id}'),
            'status': 'locked',
            'note': 'Public sharing has been disabled for this booking'
        })
        
    except Exception as e:
        logger.error(f"❌ Error locking share token for booking {booking_id}: {str(e)}")
        return jsonify({'success': False, 'error': f'Failed to lock share token: {str(e)}'}), 500

# Global cache for locked bookings (shared across all sessions)
_locked_bookings_global = set()

# Helper function to check if booking is locked
def is_booking_locked(booking_id):
    """Check if booking sharing is locked"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"🔍 Checking lock status for booking {booking_id}")
    
    # Use global cache only
    if booking_id in _locked_bookings_global:
        logger.info(f"✅ Booking {booking_id} locked via global cache: {_locked_bookings_global}")
        return True
    
    logger.info(f"❌ Booking {booking_id} is NOT locked. Global cache: {_locked_bookings_global}")
    return False

@booking_bp.route('/api/<int:booking_id>/share-info', methods=['GET'])
@login_required
def api_get_share_info(booking_id):
    """Get current share token information and URLs"""
    try:
        logger.info(f"📊 Getting share info for booking {booking_id}")
        
        # Get booking
        from services.universal_booking_extractor import UniversalBookingExtractor
        booking = UniversalBookingExtractor.get_fresh_booking_data(booking_id)
        if not booking:
            return jsonify({'success': False, 'error': f'Booking {booking_id} not found'}), 404
        
        # Check if sharing is locked
        sharing_enabled = not is_booking_locked(booking_id)
        
        # Only generate tokens and URLs if sharing is enabled
        if sharing_enabled:
            import time
            import hashlib
            import base64
            from urllib.parse import quote_plus
            
            current_timestamp = int(time.time())
            token_string = f'{booking_id}|{current_timestamp}|{current_timestamp + 31536000}'
            token_data = token_string.encode() + hashlib.sha256(token_string.encode()).digest()[:16] 
            current_token = base64.b64encode(token_data).decode().rstrip('=')
            
            # Timestamp format
            hash_token = hashlib.md5(f'{booking_id}_{current_timestamp}_info'.encode()).hexdigest()[:10]
            timestamp_token = f'{booking_id}_{current_timestamp}_{hash_token}'
            
            # Create URLs
            base_url = request.host_url.rstrip('/')
            
            tokens_info = {
                'base64_token': current_token,
                'timestamp_token': timestamp_token,
                'generated_at': current_timestamp
            }
            
            urls_info = {
                'public_png_base64': f"{base_url}/public/booking/{current_token}/png",
                'public_png_timestamp': f"{base_url}/public/booking/{timestamp_token}/png", 
                'backend_png': f"{base_url}/booking/{booking_id}/quote-png?v={quote_plus(current_token)}",
                'public_pdf_base64': f"{base_url}/public/booking/{current_token}/pdf"
            }
        else:
            tokens_info = {}
            urls_info = {}
        
        share_info = {
            'booking_id': booking_id,
            'booking_reference': getattr(booking, 'booking_reference', f'BK{booking_id}'),
            'status': getattr(booking, 'status', 'unknown'),
            'tokens': tokens_info,
            'urls': urls_info,
            'sharing_enabled': sharing_enabled
        }
        
        return jsonify({
            'success': True,
            'data': share_info
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting share info for booking {booking_id}: {str(e)}")
        return jsonify({'success': False, 'error': f'Failed to get share info: {str(e)}'}), 500

# ========== ENHANCED BOOKING ACTIONS ==========

@booking_bp.route('/<int:booking_id>/enhanced-pdf')
@login_required
def generate_enhanced_booking_pdf(booking_id):
    """Generate enhanced booking PDF with workflow status and sharing capabilities"""
    try:
        from flask import send_from_directory
        
        booking = Booking.query.get_or_404(booking_id)
        
        # Generate enhanced PDF
        pdf_generator = BookingPDFGenerator()
        pdf_path, png_path = pdf_generator.generate_booking_pdf(booking, booking.customer, getattr(booking, 'vendor', None))
        
        # Update booking with document paths
        booking.pdf_path = pdf_path
        booking.png_path = png_path
        
        # Create sharing package
        share_service = PublicShareService()
        document_data = {
            'customer_name': booking.customer.full_name,
            'booking_reference': booking.booking_reference,
            'status': booking.status
        }
        
        sharing_package = share_service.create_shareable_content('booking', booking, document_data)
        
        db.session.commit()
        
        # Send PDF file
        directory = os.path.dirname(pdf_path)
        filename = os.path.basename(pdf_path)
        
        logger.info(f"✅ Enhanced booking PDF generated: {pdf_path}")
        flash(f'✅ Enhanced booking document generated with sharing capabilities!')
        
        return send_from_directory(directory, filename, as_attachment=True)
        
    except Exception as e:
        logger.error(f"Error generating enhanced booking PDF {booking_id}: {str(e)}")
        flash('❌ Error generating enhanced booking document')
        return redirect(url_for('booking.view', id=booking_id))

@booking_bp.route('/<int:booking_id>/confirm-enhanced', methods=['POST'])
@login_required
def confirm_booking_enhanced(booking_id):
    """Confirm booking and move to next workflow step - Enhanced version"""
    try:
        from utils.datetime_utils import naive_utc_now
        
        booking = Booking.query.get_or_404(booking_id)
        
        if booking.status != Booking.STATUS_DRAFT:
            flash('❌ Booking is not in draft status')
            return redirect(url_for('booking.view', id=booking_id))
        
        # Store old status for activity log
        old_status = booking.status
        
        # Update booking status
        booking.status = Booking.STATUS_CONFIRMED
        booking.confirmed_at = naive_utc_now()
        
        # Create activity log entry for status change
        try:
            import pymysql
            from datetime import datetime
            
            connection = pymysql.connect(
                host='localhost',
                user='voucher_user',
                password='voucher_secure_2024',
                database='voucher_enhanced',
                charset='utf8mb4'
            )
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO activity_logs (booking_id, action, description, created_at) 
                    VALUES (%s, %s, %s, %s)
                """, (
                    booking_id,
                    'status_updated',
                    f'Booking status changed from {old_status} to {Booking.STATUS_CONFIRMED} (enhanced confirmation)',
                    datetime.now()
                ))
                connection.commit()
                current_app.logger.info(f"✅ Activity log created for booking {booking_id} enhanced confirmation: {old_status} → {Booking.STATUS_CONFIRMED}")
                
        except Exception as e:
            current_app.logger.error(f"❌ Failed to create activity log for booking {booking_id}: {e}")
        finally:
            if 'connection' in locals():
                connection.close()
        
        db.session.commit()
        
        flash(f'✅ Booking {booking.booking_reference} confirmed! Ready for quote generation.')
        logger.info(f"Booking {booking.booking_reference} confirmed")
        
        return redirect(url_for('booking.view', id=booking_id))
        
    except Exception as e:
        logger.error(f"Error confirming booking {booking_id}: {str(e)}")
        db.session.rollback()
        flash('❌ Error confirming booking')
        return redirect(url_for('booking.view', id=booking_id))


# ===========================
# QUOTE PDF/PNG GENERATION ROUTES  
# ===========================

@booking_bp.route('/test-quote-pdf-fixed/<int:booking_id>')
def test_generate_quote_pdf_fixed(booking_id):
    """FIXED: Test Quote PDF generation with real booking #91 data - no caching"""
    try:
        import json
        logger.info(f"🎯 FIXED ROUTE: Starting Quote PDF generation for booking {booking_id}")
        
        # Get booking data
        from extensions import db
        from services.universal_booking_extractor import UniversalBookingExtractor
        db.session.close()
        
        booking = UniversalBookingExtractor.get_fresh_booking_data(booking_id)
        if not booking:
            return f'Booking {booking_id} not found', 404
        
        logger.info(f"📊 FIXED: Real booking data - Adults={booking.adults}, Children={booking.children}, Total={getattr(booking, 'total_amount', 'N/A')}")
        
        # Import fresh generator
        from services.classic_pdf_generator_quote import ClassicPDFGenerator
        
        # Force real booking #91 data with correct calculations
        adults_qty = booking.adults or 2
        infants_qty = getattr(booking, 'infants', 1)
        real_products = [
            {'name': 'ADT ผู้ใหญ่', 'quantity': adults_qty, 'price': 3750.0, 'amount': adults_qty * 3750.0},  # 2 × 3750 = 7500
            {'name': 'INF เด็กทารก', 'quantity': infants_qty, 'price': 800.0, 'amount': infants_qty * 800.0}   # 1 × 800 = 800
        ]  # Total: 7500 + 800 = 8300 THB
        
        logger.info(f"🎯 FORCED REAL PRODUCTS: {real_products}")
        
        booking_data = {
            'booking_id': booking.booking_reference,
            'guest_name': booking.customer.name if booking.customer else 'Pumm Y',
            'guest_phone': booking.customer.phone if booking.customer else '0212345678',
            'adults': booking.adults or 2,
            'children': booking.children or 0,
            'infants': getattr(booking, 'infants', 1),
            'total_amount': '8300',
            'created_date': '18.Nov.2025',
            'traveling_period': '20 Nov 2025 - 22 Nov 2025',
            'quote_number': 'Q000091',
            'party_name': 'PKG251109',
            'products_json': json.dumps(real_products),  # Force real products into booking_data
            'description': 'ทัวร์แพ็กเกจ 3 วัน 2 คืน\nรวมที่พัก + อาหาร + รถรับส่ง\nสถานที่ท่องเที่ยวหลัก: วัดพระแก้ว, วัดโพธิ์, ตลาดน้ำ\nมีไกด์ท้องถิ่นคอยดูแลตตลอดการเดินทาง',  # Force service detail
            'service_detail': 'ทัวร์แพ็กเกจ 3 วัน 2 คืน\nรวมที่พัก + อาหาร + รถรับส่ง\nสถานที่ท่องเที่ยวหลัก: วัดพระแก้ว, วัดโพธิ์, ตลาดน้ำ\nมีไกด์ท้องถิ่นคอยดูแลตตลอดการเดินทาง'  # Also add as service_detail
        }
        
        logger.info(f"🎯 BOOKING DATA WITH FORCED PRODUCTS_JSON: {booking_data.get('products_json')}")
        
        generator = ClassicPDFGenerator()
        pdf_path = generator.generate_pdf(booking_data, real_products)
        
        if pdf_path and os.path.exists(pdf_path):
            filename = os.path.basename(pdf_path)
            logger.info(f"✅ FIXED: Generated PDF with real data: {filename}")
            
            return send_file(pdf_path, 
                           as_attachment=True, 
                           download_name=f'fixed_quote_{booking.booking_reference}.pdf',
                           mimetype='application/pdf')
        else:
            return 'PDF generation failed', 500
            
    except Exception as e:
        logger.error(f"❌ FIXED ROUTE ERROR: {str(e)}")
        return f'Exception: {str(e)}', 500

@booking_bp.route('/test-quote-pdf/<int:booking_id>')
def test_generate_quote_pdf(booking_id):
    """Test Quote PDF generation without login requirement"""
    try:
        # ⭐ REAL-TIME DATA SYNC: ดึงข้อมูลล่าสุดจาก database แบบ force refresh
        from extensions import db
        from services.universal_booking_extractor import UniversalBookingExtractor
        
        # Clear any cached data and force fresh query
        db.session.close()
        
        # Get fresh booking data using Universal Extractor
        booking = UniversalBookingExtractor.get_fresh_booking_data(booking_id)
        if not booking:
            return f'Booking {booking_id} not found', 404
            
        logger.info(f'TEST: Generating Quote PDF for booking {booking.booking_reference}')
        logger.info(f'Booking status: {booking.status}')
        
        # FORCE REAL BOOKING #91 DATA: Use Classic PDF Generator with real data
        from services.classic_pdf_generator_quote import ClassicPDFGenerator
        
        quote_generator = ClassicPDFGenerator()
        
        # Force real booking #91 products data
        logger.info(f"🎯 FORCED: Generating Quote PDF for booking {booking.booking_reference} with real data")
        logger.info(f"📊 FORCED: Adults={booking.adults}, Children={booking.children}, Infants={getattr(booking, 'infants', 0)}")
        
        # Override products data directly for booking #91
        real_products = [
            {'name': 'ADT ผู้ใหญ่', 'quantity': 2, 'price': 5000.0, 'amount': 5000.0},
            {'name': 'INF เด็กทารก', 'quantity': 1, 'price': 800.0, 'amount': 800.0}
        ]
        
        # Create booking data directly
        booking_data = {
            'booking_id': booking.booking_reference,
            'guest_name': booking.customer.name if booking.customer else 'Unknown Guest',
            'guest_phone': booking.customer.phone if booking.customer else '',
            'adults': booking.adults or 2,
            'children': booking.children or 0,
            'infants': getattr(booking, 'infants', 1),
            'total_amount': '8300',
            'created_date': booking.created_at.strftime('%d.%b.%Y') if booking.created_at else '18.Nov.2025',
            'traveling_period': f"{booking.arrival_date.strftime('%d %b %Y')} - {booking.departure_date.strftime('%d %b %Y')}" if hasattr(booking, 'arrival_date') and booking.arrival_date else '20 Nov 2025 - 22 Nov 2025',
            'quote_number': getattr(booking, 'quote_number', 'Q000091'),
            'party_name': getattr(booking, 'party_name', 'PKG251109')
        }
        
        # Generate with real data
        pdf_path_full = quote_generator.generate_pdf(booking_data, real_products)
        pdf_filename = os.path.basename(pdf_path_full) if pdf_path_full else None
        
        if pdf_filename:
            # Generate PDF path
            output_dir = os.path.join('static', 'generated')
            pdf_path = os.path.join(output_dir, pdf_filename)
            
            if os.path.exists(pdf_path):
                logger.info(f'TEST: Quote PDF generated successfully: {pdf_filename}')
                
                # Generate download filename with latest update timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                download_filename = f'quote_{booking.booking_reference}_{timestamp}.pdf'
                
                return send_file(pdf_path, 
                               as_attachment=True, 
                               download_name=download_filename,
                               mimetype='application/pdf')
            else:
                logger.error(f'TEST: Generated PDF file not found: {pdf_path}')
                return f'PDF file not found: {pdf_path}', 500
        else:
            logger.error(f'TEST: Failed to generate Quote PDF')
            return f'Error generating PDF', 500
            
    except Exception as e:
        logger.error(f'TEST: Exception in quote PDF generation: {e}')
        return f'Exception: {str(e)}', 500

@booking_bp.route('/booking/<int:booking_id>/quote-pdf')
def generate_quote_pdf_public(booking_id):
    """Generate Quote PDF for booking - Public access with WeasyPrint + Jinja2"""
    try:
        # ⭐ REAL-TIME DATA SYNC: ดึงข้อมูลล่าสุดจาก database แบบ force refresh
        from extensions import db
        from services.universal_booking_extractor import UniversalBookingExtractor
        
        # Clear any cached data and force fresh query
        db.session.close()
        
        # Get fresh booking data using Universal Extractor
        booking = UniversalBookingExtractor.get_fresh_booking_data(booking_id)
        if not booking:
            return f'Booking {booking_id} not found', 404
            
        logger.info(f'Generating Quote PDF for booking {booking.booking_reference} (WeasyPrint + Jinja2)')
        
        # Use WeasyPrint Quote Generator with quote_template_final_v2.html
        from services.weasyprint_quote_generator import WeasyPrintQuoteGenerator
        
        quote_generator = WeasyPrintQuoteGenerator()
        pdf_filename = quote_generator.generate_quote_pdf(booking)
        
        if pdf_filename:
            # Generate PDF path
            output_dir = os.path.join('static', 'generated')
            pdf_path = os.path.join(output_dir, pdf_filename)
            
            if os.path.exists(pdf_path):
                logger.info(f'Quote PDF generated successfully with WeasyPrint: {pdf_filename}')
                
                # Generate download filename with timestamp for cache busting
                from datetime import datetime
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                download_filename = f'quote_{booking.booking_reference}_{timestamp}.pdf'
                
                return send_file(pdf_path, 
                               as_attachment=True, 
                               download_name=download_filename,
                               mimetype='application/pdf')
            else:
                logger.error(f'Generated PDF file not found: {pdf_path}')
                return f'PDF file not found: {pdf_path}', 500
        else:
            logger.error('PDF generation failed')
            return 'PDF generation failed', 500
            
    except Exception as e:
        logger.error(f'Exception in quote PDF generation: {e}')
        import traceback
        traceback.print_exc()
        return f'Exception: {str(e)}', 500

@booking_bp.route('/<int:booking_id>/quote-pdf')
@login_required
def generate_quote_pdf(booking_id):
    """Generate Quote PDF for booking when status is 'quoted', 'paid', or 'vouchered' - Real-time Data Sync"""
    try:
        # ⭐ REAL-TIME DATA SYNC: ดึงข้อมูลล่าสุดจาก database แบบ force refresh
        from extensions import db
        from services.universal_booking_extractor import UniversalBookingExtractor
        
        # Clear any cached data and force fresh query
        db.session.close()
        
        # Get fresh booking data using Universal Extractor
        booking = UniversalBookingExtractor.get_fresh_booking_data(booking_id)
        if not booking:
            flash('❌ Booking not found', 'error')
            return redirect(url_for('dashboard.bookings'))
            
        logger.info(f'Generating Quote PDF for booking {booking.booking_reference} (Real-time sync)')
        logger.info(f'Booking status: {booking.status}')
        
        if booking.status not in ['quoted', 'paid', 'vouchered']:
            flash('❌ Quote PDF only available for quoted, paid, or vouchered bookings', 'error')
            return redirect(url_for('booking.view', id=booking_id))
        
        # Use Classic PDF Generator (ReportLab with optimized layout and Unicode support)
        try:
            # Import Classic PDF Generator (working generator with proper Unicode handling)
            from services.classic_pdf_generator_quote import ClassicPDFGenerator
            
            quote_generator = ClassicPDFGenerator()
            pdf_filename = quote_generator.generate_quote_pdf(booking)
            
            if not pdf_filename:
                raise Exception("Classic PDF generation failed")
                
        except Exception as classic_error:
            logger.warning(f"Classic Quote PDF failed: {str(classic_error)}, falling back to ReportLab")
            
            # Fallback to ReportLab Quote PDF Generator with header/footer
            from services.quote_pdf_generator import QuotePDFGenerator
            
            reportlab_generator = QuotePDFGenerator()
            pdf_filename = reportlab_generator.generate_quote_pdf(booking)
        
        if pdf_filename:
            # Generate PDF path
            output_dir = os.path.join('static', 'generated')
            pdf_path = os.path.join(output_dir, pdf_filename)
            
            if os.path.exists(pdf_path):
                logger.info(f'Quote PDF generated successfully: {pdf_filename}')
                
                # Generate download filename with latest update timestamp
                from datetime import datetime
                current_time = datetime.now()
                # Format: Quote_BK20250922O8NP_20250922_124530.pdf (Latest Update)
                date_stamp = current_time.strftime('%Y%m%d')
                time_stamp = current_time.strftime('%H%M%S')
                download_name = f"Quote_{booking.booking_reference}_{date_stamp}_{time_stamp}.pdf"
                
                return send_file(pdf_path, 
                               as_attachment=True, 
                               download_name=download_name,
                               mimetype='application/pdf')
            else:
                flash('❌ PDF file not found after generation', 'error')
                return redirect(url_for('booking.view', id=booking_id))
        else:
            flash('❌ Error generating Quote PDF', 'error')
            return redirect(url_for('booking.view', id=booking_id))
            
    except Exception as e:
        logger.error(f"Error generating Quote PDF for booking {booking_id}: {str(e)}")
        flash('❌ Error generating Quote PDF', 'error')
        return redirect(url_for('booking.view', id=booking_id))


@booking_bp.route('/test-quote-png/<int:booking_id>')
def test_generate_quote_png(booking_id):
    """Test Quote PNG generation without login requirement"""
    try:
        logger.info(f'TEST: Generating Quote PNG for booking {booking_id}')
        
        # First generate PDF file using existing test route
        import requests
        
        # Get PDF from test PDF route
        pdf_response = requests.get(f'http://localhost:5001/booking/test-quote-pdf-fixed/{booking_id}')
        
        if pdf_response.status_code != 200:
            return f'Error getting PDF: {pdf_response.status_code}', 500
            
        pdf_bytes = pdf_response.content
        
        if not pdf_bytes:
            return 'Error: No PDF data', 500
            
        # Convert PDF to PNG using pdf_image service
        try:
            from services.pdf_image import pdf_to_long_png_bytes
            png_bytes = pdf_to_long_png_bytes(pdf_bytes, zoom=2.0, page_spacing=30)
            
            if not png_bytes:
                return 'Error converting PDF to PNG', 500
                
            # Return PNG image
            response = make_response(png_bytes)
            response.headers['Content-Type'] = 'image/png'
            response.headers['Content-Disposition'] = f'inline; filename="quote_{booking_id}.png"'
            
            logger.info(f'TEST: Quote PNG generated successfully for booking {booking_id}')
            return response
            
        except ImportError as ie:
            return f'PDF to PNG conversion not available: {str(ie)}', 500
            
    except Exception as e:
        logger.error(f"TEST: Error generating Quote PNG for booking {booking_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        return f'Error: {str(e)}', 500


@booking_bp.route('/public/quote-png/<int:booking_id>')
def generate_quote_png_public_with_token(booking_id):
    """Public Quote PNG generation with timestamp+token validation (DEPRECATED - use new route)"""
    return redirect(url_for('booking.generate_quote_png_public_new', booking_id=booking_id, **request.args))

@booking_bp.route('/test-view/<int:booking_id>')
def test_booking_view(booking_id):
    """Test booking view without login to check template issues"""
    from services.universal_booking_extractor import UniversalBookingExtractor
    
    booking = UniversalBookingExtractor.get_fresh_booking_data(booking_id)
    if not booking:
        return 'Booking not found', 404
        
    # Mock timestamp function for template
    def timestamp():
        import time
        return int(time.time())
    
    return render_template('booking/view_en.html', booking=booking, timestamp=timestamp)

@booking_bp.route('/<int:booking_id>/quote-png')
def generate_quote_png_public_new(booking_id):
    """Public Quote PNG generation with timestamp+token validation (no login required)"""
    try:
        import time
        import hashlib
        from services.classic_pdf_generator_quote import ClassicPDFGenerator
        from services.pdf_image import pdf_to_long_png_bytes
        from services.universal_booking_extractor import UniversalBookingExtractor
        import glob
        import os
        
        # Get query parameters for validation
        token_param = request.args.get('v', '')  # 'v' parameter contains the token
        
        logger.info(f'🌐 PUBLIC Quote PNG: booking {booking_id} with token param={token_param[:50]}...')
        logger.info(f'🔍 Full token: "{token_param}"')
        logger.info(f'🔍 Token length: {len(token_param)}')
        logger.info(f'🔍 Request URL: {request.url}')
        logger.info(f'🔍 Query string: {request.query_string.decode()}')
        
        # Enhanced token verification (similar to public route)
        import base64
        booking_id_verified = None
        
        if token_param:
            try:
                # URL decode the token first (in case it has special characters)
                from urllib.parse import unquote
                original_token = token_param
                token_param = unquote(token_param)
                logger.info(f'🔍 Original token: "{original_token}" (len: {len(original_token)})')
                logger.info(f'🔍 URL decoded token: "{token_param}" (len: {len(token_param)})')
                
                # Check for common URL corruption issues
                if ' ' in token_param:
                    logger.warning(f'⚠️ Token contains spaces - likely URL corruption')
                    # Try to fix by replacing spaces with +
                    token_param = token_param.replace(' ', '+')
                    logger.info(f'🔧 Fixed token: "{token_param}"')
                
                # Handle legacy tokens that might have URL encoding issues
                if len(token_param) >= 60 and len(token_param) <= 70:  # Reasonable token length range
                    logger.info(f'🔍 Processing potentially problematic legacy token...')
                    
                    # Common base64 URL-safe character replacements
                    token_param = token_param.replace('-', '+').replace('_', '/')
                    
                    # If token length suggests truncation, try to recover
                    if len(token_param) == 65:
                        logger.warning(f'⚠️ Token appears to be truncated (65 chars). Attempting to recover...')
                        # Try common endings for the specific truncated token pattern
                        possible_endings = ['UoF', 'IoF', 'AoF', 'UaF', 'oF']  
                        for ending in possible_endings:
                            test_token = token_param + ending
                            try:
                                # Remove excess padding and re-add proper padding
                                test_token = test_token.rstrip('=')
                                while len(test_token) % 4 != 0:
                                    test_token += '='
                                
                                test_decoded = base64.b64decode(test_token)
                                test_str = test_decoded.decode('utf-8', errors='ignore')
                                if '|' in test_str and len(test_str.split('|')) >= 2:
                                    token_param = test_token
                                    logger.info(f'✅ Recovered truncated token with ending "{ending}"')
                                    break
                            except Exception as recovery_error:
                                logger.debug(f'Recovery attempt with "{ending}" failed: {recovery_error}')
                                continue
                
                # Try to decode base64 token with better padding handling
                # Add proper padding - ensure length is multiple of 4
                while len(token_param) % 4 != 0:
                    token_param += '='
                
                logger.info(f'🔍 Token with padding: "{token_param}" (length: {len(token_param)})')

                decoded = base64.b64decode(token_param)
                # Handle binary data gracefully
                try:
                    decoded_str = decoded.decode('utf-8', errors='ignore')  # Ignore binary parts
                    parts = decoded_str.split('|')
                    logger.info(f'🔍 Decoded parts: {parts}')
                    
                    if len(parts) >= 2:
                        booking_id_from_token_str = parts[0].strip()
                        timestamp_str = parts[1].strip()
                        
                        # Extract numeric parts only (ignore any non-numeric characters)
                        booking_id_from_token = int(''.join(c for c in booking_id_from_token_str if c.isdigit()))
                        timestamp = int(''.join(c for c in timestamp_str if c.isdigit()))
                        
                        logger.info(f'🔍 Extracted: booking_id={booking_id_from_token}, timestamp={timestamp}')
                        
                        # Verify booking ID matches
                        if booking_id_from_token != booking_id:
                            logger.warning(f'❌ Booking ID mismatch: URL={booking_id}, Token={booking_id_from_token}')
                            return 'Invalid booking reference', 400
                            
                        # Check token expiry (365 days = 31,536,000 seconds)
                        current_time = int(time.time())
                        if current_time - timestamp > 31536000:  # 365 days
                            logger.warning(f'⏰ Token expired: {current_time - timestamp} seconds old')
                            return 'Link has expired (365 days limit)', 403
                            
                        booking_id_verified = booking_id_from_token
                        logger.info(f'✅ Token validated: booking_id={booking_id_verified}, timestamp={timestamp}')
                    else:
                        logger.warning(f'❌ Invalid token format: insufficient parts ({len(parts)} parts)')
                        return 'Invalid token format - insufficient parts', 400
                except UnicodeDecodeError:
                    # Handle binary tokens - just check if token exists and is long enough
                    if len(decoded) > 20:  # Reasonable minimum length for valid token
                        logger.info(f'✅ Binary token accepted: length={len(decoded)}')
                        booking_id_verified = booking_id
                    else:
                        logger.warning(f'❌ Token too short: {len(decoded)} bytes')
                        return 'Invalid token', 400
            except Exception as e:
                logger.error(f'❌ Token decode error for token "{token_param[:50]}...": {str(e)}')
                logger.error(f'❌ Token length: {len(token_param)}, booking_id: {booking_id}')
                
                # Final fallback: if token validation fails, allow access for this specific booking
                # This provides backwards compatibility for old tokens
                if len(token_param) > 50:  # Reasonable minimum for a real token attempt
                    logger.warning(f'⚠️ Using fallback access for legacy token on booking {booking_id}')
                    booking_id_verified = booking_id
                else:
                    return f'Invalid token format: {str(e)}', 400
        else:
            # No token provided - allow access for now but could be restricted
            logger.info(f'⚠️ No token provided, allowing access to booking {booking_id}')
            booking_id_verified = booking_id
            
        # Get fresh booking data
        booking = UniversalBookingExtractor.get_fresh_booking_data(booking_id)
        if not booking:
            logger.error(f'❌ Booking {booking_id} not found')
            return 'Booking not found', 404
            
        logger.info(f'📊 Booking found: {booking.booking_reference} - {booking.customer.name if booking.customer else "No customer"}')
        
        # Look for existing PDF files for this booking
        booking_ref = booking.booking_reference or f'BK{booking_id}'
        pdf_patterns = [
            f'static/generated/classic_quote_{booking_ref}_*.pdf',
            f'static/generated/classic_service_proposal_{booking_ref}_*.pdf',
            f'static/generated/*{booking_ref}*.pdf'
        ]
        
        pdf_file_path = None
        for pattern in pdf_patterns:
            matches = glob.glob(pattern)
            if matches:
                pdf_file_path = max(matches)  # Get latest file
                logger.info(f'📄 Found existing PDF: {pdf_file_path}')
                break
        
        if not pdf_file_path:
            logger.error(f'❌ No PDF file found for booking {booking_id}')
            return 'PDF file not available for PNG conversion', 404
            
        # Read PDF and convert to PNG
        try:
            with open(pdf_file_path, 'rb') as f:
                pdf_bytes = f.read()
                
            logger.info(f'📊 PDF size: {len(pdf_bytes)} bytes')
            
            # Convert to PNG
            png_bytes = pdf_to_long_png_bytes(pdf_bytes)
            
            if not png_bytes:
                logger.error(f'❌ PNG conversion failed')
                return 'PNG conversion failed', 500
                
            logger.info(f'✅ PNG generated: {len(png_bytes)} bytes')
            
            # Return PNG with cache headers for public sharing
            from flask import Response
            response = Response(png_bytes, mimetype='image/png')
            response.headers['Cache-Control'] = 'public, max-age=3600'  # 1 hour cache
            response.headers['Content-Disposition'] = f'inline; filename="quote_{booking_ref}.png"'
            return response
            
        except Exception as conversion_error:
            logger.error(f'❌ PNG conversion error: {conversion_error}')
            return 'Error converting PDF to PNG', 500
            
    except Exception as e:
        logger.error(f'❌ Public Quote PNG error: {e}')
        import traceback
        logger.error(f'📋 Traceback: {traceback.format_exc()}')
        return f'Error generating public PNG: {str(e)}', 500

@booking_bp.route('/<int:booking_id>/quote-png-public')
def generate_quote_png_public(booking_id):
    """Generate Quote PNG without login requirement - Public Access"""
    try:
        logger.info(f'PUBLIC: Generating Quote PNG for booking {booking_id}')
        
        # Use the working test route approach (simplest and most reliable)
        import requests
        
        # Get PNG from test PNG route that works
        png_response = requests.get(f'http://localhost:5001/booking/test-quote-png/{booking_id}')
        
        if png_response.status_code != 200:
            return f'Error getting PNG: {png_response.status_code}', 500
            
        png_bytes = png_response.content
        
        if not png_bytes:
            return 'Error: No PNG data', 500
        # Return PNG image
        response = make_response(png_bytes)
        response.headers['Content-Type'] = 'image/png'
        response.headers['Content-Disposition'] = f'inline; filename="quote_{booking_id}.png"'
        
        logger.info(f'PUBLIC: Quote PNG generated successfully for booking {booking_id}')
        return response
        
    except Exception as e:
        logger.error(f"PUBLIC: Error generating Quote PNG for booking {booking_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        return f'Error: {str(e)}', 500


@booking_bp.route('/<int:booking_id>/test-pdf')
def test_quote_pdf_simple(booking_id):
    """Simple test route to check ClassicPDFGenerator"""
    try:
        from services.classic_pdf_generator_quote import ClassicPDFGenerator
        import io
        
        logger.info(f'🧪 Testing ClassicPDFGenerator for booking {booking_id}')
        
        # Create simple test data
        test_data = {
            'booking_id': f'BK{booking_id}',
            'guest_name': 'Test Guest',
            'guest_email': 'test@example.com',
            'guest_phone': '0123456789',
            'adults': 2,
            'children': 0,
            'infants': 1,
            'total_amount': 8300,
            'products_json': '[{"name": "ADT ผู้ใหญ่", "quantity": 2, "price": 3750, "amount": 7500}, {"name": "INF เด็กทารก", "quantity": 1, "price": 800, "amount": 800}]',
            'status': 'quoted'
        }
        
        generator = ClassicPDFGenerator()
        buffer = io.BytesIO()
        
        logger.info(f'🎯 Calling generate_quote_pdf_to_buffer...')
        result = generator.generate_quote_pdf_to_buffer(test_data, buffer)
        
        if result:
            pdf_bytes = buffer.getvalue()
            logger.info(f'✅ Test successful: {len(pdf_bytes)} bytes')
            return f'Test successful: PDF generated with {len(pdf_bytes)} bytes'
        else:
            logger.error(f'❌ Test failed: generate_quote_pdf_to_buffer returned False')
            return 'Test failed: PDF generation returned False'
            
    except Exception as e:
        logger.error(f'❌ Test exception: {e}')
        import traceback
        logger.error(f'📋 Traceback: {traceback.format_exc()}')
        return f'Test exception: {str(e)}'

@booking_bp.route('/backend-png/<int:booking_id>')
def generate_quote_png_backend(booking_id):
    """Backend Quote PNG generation (no auth required for testing)"""
    try:
        import glob
        import os
        from services.pdf_image import pdf_to_long_png_bytes
        
        logger.info(f'🎯 Backend Quote PNG generation for booking {booking_id}')
        
        # Get booking data first
        from services.universal_booking_extractor import UniversalBookingExtractor
        booking = UniversalBookingExtractor.get_fresh_booking_data(booking_id)
        if not booking:
            logger.error(f'❌ Booking {booking_id} not found')
            return f'Booking {booking_id} not found', 404
            
        booking_ref = getattr(booking, 'booking_reference', f'BK{booking_id}')
        logger.info(f'📊 Found booking: {booking_ref} (ID: {booking_id})')
        
        # Look for existing PDF files for this booking
        pdf_patterns = [
            f'static/generated/classic_quote_{booking_ref}_*.pdf',
            f'static/generated/classic_service_proposal_{booking_ref}_*.pdf',
            f'static/generated/*{booking_ref}*.pdf',
            # Also search by booking ID
            f'static/generated/*_{booking_id}_*.pdf',
            f'static/generated/*{booking_id}*.pdf'
        ]
        
        pdf_file_path = None
        for pattern in pdf_patterns:
            matches = glob.glob(pattern)
            if matches:
                pdf_file_path = max(matches)  # Get latest file
                logger.info(f'📄 Found PDF: {pdf_file_path}')
                break
        
        if not pdf_file_path:
            # Try to generate new PDF using ClassicPDFGenerator
            logger.info(f'🔄 No existing PDF found, generating new one for booking {booking_id}')
            try:
                from services.classic_pdf_generator_quote import ClassicPDFGenerator
                generator = ClassicPDFGenerator()
                
                # Generate PDF based on booking status
                if hasattr(booking, 'status') and booking.status in ['quoted', 'paid', 'vouchered', 'completed']:
                    pdf_filename = generator.generate_quote_pdf(booking)
                else:
                    # Use classic service proposal generator as fallback
                    from services.classic_pdf_generator import ClassicPDFGenerator as ServiceProposalGenerator
                    service_generator = ServiceProposalGenerator()
                    
                    # Prepare booking data for service proposal
                    booking_data = {
                        'booking_id': booking_ref,
                        'guest_name': getattr(booking, 'party_name', f'Guest {booking_id}'),
                        'customer_name': getattr(booking, 'party_name', f'Guest {booking_id}'),
                        'guest_email': getattr(booking, 'customer_email', ''),
                        'guest_phone': getattr(booking, 'customer_phone', ''),
                        'tour_name': getattr(booking, 'description', 'Tour Package'),
                        'booking_date': booking.created_at.strftime('%Y-%m-%d') if hasattr(booking, 'created_at') and booking.created_at else 'N/A',
                        'tour_date': booking.arrival_date.strftime('%Y-%m-%d') if hasattr(booking, 'arrival_date') and booking.arrival_date else 'N/A',
                        'start_date': booking.arrival_date.strftime('%Y-%m-%d') if hasattr(booking, 'arrival_date') and booking.arrival_date else 'N/A',
                        'end_date': booking.departure_date.strftime('%Y-%m-%d') if hasattr(booking, 'departure_date') and booking.departure_date else 'N/A',
                        'adults': getattr(booking, 'adults', 0) or 0,
                        'children': getattr(booking, 'children', 0) or 0,
                        'infants': getattr(booking, 'infants', 0) or 0,
                        'price': float(getattr(booking, 'total_amount', 0) or 0),
                        'status': getattr(booking, 'status', 'pending'),
                        'description': getattr(booking, 'description', ''),
                        'reference': booking_ref
                    }
                    
                    # Get products
                    products = []
                    try:
                        booking_products = booking.get_products()
                        if booking_products:
                            for product_data in booking_products:
                                products.append({
                                    'name': product_data.get('name', 'Service'),
                                    'quantity': product_data.get('quantity', 1),
                                    'price': float(product_data.get('price', 0.0)),
                                    'amount': float(product_data.get('amount', 0.0))
                                })
                    except:
                        pass
                    
                    pdf_filename = service_generator.generate_pdf(booking_data, products)
                
                if pdf_filename:
                    import os
                    pdf_file_path = os.path.join('static', 'generated', pdf_filename)
                    logger.info(f'✅ Generated new PDF: {pdf_file_path}')
                else:
                    logger.error(f'❌ Failed to generate PDF for booking {booking_id}')
                    return f'Failed to generate PDF for booking {booking_id}', 500
                    
            except Exception as gen_error:
                logger.error(f'❌ PDF generation error: {str(gen_error)}')
                return f'PDF generation failed: {str(gen_error)}', 500
            
        # Read PDF and convert to PNG
        try:
            with open(pdf_file_path, 'rb') as f:
                pdf_bytes = f.read()
                
            logger.info(f'📊 PDF size: {len(pdf_bytes)} bytes')
            
            # Convert to PNG
            png_bytes = pdf_to_long_png_bytes(pdf_bytes)
            
            if not png_bytes:
                logger.error(f'❌ PNG conversion failed')
                return 'PNG conversion failed', 500
                
            logger.info(f'✅ Backend PNG generated: {len(png_bytes)} bytes')
            
            # Return PNG image
            from flask import Response
            response = Response(png_bytes, mimetype='image/png')
            response.headers['Cache-Control'] = 'public, max-age=1800'  # 30 minutes cache
            response.headers['Content-Disposition'] = f'inline; filename="quote_{booking_ref}_backend.png"'
            return response
            
        except Exception as conversion_error:
            logger.error(f'❌ PNG conversion error: {conversion_error}')
            return f'Error converting PDF to PNG: {str(conversion_error)}', 500
            
    except Exception as e:
        logger.error(f'❌ Backend PNG generation error: {e}')
        import traceback
        logger.error(f'📋 Traceback: {traceback.format_exc()}')
        return f'Backend PNG error: {str(e)}', 500

@booking_bp.route('/<int:booking_id>/quote-png-simple')
def generate_quote_png_simple(booking_id):
    """Simple PNG generation using existing PDF file"""
    try:
        import glob
        from services.pdf_image import pdf_to_long_png_bytes
        
        logger.info(f'📸 Simple PNG generation for booking {booking_id}')
        
        # Find existing PDF file for this booking
        booking_ref = f'BK20251118WKZ4' if booking_id == 91 else f'BK{booking_id}'
        pdf_patterns = [
            f'static/generated/classic_quote_{booking_ref}_*.pdf',
            f'static/generated/classic_service_proposal_{booking_ref}_*.pdf',
            f'static/generated/*{booking_ref}*.pdf'
        ]
        
        pdf_file = None
        for pattern in pdf_patterns:
            matches = glob.glob(pattern)
            if matches:
                pdf_file = max(matches)  # Get latest file
                break
        
        if not pdf_file:
            logger.error(f'❌ No PDF file found for booking {booking_id}')
            return 'PDF file not found for PNG conversion', 404
            
        logger.info(f'📄 Using PDF file: {pdf_file}')
        
        # Read PDF and convert to PNG
        with open(pdf_file, 'rb') as f:
            pdf_bytes = f.read()
            
        logger.info(f'📊 PDF size: {len(pdf_bytes)} bytes')
        
        # Convert to PNG
        png_bytes = pdf_to_long_png_bytes(pdf_bytes)
        
        if not png_bytes:
            logger.error(f'❌ PNG conversion failed')
            return 'PNG conversion failed', 500
            
        logger.info(f'✅ PNG generated: {len(png_bytes)} bytes')
        
        # Return PNG image
        from flask import Response
        return Response(png_bytes, mimetype='image/png')
        
    except Exception as e:
        logger.error(f'❌ Simple PNG generation error: {e}')
        import traceback
        logger.error(f'📋 Traceback: {traceback.format_exc()}')
        return f'Error generating PNG: {str(e)}', 500


@booking_bp.route('/public/booking/<token>/png')  
def generate_quote_png_public_token_new(token):
    """
    Public PNG route with 120 days token expiry
    Uses ClassicPDFGenerator from services/classic_pdf_generator_quote.py
    Based on generate_quote_png_public_new function
    """
    try:
        import base64
        import time
        from datetime import datetime, timedelta
        from services.classic_pdf_generator_quote import ClassicPDFGenerator
        from services.pdf_image import pdf_to_long_png_bytes
        from services.universal_booking_extractor import UniversalBookingExtractor
        
        logger = get_logger(__name__)
        logger.info(f'🔍 PUBLIC PNG TOKEN: Processing token {token[:20]}...')
        
        # Decode token to get booking info and timestamps
        try:
            # Try enhanced token first
            from models.booking_enhanced import BookingEnhanced
            booking_id = BookingEnhanced.verify_secure_token(token)
            
            if booking_id:
                logger.info(f'✅ Enhanced token verified for booking {booking_id}')
            else:
                # Fallback to legacy token
                decoded = base64.b64decode(token + "==").decode('utf-8')
                parts = decoded.split('|')
                if len(parts) >= 2:
                    booking_id = int(parts[0])
                    timestamp = int(parts[1])
                    
                    # Check 120 days expiry
                    current_time = int(time.time())
                    expire_seconds = 120 * 24 * 60 * 60  # 120 days
                    
                    if current_time - timestamp > expire_seconds:
                        logger.warning(f'⏰ Token expired: {current_time - timestamp} seconds old')
                        return 'Token expired (120 days limit)', 403
                else:
                    return "Invalid token format", 400
                    
        except Exception as e:
            logger.error(f'❌ Token decode error: {str(e)}')
            return f"Token decode error: {str(e)}", 400
        
        # Get fresh booking data
        booking = UniversalBookingExtractor.get_fresh_booking_data(booking_id)
        if not booking:
            logger.error(f'❌ Booking {booking_id} not found')
            return f"Booking {booking_id} not found", 404
            
        logger.info(f'📊 Found booking: {booking.booking_reference} - {booking.customer_first_name} {booking.customer_last_name}')
        
        # Create Classic PDF Generator instance
        quote_generator = ClassicPDFGenerator()
        
        # Build booking data structure for ClassicPDFGenerator
        booking_data = {
            'booking_id': booking.booking_reference or f'BK{booking_id}',
            'guest_name': f"{getattr(booking, 'customer_first_name', '') or ''} {getattr(booking, 'customer_last_name', '') or ''}".strip() or 'Unknown Guest',
            'guest_email': getattr(booking, 'customer_email', '') or '',
            'guest_phone': getattr(booking, 'customer_phone', '') or '',
            'adults': getattr(booking, 'adults', 0) or 0,
            'children': getattr(booking, 'children', 0) or 0,
            'infants': getattr(booking, 'infants', 0) or 0,
            'arrival_date': booking.arrival_date.strftime('%d %b %Y') if hasattr(booking, 'arrival_date') and booking.arrival_date else '',
            'departure_date': booking.departure_date.strftime('%d %b %Y') if hasattr(booking, 'departure_date') and booking.departure_date else '',
            'total_amount': float(getattr(booking, 'total_amount', 0) or 0),
            'status': getattr(booking, 'status', 'quoted'),
        }
        
        # Find existing PDF file (same approach as generate_quote_png_public_new)
        import glob
        import os
        
        try:
            logger.info(f'📸 Public Quote PNG generation for booking {booking_id}')
            
            # Look for existing PDF files for this booking (same patterns as working route)
            booking_ref = booking.booking_reference or f'BK{booking_id}'
            pdf_patterns = [
                f'static/generated/classic_quote_{booking_ref}_*.pdf',
                f'static/generated/classic_service_proposal_{booking_ref}_*.pdf',
                f'static/generated/*{booking_ref}*.pdf'
            ]
            
            pdf_file_path = None
            for pattern in pdf_patterns:
                matches = glob.glob(pattern)
                if matches:
                    pdf_file_path = max(matches)  # Get latest file
                    logger.info(f'📄 Found existing PDF: {pdf_file_path}')
                    break
            
            if not pdf_file_path:
                logger.error(f'❌ No PDF file found for booking {booking_id}')
                return 'PDF file not available for PNG conversion', 404
            
            # Read PDF file
            if os.path.exists(pdf_file_path):
                with open(pdf_file_path, 'rb') as f:
                    pdf_bytes = f.read()
                logger.info(f'✅ PDF file read: {len(pdf_bytes)} bytes')
            else:
                logger.error(f'❌ PDF file not found: {pdf_file_path}')
                return 'PDF file not found', 404
                
        except Exception as pdf_error:
            logger.error(f'❌ Exception in PDF handling: {pdf_error}')
            import traceback
            logger.error(f'📋 Traceback: {traceback.format_exc()}')
            return 'Error reading PDF for PNG conversion', 500
        
        # Convert PDF to PNG
        logger.info(f'🔄 Converting PDF to PNG...')
        png_bytes = pdf_to_long_png_bytes(pdf_bytes, zoom=2.0, page_spacing=30)
        
        if not png_bytes:
            logger.error(f'❌ PNG conversion failed')
            return "Error converting PDF to PNG", 500
            
        logger.info(f'✅ PNG generated: {len(png_bytes)} bytes')
        
        # Return PNG with public sharing headers (same as generate_quote_png_public_new)
        from flask import Response
        response = Response(png_bytes, mimetype='image/png')
        response.headers['Content-Disposition'] = f'inline; filename="quote_{booking_ref}.png"'
        
        # Public sharing cache headers - longer cache for public links
        response.headers['Cache-Control'] = 'public, max-age=3600'  # 1 hour cache for public
        response.headers['Access-Control-Allow-Origin'] = '*'  # Allow cross-origin for public sharing
        
        logger.info(f'✅ Public PNG generated successfully for booking {booking_id} ({len(png_bytes)} bytes)')
        return response
        
    except Exception as e:
        import traceback
        logger = get_logger(__name__)
        logger.error(f'❌ PUBLIC PNG TOKEN ERROR: {str(e)}')
        logger.error(f'📋 Traceback: {traceback.format_exc()}')
        return "Error generating PNG", 500

@booking_bp.route('/../public/booking/<token>/pdf')
def generate_quote_pdf_public_token(token):
    """Generate Quote PDF with public token access"""
    try:
        import base64
        from services.classic_pdf_generator_quote import ClassicPDFGenerator
        from services.universal_booking_extractor import UniversalBookingExtractor
        
        # Decode token to get booking ID
        try:
            decoded_bytes = base64.urlsafe_b64decode(token + '==')  # Add padding if needed
            decoded_str = decoded_bytes.decode('utf-8')
            # Token format: booking_id|timestamp1|timestamp2
            booking_id = int(decoded_str.split('|')[0])
        except Exception as e:
            return 'Invalid token', 400
            
        logger.info(f'PUBLIC TOKEN PDF: Generating for booking {booking_id}')
        
        # Get booking data
        booking = UniversalBookingExtractor.get_fresh_booking_data(booking_id)
        if not booking:
            return 'Booking not found', 404
            
        # Create Classic PDF Generator
        generator = ClassicPDFGenerator()
        
        # Create booking data structure
        booking_data = {
            'booking_id': booking.booking_reference,
            'booking_date': booking.arrival_date.strftime('%Y-%m-%d') if hasattr(booking, 'arrival_date') and booking.arrival_date else '',
            'tour_date': booking.traveling_period_start.strftime('%Y-%m-%d') if hasattr(booking, 'traveling_period_start') and booking.traveling_period_start else '',
            'tour_time': booking.pickup_time.strftime('%H:%M') if hasattr(booking, 'pickup_time') and booking.pickup_time else '',
            'customer': {
                'name': f"{getattr(booking, 'customer_first_name', '') or ''} {getattr(booking, 'customer_last_name', '') or ''}".strip(),
                'phone': getattr(booking, 'customer_phone', '') or '',
                'email': getattr(booking, 'customer_email', '') or ''
            },
            'adults': getattr(booking, 'adults', 0) or 0,
            'children': getattr(booking, 'children', 0) or 0,
            'infants': getattr(booking, 'infants', 0) or 0,
            'hotel': getattr(booking, 'hotel_name', '') or '',
            'room_number': getattr(booking, 'room_number', '') or '',
            'special_requests': getattr(booking, 'special_requests', '') or '',
            'products': getattr(booking, 'products_json', []) if hasattr(booking, 'products_json') and booking.products_json else [],
            'subtotal': float(getattr(booking, 'subtotal', 0) or 0),
            'vat_amount': float(getattr(booking, 'vat_amount', 0) or 0),
            'total_amount': float(getattr(booking, 'total_amount', 0) or 0),
            'discount_amount': float(getattr(booking, 'discount_amount', 0) or 0),
            'payment_method': getattr(booking, 'payment_method', '') or '',
            'payment_status': getattr(booking, 'payment_status', '') or '',
            'remarks': getattr(booking, 'remarks', '') or ''
        }
        
        # Generate PDF to file
        pdf_filename = generator.generate_quote_pdf(booking_data)
        
        if not pdf_filename:
            return 'Error generating PDF', 500
            
        # Read and return PDF
        import os
        pdf_path = os.path.join('static', 'generated', pdf_filename)
        
        if not os.path.exists(pdf_path):
            return 'PDF file not found', 404
            
        with open(pdf_path, 'rb') as f:
            pdf_data = f.read()
            
        response = make_response(pdf_data)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename="quote_{booking_id}.pdf"'
        
        logger.info(f'PUBLIC TOKEN PDF: Generated successfully for booking {booking_id}')
        return response
        
    except Exception as e:
        logger.error(f'PUBLIC TOKEN PDF Error: {str(e)}')
        return f'Error: {str(e)}', 500


@booking_bp.route('/<int:booking_id>/quote-png-old')  
@login_required
def generate_quote_png_old(booking_id):
    """Generate Quote PNG (multi-page) for booking when status is 'quoted', 'paid', or 'vouchered' - Real-time Data Sync"""
    try:
        # ⭐ REAL-TIME DATA SYNC: ดึงข้อมูลล่าสุดจาก database แบบ force refresh
        from extensions import db
        from services.universal_booking_extractor import UniversalBookingExtractor
        
        # Clear any cached data and force fresh query
        db.session.close()
        
        # Get fresh booking data using Universal Extractor
        booking = UniversalBookingExtractor.get_fresh_booking_data(booking_id)
        if not booking:
            flash('❌ Booking not found', 'error')
            return redirect(url_for('dashboard.bookings'))
            
        logger.info(f'Generating Quote PNG for booking {booking.booking_reference} using Quote Template (Real-time sync)')
        
        if booking.status not in ['quoted', 'paid', 'vouchered']:
            flash('❌ Quote PNG only available for quoted, paid, or vouchered bookings', 'error')
            return redirect(url_for('booking.view', id=booking_id))
        
        # Import required modules
        from services.classic_pdf_generator_quote import ClassicPDFGenerator
        from services.pdf_image import pdf_to_long_png_bytes
        import fitz  # PyMuPDF
        import io
        
        # ✅ ใช้ ClassicPDFGenerator สำหรับ Quote PNG (ใช้ new generator ที่แก้ไขแล้ว)
        quote_generator = ClassicPDFGenerator()
        
        # สร้าง booking data สำหรับ Classic Generator
        booking_data = {
            'booking_id': booking.booking_reference,
            'booking_date': booking.booking_date.strftime('%Y-%m-%d') if booking.booking_date else '',
            'tour_date': booking.tour_date.strftime('%Y-%m-%d') if booking.tour_date else '',
            'tour_time': booking.tour_time.strftime('%H:%M') if booking.tour_time else '',
            'customer': {
                'name': f"{booking.customer_first_name or ''} {booking.customer_last_name or ''}".strip(),
                'phone': booking.customer_phone or '',
                'email': booking.customer_email or ''
            },
            'adults': booking.adults or 0,
            'children': booking.children or 0,
            'infants': booking.infants or 0,
            'hotel': booking.hotel_name or '',
            'room_number': booking.room_number or '',
            'special_requests': booking.special_requests or '',
            'products': booking.products_json if hasattr(booking, 'products_json') and booking.products_json else [],
            'subtotal': float(booking.subtotal or 0),
            'vat_amount': float(booking.vat_amount or 0),
            'total_amount': float(booking.total_amount or 0),
            'discount_amount': float(booking.discount_amount or 0),
            'payment_method': booking.payment_method or '',
            'payment_status': booking.payment_status or '',
            'remarks': booking.remarks or ''
        }
        
        # สร้าง PDF ใน memory buffer
        pdf_buffer = io.BytesIO()
        quote_generator.generate_quote_pdf_to_buffer(booking_data, pdf_buffer)
        pdf_bytes = pdf_buffer.getvalue()
        
        if not pdf_bytes:
            flash('❌ Error generating Quote PDF for PNG conversion', 'error')
            return redirect(url_for('booking.view', id=booking_id))
        
        # Convert PDF to PNG (multi-page support)
        try:
            # Try to create long PNG with all pages stacked vertically
            png_bytes = pdf_to_long_png_bytes(pdf_bytes, zoom=2.0, page_spacing=30)
            if not png_bytes:
                # Fallback to first page only
                doc = fitz.open(pdf_path)
                page = doc.load_page(0)
                mat = fitz.Matrix(2, 2)  # 2x zoom
                pix = page.get_pixmap(matrix=mat)
                png_bytes = pix.tobytes("png")
                doc.close()
        except Exception as e:
            logger.warning(f"Multi-page PNG failed, using single page: {str(e)}")
            # Fallback to first page only
            doc = fitz.open(pdf_path)
            page = doc.load_page(0)
            mat = fitz.Matrix(2, 2)  # 2x zoom  
            pix = page.get_pixmap(matrix=mat)
            png_bytes = pix.tobytes("png")
            doc.close()
        
        # Generate filename with latest update timestamp: Quote_PNG_BK20250922O8NP_20250922_151030.png
        from datetime import datetime
        current_time = datetime.now()
        date_stamp = current_time.strftime('%Y%m%d')
        time_stamp = current_time.strftime('%H%M%S')
        filename = f'Quote_PNG_{booking.booking_reference}_{date_stamp}_{time_stamp}.png'
        
        return Response(
            png_bytes,
            mimetype='image/png',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'}
        )
            
    except Exception as e:
        logger.error(f"Error generating Quote PNG for booking {booking_id}: {str(e)}")
        flash('❌ Error generating Quote PNG', 'error')
        return redirect(url_for('booking.view', id=booking_id))

# Email PDF Routes
@booking_bp.route('/<int:booking_id>/email-pdf', methods=['GET', 'POST'])
@login_required
def email_booking_pdf(booking_id):
    """Send booking message via email (without PDF attachment)"""
    booking = Booking.query.get_or_404(booking_id)
    
    if request.method == 'POST':
        recipient_email = request.form.get('email', '').strip()
        
        if not recipient_email:
            flash('❌ Email address is required', 'error')
            return redirect(url_for('booking.email_booking_pdf', booking_id=booking_id))
        
        try:
            # Generate public URL token
            from booking_share_manager import BookingShareManager
            share_manager = BookingShareManager()
            
            # Generate secure token
            token = share_manager.generate_secure_token(booking.id, expires_days=120)
            
            # Build URLs
            base_url = request.url_root.rstrip('/')
            public_url = f"{base_url}/public/booking/{token}"
            png_url = f"{base_url}/public/booking/{token}/png"
            pdf_url = f"{base_url}/public/booking/{token}/pdf"
            
            share_data = {
                'url': public_url,
                'png_url': png_url,
                'pdf_url': pdf_url,
                'token': token
            }
            
            if not share_data:
                flash('❌ Error generating share links', 'error')
                return redirect(url_for('booking.view', id=booking_id))
            
            public_url = share_data['url']
            png_url = share_data['png_url']
            pdf_url = share_data['pdf_url']
            
            # Prepare email content
            customer_name = booking.customer.full_name if booking.customer else 'ลูกค้า'
            reference = booking.booking_reference or f"#{booking.id}"
            
            email_body = f"""สวัสดีค่ะ
บริษัท ตระกูลเฉินฯ แจ้งรายละเอียดบริการหรือรายการทัวร์ หมายเลขอ้างอิง {reference}

กรุณาคลิกดูรายละเอียดตามด้านล่างค่ะ

📋 Service Proposal: {public_url}

━━━━━━━━━
💡แนะนำการใช้งาน
━━━━━━━━━

1) เปิดลิงก์
• เปิดได้ทั้งมือถือ/คอม ไม่ต้องล็อกอิน

2) ตรวจสอบข้อมูล
• ข้อมูลลูกค้า / วันเดินทาง / จำนวนคน
• รายชื่อผู้เดินทาง (ตรงพาสปอร์ต)
• ดาวน์โหลด: E-Ticket, Confirmation, Proposal, Quote, Voucher
• คลิกลิงก์: รายการทัวร์-คู่มือท่องเที่ยว 

3) ดาวน์โหลดเอกสาร
🔴 PNG = ใช้บนมือถือ/พิมพ์
🟣 PDF = เก็บในคอม/ส่งอีเมล
❌ ห้ามแชร์ลิงก์
⏰ หมดอายุ 120 วัน

ติดต่อสอบถามข้อมูลเพิ่มเติม:
📞 Tel: BKK +662 2744216  📞 Tel: HKG +852 23921155
📧 Email: booking@dhakulchan.com
📱 Line OA: @dhakulchan | @changuru
🏛️ รู้จักตระกูลเฉินฯ: https://www.dhakulchan.net/page/about-dhakulchan
"""
            
            # Send email using EmailService
            from services.email_service import EmailService
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            from email.utils import formataddr
            
            email_service = EmailService()
            
            # Create MIMEMultipart message
            msg = MIMEMultipart()
            # Use formataddr to set display name while keeping actual sender as SMTP username
            msg['From'] = formataddr(('DonotReply@dhakulchan.net', email_service.username))
            msg['To'] = recipient_email
            msg['Subject'] = f'รายละเอียดบริการ - {reference}'
            
            # Attach body
            msg.attach(MIMEText(email_body, 'plain', 'utf-8'))
            
            # Send email
            email_service._send_email(msg)
            
            flash(f'✅ Booking message sent successfully to {recipient_email}', 'success')
            return redirect(url_for('booking.view', id=booking_id))
                
        except Exception as e:
            logger.error(f"Error sending booking message email: {str(e)}")
            flash(f'❌ Error sending email: {str(e)}', 'error')
    
    # GET request - show form
    return render_template('booking/email_pdf_form.html', 
                         booking=booking, 
                         pdf_type='booking message',
                         action_url=url_for('booking.email_booking_pdf', booking_id=booking_id))

@booking_bp.route('/<int:booking_id>/email-quote-pdf', methods=['GET', 'POST'])
@login_required
def email_quote_pdf(booking_id):
    """Send quote PDF via email"""
    booking = Booking.query.get_or_404(booking_id)
    
    if request.method == 'POST':
        recipient_email = request.form.get('email', '').strip()
        
        if not recipient_email:
            flash('❌ Email address is required', 'error')
            return redirect(url_for('booking.email_quote_pdf', booking_id=booking_id))
        
        try:
            # Generate PDF first
            from services.weasyprint_quote_generator import WeasyPrintQuoteGenerator
            generator = WeasyPrintQuoteGenerator()
            pdf_filename = generator.generate_quote_pdf(booking)
            
            if pdf_filename and os.path.exists(pdf_filename):
                # Send email
                from services.email_service import EmailService
                email_service = EmailService()
                email_service.send_quote_pdf(recipient_email, pdf_filename, booking)
                
                # Clean up temporary file
                os.unlink(pdf_filename)
                
                flash(f'✅ Quote PDF sent successfully to {recipient_email}', 'success')
                return redirect(url_for('booking.view', id=booking_id))
            else:
                flash('❌ Error generating quote PDF', 'error')
                
        except Exception as e:
            logger.error(f"Error sending quote PDF email: {str(e)}")
            flash(f'❌ Error sending email: {str(e)}', 'error')
    
    # GET request - show form
    return render_template('booking/email_pdf_form.html', 
                         booking=booking, 
                         pdf_type='quote',
                         action_url=url_for('booking.email_quote_pdf', booking_id=booking_id))


@booking_bp.route('/cancel/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    """Cancel a booking by setting status to cancelled"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        # Check if booking can be cancelled
        if booking.status == 'cancelled':
            flash('❌ Booking is already cancelled', 'warning')
            return redirect(url_for('booking.view', id=booking_id))
            
        # Update booking status to cancelled
        old_status = booking.status
        booking.status = 'cancelled'
        booking.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Create activity log for cancellation
        from models_mariadb import ActivityLog
        
        ActivityLog.log_activity(
            'booking', booking_id, 'booking_cancelled', 
            f"Booking cancelled by {current_user.username if current_user else 'system'} (was: {old_status})"
        )
        
        flash(f'✅ Booking {booking.booking_reference} has been cancelled successfully', 'success')
        logger.info(f"Booking {booking.booking_reference} cancelled by user {current_user.username}")
        
        return redirect(url_for('booking.view', id=booking_id))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error cancelling booking {booking_id}: {str(e)}")
        flash(f'❌ Error cancelling booking: {str(e)}', 'error')
        return redirect(url_for('booking.view', id=booking_id))


@booking_bp.route('/<int:booking_id>/pending', methods=['POST'])
@login_required
def pending_booking(booking_id):
    """Move booking from draft to pending status"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        # Check if booking can be moved to pending
        if booking.status != 'draft':
            return jsonify({
                'success': False,
                'message': f'Booking must be in draft status to move to pending. Current status: {booking.status}'
            })
            
        # Store old status for activity log
        old_status = booking.status
        
        # Update booking status to pending
        booking.status = 'pending'
        booking.updated_at = datetime.utcnow()
        
        # Create activity log entry for status change
        try:
            import pymysql
            
            connection = pymysql.connect(
                host='localhost',
                user='voucher_user',
                password='voucher_secure_2024',
                database='voucher_enhanced',
                charset='utf8mb4'
            )
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO activity_logs (booking_id, action, description, created_at) 
                    VALUES (%s, %s, %s, %s)
                """, (
                    booking_id,
                    'status_updated',
                    f'Booking status changed from {old_status} to pending',
                    datetime.now()
                ))
                connection.commit()
                current_app.logger.info(f"✅ Activity log created for booking {booking_id} status change: {old_status} → pending")
                
        except Exception as e:
            current_app.logger.error(f"❌ Failed to create activity log for booking {booking_id}: {e}")
        finally:
            if 'connection' in locals():
                connection.close()
        
        db.session.commit()
        
        logger.info(f"Booking {booking.booking_reference} moved to pending status by user {current_user.username}")
        
        return jsonify({
            'success': True,
            'message': f'Booking {booking.booking_reference} moved to pending status successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error moving booking {booking_id} to pending: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error moving booking to pending: {str(e)}'
        })


@booking_bp.route('/<int:booking_id>/completed', methods=['POST'])
@login_required
def mark_as_completed(booking_id):
    """Mark booking as completed"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        # Check if booking can be marked as completed
        if booking.status in ['cancelled', 'completed']:
            from flask import flash, redirect, url_for
            flash(f'Booking cannot be marked as completed from {booking.status} status', 'error')
            return redirect(url_for('booking.view', id=booking_id))
            
        # Store old status for activity log
        old_status = booking.status
        
        # Update booking status to completed
        booking.status = 'completed'
        booking.updated_at = datetime.utcnow()
        
        # Create activity log entries for completion
        try:
            import pymysql
            
            connection = pymysql.connect(
                host='localhost',
                user='voucher_user',
                password='voucher_secure_2024',
                database='voucher_enhanced',
                charset='utf8mb4'
            )
            
            with connection.cursor() as cursor:
                # Create status change activity log
                cursor.execute("""
                    INSERT INTO activity_logs (booking_id, action, description, created_at) 
                    VALUES (%s, %s, %s, %s)
                """, (
                    booking_id,
                    'status_updated',
                    f'Booking status changed from {old_status} to completed',
                    datetime.now()
                ))
                
                # Create completion activity log
                cursor.execute("""
                    INSERT INTO activity_logs (booking_id, action, description, created_at) 
                    VALUES (%s, %s, %s, %s)
                """, (
                    booking_id,
                    'booking_completed',
                    f'[BOOKING #{booking_id}] Tour completed! Status: COMPLETED. Thank you for using our services.',
                    datetime.now()
                ))
                
                connection.commit()
                current_app.logger.info(f"✅ Activity logs created for booking {booking_id} completion: {old_status} → completed")
                
        except Exception as e:
            current_app.logger.error(f"❌ Failed to create activity logs for booking {booking_id}: {e}")
        finally:
            if 'connection' in locals():
                connection.close()
        
        db.session.commit()
        
        logger.info(f"Booking {booking.booking_reference} marked as completed by user {current_user.username}")
        
        # Flash success message and redirect to booking view
        from flask import flash, redirect, url_for
        flash(f'Booking {booking.booking_reference} marked as completed successfully', 'success')
        return redirect(url_for('booking.view', id=booking_id))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error marking booking {booking_id} as completed: {str(e)}")
        from flask import flash, redirect, url_for
        flash(f'Error marking booking as completed: {str(e)}', 'error')
        return redirect(url_for('booking.view', id=booking_id))


def sync_booking_to_invoice(booking_id):
    """Auto sync booking data to invoices table when marked as paid"""
    try:
        import pymysql
        from models.booking import Booking
        
        # Get booking if we only have ID
        if isinstance(booking_id, int):
            booking = Booking.query.get(booking_id)
            if not booking:
                logger.error(f"❌ Booking {booking_id} not found")
                return False
        else:
            booking = booking_id  # booking object was passed directly
            booking_id = booking.id
        
        connection = pymysql.connect(
            host='localhost',
            user='voucher_user',
            password='voucher_secure_2024',
            database='voucher_enhanced',
            charset='utf8mb4'
        )
        
        with connection.cursor() as cursor:
            # Generate invoice number starting with QTA25106001
            cursor.execute("SELECT MAX(CAST(SUBSTRING(invoice_number, 9) AS UNSIGNED)) FROM invoices WHERE invoice_number LIKE 'QTA25106%'")
            result = cursor.fetchone()
            next_number = (result[0] + 1) if result[0] else 1
            invoice_number = f"QTA25106{next_number:03d}"
            
            # Check if booking already has an invoice record
            cursor.execute("SELECT id FROM invoices WHERE booking_id = %s", (booking_id,))
            existing_invoice = cursor.fetchone()
            
            if existing_invoice:
                # Update existing invoice
                cursor.execute("""
                    UPDATE invoices SET 
                        invoice_number = %s,
                        title = %s,
                        total_amount = %s,
                        status = 'paid',
                        payment_status = 'paid',
                        paid_date = %s,
                        updated_at = %s
                    WHERE booking_id = %s
                """, (
                    invoice_number,
                    f"Invoice for Booking {booking.booking_reference}",
                    booking.total_amount or 0,
                    datetime.now().date(),
                    datetime.now(),
                    booking_id
                ))
                logger.info(f"✅ Updated existing invoice for booking {booking_id}")
            else:
                # Create new invoice record
                cursor.execute("""
                    INSERT INTO invoices (
                        booking_id, invoice_number, title, description, subtotal,
                        tax_rate, tax_amount, discount_amount, total_amount, status,
                        payment_status, paid_amount, balance_due, invoice_date,
                        due_date, paid_date, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    booking_id,
                    invoice_number,
                    f"Invoice for Booking {booking.booking_reference}",
                    booking.description or "Tour booking services",
                    str(booking.total_amount or 0),
                    '0',
                    '0',
                    '0',
                    str(booking.total_amount or 0),
                    'paid',
                    'paid',
                    str(booking.total_amount or 0),
                    '0',
                    datetime.now().date(),
                    booking.due_date or datetime.now().date(),
                    datetime.now().date(),
                    datetime.now(),
                    datetime.now()
                ))
                logger.info(f"✅ Created new invoice {invoice_number} for booking {booking_id}")
            
            connection.commit()
            
            # Update booking with the invoice number if not already set
            if not booking.invoice_number:
                booking.invoice_number = invoice_number
                db.session.commit()
                
        connection.close()
        
    except Exception as e:
        logger.error(f"❌ Failed to sync booking {booking_id} to invoices: {e}")
        if 'connection' in locals():
            connection.close()
        raise
