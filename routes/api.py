from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models.customer import Customer
from models.booking import Booking
from extensions import db
from utils.booking_utils import generate_booking_reference
from datetime import datetime, timedelta
from sqlalchemy import text
import sqlite3
import os

# Thai Language Support
def get_thai_message(message_key):
    """Get Thai translated message"""
    thai_messages = {
        'booking_confirmed': 'การจองได้รับการยืนยันเรียบร้อยแล้ว',
        'booking_marked_paid': 'ทำเครื่องหมายการจองเป็นชำระแล้วเรียบร้อย',
        'voucher_generated': 'สร้างใบบัตรเรียบร้อยแล้ว',
        'pdf_generated': 'สร้างไฟล์ PDF เรียบร้อยแล้ว',
        'png_generated': 'สร้างไฟล์ PNG เรียบร้อยแล้ว',
        'share_token_created': 'สร้างลิงก์แชร์เรียบร้อยแล้ว',
        'settings_updated': 'อัปเดตการตั้งค่าระบบเรียบร้อยแล้ว',
        'banker_added': 'เพิ่มธนาคารเรียบร้อยแล้ว',
        'access_denied': 'ไม่อนุญาตให้เข้าถึง ต้องการสิทธิ์ผู้ดูแลระบบ',
        'booking_not_found': 'ไม่พบข้อมูลการจอง',
        'quote_not_found': 'ไม่พบข้อมูลใบเสนอราคา',
        'invalid_status': 'สถานะไม่ถูกต้อง',
        'required_field': 'ข้อมูลที่จำเป็นไม่ครบถ้วน',
        'invalid_date_format': 'รูปแบบวันที่ไม่ถูกต้อง ใช้ YYYY-MM-DD',
        'invalid_token': 'ลิงก์แชร์ไม่ถูกต้องหรือหมดอายุ'
    }
    return thai_messages.get(message_key, message_key)
import json

api_bp = Blueprint('api', __name__)

@api_bp.route('/docs')
def docs():
    """API Documentation"""
    api_endpoints = {
        'customers': {
            'GET /api/customers': 'Get all customers',
            'POST /api/customers': 'Create new customer',
            'GET /api/customers/<id>': 'Get customer by ID',
            'PUT /api/customers/<id>': 'Update customer',
            'DELETE /api/customers/<id>': 'Delete customer'
        },
        'bookings': {
            'GET /api/bookings': 'Get all bookings',
            'POST /api/bookings': 'Create new booking',
            'GET /api/bookings/<id>': 'Get booking by ID',
            'PUT /api/bookings/<id>': 'Update booking',
            'DELETE /api/bookings/<id>': 'Delete booking'
        },
        'vouchers': {
            'GET /api/vouchers': 'Get all vouchers',
            'POST /api/vouchers': 'Create new voucher',
            'GET /api/vouchers/<id>': 'Get voucher by ID'
        }
    }
    
    return jsonify({
        'status': 'success',
        'message': 'Welcome to the API',
        'title': 'Dhakul Chan Management System API',
        'version': '1.0'
    })

@api_bp.route('/customers', methods=['GET', 'POST'])
@login_required
def customers():
    """Customer API endpoints"""
    if request.method == 'GET':
        customers = Customer.query.all()
        return jsonify([customer.to_dict() for customer in customers])
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            
            # Handle both old and new customer field structure
            if data.get('first_name') or data.get('last_name'):
                # New structure with separate fields
                first_name = data.get('first_name', '').strip()
                last_name = data.get('last_name', '').strip()
                name = f"{first_name} {last_name}".strip()
                
                customer = Customer(
                    name=name,
                    first_name=first_name,
                    last_name=last_name,
                    email=data.get('email'),
                    phone=data.get('phone'),
                    address=data.get('address'),
                    nationality=data.get('nationality'),
                    notes=data.get('notes')
                )
            else:
                # Old structure with single name field
                customer = Customer(
                    name=data.get('name'),
                    email=data.get('email'),
                    phone=data.get('phone'),
                    address=data.get('address'),
                    nationality=data.get('nationality'),
                    notes=data.get('notes')
                )
            
            db.session.add(customer)
            db.session.commit()
            return jsonify(customer.to_dict()), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400

@api_bp.route('/customers/<int:customer_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def customer_detail(customer_id):
    """Individual customer API endpoints"""
    customer = Customer.query.get_or_404(customer_id)
    
    if request.method == 'GET':
        return jsonify(customer.to_dict())
    
    elif request.method == 'PUT':
        try:
            data = request.get_json()
            
            # Handle both old and new customer field structure
            if data.get('first_name') is not None or data.get('last_name') is not None:
                # Update separate name fields
                customer.first_name = data.get('first_name', customer.first_name)
                customer.last_name = data.get('last_name', customer.last_name)
                # Update combined name field
                if customer.first_name or customer.last_name:
                    customer.name = f"{customer.first_name or ''} {customer.last_name or ''}".strip()
            else:
                # Update single name field
                customer.name = data.get('name', customer.name)
            
            customer.email = data.get('email', customer.email)
            customer.phone = data.get('phone', customer.phone)
            customer.address = data.get('address', customer.address)
            customer.nationality = data.get('nationality', customer.nationality)
            customer.notes = data.get('notes', customer.notes)
            db.session.commit()
            return jsonify(customer.to_dict())
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400
    
    elif request.method == 'DELETE':
        try:
            db.session.delete(customer)
            db.session.commit()
            return '', 204
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400

@api_bp.route('/bookings', methods=['GET', 'POST'])
@login_required
def bookings():
    """Booking API endpoints"""
    if request.method == 'GET':
        bookings = Booking.query.all()
        return jsonify([booking.to_dict() for booking in bookings])
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            booking = Booking(
                customer_id=data.get('customer_id'),
                booking_reference=generate_booking_reference(),
                booking_type=data.get('booking_type'),
                status=data.get('status', 'pending'),
                created_by=current_user.id
            )
            
            # Set additional fields based on data
            for field in ['arrival_date', 'departure_date', 'traveling_period_start', 
                         'traveling_period_end', 'total_pax', 'total_amount', 'currency',
                         'agency_reference', 'hotel_name', 'room_type', 'special_request',
                         'pickup_point', 'destination', 'vehicle_type', 'internal_note', 'flight_info']:
                if field in data:
                    setattr(booking, field, data[field])
            
            # Handle guest list and daily services
            if 'guest_list' in data:
                booking.set_guest_list(data['guest_list'])
            if 'daily_services' in data:
                booking.set_daily_services(data['daily_services'])
            
            db.session.add(booking)
            db.session.commit()
            return jsonify(booking.to_dict()), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400

@api_bp.route('/bookings/<int:booking_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def booking_detail(booking_id):
    """Individual booking API endpoints"""
    booking = Booking.query.get_or_404(booking_id)
    
    if request.method == 'GET':
        return jsonify(booking.to_dict())
    
    elif request.method == 'PUT':
        try:
            data = request.get_json()
            
            # Update fields
            for field in ['booking_type', 'status', 'arrival_date', 'departure_date', 
                         'traveling_period_start', 'traveling_period_end', 'total_pax', 
                         'total_amount', 'currency', 'agency_reference', 'hotel_name', 
                         'room_type', 'special_request', 'pickup_point', 'destination', 
                         'vehicle_type', 'internal_note', 'flight_info']:
                if field in data:
                    setattr(booking, field, data[field])
            
            # Handle guest list and daily services
            if 'guest_list' in data:
                booking.set_guest_list(data['guest_list'])
            if 'daily_services' in data:
                booking.set_daily_services(data['daily_services'])
            
            db.session.commit()
            return jsonify(booking.to_dict())
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400
    
    elif request.method == 'DELETE':
        try:
            db.session.delete(booking)
            db.session.commit()
            return '', 204
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400

@api_bp.route('/invoice-ninja/quote', methods=['POST'])
@login_required
def create_quote():
    """Create quote (Invoice Ninja integration removed)"""
    try:
        return jsonify({
            'error': 'Invoice Ninja integration has been removed',
            'message': 'Use internal quote system instead'
        }), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@api_bp.route('/invoice-ninja/invoice', methods=['POST'])
@login_required
def create_invoice():
    """Create invoice (Invoice Ninja integration removed)"""
    try:
        return jsonify({
            'error': 'Invoice Ninja integration has been removed',
            'message': 'Use internal invoice system instead'
        }), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@api_bp.route('/stats/dashboard')
@login_required
def dashboard_stats():
    """Get dashboard statistics"""
    from datetime import datetime, timedelta
    from sqlalchemy import func
    
    # Basic counts
    total_customers = Customer.query.count()
    total_bookings = Booking.query.count()
    pending_bookings = Booking.query.filter_by(status='pending').count()
    confirmed_bookings = Booking.query.filter_by(status='confirmed').count()
    
    # Revenue stats
    total_revenue = db.session.query(func.sum(Booking.total_amount)).filter(
        Booking.status == 'confirmed'
    ).scalar() or 0
    
    # Monthly stats
    current_month = datetime.now().replace(day=1)
    monthly_bookings = Booking.query.filter(Booking.created_at >= current_month).count()
    monthly_revenue = db.session.query(func.sum(Booking.total_amount)).filter(
        Booking.created_at >= current_month,
        Booking.status == 'confirmed'
    ).scalar() or 0
    
    return jsonify({
        'total_customers': total_customers,
        'total_bookings': total_bookings,
        'pending_bookings': pending_bookings,
        'confirmed_bookings': confirmed_bookings,
        'total_revenue': float(total_revenue),
        'monthly_bookings': monthly_bookings,
        'monthly_revenue': float(monthly_revenue)
    })

# Booking Details API endpoint
@api_bp.route('/booking/<int:booking_id>/details')
@login_required
def get_booking_details(booking_id):
    """Get booking details including status - used by View Quote button"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        return jsonify({
            'success': True,
            'booking_id': booking.id,
            'booking_reference': booking.booking_reference,
            'status': booking.status,
            'booking_type': booking.booking_type,
            'quote_number': booking.quote_number,
            'invoice_number': booking.invoice_number,
            'customer_name': booking.customer_name
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Quote API endpoint
@api_bp.route('/booking/<int:booking_id>/quote-id')
@login_required
def get_booking_quote_id(booking_id):
    """Get quote ID for a booking - used by View Quote button"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        # Try to find quote that matches booking's quote_number first
        from models.quote import Quote
        quote = None
        
        # First try to find quote with matching quote_number
        if booking.quote_number:
            quote = Quote.query.filter_by(
                booking_id=booking_id, 
                quote_number=booking.quote_number
            ).first()
        
        # If no match found, get the latest quote for this booking
        if not quote:
            quote = Quote.query.filter_by(booking_id=booking_id).order_by(Quote.created_at.desc()).first()
        
        if quote:
            return jsonify({
                'quote_id': quote.id,
                'quote_number': quote.quote_number,
                'status': quote.status
            })
        
        # Fallback: Use raw SQL with proper database path
        import mysql.connector
        
        mariadb_config = {
            'user': 'voucher_user',
            'password': 'voucher_secure_2024',
            'host': 'localhost',
            'port': 3306,
            'database': 'voucher_enhanced',
            'charset': 'utf8mb4'
        }
        
        conn = mysql.connector.connect(**mariadb_config)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, quote_number, status 
            FROM quotes 
            WHERE booking_id = %s 
            ORDER BY created_at DESC 
            LIMIT 1
        """, (booking_id,))
        
        quote_row = cursor.fetchone()
        conn.close()
        
        if not quote_row:
            return jsonify({
                'error': 'No quote found for this booking'
            }), 404
            
        return jsonify({
            'quote_id': quote_row[0],
            'quote_number': quote_row[1],
            'status': quote_row[2]
        })
        
    except Exception as e:
        print(f"Error getting quote ID for booking {booking_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500


# =============================================================================
# PHASE 3: WORKFLOW MANAGEMENT APIs
# =============================================================================

@api_bp.route('/booking/<int:booking_id>/confirm', methods=['POST'])
@login_required
def confirm_booking(booking_id):
    """Confirm a booking - Phase 3"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        if booking.status != 'draft':
            return jsonify({'error': 'Only pending bookings can be confirmed'}), 400
        
        # Update booking using raw SQL to match existing pattern
        db.session.execute(text("""
            UPDATE booking SET
                status = 'confirmed',
                confirmed_at = :confirmed_at,
                updated_at = :updated_at
            WHERE id = :booking_id
        """), {
            'booking_id': booking_id,
            'confirmed_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        })
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': get_thai_message('booking_confirmed'),
            'message_en': 'Booking confirmed successfully',
            'new_status': 'confirmed'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error confirming booking {booking_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/booking/<int:booking_id>/mark-paid', methods=['POST'])
@login_required
def mark_booking_paid(booking_id):
    """Mark booking as paid - Admin only"""
    try:
        # Check if user is admin (basic check - can be enhanced)
        if not hasattr(current_user, 'role') or current_user.role != 'administrator':
            # Fallback: check if user has admin privileges (adjust based on your user model)
            if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
                return jsonify({
                    'error': get_thai_message('access_denied'),
                    'error_en': 'Access denied. Administrator rights required.'
                }), 403
        
        booking = Booking.query.get_or_404(booking_id)
        
        if booking.status != 'quoted':
            return jsonify({'error': 'Only quoted bookings can be marked as paid'}), 400
        
        data = request.get_json()
        
        # Validate required fields
        received_date = data.get('received_date')
        banker = data.get('banker')
        received_by = data.get('received_by')
        
        if not received_date:
            return jsonify({
                'error': get_thai_message('required_field') + ': วันที่รับเงิน',
                'error_en': 'Received date is required'
            }), 400
        if not banker:
            return jsonify({
                'error': get_thai_message('required_field') + ': ธนาคาร',
                'error_en': 'Banker is required'
            }), 400
        if not received_by:
            return jsonify({
                'error': get_thai_message('required_field') + ': ผู้รับเงิน',
                'error_en': 'Received by is required'
            }), 400
        
        # Parse received_date
        try:
            received_date_obj = datetime.strptime(received_date, '%Y-%m-%d')
        except ValueError:
            return jsonify({
                'error': get_thai_message('invalid_date_format'),
                'error_en': 'Invalid date format. Use YYYY-MM-DD'
            }), 400
        
        # Update booking using raw SQL
        db.session.execute(text("""
            UPDATE booking SET
                status = 'paid',
                paid_at = :paid_at,
                payment_received_date = :received_date,
                payment_banker = :banker,
                payment_received_by = :received_by,
                payment_updated_by = :updated_by,
                updated_at = :updated_at
            WHERE id = :booking_id
        """), {
            'booking_id': booking_id,
            'paid_at': datetime.utcnow(),
            'received_date': received_date_obj,
            'banker': banker,
            'received_by': received_by,
            'updated_by': current_user.id,
            'updated_at': datetime.utcnow()
        })
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': get_thai_message('booking_marked_paid'),
            'message_en': 'Booking marked as paid successfully',
            'new_status': 'paid',
            'payment_details': {
                'received_date': received_date,
                'banker': banker,
                'received_by': received_by,
                'updated_by': current_user.username if hasattr(current_user, 'username') else 'admin'
            }
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error marking booking {booking_id} as paid: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/booking/<int:booking_id>/generate-voucher', methods=['POST'])
@login_required
def generate_voucher_for_booking(booking_id):
    """Generate voucher for a paid booking"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        if booking.status != 'paid':
            return jsonify({'error': 'Booking must be paid to generate voucher'}), 400
        
        # Update status to vouchered using ORM to trigger activity logging
        booking.mark_as_vouchered()
        # Set additional fields that aren't handled by mark_as_vouchered
        booking.voucher_id = booking_id  # For now, voucher_id = booking_id
        booking.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'voucher_id': booking_id,
            'new_status': 'vouchered',
            'message': get_thai_message('voucher_generated'),
            'message_en': 'Voucher generated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error generating voucher for booking {booking_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/booking/<int:booking_id>/voucher-id')
@login_required
def get_booking_voucher_id(booking_id):
    """Get voucher ID for a booking"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        if booking.status == 'vouchered':
            # Use raw SQL to get voucher info
            result = db.session.execute(text("""
                SELECT voucher_id, vouchered_at
                FROM booking 
                WHERE id = :booking_id AND status = 'vouchered'
            """), {'booking_id': booking_id}).fetchone()
            
            if result:
                return jsonify({
                    'voucher_id': result[0] or booking_id,
                    'status': 'vouchered',
                    'vouchered_at': result[1].isoformat() if result[1] else None
                })
        
        return jsonify({'error': 'No voucher found for this booking'}), 404
            
    except Exception as e:
        print(f"Error getting voucher ID for booking {booking_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500


# =============================================================================
# PHASE 3: QUOTE DOCUMENT APIs
# =============================================================================

@api_bp.route('/quote/<int:quote_id>/generate-pdf')
@login_required
def generate_quote_pdf(quote_id):
    """Generate PDF document for a quote"""
    try:
        # Find quote by ID using raw SQL
        result = db.session.execute(text("""
            SELECT q.*, b.id as booking_id, b.guest_name, b.tour_name
            FROM quote q
            LEFT JOIN booking b ON q.booking_id = b.id
            WHERE q.id = :quote_id
        """), {'quote_id': quote_id}).fetchone()
        
        if not result:
            return jsonify({'error': 'Quote not found'}), 404
        
        # For now, return a mock PDF generation response
        # TODO: Implement actual PDF generation using existing booking_invoice_simple.py logic
        return jsonify({
            'success': True,
            'pdf_url': f'/api/quote/{quote_id}/download-pdf',
            'file_name': f'Quote_{result.quote_number or quote_id}.pdf',
            'message': get_thai_message('pdf_generated'),
            'message_en': 'PDF generated successfully'
        })
        
    except Exception as e:
        print(f"Error generating PDF for quote {quote_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/quote/<int:quote_id>/generate-png')
@login_required
def generate_quote_png(quote_id):
    """Generate PNG document for a quote"""
    try:
        # Find quote by ID using raw SQL
        result = db.session.execute(text("""
            SELECT q.*, b.id as booking_id, b.guest_name, b.tour_name
            FROM quote q
            LEFT JOIN booking b ON q.booking_id = b.id
            WHERE q.id = :quote_id
        """), {'quote_id': quote_id}).fetchone()
        
        if not result:
            return jsonify({'error': 'Quote not found'}), 404
        
        # For now, return a mock PNG generation response
        # TODO: Implement actual PNG generation using existing booking_invoice_simple.py logic
        return jsonify({
            'success': True,
            'png_url': f'/api/quote/{quote_id}/download-png',
            'file_name': f'Quote_{result.quote_number or quote_id}.png',
            'message': get_thai_message('png_generated'),
            'message_en': 'PNG generated successfully'
        })
        
    except Exception as e:
        print(f"Error generating PNG for quote {quote_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/quote/<int:quote_id>/share-token', methods=['POST'])
@login_required
def create_quote_share_token(quote_id):
    """Create a shareable token for a quote"""
    try:
        # Find quote by ID
        result = db.session.execute(text("""
            SELECT id, quote_number, booking_id
            FROM quote 
            WHERE id = :quote_id
        """), {'quote_id': quote_id}).fetchone()
        
        if not result:
            return jsonify({'error': 'Quote not found'}), 404
        
        # Generate a unique share token
        import secrets
        share_token = secrets.token_urlsafe(32)
        
        # Store the share token (using booking table for now - can be extended to dedicated share_tokens table)
        db.session.execute(text("""
            UPDATE booking SET
                share_token = :share_token,
                share_token_created_at = :created_at
            WHERE id = :booking_id
        """), {
            'share_token': share_token,
            'created_at': datetime.utcnow(),
            'booking_id': result.booking_id
        })
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'share_token': share_token,
            'share_url': f'/quote/shared/{share_token}',
            'message': 'Share token created successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating share token for quote {quote_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/quote/shared/<share_token>')
def view_shared_quote(share_token):
    """View a quote using a share token (public endpoint)"""
    try:
        # Find booking and quote by share token
        result = db.session.execute(text("""
            SELECT b.id as booking_id, b.guest_name, b.tour_name, 
                   q.id as quote_id, q.quote_number
            FROM booking b
            LEFT JOIN quote q ON b.id = q.booking_id
            WHERE b.share_token = :share_token
        """), {'share_token': share_token}).fetchone()
        
        if not result:
            return jsonify({'error': 'Invalid or expired share token'}), 404
        
        # Return basic quote information for public viewing
        return jsonify({
            'quote_id': result.quote_id,
            'quote_number': result.quote_number,
            'guest_name': result.guest_name,
            'tour_name': result.tour_name,
            'booking_id': result.booking_id,
            'share_token': share_token
        })
        
    except Exception as e:
        print(f"Error viewing shared quote with token {share_token}: {str(e)}")
        return jsonify({'error': str(e)}), 500


# =============================================================================
# PHASE 3: DOCUMENT GENERATION APIs
# =============================================================================

@api_bp.route('/booking/<int:booking_id>/generate-service-proposal', methods=['POST'])
@login_required
def generate_service_proposal(booking_id):
    """Generate service proposal document for a booking"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        data = request.get_json() or {}
        format_type = data.get('format', 'pdf').lower()  # 'pdf' or 'png'
        
        if format_type not in ['pdf', 'png']:
            return jsonify({'error': 'Format must be pdf or png'}), 400
        
        # TODO: Implement actual document generation using existing logic
        # For now, return mock response
        file_name = f"Service_Proposal_{booking.id}_{int(datetime.utcnow().timestamp())}.{format_type}"
        
        return jsonify({
            'success': True,
            'document_url': f'/api/booking/{booking_id}/download-service-proposal/{format_type}',
            'file_name': file_name,
            'format': format_type,
            'message': f'Service proposal {format_type.upper()} generated successfully'
        })
        
    except Exception as e:
        print(f"Error generating service proposal for booking {booking_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/booking/<int:booking_id>/generate-tour-voucher', methods=['POST'])
@login_required
def generate_tour_voucher(booking_id):
    """Generate tour voucher document for a booking"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        if booking.status != 'vouchered':
            return jsonify({'error': 'Booking must be in vouchered status to generate tour voucher'}), 400
        
        data = request.get_json() or {}
        format_type = data.get('format', 'pdf').lower()  # 'pdf' or 'png'
        
        if format_type not in ['pdf', 'png']:
            return jsonify({'error': 'Format must be pdf or png'}), 400
        
        # TODO: Implement actual document generation using existing logic
        # For now, return mock response
        file_name = f"Tour_Voucher_{booking.id}_{int(datetime.utcnow().timestamp())}.{format_type}"
        
        return jsonify({
            'success': True,
            'document_url': f'/api/booking/{booking_id}/download-tour-voucher/{format_type}',
            'file_name': file_name,
            'format': format_type,
            'voucher_id': booking.id,
            'message': f'Tour voucher {format_type.upper()} generated successfully'
        })
        
    except Exception as e:
        print(f"Error generating tour voucher for booking {booking_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/documents/batch-generate', methods=['POST'])
@login_required
def batch_generate_documents():
    """Batch generate multiple documents"""
    try:
        data = request.get_json()
        
        if not data or 'bookings' not in data:
            return jsonify({'error': 'Bookings array is required'}), 400
        
        bookings_data = data['bookings']
        doc_type = data.get('document_type', 'service_proposal')  # 'service_proposal', 'tour_voucher', 'quote'
        format_type = data.get('format', 'pdf')
        
        results = []
        errors = []
        
        for booking_data in bookings_data:
            booking_id = booking_data.get('booking_id')
            if not booking_id:
                errors.append({'error': 'booking_id is required for each booking'})
                continue
            
            try:
                booking = Booking.query.get(booking_id)
                if not booking:
                    errors.append({'booking_id': booking_id, 'error': 'Booking not found'})
                    continue
                
                # Mock generation - TODO: implement actual logic
                file_name = f"{doc_type}_{booking_id}_{int(datetime.utcnow().timestamp())}.{format_type}"
                results.append({
                    'booking_id': booking_id,
                    'success': True,
                    'file_name': file_name,
                    'document_url': f'/api/booking/{booking_id}/download-{doc_type.replace("_", "-")}/{format_type}'
                })
                
            except Exception as e:
                errors.append({'booking_id': booking_id, 'error': str(e)})
        
        return jsonify({
            'success': len(results) > 0,
            'generated_count': len(results),
            'error_count': len(errors),
            'results': results,
            'errors': errors
        })
        
    except Exception as e:
        print(f"Error in batch document generation: {str(e)}")
        return jsonify({'error': str(e)}), 500


# =============================================================================
# PHASE 3: CONFIGURATION APIs
# =============================================================================

@api_bp.route('/config/bankers', methods=['GET'])
@login_required
def get_bankers_list():
    """Get list of available bankers"""
    try:
        # For now, return a default list - can be moved to database later
        bankers = [
            "First Bank",
            "National Bank",
            "Commercial Bank",
            "Trust Bank",
            "Regional Bank",
            "Online Bank"
        ]
        
        return jsonify({
            'success': True,
            'bankers': bankers
        })
        
    except Exception as e:
        print(f"Error getting bankers list: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/config/bankers', methods=['POST'])
@login_required
def add_banker():
    """Add a new banker to the list (Admin only)"""
    try:
        # Check admin permissions
        if not hasattr(current_user, 'role') or current_user.role != 'administrator':
            if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
                return jsonify({'error': 'Access denied. Administrator rights required.'}), 403
        
        data = request.get_json()
        banker_name = data.get('banker_name', '').strip()
        
        if not banker_name:
            return jsonify({'error': 'Banker name is required'}), 400
        
        # TODO: Store in database table instead of hardcoded list
        # For now, return success message
        return jsonify({
            'success': True,
            'banker_name': banker_name,
            'message': f'Banker "{banker_name}" added successfully'
        })
        
    except Exception as e:
        print(f"Error adding banker: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/config/system-settings', methods=['GET'])
@login_required
def get_system_settings():
    """Get system configuration settings"""
    try:
        # Mock system settings - can be extended with actual config
        settings = {
            'quote_number_prefix': 'QT',
            'quote_number_start': 5449112,
            'default_currency': 'USD',
            'max_file_upload_size': '10MB',
            'pdf_generation_enabled': True,
            'png_generation_enabled': True,
            'email_notifications_enabled': True,
            'auto_backup_enabled': True,
            'workflow_steps': [
                'draft',
                'confirmed', 
                'quoted',
                'paid',
                'vouchered'
            ]
        }
        
        return jsonify({
            'success': True,
            'settings': settings
        })
        
    except Exception as e:
        print(f"Error getting system settings: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/config/system-settings', methods=['PUT'])
@login_required
def update_system_settings():
    """Update system configuration settings (Admin only)"""
    try:
        # Check admin permissions
        if not hasattr(current_user, 'role') or current_user.role != 'administrator':
            if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
                return jsonify({'error': 'Access denied. Administrator rights required.'}), 403
        
        data = request.get_json()
        
        # TODO: Implement actual settings update logic
        # For now, return success message
        return jsonify({
            'success': True,
            'updated_settings': data,
            'message': 'System settings updated successfully'
        })
        
    except Exception as e:
        print(f"Error updating system settings: {str(e)}")
        return jsonify({'error': str(e)}), 500


# =============================================================================
# PHASE 3: ENHANCED STATISTICS API
# =============================================================================

@api_bp.route('/stats/dashboard')
@login_required
def get_enhanced_dashboard_stats():
    """Get comprehensive dashboard statistics"""
    try:
        # Get current date info
        today = datetime.utcnow().date()
        this_month_start = today.replace(day=1)
        last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
        this_year_start = today.replace(month=1, day=1)
        
        # Basic booking counts by status
        status_counts = db.session.execute(text("""
            SELECT status, COUNT(*) as count
            FROM booking 
            GROUP BY status
        """)).fetchall()
        
        # Monthly booking trends
        monthly_bookings = db.session.execute(text("""
            SELECT 
                strftime('%Y-%m', created_at) as month,
                COUNT(*) as count,
                SUM(CASE WHEN status = 'paid' THEN 1 ELSE 0 END) as paid_count,
                SUM(CASE WHEN status = 'vouchered' THEN 1 ELSE 0 END) as vouchered_count
            FROM booking
            WHERE created_at >= date('now', '-12 months')
            GROUP BY strftime('%Y-%m', created_at)
            ORDER BY month
        """)).fetchall()
        
        # Top destinations/tours
        top_tours = db.session.execute(text("""
            SELECT 
                tour_name,
                COUNT(*) as booking_count,
                SUM(CASE WHEN status = 'paid' THEN 1 ELSE 0 END) as paid_bookings
            FROM booking
            WHERE tour_name IS NOT NULL AND tour_name != ''
            GROUP BY tour_name
            ORDER BY booking_count DESC
            LIMIT 10
        """)).fetchall()
        
        # Revenue statistics (if price/amount fields exist)
        revenue_stats = db.session.execute(text("""
            SELECT 
                COUNT(CASE WHEN status = 'paid' THEN 1 END) as paid_bookings,
                COUNT(CASE WHEN status = 'quoted' THEN 1 END) as quoted_bookings,
                COUNT(CASE WHEN status = 'confirmed' THEN 1 END) as confirmed_bookings
            FROM booking
        """)).fetchone()
        
        # Recent activity
        recent_bookings = db.session.execute(text("""
            SELECT id, guest_name, tour_name, status, created_at, updated_at
            FROM booking
            ORDER BY updated_at DESC
            LIMIT 10
        """)).fetchall()
        
        # Conversion funnel
        conversion_stats = db.session.execute(text("""
            SELECT 
                SUM(CASE WHEN status = 'draft' THEN 1 ELSE 0 END) as draft_count,
                SUM(CASE WHEN status = 'confirmed' THEN 1 ELSE 0 END) as confirmed_count,
                SUM(CASE WHEN status = 'quoted' THEN 1 ELSE 0 END) as quoted_count,
                SUM(CASE WHEN status = 'paid' THEN 1 ELSE 0 END) as paid_count,
                SUM(CASE WHEN status = 'vouchered' THEN 1 ELSE 0 END) as vouchered_count,
                COUNT(*) as total_bookings
            FROM booking
        """)).fetchone()
        
        # Format results
        dashboard_stats = {
            'summary': {
                'total_bookings': sum([row[1] for row in status_counts]),
                'status_breakdown': {row[0]: row[1] for row in status_counts},
                'paid_bookings': revenue_stats[0] if revenue_stats else 0,
                'quoted_bookings': revenue_stats[1] if revenue_stats else 0,
                'confirmed_bookings': revenue_stats[2] if revenue_stats else 0
            },
            'monthly_trends': [
                {
                    'month': row[0],
                    'total_bookings': row[1],
                    'paid_bookings': row[2],
                    'vouchered_bookings': row[3]
                } for row in monthly_bookings
            ],
            'top_tours': [
                {
                    'tour_name': row[0],
                    'booking_count': row[1],
                    'paid_count': row[2]
                } for row in top_tours
            ],
            'conversion_funnel': {
                'draft': conversion_stats[0] if conversion_stats else 0,
                'confirmed': conversion_stats[1] if conversion_stats else 0,
                'quoted': conversion_stats[2] if conversion_stats else 0,
                'paid': conversion_stats[3] if conversion_stats else 0,
                'vouchered': conversion_stats[4] if conversion_stats else 0,
                'total': conversion_stats[5] if conversion_stats else 0
            },
            'recent_activity': [
                {
                    'id': row[0],
                    'guest_name': row[1],
                    'tour_name': row[2],
                    'status': row[3],
                    'created_at': row[4],
                    'updated_at': row[5]
                } for row in recent_bookings
            ],
            'generated_at': datetime.utcnow().isoformat()
        }
        
        return jsonify({
            'success': True,
            'stats': dashboard_stats
        })
        
    except Exception as e:
        print(f"Error getting enhanced dashboard stats: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/stats/export')
@login_required  
def export_statistics():
    """Export statistics data for reporting"""
    try:
        # Check admin permissions for export
        if not hasattr(current_user, 'role') or current_user.role != 'administrator':
            if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
                return jsonify({'error': 'Access denied. Administrator rights required.'}), 403
        
        # Get all bookings with detailed info
        all_bookings = db.session.execute(text("""
            SELECT 
                b.id, b.guest_name, b.tour_name, b.status, b.created_at, b.updated_at,
                b.paid_at, b.confirmed_at, b.vouchered_at,
                q.id as quote_id, q.quote_number
            FROM booking b
            LEFT JOIN quote q ON b.id = q.booking_id
            ORDER BY b.created_at DESC
        """)).fetchall()
        
        export_data = {
            'export_timestamp': datetime.utcnow().isoformat(),
            'total_records': len(all_bookings),
            'bookings': [
                {
                    'booking_id': row[0],
                    'guest_name': row[1],
                    'tour_name': row[2],
                    'status': row[3],
                    'created_at': row[4],
                    'updated_at': row[5],
                    'paid_at': row[6],
                    'confirmed_at': row[7],
                    'vouchered_at': row[8],
                    'quote_id': row[9],
                    'quote_number': row[10]
                } for row in all_bookings
            ]
        }
        
        return jsonify({
            'success': True,
            'export_data': export_data
        })
        
    except Exception as e:
        print(f"Error exporting statistics: {str(e)}")
        return jsonify({'error': str(e)}), 500


# =============================================================================
# THAI LANGUAGE SUPPORT APIs
# =============================================================================

@api_bp.route('/lang/translations')
def get_translations():
    """Get all available translations for frontend"""
    try:
        from routes.language import TRANSLATIONS, get_current_language
        
        current_lang = get_current_language()
        
        # Extended Thai translations for API responses
        extended_translations = {
            'th': {
                **TRANSLATIONS.get('th', {}),
                'api_messages': {
                    'booking_confirmed': 'การจองได้รับการยืนยันเรียบร้อยแล้ว',
                    'booking_marked_paid': 'ทำเครื่องหมายการจองเป็นชำระแล้วเรียบร้อย',
                    'voucher_generated': 'สร้างใบบัตรเรียบร้อยแล้ว',
                    'pdf_generated': 'สร้างไฟล์ PDF เรียบร้อยแล้ว',
                    'png_generated': 'สร้างไฟล์ PNG เรียบร้อยแล้ว',
                    'share_token_created': 'สร้างลิงก์แชร์เรียบร้อยแล้ว',
                    'settings_updated': 'อัปเดตการตั้งค่าระบบเรียบร้อยแล้ว',
                    'banker_added': 'เพิ่มธนาคารเรียบร้อยแล้ว',
                    'access_denied': 'ไม่อนุญาตให้เข้าถึง ต้องการสิทธิ์ผู้ดูแลระบบ',
                    'booking_not_found': 'ไม่พบข้อมูลการจอง',
                    'quote_not_found': 'ไม่พบข้อมูลใบเสนอราคา',
                    'invalid_status': 'สถานะไม่ถูกต้อง',
                    'required_field': 'ข้อมูลที่จำเป็นไม่ครบถ้วน',
                    'invalid_date_format': 'รูปแบบวันที่ไม่ถูกต้อง ใช้ YYYY-MM-DD',
                    'invalid_token': 'ลิงก์แชร์ไม่ถูกต้องหรือหมดอายุ'
                },
                'workflow_steps': {
                    'draft': 'รอดำเนินการ',
                    'confirmed': 'ยืนยันแล้ว',
                    'quoted': 'เสนอราคาแล้ว',
                    'paid': 'ชำระแล้ว',
                    'vouchered': 'ออกใบบัตรแล้ว'
                },
                'payment_details': {
                    'received_date': 'วันที่รับเงิน',
                    'banker': 'ธนาคาร',
                    'received_by': 'ผู้รับเงิน',
                    'updated_by': 'อัปเดตโดย'
                },
                'document_types': {
                    'service_proposal': 'ใบเสนอบริการ',
                    'tour_voucher': 'ใบบัตรทัวร์',
                    'quote': 'ใบเสนอราคา'
                }
            },
            'en': {
                **TRANSLATIONS.get('en', {}),
                'api_messages': {
                    'booking_confirmed': 'Booking confirmed successfully',
                    'booking_marked_paid': 'Booking marked as paid successfully',
                    'voucher_generated': 'Voucher generated successfully',
                    'pdf_generated': 'PDF generated successfully',
                    'png_generated': 'PNG generated successfully',
                    'share_token_created': 'Share token created successfully',
                    'settings_updated': 'System settings updated successfully',
                    'banker_added': 'Banker added successfully',
                    'access_denied': 'Access denied. Administrator rights required.',
                    'booking_not_found': 'Booking not found',
                    'quote_not_found': 'Quote not found',
                    'invalid_status': 'Invalid status',
                    'required_field': 'Required field missing',
                    'invalid_date_format': 'Invalid date format. Use YYYY-MM-DD',
                    'invalid_token': 'Invalid or expired share token'
                },
                'workflow_steps': {
                    'draft': 'Pending',
                    'confirmed': 'Confirmed',
                    'quoted': 'Quoted',
                    'paid': 'Paid',
                    'vouchered': 'Vouchered'
                },
                'payment_details': {
                    'received_date': 'Received Date',
                    'banker': 'Banker',
                    'received_by': 'Received By',
                    'updated_by': 'Updated By'
                },
                'document_types': {
                    'service_proposal': 'Service Proposal',
                    'tour_voucher': 'Tour Voucher',
                    'quote': 'Quote'
                }
            }
        }
        
        return jsonify({
            'success': True,
            'current_language': current_lang,
            'translations': extended_translations.get(current_lang, extended_translations['en']),
            'all_translations': extended_translations
        })
        
    except Exception as e:
        print(f"Error getting translations: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/lang/set-language/<language>', methods=['POST'])
def set_api_language(language):
    """Set language preference for API responses"""
    try:
        from flask import session
        
        supported_languages = ['th', 'en']
        
        if language in supported_languages:
            session['language'] = language
            return jsonify({
                'success': True,
                'language': language,
                'message': get_thai_message('settings_updated') if language == 'th' else 'Language updated successfully'
            })
        else:
            return jsonify({
                'error': 'Unsupported language. Supported: th, en',
                'error_th': 'ภาษาที่ไม่รองรับ รองรับเฉพาะ: th, en'
            }), 400
            
    except Exception as e:
        print(f"Error setting language: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/lang/test-thai', methods=['GET'])
def test_thai_support():
    """Test Thai language support and encoding"""
    try:
        thai_test_data = {
            'greeting': 'สวัสดีครับ/ค่ะ',
            'company_name': 'บริษัท ดาคูล จันทร์ ทราเวล เซอร์วิส (ไทยแลนด์) จำกัด',
            'sample_tours': [
                'ทัวร์กรุงเทพมหานคร',
                'ทัวร์เชียงใหม่',
                'ทัวร์ภูเก็ต',
                'ทัวร์กระบี่'
            ],
            'sample_booking': {
                'guest_name': 'คุณสมชาย ใจดี',
                'tour_name': 'ทัวร์วังพระราม 5 + อาหารไทยแท้',
                'special_requests': 'อาหารมังสวิรัติ ไม่ทานเผ็ด',
                'notes': 'ลูกค้าท่านนี้เป็นคนสำคัญ กรุณาดูแลเป็นพิเศษ'
            },
            'encoding_test': {
                'thai_chars': 'กขคงจฉชซญฏฐดตถทนนบปผฝพฟมยรลวศษสหฬอฮ',
                'tone_marks': 'ก่ ก้ ก๊ ก๋',
                'numbers': '๐๑๒๓๔๕๖๗๘๙',
                'special_chars': '฿ ๆ ฯ'
            }
        }
        
        return jsonify({
            'success': True,
            'message': 'ทดสอบการรองรับภาษาไทยสำเร็จ',
            'message_en': 'Thai language support test successful',
            'encoding': 'UTF-8',
            'thai_data': thai_test_data,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        print(f"Error in Thai language test: {str(e)}")
        return jsonify({'error': str(e)}), 500
