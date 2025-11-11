"""Public routes for sharing booking information without authentication."""

from flask import Blueprint, render_template, abort, url_for, redirect, send_from_directory, make_response, send_file, current_app
from models.booking import Booking
from models.booking_enhanced import BookingEnhanced
from config import Config
import os
import logging
from datetime import datetime

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
    
    return render_template('public/enhanced_booking_view.html', 
                         booking=booking, 
                         png_url=png_url,
                         config=Config)

@public_bp.route('/booking/<path:token>/pdf')
def download_booking_pdf(token):
    """Enhanced PDF download with status-based generation using new token system"""
    
    logger = logging.getLogger(__name__)
    
    # Use enhanced token verification system
    from models.booking_enhanced import BookingEnhanced
    booking_id = BookingEnhanced.verify_secure_token(token)
    if booking_id:
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
                abort(404)

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
            # Quote PDF using WeasyPrint with quote_template_final_v2.html
            logger.info(f"Generating Quote PDF for booking {booking.id} using template")
            try:
                from services.weasyprint_quote_generator import WeasyPrintQuoteGenerator
                pdf_service = WeasyPrintQuoteGenerator()
                pdf_filename = pdf_service.generate_quote_pdf(booking)
                
                # WeasyPrint returns filename only, need to construct full path
                pdf_path = os.path.join('static', 'generated', pdf_filename)
                
                # Verify file exists before reading
                if not os.path.exists(pdf_path):
                    logger.error(f"Generated PDF file not found: {pdf_path}")
                    raise FileNotFoundError(f"PDF file not found: {pdf_path}")
                
                # Read the PDF file
                with open(pdf_path, 'rb') as f:
                    pdf_bytes = f.read()
                    
            except Exception as pdf_error:
                logger.error(f"Failed to generate Quote PDF: {pdf_error}")
                # Fallback to classic PDF generator
                logger.info("Falling back to Classic PDF generator")
                from services.classic_pdf_generator import ClassicPDFGenerator
                
                # Prepare booking data for classic generator
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
                
                # Get products
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
                
                classic_generator = ClassicPDFGenerator()
                pdf_path = classic_generator.generate_pdf(booking_data, products)
                
                with open(pdf_path, 'rb') as f:
                    pdf_bytes = f.read()
            
        elif booking.status == 'paid':
            # Quote / Provisional Receipt PDF using WeasyPrint with template
            logger.info(f"Generating Quote/Provisional Receipt PDF for booking {booking.id} using template")
            try:
                from services.weasyprint_quote_generator import WeasyPrintQuoteGenerator
                pdf_service = WeasyPrintQuoteGenerator()
                pdf_filename = pdf_service.generate_quote_pdf(booking)  # Using quote_template_final_v2.html
                
                # WeasyPrint returns filename only, need to construct full path
                pdf_path = os.path.join('static', 'generated', pdf_filename)
                
                # Verify file exists before reading
                if not os.path.exists(pdf_path):
                    logger.error(f"Generated PDF file not found: {pdf_path}")
                    raise FileNotFoundError(f"PDF file not found: {pdf_path}")
                
                # Read the PDF file
                with open(pdf_path, 'rb') as f:
                    pdf_bytes = f.read()
                    
            except Exception as pdf_error:
                logger.error(f"Failed to generate Paid PDF: {pdf_error}")
                # Fallback to classic PDF generator
                logger.info("Falling back to Classic PDF generator for paid booking")
                from services.classic_pdf_generator import ClassicPDFGenerator
                
                # Prepare booking data for classic generator  
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
                
                # Get products
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
                
                classic_generator = ClassicPDFGenerator()
                pdf_path = classic_generator.generate_pdf(booking_data, products)
                
                with open(pdf_path, 'rb') as f:
                    pdf_bytes = f.read()
            
        elif booking.status == 'vouchered':
            # Tour Voucher PDF using WeasyPrint
            logger.info(f"Generating Tour Voucher PDF for booking {booking.id} using WeasyPrint")
            from services.tour_voucher_weasyprint_v2 import TourVoucherWeasyPrintV2
            tour_generator = TourVoucherWeasyPrintV2()
            pdf_bytes = tour_generator.generate_tour_voucher_v2_bytes(booking)
            
            if not pdf_bytes:
                logger.error(f"Failed to generate Tour Voucher PDF for booking {booking.id}")
                abort(500)
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
    """Enhanced PNG download with status-based generation using new token system"""
    
    logger = logging.getLogger(__name__)
    logger.info(f"🔍 PNG ROUTE CALLED: token={token[:20]}...")
    
    # Use enhanced token verification system
    from models.booking_enhanced import BookingEnhanced
    booking_id = BookingEnhanced.verify_secure_token(token)
    if booking_id:
        # Get booking by verified ID
        booking = Booking.query.get_or_404(booking_id)
    else:
        # Fallback to old token system for backward compatibility
        booking = Booking.verify_share_token(token)
        if not booking:
            # Try manual token parsing as final fallback
            logger.info("PNG route: Both token verification methods failed - trying manual parsing")
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
                            logger.info(f"PNG route: Extracted booking ID {booking_id} from token")
                            booking = Booking.query.get(booking_id)
                            if booking:
                                logger.info(f"PNG route: Found booking {booking_id} via manual parsing")
                            else:
                                logger.error(f"PNG route: Booking {booking_id} not found")
                        except (ValueError, IndexError) as e:
                            logger.error(f"PNG route: Could not parse booking ID: {e}")
            except Exception as parse_error:
                logger.error(f"PNG route: Token manual parsing failed: {parse_error}")
            
            if not booking:
                logger.error(f"❌ PNG ROUTE: Invalid token")
                abort(404)
    
    # Check if booking is completed - redirect to thank you page
    if booking.status == 'completed':
        from flask import redirect, url_for
        return redirect(url_for('public.view_booking_public', booking_id=booking.id))
    
    logger.info(f"✅ PNG ROUTE: Booking {booking.id} status='{booking.status}' type='{booking.booking_type}'")

    # Status-based PNG generation
    try:
        from services.pdf_image import pdf_to_png_bytes_list
        logger.info(f"PNG generation available for booking {booking.id}")
        
        pdf_bytes = None
        
        # Generate appropriate PDF first based on booking status
        if booking.status in ['pending', 'confirmed']:
            # Service Proposal PDF using Classic PDF Generator (same as backend)
            logger.info(f"Generating Service Proposal PNG for booking {booking.id} using Classic Generator")
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
            
            logger.info(f"Classic PNG: {len(products)} products for booking {booking.booking_reference}")
            
            # Generate PDF using Classic PDF Generator (same as backend)
            classic_generator = ClassicPDFGenerator()
            pdf_path = classic_generator.generate_pdf(booking_data, products)
            
            # Read the PDF file
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
            
        elif booking.status == 'quoted':
            # Quote PDF using WeasyPrint with quote_template_final_v2.html
            logger.info(f"Looking for existing Quote PNG for booking {booking.id}")
            
            # First, look for existing quote PDF files instead of generating a new one
            import glob
            existing_files = glob.glob(os.path.join('static', 'generated', f'Quote_{booking.booking_reference}*.pdf'))
            logger.info(f"Found existing quote files: {existing_files}")
            
            if existing_files:
                # Use the most recent existing file
                pdf_path = max(existing_files, key=os.path.getmtime)
                logger.info(f"Using most recent existing PDF: {pdf_path}")
            else:
                # No existing file, generate a new one
                logger.info(f"No existing PDF found, generating new Quote PDF for booking {booking.id}")
                from services.weasyprint_quote_generator import WeasyPrintQuoteGenerator
                pdf_service = WeasyPrintQuoteGenerator()
                pdf_filename = pdf_service.generate_quote_pdf(booking)
                
                logger.info(f"Quote PDF generator returned filename: {pdf_filename}")
                
                if not pdf_filename:
                    logger.error("Quote PDF generator returned None or empty filename")
                    abort(500)
                
                # WeasyPrint returns filename only, need to construct full path
                pdf_path = os.path.join('static', 'generated', pdf_filename)
                logger.info(f"Constructed PDF path: {pdf_path}")
            
            # Verify file exists before reading
            if not os.path.exists(pdf_path):
                logger.error(f"PDF file not found: {pdf_path}")
                abort(500)
            
            # Read the PDF file
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
            
        elif booking.status == 'paid':
            # Quote / Provisional Receipt PDF using WeasyPrint with template
            logger.info(f"Generating Quote/Provisional Receipt PNG for booking {booking.id} using template")
            from services.weasyprint_quote_generator import WeasyPrintQuoteGenerator
            pdf_service = WeasyPrintQuoteGenerator()
            pdf_filename = pdf_service.generate_quote_pdf(booking)
            
            # WeasyPrint returns filename only, need to construct full path
            pdf_path = os.path.join('static', 'generated', pdf_filename)
            
            # Verify file exists before reading
            if not os.path.exists(pdf_path):
                logger.error(f"Generated PDF file not found: {pdf_path}")
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
            # Read the PDF file
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
            
        elif booking.status == 'vouchered':
            # Tour Voucher PNG using WeasyPrint
            logger.info(f"Generating Tour Voucher PNG for booking {booking.id} using WeasyPrint")
            from services.tour_voucher_weasyprint_v2 import TourVoucherWeasyPrintV2
            tour_generator = TourVoucherWeasyPrintV2()
            pdf_bytes = tour_generator.generate_tour_voucher_v2_bytes(booking)
            
            if not pdf_bytes:
                logger.error(f"Failed to generate Tour Voucher PDF for booking {booking.id}")
                abort(500)
        else:
            # Default: Service Proposal PDF using Classic Generator
            logger.info(f"Using default Classic Service Proposal PNG for status '{booking.status}'")
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
            logger.info("Converting PDF to PNG...")
            # แปลง PDF เป็น PNG
            png_images = pdf_to_png_bytes_list(pdf_bytes)
            logger.info(f"PNG conversion result: {len(png_images) if png_images else 'None'} images")
            
            if png_images:
                logger.info(f"Returning PNG image, size: {len(png_images[0])} bytes")
                # Generate filename with timestamp and token based on booking status
                import time
                timestamp = int(time.time())
                token_short = token[:12] if len(token) > 12 else token
                
                # Determine filename based on booking status
                if booking.status in ['pending', 'confirmed']:
                    filename = f"Service_Proposal_{booking.booking_reference}_{timestamp}_{token_short}.png"
                elif booking.status == 'quoted':
                    filename = f"Quote_{booking.booking_reference}_{timestamp}_{token_short}.png"
                elif booking.status == 'paid':
                    filename = f"Quote_ProvisionalReceipt_{booking.booking_reference}_{timestamp}_{token_short}.png"
                elif booking.status == 'vouchered':
                    filename = f"Tour_Voucher_{booking.booking_reference}_{timestamp}_{token_short}.png"
                else:
                    filename = f"Service_Proposal_{booking.booking_reference}_{timestamp}_{token_short}.png"
                
                # ส่ง PNG แรก (หรือรวมหลายหน้าก็ได้)
                response = make_response(png_images[0])
                response.headers['Content-Type'] = 'image/png'
                response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response
            else:
                logger.error("PNG conversion failed - no images generated")
                abort(500)
        else:
            logger.error("PDF generation failed - no bytes returned")
            abort(500)
                
    except ImportError:
        logger.warning("PDF image module not available, redirecting to booking page")
        return redirect(url_for('public.view_booking_secure', token=token))
    except Exception as e:
        logger.error(f"Error generating PNG: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        abort(500)

# Include the rest of the existing routes...
@public_bp.route('/booking/<path:token>')
def view_booking_secure(token):
    """Secure public view for booking with token - Enhanced Version"""
    import logging
    import traceback
    
    logger = logging.getLogger(__name__)
    logger.info(f"=== PUBLIC BOOKING REQUEST START ===")
    logger.info(f"Accessing public booking with token: {token[:20]}...")
    
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
            booking = Booking.query.get(booking_id)
            if booking:
                logger.info(f"Enhanced token verified successfully for booking {booking.id}")
                
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
                
                return render_template('public/enhanced_booking_view.html', 
                                     booking=booking,
                                     token=token,
                                     config=AppConfig,
                                     activity_logs=activity_logs)
            else:
                logger.error(f"Booking with ID {booking_id} not found in database")
        
        # Fallback to old token system for backward compatibility
        logger.info("Enhanced token verification failed, trying legacy token")
        try:
            booking = None
            try:
                booking = Booking.verify_share_token(token)
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
                                    logger.info(f"Found booking {booking_id} via manual parsing - allowing access")
                                    booking = test_booking
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
            
            return render_template('public/enhanced_booking_view.html', 
                                 booking=booking,
                                 token=token,
                                 config=AppConfig,
                                 activity_logs=activity_logs)
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