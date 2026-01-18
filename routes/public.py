"""Public routes for sharing booking information without authentication."""

from flask import Blueprint, render_template, abort, url_for, redirect, send_from_directory, make_response, send_file, current_app
from models.booking import Booking
from models.booking_enhanced import BookingEnhanced
from config import Config
from extensions import db
import os
import logging
from datetime import datetime
from io import BytesIO

# Set up logger
logger = logging.getLogger(__name__)

public_bp = Blueprint('public', __name__, url_prefix='/public')

@public_bp.route('/test')
def test_route():
    """Simple test route to verify blueprint works"""
    return "Public route works!", 200

@public_bp.app_template_filter('safe_date')
def safe_date_filter(date_value, format='%d/%m/%Y'):
    """Safely format date - handles both string and datetime objects"""
    if not date_value:
        return 'N/A'
    
    # If it's already a string, return as is
    if isinstance(date_value, str):
        return date_value
    
    # If it's a datetime object, format it
    try:
        if hasattr(date_value, 'strftime'):
            return date_value.strftime(format)
        else:
            return str(date_value)
    except Exception:
        return str(date_value)

@public_bp.route('/booking/<int:booking_id>')
def view_booking_public(booking_id):
    """Public view for booking - no login required (backward compatibility)"""
    booking = Booking.query.get_or_404(booking_id)
    
    # Redirect to thank you page if booking is completed
    if booking.status == 'completed':
        return render_template('public/completed_thank_you.html', booking=booking, config=Config)
    
    # สร้าง PNG URL สำหรับ public view
    png_url = url_for('booking.generate_service_proposal_png', booking_id=booking.id, _external=True)
    
    # Generate secure token for PDF/PNG downloads
    from models.booking_enhanced import BookingEnhanced
    token = BookingEnhanced.generate_secure_token(booking.id)
    
    from datetime import datetime
    return render_template('public/enhanced_booking_view.html', 
                         booking=booking, 
                         token=token,
                         png_url=png_url,
                         config=Config,
                         now=datetime.now)

@public_bp.route('/booking/<path:token>/pdf')
def download_booking_pdf(token):
    """Enhanced PDF download with status-based generation using new token system"""
    
    from extensions import db  # Import db for raw SQL
    logger = logging.getLogger(__name__)
    
    # Use enhanced token verification system
    from models.booking_enhanced import BookingEnhanced
    from models.booking import Booking as BookingModel
    
    booking_id = BookingEnhanced.verify_secure_token(token)
    if booking_id:
        # Get DB version via RAW SQL to avoid ORM cache
        raw_version_sql = db.session.execute(
            db.text("SELECT share_token_version FROM bookings WHERE id = :id"),
            {"id": booking_id}
        ).fetchone()
        db_version = raw_version_sql[0] if raw_version_sql else 1
        
        # Verify token version and check booking status
        booking_model = BookingModel.query.get(booking_id)
        if booking_model:
            # Extract version from token
            try:
                import base64
                padded_token = token + '=' * (4 - len(token) % 4)
                decoded_bytes = base64.b64decode(padded_token)
                decoded_str = decoded_bytes.decode('utf-8', errors='ignore')
                parts = decoded_str.split('|')
                
                # Check token version
                if len(parts) >= 4:
                    try:
                        token_version = int(parts[2])
                        if token_version < db_version:
                            logger.warning(f'🚫 Old token version {token_version} < {db_version}')
                            return render_template('public/token_expired.html'), 403
                    except (ValueError, IndexError):
                        pass
                elif len(parts) == 3:
                    # Old token format - check if token was reset
                    if db_version > 1:
                        logger.warning(f'🚫 Old token format, current version {db_version}')
                        return render_template('public/token_expired.html'), 403
            except Exception as e:
                logger.warning(f'Could not parse token version: {e}')
            
            # Check if booking is cancelled
            if booking_model.status == 'cancelled':
                logger.warning(f'🚫 Booking {booking_id} is cancelled')
                return render_template('public/token_expired.html'), 403
        
        # Check if booking is locked
        try:
            from routes.booking import is_booking_locked
            if is_booking_locked(booking_id):
                logger.warning(f'🔒 Booking {booking_id} PDF sharing is locked')
                return render_template('public/token_expired.html'), 403
        except ImportError:
            pass  # Gracefully handle if function doesn't exist
        # Get booking by verified ID
        booking = Booking.query.get_or_404(booking_id)
    else:
        # Fallback to old token system for backward compatibility
        booking = Booking.verify_share_token(token)
        if not booking:
            # Try manual token parsing as final fallback
            logger.info("PDF route: Both token verification methods failed - trying manual parsing")
            try:
                import base64
                # Add padding if needed
                padded_token = token + '=' * (4 - len(token) % 4)
                decoded_bytes = base64.urlsafe_b64decode(padded_token)
                decoded_str = decoded_bytes.decode('utf-8', errors='ignore')
                
                # Look for booking ID pattern
                if '|' in decoded_str:
                    parts = decoded_str.split('|')
                    if len(parts) >= 1:
                        try:
                            booking_id = int(parts[0])
                            logger.info(f"PDF route: Extracted booking ID {booking_id} from token")
                            
                            # Verify token version from decoded data
                            booking_model = BookingModel.query.get(booking_id)
                            if booking_model:
                                # Get DB version via RAW SQL
                                raw_ver = db.session.execute(
                                    db.text("SELECT share_token_version FROM bookings WHERE id = :id"),
                                    {"id": booking_id}
                                ).fetchone()
                                db_ver = raw_ver[0] if raw_ver else 1
                                
                                # Check token version if available in decoded token
                                if len(parts) >= 4:
                                    try:
                                        token_version = int(parts[2])
                                        if token_version < db_ver:
                                            logger.warning(f'🚫 PDF: Old token version {token_version} < {db_ver}')
                                            return render_template('public/token_expired.html'), 403
                                    except (ValueError, AttributeError):
                                        pass
                                elif len(parts) == 3:
                                    # Old 3-part format - check if version > 1
                                    if db_ver > 1:
                                        logger.warning(f'🚫 PDF: Old 3-part token, DB version={db_ver}')
                                        return render_template('public/token_expired.html'), 403
                                
                                # Check if booking is cancelled
                                if booking_model.status == 'cancelled':
                                    logger.warning(f'🚫 Booking {booking_id} is cancelled')
                                    return render_template('public/token_expired.html'), 403
                            
                            booking = Booking.query.get(booking_id)
                            if booking:
                                logger.info(f"PDF route: Found booking {booking_id} via manual parsing")
                            else:
                                logger.error(f"PDF route: Booking {booking_id} not found")
                        except (ValueError, IndexError) as e:
                            logger.error(f"PDF route: Could not parse booking ID: {e}")
            except Exception as parse_error:
                logger.error(f"PDF route: Token manual parsing failed: {parse_error}")
            
            if not booking:
                return render_template('public/token_expired.html'), 404

    # Check if booking is completed - redirect to thank you page
    if booking.status == 'completed':
        from flask import redirect, url_for
        return redirect(url_for('public.view_booking_public', booking_id=booking.id))

    # Generate appropriate PDF based on booking status
    try:
        logger.info(f"🔍 PDF ROUTE CALLED: token={token[:20]}...")
        logger.info(f"✅ PDF ROUTE: Booking {booking.id} status='{booking.status}' type='{booking.booking_type}'")
        
        pdf_bytes = None
        
        # Status-based PDF generation
        if booking.status in ['pending', 'confirmed']:
            # Service Proposal PDF using Classic PDF Generator (same as backend)
            logger.info(f"Generating Service Proposal PDF for booking {booking.id} using Classic Generator")
            from services.classic_pdf_generator import ClassicPDFGenerator
            
            # Prepare complete booking data for Classic PDF (same as backend)
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
                'guest_list': booking.guest_list or '',
                'flight_info': booking.flight_info or '',
                'special_request': booking.special_request or '',
                'customer_address': getattr(booking.customer, 'address', '') if booking.customer else '',
                'customer_nationality': getattr(booking.customer, 'nationality', '') if booking.customer else '',
                'reference': booking.booking_reference
            }
            
            # Get products for this booking (same as backend)
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
            
            logger.info(f"Classic PDF: {len(products)} products for booking {booking.booking_reference}")
            
            # Generate PDF using Classic PDF Generator (same as backend)
            classic_generator = ClassicPDFGenerator()
            pdf_path = classic_generator.generate_pdf(booking_data, products)
            
            # Read the PDF file
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
            
        elif booking.status == 'quoted':
            # Quote PDF using ClassicPDFGenerator (original deployment method)
            logger.info(f"Generating Quote PDF for booking {booking.id} using classic_pdf_generator_quote.py")
            from services.classic_pdf_generator_quote import ClassicPDFGenerator
            from services.universal_booking_extractor import UniversalBookingExtractor
            
            # Get booking data using UniversalBookingExtractor
            booking_data = UniversalBookingExtractor.get_fresh_booking_data(booking.id)
            if not booking_data:
                logger.error(f"Booking data not found for ID {booking.id}")
                abort(404)
                
            # Prepare booking data for ClassicPDFGenerator
            classic_booking_data = {
                'booking_id': booking_data.booking_reference,
                'guest_name': booking_data.customer.name if booking_data.customer else 'Unknown Guest',
                'guest_email': booking_data.customer.email if booking_data.customer else '',
                'guest_phone': booking_data.customer.phone if booking_data.customer else '',
                'adults': booking_data.adults or 0,
                'children': booking_data.children or 0,
                'infants': getattr(booking_data, 'infants', 0) or 0,
                'total_guests': (booking_data.adults or 0) + (booking_data.children or 0) + (getattr(booking_data, 'infants', 0) or 0),
                'arrival_date': booking_data.arrival_date if hasattr(booking_data, 'arrival_date') else None,
                'departure_date': booking_data.departure_date if hasattr(booking_data, 'departure_date') else None,
                'total_amount': getattr(booking_data, 'total_amount', 0) or 0,
                'status': 'quoted',
                'created_date': booking_data.created_at.strftime('%d.%b.%Y') if booking_data.created_at else 'N/A',
                'guest_list': booking_data.guest_list or '',
                'flight_info': booking_data.flight_info or '',
                'special_request': booking_data.special_request or ''
            }
            
            # Get products from booking using get_products() method
            products = []
            booking_products = booking_data.get_products()
            if booking_products:
                for product_data in booking_products:
                    products.append({
                        'name': product_data.get('name', 'Unknown Product'),
                        'quantity': product_data.get('quantity', 1),
                        'price': float(product_data.get('price', 0.0)),
                        'amount': float(product_data.get('amount', 0.0))
                    })
            
            # Convert products to JSON for generator
            import json
            products_json = json.dumps(products) if products else '[]'
            classic_booking_data['products_json'] = products_json
            
            logger.info(f"Quote PDF: {len(products)} products for booking {booking_data.booking_reference}")
            
            # Generate PDF using ClassicPDFGenerator.generate_quote_pdf_to_buffer
            generator = ClassicPDFGenerator()
            pdf_buffer = BytesIO()
            success = generator.generate_quote_pdf_to_buffer(classic_booking_data, pdf_buffer)
            
            if success:
                pdf_bytes = pdf_buffer.getvalue()
            else:
                logger.error("Failed to generate Quote PDF")
                abort(500)
        
        elif booking.status == 'vouchered':
            # Tour Voucher PDF using WeasyPrint (for vouchered bookings)
            logger.info(f"Generating Tour Voucher PDF for vouchered booking {booking.id} using WeasyPrint")
            from services.tour_voucher_weasyprint_v2 import TourVoucherWeasyPrintV2
            tour_generator = TourVoucherWeasyPrintV2()
            pdf_bytes = tour_generator.generate_tour_voucher_v2_bytes(booking)
            
            if not pdf_bytes:
                logger.error(f"Failed to generate Tour Voucher PDF for booking {booking.id}")
                abort(500)
            
        elif booking.status in ['paid', 'completed']:
            # Quote / Provisional Receipt PDF using ClassicPDFGenerator (Enhanced Version)
            logger.info(f"Generating Quote/Provisional Receipt PDF for booking {booking.id} using ClassicPDFGenerator")
            from services.classic_pdf_generator_quote import ClassicPDFGenerator
            from services.universal_booking_extractor import UniversalBookingExtractor
            
            # Get booking data using UniversalBookingExtractor
            booking_data = UniversalBookingExtractor.get_fresh_booking_data(booking.id)
            if not booking_data:
                logger.error(f"Booking data not found for ID {booking.id}")
                abort(404)
                
            # Prepare booking data for ClassicPDFGenerator
            classic_booking_data = {
                'booking_id': booking_data.booking_reference,
                'guest_name': booking_data.customer.name if booking_data.customer else 'Unknown Guest',
                'guest_email': booking_data.customer.email if booking_data.customer else '',
                'guest_phone': booking_data.customer.phone if booking_data.customer else '',
                'adults': booking_data.adults or 0,
                'children': booking_data.children or 0,
                'infants': getattr(booking_data, 'infants', 0) or 0,
                'total_guests': (booking_data.adults or 0) + (booking_data.children or 0) + (getattr(booking_data, 'infants', 0) or 0),
                'arrival_date': booking_data.arrival_date if hasattr(booking_data, 'arrival_date') else None,
                'departure_date': booking_data.departure_date if hasattr(booking_data, 'departure_date') else None,
                'total_amount': getattr(booking_data, 'total_amount', 0) or 0,
                'status': booking_data.status,  # Pass status for document title determination
                'created_date': booking_data.created_at.strftime('%d.%b.%Y') if booking_data.created_at else 'N/A',
                'traveling_period': f"{booking_data.arrival_date.strftime('%d %b %Y') if hasattr(booking_data, 'arrival_date') and booking_data.arrival_date else 'N/A'} - {booking_data.departure_date.strftime('%d %b %Y') if hasattr(booking_data, 'departure_date') and booking_data.departure_date else 'N/A'}",
                'service_detail': booking_data.description if hasattr(booking_data, 'description') else '',
                'flight_info': booking_data.flight_info if hasattr(booking_data, 'flight_info') else '',
                'guest_list': booking_data.guest_list if hasattr(booking_data, 'guest_list') else '',
                'quote_number': getattr(booking_data, 'quote_number', None) or f'QT{booking_data.id}',
                'party_name': getattr(booking_data, 'party_name', booking_data.customer.name if booking_data.customer else 'N/A')
            }
            
            # Parse products data
            generator = ClassicPDFGenerator()
            products = generator._parse_products_data(getattr(booking_data, 'products', '[]'))
            
            # Generate PDF using ClassicPDFGenerator
            pdf_path = generator.generate_pdf(classic_booking_data, products)
            
            # Read the PDF file
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
            
        else:
            # Default: Service Proposal PDF using Classic Generator for unknown statuses
            logger.info(f"Using default Classic Service Proposal PDF for status '{booking.status}'")
            from services.classic_pdf_generator import ClassicPDFGenerator
            
            # Prepare booking data using Classic format
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
                'guest_list': booking.guest_list or '',
                'flight_info': booking.flight_info or '',
                'special_request': booking.special_request or '',
                'customer_address': getattr(booking.customer, 'address', '') if booking.customer else '',
                'customer_nationality': getattr(booking.customer, 'nationality', '') if booking.customer else '',
                'reference': booking.booking_reference
            }
            
            # Get products for this booking
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
            
            # Generate PDF using Classic PDF Generator
            classic_generator = ClassicPDFGenerator()
            pdf_path = classic_generator.generate_pdf(booking_data, products)
            
            # Read the PDF file
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
        
        logger.info(f"PDF generated, size: {len(pdf_bytes) if pdf_bytes else 'None'} bytes")
        
        if pdf_bytes:
            # Generate appropriate filename based on booking status using enhanced system
            import time
            from models.booking_enhanced import BookingEnhanced
            timestamp = int(time.time())
            token_short = token[:12] if len(token) > 12 else token
            
            # Use enhanced system for consistent naming
            document_title = BookingEnhanced.get_document_title_for_status(booking.status)
            filename_prefix = document_title.replace(' ', '').replace('/', '')
            filename = f"{filename_prefix}_{booking.booking_reference}_{timestamp}_{token_short}.pdf"
            
            response = make_response(pdf_bytes)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        else:
            logger.error("PDF generation failed - no bytes returned")
            abort(500)
                
    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        abort(500)

@public_bp.route('/booking/<path:token>/png')
def download_booking_png(token):
    """
    Public PNG download with ClassicPDFGenerator
    Generate Quote PNG document as per DHAKUL CHAN format
    Uses: services/classic_pdf_generator_quote.py -> generate_quote_pdf_to_buffer
    """
    print(f"🚀 PNG ROUTE CALLED: token={token[:30]}...")
    try:
        import base64
        import time
        from datetime import datetime, timedelta
        from models.booking import Booking as BookingModel
        from extensions import db  # Import db for raw SQL
        from flask import render_template  # Import for error pages
        
        logger = logging.getLogger(__name__)
        logger.info(f"🔍 PUBLIC PNG ROUTE START: Processing token {token[:20]}...")
        logger.info(f"🔍 Full token: {token}")
        
        # Enhanced token verification with multiple formats
        import time
        from models.booking_enhanced import BookingEnhanced
        booking_id = None  # Initialize booking_id
        
        # Try enhanced token verification first
        verified_booking_id = BookingEnhanced.verify_secure_token(token)
        if verified_booking_id:
            booking_id = verified_booking_id
            logger.info(f"✅ Enhanced token verified for booking {booking_id}")
            
            # Get DB version via RAW SQL to avoid ORM cache
            raw_version_sql = db.session.execute(
                db.text("SELECT share_token_version FROM bookings WHERE id = :id"),
                {"id": booking_id}
            ).fetchone()
            db_version = raw_version_sql[0] if raw_version_sql else 1
            
            # Verify token version and booking status
            booking_model = BookingModel.query.get(booking_id)
            if booking_model:
                # Extract version from token
                try:
                    padded_token = token + '=' * (4 - len(token) % 4)
                    decoded_bytes = base64.b64decode(padded_token)
                    decoded_str = decoded_bytes.decode('utf-8', errors='ignore')
                    parts = decoded_str.split('|')
                    
                    # Check token version
                    if len(parts) >= 4:
                        try:
                            token_version = int(parts[2])
                            if token_version < db_version:
                                logger.warning(f'🚫 Old token version {token_version} < {db_version}')
                                return render_template('public/token_expired.html'), 403
                        except (ValueError, IndexError):
                            pass
                    elif len(parts) == 3:
                        # Old token format - check if token was reset
                        if db_version > 1:
                            logger.warning(f'🚫 Old token format, current version {db_version}')
                            return render_template('public/token_expired.html'), 403
                except Exception as e:
                    logger.warning(f'Could not parse token version: {e}')
                
                # Check if booking is cancelled
                if booking_model.status == 'cancelled':
                    logger.warning(f'🚫 Booking {booking_id} is cancelled')
                    return render_template('public/token_expired.html'), 403
        else:
            # Fallback to Booking.verify_share_token for UUID tokens
            booking_obj = BookingModel.verify_share_token(token)
            if booking_obj:
                booking_id = booking_obj.id
                logger.info(f"✅ UUID token verified for booking {booking_id}")
                
                # Check if booking is cancelled
                if booking_obj.status == 'cancelled':
                    logger.warning(f'🚫 Booking {booking_id} is cancelled')
                    return render_template('public/token_expired.html'), 403
            # Check if token is in simple format: booking_id_timestamp_hash (e.g., 91_1732080018_57d7891455)
            # Only if token looks like digits_digits_hash pattern (not complex base64)
            if ('_' in token and not token.startswith('eyJ') and 
                len(token.split('_')) == 3 and token.split('_')[0].isdigit() and token.split('_')[1].isdigit()):
                parts = token.split('_')
                try:
                    booking_id = int(parts[0])
                    timestamp = int(parts[1])
                    token_hash = parts[2]
                    
                    # Verify token version
                    booking_model = BookingModel.query.get(booking_id)
                    if booking_model:
                        # Check if booking is cancelled
                        if booking_model.status == 'cancelled':
                            logger.warning(f'🚫 Booking {booking_id} is cancelled')
                            return render_template('public/token_expired.html'), 403
                    
                    # Check 365 days expiry (extended for testing)
                    current_time = int(time.time())
                    expire_seconds = 365 * 24 * 60 * 60  # 365 days
                    
                    if current_time - timestamp > expire_seconds:
                        logger.warning(f'⏰ Token expired: {current_time - timestamp} seconds old')
                        return render_template('public/token_expired.html'), 403
                        
                    logger.info(f"✅ Parsed simple token format: booking_id={booking_id}, timestamp={timestamp}, hash={token_hash}")
                    
                except ValueError as e:
                    logger.error(f'❌ Invalid simple token format: {str(e)}')
                    # Continue to base64 decoding instead of returning error
                    pass
                    
            # If not simple token format, try base64 decoding
            if not booking_id:
                # Fallback to legacy base64 token decoding with enhanced error handling
                try:
                    # Try different base64 decoding approaches
                    token_variants = [
                        token,
                        token + "=",
                        token + "==", 
                        token + "===",
                        token.replace('-', '+').replace('_', '/'),  # URL-safe base64
                        token.replace('-', '+').replace('_', '/') + "="
                    ]
                    
                    decoded = None
                    for variant in token_variants:
                        try:
                            decoded = base64.b64decode(variant)
                            break
                        except Exception:
                            continue
                    
                    if not decoded:
                        logger.error(f'❌ All base64 decode attempts failed for token: {token[:20]}...')
                        return render_template('public/token_expired.html'), 400
                    
                    # Handle binary data gracefully (similar to booking route)
                    try:
                        decoded_str = decoded.decode('utf-8')
                        parts = decoded_str.split('|')
                        if len(parts) >= 2:
                            booking_id = int(parts[0])
                            timestamp = int(parts[1])
                            
                            # Get DB version via RAW SQL
                            raw_ver = db.session.execute(
                                db.text("SELECT share_token_version FROM bookings WHERE id = :id"),
                                {"id": booking_id}
                            ).fetchone()
                            db_ver = raw_ver[0] if raw_ver else 1
                            
                            # Check token version if available in decoded data
                            if len(parts) >= 4:
                                try:
                                    token_version = int(parts[2])
                                    if token_version < db_ver:
                                        logger.warning(f'🚫 Old token version {token_version} < {db_ver}')
                                        return render_template('public/token_expired.html'), 403
                                except (ValueError, AttributeError):
                                    pass
                            elif len(parts) == 3:
                                # Old 3-part format - check if version > 1
                                if db_ver > 1:
                                    logger.warning(f'🚫 Old 3-part token, DB version={db_ver}')
                                    return render_template('public/token_expired.html'), 403
                            
                            # Check if booking is cancelled
                            booking_model = BookingModel.query.get(booking_id)
                            if booking_model and booking_model.status == 'cancelled':
                                logger.warning(f'🚫 Booking {booking_id} is cancelled')
                                return render_template('public/token_expired.html'), 403
                            
                            # Check 365 days expiry (extended)
                            current_time = int(time.time())
                            expire_seconds = 365 * 24 * 60 * 60  # 365 days
                            
                            if current_time - timestamp > expire_seconds:
                                logger.warning(f'⏰ Token expired: {current_time - timestamp} seconds old')
                                return render_template('public/token_expired.html'), 403
                        else:
                            logger.error("Invalid legacy token format")
                            return 'Invalid token structure', 400
                    except UnicodeDecodeError:
                        # Handle binary tokens - extract booking_id from first part (enhanced)
                        logger.info(f'✅ Binary token detected: length={len(decoded)} bytes')
                        try:
                            # Try to extract booking_id from first 40 bytes (as confirmed by test)
                            text_part = decoded[:40]
                            partial_str = text_part.decode('utf-8', errors='ignore')
                            logger.info(f'🔍 Partial decode result: {repr(partial_str)}')
                            
                            if '|' in partial_str:
                                parts = partial_str.split('|')
                                logger.info(f'🔍 Token parts: {parts}')
                                
                                if len(parts) >= 1 and parts[0].isdigit():
                                    booking_id = int(parts[0])
                                    logger.info(f'✅ Extracted booking_id: {booking_id}')
                                    
                                    # Check token version for binary tokens (3 parts = old format)
                                    raw_ver = db.session.execute(
                                        db.text("SELECT share_token_version FROM bookings WHERE id = :id"),
                                        {"id": booking_id}
                                    ).fetchone()
                                    db_ver = raw_ver[0] if raw_ver else 1
                                    if len(parts) == 3 and db_ver > 1:
                                        logger.warning(f'🚫 Binary token - old format (3 parts), DB version={db_ver}')
                                        return render_template('public/token_expired.html'), 403
                                    
                                    # Check if 4-part token with version mismatch
                                    if len(parts) == 4:
                                        try:
                                            token_ver = int(parts[2])
                                            if token_ver < db_ver:
                                                logger.warning(f'🚫 Binary token - version mismatch v{token_ver} < DB v{db_ver}')
                                                return render_template('public/token_expired.html'), 403
                                        except (ValueError, IndexError):
                                            pass
                                    
                                    # Check if booking is cancelled
                                    booking_model = BookingModel.query.get(booking_id)
                                    if booking_model and booking_model.status == 'cancelled':
                                        logger.warning(f'🚫 Booking {booking_id} is cancelled (binary token path)')
                                        return render_template('public/token_expired.html'), 403
                                    
                                    # Extract timestamp if available
                                    if len(parts) >= 2 and parts[1].isdigit():
                                        timestamp = int(parts[1])
                                        # Check 365 days expiry
                                        current_time = int(time.time())
                                        expire_seconds = 365 * 24 * 60 * 60  # 365 days
                                        if current_time - timestamp > expire_seconds:
                                            logger.warning(f'⏰ Token expired: {current_time - timestamp} seconds old')
                                            return 'Token expired (365 days limit)', 403
                                        logger.info(f'✅ Token timestamp verified: {timestamp}')
                                    
                                    logger.info(f'✅ Successfully extracted from binary token: booking_id={booking_id}')
                                else:
                                    logger.warning(f'⚠️ Cannot extract valid booking_id from binary token: parts={parts}')
                                    return 'Cannot parse booking ID from token', 400
                            else:
                                logger.warning(f'⚠️ No delimiter found in binary token: {repr(partial_str)}')
                                return 'Invalid token structure', 400
                        except Exception as extract_error:
                            logger.error(f'❌ Failed to extract from binary token: {str(extract_error)}')
                            return 'Token extraction failed', 400
                except Exception as e:
                    logger.error(f'❌ Token decode error: {str(e)}')
                    return 'Token decoding failed', 400
        
        # Final check if booking_id was successfully extracted
        if not booking_id:
            logger.error('❌ No booking ID could be extracted from any token format')
            return 'Invalid token: booking ID not found', 400
        
        logger.info(f'✅ Final booking_id extracted: {booking_id}')
        
        # Check if booking is locked (import helper function from booking.py)
        try:
            from routes.booking import is_booking_locked
            if is_booking_locked(booking_id):
                logger.warning(f'🔒 Booking {booking_id} sharing is locked')
                return 'This booking is no longer available for public sharing', 403
        except ImportError:
            pass  # Gracefully handle if function doesn't exist
        
        # Get booking data
        from services.universal_booking_extractor import UniversalBookingExtractor
        booking = UniversalBookingExtractor.get_fresh_booking_data(booking_id)
        if not booking:
            logger.error(f'❌ Booking {booking_id} not found')
            abort(404)
            
        logger.info(f'📊 Found booking: {getattr(booking, "booking_reference", booking_id)} - ID: {booking_id}')
        
        # ✅ Check if booking is completed - redirect to Thank You page
        booking_status = getattr(booking, 'status', '').lower()
        if booking_status == 'completed':
            logger.info(f'🎉 Booking {booking_id} is completed - redirecting to Thank You page')
            from flask import render_template
            return render_template('public/completed_thank_you.html', 
                                 booking=booking,
                                 token=token)
        
        pdf_bytes = None  # Initialize pdf_bytes
        
        # Generate PDF based on booking status (same logic as PDF route)
        if booking_status == 'vouchered':
            # Use Tour Voucher for vouchered bookings
            logger.info(f"Generating Tour Voucher PNG for vouchered booking {booking_id}")
            from services.tour_voucher_weasyprint_v2 import TourVoucherWeasyPrintV2
            tour_generator = TourVoucherWeasyPrintV2()
            pdf_bytes = tour_generator.generate_tour_voucher_v2_bytes(booking)
            
            if not pdf_bytes:
                logger.error(f"Failed to generate Tour Voucher PDF for booking {booking_id}")
                return 'PDF generation failed', 500
        elif booking_status in ['pending', 'confirmed', 'draft']:
            # Service Proposal PDF using ClassicPDFGenerator (same as PDF route)
            from services.classic_pdf_generator import ClassicPDFGenerator
            from io import BytesIO
            
            logger.info(f"Generating Service Proposal PDF for PNG (status: {booking_status})")
            
            # Prepare complete booking data (same structure as PDF route)
            booking_data = {
                'booking_id': getattr(booking, 'booking_reference', f'BK{booking_id}'),
                'guest_name': getattr(booking.customer, 'name', None) if hasattr(booking, 'customer') and booking.customer else getattr(booking, 'party_name', 'N/A'),
                'customer_name': getattr(booking.customer, 'name', 'N/A') if hasattr(booking, 'customer') and booking.customer else 'N/A',
                'guest_email': getattr(booking.customer, 'email', 'N/A') if hasattr(booking, 'customer') and booking.customer else 'N/A',
                'guest_phone': getattr(booking.customer, 'phone', 'N/A') if hasattr(booking, 'customer') and booking.customer else 'N/A',
                'tour_name': getattr(booking, 'description', None) or getattr(booking, 'hotel_name', 'Tour Package'),
                'booking_date': booking.created_at.strftime('%Y-%m-%d') if hasattr(booking, 'created_at') and booking.created_at else 'N/A',
                'tour_date': booking.arrival_date.strftime('%Y-%m-%d') if hasattr(booking, 'arrival_date') and booking.arrival_date else 'N/A',
                'start_date': booking.traveling_period_start.strftime('%Y-%m-%d') if hasattr(booking, 'traveling_period_start') and booking.traveling_period_start else (booking.arrival_date.strftime('%Y-%m-%d') if hasattr(booking, 'arrival_date') and booking.arrival_date else 'N/A'),
                'end_date': booking.traveling_period_end.strftime('%Y-%m-%d') if hasattr(booking, 'traveling_period_end') and booking.traveling_period_end else (booking.departure_date.strftime('%Y-%m-%d') if hasattr(booking, 'departure_date') and booking.departure_date else 'N/A'),
                'pax': getattr(booking, 'total_pax', 1) or 1,
                'adults': getattr(booking, 'adults', None) or getattr(booking, 'total_pax', 1) or 1,
                'children': getattr(booking, 'children', 0) or 0,
                'infants': getattr(booking, 'infants', 0) or 0,
                'price': float(getattr(booking, 'total_amount', 0) or 0),
                'status': booking_status,
                'description': getattr(booking, 'description', ''),
                'internal_note': getattr(booking, 'admin_notes', None) or getattr(booking, 'internal_note', ''),
                'daily_services': getattr(booking, 'daily_services', ''),
                'guest_list': getattr(booking, 'guest_list', ''),
                'flight_info': getattr(booking, 'flight_info', ''),
                'special_request': getattr(booking, 'special_request', ''),
                'customer_address': getattr(booking.customer, 'address', '') if hasattr(booking, 'customer') and booking.customer else '',
                'customer_nationality': getattr(booking.customer, 'nationality', '') if hasattr(booking, 'customer') and booking.customer else '',
                'reference': getattr(booking, 'booking_reference', f'BK{booking_id}')
            }
            
            # Get products - ใช้ dict.get() เพราะ booking.get_products() return list of dicts
            products = []
            if hasattr(booking, 'get_products'):
                booking_products = booking.get_products()
                if booking_products:
                    for product_data in booking_products:
                        products.append({
                            'name': product_data.get('name', 'Unknown Product'),
                            'quantity': product_data.get('quantity', 1),
                            'price': float(product_data.get('price', 0.0)),
                            'amount': float(product_data.get('amount', 0.0))
                        })
            
            # Debug log
            logger.info(f'🔍 PNG Products for {booking.booking_reference} ({len(products)} items)')
            for i, product in enumerate(products, 1):
                logger.info(f"  {i}. {product['name']} x{product['quantity']} = {product['price']:,.2f}")
            
            # Generate PDF
            classic_generator = ClassicPDFGenerator()
            pdf_path = classic_generator.generate_pdf(booking_data, products)
            
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
                
        else:
            # Use ClassicPDFGenerator Quote for quoted/paid statuses
            from services.classic_pdf_generator_quote import ClassicPDFGenerator
            from io import BytesIO
            
            # สร้าง booking data structure สำหรับ DHAKUL CHAN Quote - ใช้ safe attribute access
            first_name = getattr(booking, 'first_name', getattr(booking, 'customer_first_name', ''))
            last_name = getattr(booking, 'last_name', getattr(booking, 'customer_last_name', ''))
            guest_name = f"{first_name or ''} {last_name or ''}".strip() or 'Unknown Guest'
            
            # Get products_json for quote generator
            products_json = getattr(booking, 'products', '[]')
            if not products_json or products_json == '':
                products_json = '[]'
            
            booking_data = {
                'booking_id': getattr(booking, 'booking_reference', f'BK{booking_id}'),
                'guest_name': guest_name,
                'guest_email': getattr(booking, 'email', getattr(booking, 'customer_email', '')),
                'guest_phone': getattr(booking, 'phone', getattr(booking, 'customer_phone', '')),
                'adults': getattr(booking, 'adults', 0) or 0,
                'children': getattr(booking, 'children', 0) or 0,
                'infants': getattr(booking, 'infants', 0) or 0,
                'arrival_date': booking.arrival_date.strftime('%d %b %Y') if hasattr(booking, 'arrival_date') and booking.arrival_date else '',
                'departure_date': booking.departure_date.strftime('%d %b %Y') if hasattr(booking, 'departure_date') and booking.departure_date else '',
                'total_amount': float(getattr(booking, 'total_amount', 0) or 0),
                'status': getattr(booking, 'status', 'quoted'),  # ส่ง status ไปยัง ClassicPDFGenerator
                'products_json': products_json,  # ⭐ ส่ง products_json สำหรับ generate_quote_pdf_to_buffer
            }
            
            # Generate PDF using ClassicPDFGenerator.generate_quote_pdf_to_buffer
            generator = ClassicPDFGenerator()
            # Generate PDF using ClassicPDFGenerator.generate_quote_pdf_to_buffer
            generator = ClassicPDFGenerator()
            
            try:
                # ใช้ method ตามที่ระบุ: generate_quote_pdf_to_buffer
                pdf_buffer = BytesIO()
                success = generator.generate_quote_pdf_to_buffer(booking_data, pdf_buffer)
                
                if success:
                    pdf_bytes = pdf_buffer.getvalue()
                    logger.info(f'✅ Generated PDF: {len(pdf_bytes)} bytes')
                else:
                    logger.error(f'❌ Failed to generate PDF buffer')
                    raise Exception("PDF buffer generation failed")
                    
            except Exception as pdf_error:
                # Fallback: ใช้ existing PDF file หากมี
                import os
                import glob
                
                booking_ref = booking.booking_reference or f'BK{booking_id}'
                pdf_patterns = [
                    f'static/generated/classic_quote_{booking_ref}_*.pdf',
                    f'static/generated/Quote_{booking_ref}_*.pdf', 
                    f'static/generated/*{booking_ref}*.pdf'
                ]
                
                pdf_file_path = None
                for pattern in pdf_patterns:
                    matches = glob.glob(pattern)
                    if matches:
                        pdf_file_path = max(matches)  # Get latest file
                        logger.info(f'📄 Using existing PDF: {pdf_file_path}')
                        break
                
                if pdf_file_path and os.path.exists(pdf_file_path):
                    with open(pdf_file_path, 'rb') as f:
                        pdf_bytes = f.read()
                    logger.info(f'✅ Using existing PDF: {len(pdf_bytes)} bytes')
                else:
                    logger.error(f'❌ No PDF available: {str(pdf_error)}')
                    return 'PDF generation failed', 500
        
        # Convert PDF to PNG using pdf_to_long_png_bytes
        from services.pdf_image import pdf_to_long_png_bytes
        
        if not pdf_bytes:
            logger.error(f'❌ No PDF data available for PNG conversion')
            return 'No PDF data available', 500
            
        png_bytes = pdf_to_long_png_bytes(pdf_bytes, zoom=2.0, page_spacing=30)
        
        if not png_bytes:
            logger.error(f'❌ PNG conversion failed')
            return 'PNG conversion failed', 500
            
        logger.info(f'✅ PNG generated: {len(png_bytes)} bytes')
        
        # Return PNG response with status-based filename
        from flask import Response
        booking_status = getattr(booking, 'status', '').lower()
        booking_ref = booking.booking_reference or booking_id
        
        # Determine filename based on status
        if booking_status == 'vouchered':
            filename_prefix = 'TourVoucher'
        elif booking_status in ['quoted', 'paid']:
            filename_prefix = 'Quote'
        else:
            filename_prefix = 'ServiceProposal'
            
        response = Response(png_bytes, mimetype='image/png')
        response.headers['Content-Disposition'] = f'inline; filename="{filename_prefix}_{booking_ref}.png"'
        response.headers['Cache-Control'] = 'public, max-age=3600'  # 1 hour cache
        response.headers['Access-Control-Allow-Origin'] = '*'
        
        return response
        
    except Exception as e:
        import traceback
        logger.error(f'❌ PUBLIC PNG ERROR: {str(e)}')
        logger.error(f'📋 Traceback: {traceback.format_exc()}')
        return f'Internal server error: {str(e)}', 500
@public_bp.route('/booking/<path:token>')
def view_booking_secure(token):
    """Secure public view for booking with token - Enhanced Version"""
    import logging
    import traceback
    
    # Set up logger first before any other imports
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"=== PUBLIC BOOKING REQUEST START ===")
        logger.info(f"Accessing public booking with token: {token[:20]}...")
        
        # Import after logging setup
        from models.booking import Booking as BookingModel
        from extensions import db  # Import db inside function
        logger.info("✅ Imports successful")
    except Exception as import_error:
        logger.error(f"❌ IMPORT ERROR: {import_error}")
        logger.error(f"Import traceback: {traceback.format_exc()}")
        return f"Import error: {str(import_error)}", 500
    
    try:
        # Try enhanced token verification first
        logger.info("Attempting to import BookingEnhanced...")
        from models.booking_enhanced import BookingEnhanced
        logger.info("BookingEnhanced imported successfully")
        logger.info("Starting enhanced token verification...")
        
        try:
            booking_id = BookingEnhanced.verify_secure_token(token)
            logger.info(f"Enhanced verification result: {booking_id}")
        except Exception as verify_error:
            logger.error(f"Enhanced verification error: {verify_error}")
            logger.error(f"Verify traceback: {traceback.format_exc()}")
            booking_id = None
        
        if booking_id:
            logger.info(f"Enhanced token valid - attempting to get booking {booking_id}")
            
            # Verify token version and booking status - Use RAW SQL to avoid ORM cache
            raw_version_sql = db.session.execute(
                db.text("SELECT share_token_version FROM bookings WHERE id = :id"),
                {"id": booking_id}
            ).fetchone()
            db_version = raw_version_sql[0] if raw_version_sql else 1
            logger.info(f"🔍 DEBUG: RAW SQL DB version={db_version}")
            
            booking_model = BookingModel.query.get(booking_id)
            if booking_model:
                logger.info(f"🔍 DEBUG: Got booking model for ID {booking_id}")
                # Extract version from token to compare with database
                try:
                    import base64
                    padded_token = token + '=' * (4 - len(token) % 4)
                    decoded_bytes = base64.b64decode(padded_token)
                    decoded_str = decoded_bytes.decode('utf-8', errors='ignore')
                    parts = decoded_str.split('|')
                    
                    logger.info(f"🔍 DEBUG: Token parts count: {len(parts)}")
                    logger.info(f"🔍 DEBUG: First 3 parts: {parts[:3] if len(parts) >= 3 else parts}")
                    
                    # Check if token has version (4 parts: id|timestamp|version|expiry)
                    # Old tokens have 3 parts: id|timestamp|expiry
                    if len(parts) >= 4:
                        logger.info(f"🔍 DEBUG: Token has 4+ parts (new format)")
                        try:
                            token_version = int(parts[2])
                            current_version = getattr(booking_model, 'share_token_version', 1) or 1
                            logger.info(f"🔍 DEBUG: Token version={token_version}, DB version={current_version}")
                            if token_version < current_version:
                                logger.warning(f'🚫 Old token version {token_version} < {current_version} for booking {booking_id}')
                                return render_template('public/token_expired.html'), 403
                        except (ValueError, IndexError) as e:
                            logger.warning(f"🔍 DEBUG: Failed to parse token version: {e}")
                            pass
                    elif len(parts) == 3:
                        logger.info(f"🔍 DEBUG: Token has 3 parts (old format)")
                        # Old token format without version - check if version > 1 (means token was reset)
                        logger.info(f"🔍 DEBUG: Using RAW SQL version={db_version}")
                        if db_version > 1:
                            logger.warning(f'🚫 Old token format, but current version is {db_version} (token was reset)')
                            return render_template('public/token_expired.html'), 403
                        else:
                            logger.info(f"✅ DEBUG: Old token allowed (DB version is 1)")
                except Exception as e:
                    logger.warning(f'Could not parse token version: {e}')
                
                # Check if booking is cancelled
                if booking_model.status == 'cancelled':
                    logger.warning(f'🚫 Booking {booking_id} is cancelled')
                    return render_template('public/token_expired.html'), 403
            
            booking = Booking.query.get(booking_id)
            if booking:
                logger.info(f"Enhanced token verified successfully for booking {booking.id}")
                
                # Get quote_number from quotes table if not in booking
                if not booking.quote_number:
                    try:
                        from extensions import db
                        from sqlalchemy import text
                        result = db.session.execute(
                            text("SELECT quote_number FROM quotes WHERE booking_id = :booking_id ORDER BY created_at DESC LIMIT 1"),
                            {"booking_id": booking.id}
                        ).fetchone()
                        if result:
                            booking.quote_number = result[0]
                            logger.info(f"Retrieved quote_number from quotes table: {booking.quote_number}")
                    except Exception as e:
                        logger.warning(f"Could not retrieve quote_number: {e}")
                
                # Check if booking is completed - redirect to thank you page
                if booking.status == 'completed':
                    logger.info(f"🎉 Booking {booking.id} is completed - showing Thank You page")
                    from config import Config as AppConfig
                    return render_template('public/completed_thank_you.html', booking=booking, config=AppConfig, token=token)
                
                # Import Config here to avoid issues
                logger.info("Importing Config...")
                from config import Config as AppConfig
                logger.info("Config imported successfully")
                
                logger.info("Attempting to render template...")
                
                # Get recent activity logs for this booking (last 6 entries)
                activity_logs = []
                try:
                    from extensions import db
                    from sqlalchemy import text
                    # Use raw SQL query to avoid SQLAlchemy registration issues
                    result = db.session.execute(
                        text("""SELECT id, action, description, created_at, user_id 
                                FROM activity_logs 
                                WHERE booking_id = :booking_id 
                                ORDER BY created_at DESC 
                                LIMIT 6"""), 
                        {"booking_id": booking.id}
                    )
                    activity_logs = [
                        {
                            'id': row[0],
                            'action': row[1],
                            'description': row[2],
                            'created_at': row[3],
                            'user_id': row[4]
                        }
                        for row in result.fetchall()
                    ]
                    logger.info(f"Retrieved {len(activity_logs)} activity logs for booking {booking.id}")
                except Exception as logs_error:
                    logger.warning(f"Could not retrieve activity logs: {logs_error}")
                    activity_logs = []
                
                from datetime import datetime
                return render_template('public/enhanced_booking_view.html', 
                                     booking=booking,
                                     token=token,
                                     config=AppConfig,
                                     activity_logs=activity_logs,
                                     now=datetime.now)
            else:
                logger.error(f"Booking with ID {booking_id} not found in database")
        
        # Fallback to old token system for backward compatibility
        logger.info("Enhanced token verification failed, trying legacy token")
        try:
            booking = None
            try:
                booking = Booking.verify_share_token(token)
                if booking and booking.status == 'cancelled':
                    logger.warning(f'🚫 Booking {booking.id} is cancelled')
                    return render_template('public/token_expired.html'), 403
            except Exception as verify_error:
                logger.error(f"Token verification threw exception: {verify_error}")
                booking = None
                
            if not booking:
                logger.error("Legacy token verification failed - trying manual token parsing")
                
                # Try to manually extract booking ID from token for old tokens
                try:
                    import base64
                    # Add padding if needed
                    padded_token = token + '=' * (4 - len(token) % 4)
                    decoded_bytes = base64.urlsafe_b64decode(padded_token)
                    decoded_str = decoded_bytes.decode('utf-8', errors='ignore')
                    
                    # Look for booking ID pattern (number|timestamp|timestamp)
                    if '|' in decoded_str:
                        parts = decoded_str.split('|')
                        if len(parts) >= 1:
                            try:
                                booking_id = int(parts[0])
                                logger.info(f"Extracted booking ID {booking_id} from token")
                                
                                # Check if this booking exists and token hasn't expired
                                test_booking = Booking.query.get(booking_id)
                                if test_booking:
                                    # Check token version via RAW SQL
                                    raw_ver = db.session.execute(
                                        db.text("SELECT share_token_version FROM bookings WHERE id = :id"),
                                        {"id": booking_id}
                                    ).fetchone()
                                    db_ver = raw_ver[0] if raw_ver else 1
                                    
                                    # Check if old format (3 parts) and version > 1
                                    if len(parts) == 3 and db_ver > 1:
                                        logger.warning(f'🚫 Manual parsing: Old 3-part token, DB version={db_ver}')
                                        return render_template('public/token_expired.html'), 403
                                    
                                    # Check if 4-part token with version mismatch
                                    if len(parts) == 4:
                                        token_ver = int(parts[2]) if parts[2].isdigit() else 1
                                        if token_ver < db_ver:
                                            logger.warning(f'🚫 Manual parsing: Token version mismatch v{token_ver} < DB v{db_ver}')
                                            return render_template('public/token_expired.html'), 403
                                    
                                    # Check if booking is cancelled
                                    if test_booking.status == 'cancelled':
                                        logger.warning(f'🚫 Booking {booking_id} is cancelled (manual parsing path)')
                                        return render_template('public/token_expired.html'), 403
                                    
                                    logger.info(f"Found booking {booking_id} via manual parsing - allowing access")
                                    booking = test_booking
                                    
                                    # Get quote_number from quotes table if not in booking
                                    if not booking.quote_number:
                                        try:
                                            from extensions import db
                                            from sqlalchemy import text
                                            result = db.session.execute(
                                                text("SELECT quote_number FROM quotes WHERE booking_id = :booking_id ORDER BY created_at DESC LIMIT 1"),
                                                {"booking_id": booking.id}
                                            ).fetchone()
                                            if result:
                                                booking.quote_number = result[0]
                                                logger.info(f"Retrieved quote_number from quotes table: {booking.quote_number}")
                                        except Exception as e:
                                            logger.warning(f"Could not retrieve quote_number: {e}")
                                else:
                                    logger.error(f"Booking {booking_id} not found")
                            except (ValueError, IndexError) as e:
                                logger.error(f"Could not parse booking ID: {e}")
                    
                except Exception as parse_error:
                    logger.error(f"Token manual parsing failed: {parse_error}")
                
                if not booking:
                    logger.error("All token verification methods failed - booking not found")
                    # Return 404 instead of abort to avoid nested exception
                    from flask import render_template_string
                    return render_template_string('<h1>404 - Booking Not Found</h1><p>Invalid or expired token.</p>'), 404
            
            logger.info(f"Legacy token verified successfully for booking {booking.id}")
            
            # Check if booking is completed - redirect to thank you page
            if booking.status == 'completed':
                logger.info(f"🎉 Booking {booking.id} is completed - showing Thank You page")
                from config import Config as AppConfig
                return render_template('public/completed_thank_you.html', booking=booking, config=AppConfig, token=token)
            
            # Import Config here to avoid issues
            logger.info("Importing Config for legacy...")
            from config import Config as AppConfig
            logger.info("Config imported for legacy")
            
            logger.info("Attempting to render template for legacy...")
            
            # Get recent activity logs for this booking (last 6 entries)
            activity_logs = []
            try:
                from extensions import db
                from sqlalchemy import text
                # Use raw SQL query to avoid SQLAlchemy registration issues
                result = db.session.execute(
                    text("""SELECT id, action, description, created_at, user_id 
                            FROM activity_logs 
                            WHERE booking_id = :booking_id 
                            ORDER BY created_at DESC 
                            LIMIT 6"""), 
                    {"booking_id": booking.id}
                )
                activity_logs = [
                    {
                        'id': row[0],
                        'action': row[1],
                        'description': row[2],
                        'created_at': row[3],
                        'user_id': row[4]
                    }
                    for row in result.fetchall()
                ]
                logger.info(f"Retrieved {len(activity_logs)} activity logs for booking {booking.id}")
            except Exception as logs_error:
                logger.warning(f"Could not retrieve activity logs: {logs_error}")
                activity_logs = []
            
            from datetime import datetime
            return render_template('public/enhanced_booking_view.html', 
                                 booking=booking,
                                 token=token,
                                 config=AppConfig,
                                 activity_logs=activity_logs,
                                 now=datetime.now)
        except Exception as legacy_error:
            logger.error(f"Legacy token verification error: {legacy_error}")
            logger.error(f"Legacy traceback: {traceback.format_exc()}")
            # Return 404 instead of abort to avoid nested exception
            from flask import render_template_string
            return render_template_string('<h1>404 - Booking Not Found</h1><p>Invalid or expired token.</p>'), 404
            
    except Exception as e:
        logger.error(f"Error in view_booking_secure: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        # Return 500 instead of abort to avoid nested exception
        from flask import render_template_string
        return render_template_string('<h1>500 - Internal Error</h1><p>Something went wrong.</p>'), 500


@public_bp.route('/booking/<int:booking_id>/quote-pdf')
def download_quote_pdf_by_id(booking_id):
    """Public Quote/Provisional Receipt PDF download by booking ID with token in query parameter"""
    import time
    from flask import request
    
    logger.info(f"🔍 Quote PDF requested for booking {booking_id}")
    
    # Get token from query parameter
    token = request.args.get('v')
    if not token:
        logger.error("No token provided in query parameter")
        abort(403)
    
    # Verify token
    verified_booking_id = BookingEnhanced.verify_secure_token(token)
    if not verified_booking_id or verified_booking_id != booking_id:
        logger.error(f"Token verification failed: token={token[:20]}, expected={booking_id}, got={verified_booking_id}")
        abort(403)
    
    # Check if booking is locked
    try:
        from routes.booking import is_booking_locked
        if is_booking_locked(booking_id):
            logger.warning(f'🔒 Booking {booking_id} PDF sharing is locked')
            return 'This booking is no longer available for public sharing', 403
    except ImportError:
        pass
    
    # Get booking
    booking = Booking.query.get_or_404(booking_id)
    
    # Generate PDF using ClassicPDFGenerator (Quote version)
    try:
        from services.classic_pdf_generator_quote import ClassicPDFGenerator
        from services.universal_booking_extractor import UniversalBookingExtractor
        from io import BytesIO
        
        # Get booking data using UniversalBookingExtractor
        booking_data = UniversalBookingExtractor.get_fresh_booking_data(booking.id)
        if not booking_data:
            logger.error(f"Booking data not found for ID {booking.id}")
            abort(404)
            
        # Prepare booking data for ClassicPDFGenerator
        classic_booking_data = {
            'booking_id': booking_data.booking_reference,
            'guest_name': booking_data.customer.name if booking_data.customer else 'Unknown Guest',
            'guest_email': booking_data.customer.email if booking_data.customer else '',
            'guest_phone': booking_data.customer.phone if booking_data.customer else '',
            'adults': booking_data.adults or 0,
            'children': booking_data.children or 0,
            'infants': getattr(booking_data, 'infants', 0) or 0,
            'total_guests': (booking_data.adults or 0) + (booking_data.children or 0) + (getattr(booking_data, 'infants', 0) or 0),
            'arrival_date': booking_data.arrival_date if hasattr(booking_data, 'arrival_date') else None,
            'departure_date': booking_data.departure_date if hasattr(booking_data, 'departure_date') else None,
            'total_amount': getattr(booking_data, 'total_amount', 0) or 0,
            'status': booking_data.status,
            'created_date': booking_data.created_at.strftime('%d.%b.%Y') if booking_data.created_at else 'N/A',
            'guest_list': booking_data.guest_list or '',
            'flight_info': booking_data.flight_info or '',
            'special_request': booking_data.special_request or ''
        }
        
        # Get products from booking using get_products() method
        products = []
        booking_products = booking_data.get_products()
        if booking_products:
            for product_data in booking_products:
                products.append({
                    'name': product_data.get('name', 'Unknown Product'),
                    'quantity': product_data.get('quantity', 1),
                    'price': float(product_data.get('price', 0.0)),
                    'amount': float(product_data.get('amount', 0.0))
                })
        
        # Generate PDF using ClassicPDFGenerator.generate_quote_pdf_to_buffer
        generator = ClassicPDFGenerator()
        pdf_buffer = BytesIO()
        success = generator.generate_quote_pdf_to_buffer(classic_booking_data, pdf_buffer)
        
        if success:
            pdf_bytes = pdf_buffer.getvalue()
        else:
            logger.error("Failed to generate Quote PDF")
            abort(500)
        
        # Generate filename
        timestamp = int(time.time())
        filename = f"Quote_{booking.booking_reference}_{timestamp}.pdf"
        
        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename="{filename}"'
        return response
        
    except Exception as e:
        logger.error(f"Error generating quote PDF: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        abort(500)


@public_bp.route('/booking/<path:token>/quote-pdf')
def download_quote_pdf(token):
    """Public Quote PDF download using token in URL path (for Share Page buttons)"""
    import time
    from flask import request
    
    logger.info(f"🔍 Quote PDF requested with token in path")
    
    # Verify token and get booking ID
    verified_booking_id = BookingEnhanced.verify_secure_token(token)
    if not verified_booking_id:
        logger.error(f"Token verification failed for quote PDF")
        abort(403)
    
    # Check if booking is locked
    try:
        from routes.booking import is_booking_locked
        if is_booking_locked(verified_booking_id):
            logger.warning(f'🔒 Booking {verified_booking_id} PDF sharing is locked')
            return 'This booking is no longer available for public sharing', 403
    except ImportError:
        pass
    
    # Get booking
    booking = Booking.query.get_or_404(verified_booking_id)
    
    # Generate PDF using ClassicPDFGenerator (Quote version)
    try:
        from services.classic_pdf_generator_quote import ClassicPDFGenerator
        from services.universal_booking_extractor import UniversalBookingExtractor
        from io import BytesIO
        
        # Get booking data using UniversalBookingExtractor
        booking_data = UniversalBookingExtractor.get_fresh_booking_data(booking.id)
        if not booking_data:
            logger.error(f"Booking data not found for ID {booking.id}")
            abort(404)
            
        # Prepare booking data for ClassicPDFGenerator
        classic_booking_data = {
            'booking_id': booking_data.booking_reference,
            'guest_name': booking_data.customer.name if booking_data.customer else 'Unknown Guest',
            'guest_email': booking_data.customer.email if booking_data.customer else '',
            'guest_phone': booking_data.customer.phone if booking_data.customer else '',
            'adults': booking_data.adults or 0,
            'children': booking_data.children or 0,
            'infants': getattr(booking_data, 'infants', 0) or 0,
            'total_guests': (booking_data.adults or 0) + (booking_data.children or 0) + (getattr(booking_data, 'infants', 0) or 0),
            'arrival_date': booking_data.arrival_date if hasattr(booking_data, 'arrival_date') else None,
            'departure_date': booking_data.departure_date if hasattr(booking_data, 'departure_date') else None,
            'total_amount': getattr(booking_data, 'total_amount', 0) or 0,
            'status': booking_data.status,
            'created_date': booking_data.created_at.strftime('%d.%b.%Y') if booking_data.created_at else 'N/A',
            'guest_list': booking_data.guest_list or '',
            'flight_info': booking_data.flight_info or '',
            'special_request': booking_data.special_request or ''
        }
        
        # Generate PDF using ClassicPDFGenerator.generate_quote_pdf_to_buffer
        generator = ClassicPDFGenerator()
        pdf_buffer = BytesIO()
        success = generator.generate_quote_pdf_to_buffer(classic_booking_data, pdf_buffer)
        
        if success:
            pdf_bytes = pdf_buffer.getvalue()
        else:
            logger.error("Failed to generate Quote PDF")
            abort(500)
        
        # Generate filename
        timestamp = int(time.time())
        filename = f"Quote_{booking.booking_reference}_{timestamp}.pdf"
        
        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename="{filename}"'
        return response
        
    except Exception as e:
        logger.error(f"Error generating quote PDF: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        abort(500)


@public_bp.route('/booking/<path:token>/quote-png')
def download_quote_png(token):
    """Public Quote PNG download using token in URL path (for Share Page buttons)"""
    import time
    
    logger.info(f"🔍 Quote PNG requested with token in path")
    
    # Verify token and get booking ID
    verified_booking_id = BookingEnhanced.verify_secure_token(token)
    if not verified_booking_id:
        logger.error(f"Token verification failed for quote PNG")
        abort(403)
    
    # Redirect to backend PNG route (which already exists and works)
    from flask import redirect, url_for
    v_param = int(time.time())
    return redirect(url_for('booking.backend_png', booking_id=verified_booking_id, v=v_param))


@public_bp.route('/voucher/image/<int:image_id>/<path:token>')
def download_voucher_image(image_id, token):
    """Download voucher image with token verification"""
    try:
        # Verify token and get booking
        booking_id = BookingEnhanced.verify_secure_token(token)
        if not booking_id:
            # Fallback to old token system
            booking = Booking.verify_share_token(token)
            if not booking:
                abort(404)
            booking_id = booking.id
        
        # Get the voucher image
        from models.voucher_image import VoucherImage
        voucher_image = VoucherImage.query.filter_by(
            id=image_id, 
            booking_id=booking_id
        ).first()
        
        if not voucher_image:
            abort(404)
        
        # Check if file exists
        file_path = voucher_image.image_path
        if file_path.startswith('/'):
            file_path = file_path[1:]  # Remove leading slash
        
        full_path = os.path.join(current_app.root_path, file_path)
        
        if not os.path.exists(full_path):
            logger.error(f"Voucher image file not found: {full_path}")
            abort(404)
        
        # Generate filename
        filename = f"voucher_image_{image_id}_{voucher_image.display_order}.jpg"
        
        return send_file(full_path, as_attachment=True, download_name=filename)
        
    except Exception as e:
        logger.error(f"Error downloading voucher image: {e}")
        abort(500)


@public_bp.route('/voucher/file/<int:file_id>/<path:token>')
def download_voucher_file(file_id, token):
    """Download voucher file with token verification"""
    booking_id = None
    
    try:
        # Method 1: Try enhanced token verification
        booking_id = BookingEnhanced.verify_secure_token(token)
        
        # Method 2: Try legacy token verification  
        if not booking_id:
            try:
                booking = Booking.verify_share_token(token)
                if booking:
                    booking_id = booking.id
            except Exception:
                pass
        
        # Method 3: Manual token parsing (fallback for problematic tokens)
        if not booking_id:
            try:
                import base64
                padded_token = token + '=' * (4 - len(token) % 4)
                decoded_bytes = base64.urlsafe_b64decode(padded_token)
                decoded_str = decoded_bytes.decode('utf-8', errors='ignore')
                
                if '|' in decoded_str:
                    parts = decoded_str.split('|')
                    if len(parts) >= 1:
                        potential_booking_id = int(parts[0])
                        # Verify booking exists
                        test_booking = Booking.query.get(potential_booking_id)
                        if test_booking:
                            booking_id = potential_booking_id
            except Exception:
                pass
        
        # If no booking ID found, return 404
        if not booking_id:
            return "File not found", 404
        
        # Get the voucher file
        from models.voucher_sharing import VoucherFile
        voucher_file = VoucherFile.query.filter_by(
            id=file_id, 
            voucher_id=booking_id
        ).first()
        
        if not voucher_file or not voucher_file.is_active:
            return "File not found", 404
        
        # Check if file exists on disk
        file_path = voucher_file.file_path
        if file_path.startswith('/'):
            file_path = file_path[1:]  # Remove leading slash
        
        full_path = os.path.join(current_app.root_path, file_path)
        
        if not os.path.exists(full_path):
            return "File not found", 404
        
        # Use original filename if available
        filename = voucher_file.original_filename or voucher_file.filename
        
        return send_file(full_path, as_attachment=True, download_name=filename)
        
    except Exception as e:
        logger.error(f"Error downloading voucher file: {e}")
        return "Internal server error", 500
        
        # Get the voucher file
        from models.voucher_sharing import VoucherFile
        voucher_file = VoucherFile.query.filter_by(
            id=file_id, 
            voucher_id=booking_id  # Note: voucher_id references booking_id
        ).first()
        
        if not voucher_file or not voucher_file.is_active:
            logger.error(f"Voucher file not found or inactive: file_id={file_id}, booking_id={booking_id}")
            return "File not found", 404
        
        # Check if file exists
        file_path = voucher_file.file_path
        if file_path.startswith('/'):
            file_path = file_path[1:]  # Remove leading slash
        
        full_path = os.path.join(current_app.root_path, file_path)
        
        if not os.path.exists(full_path):
            logger.error(f"Voucher file not found on disk: {full_path}")
            return "File not found", 404
        
        # Use original filename if available
        filename = voucher_file.original_filename or voucher_file.filename
        
        logger.info(f"Serving voucher file: {filename} from {full_path}")
        return send_file(full_path, as_attachment=True, download_name=filename)
        
    except Exception as e:
        logger.error(f"Error downloading voucher file: {e}")
        return "Internal server error", 500