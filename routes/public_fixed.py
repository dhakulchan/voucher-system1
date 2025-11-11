"""Public routes for sharing booking information without authentication."""

from flask import Blueprint, render_template, abort, url_for, redirect, send_from_directory, make_response
from models.booking import Booking
from config import Config
import os
import logging
from datetime import datetime

public_bp = Blueprint('public', __name__, url_prefix='/public')

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
    
    # สร้าง PNG URL สำหรับ public view
    png_url = url_for('booking.generate_service_proposal_png', booking_id=booking.id, _external=True)
    
    return render_template('public/enhanced_booking_view.html', 
                         booking=booking, 
                         png_url=png_url,
                         config=Config)

@public_bp.route('/booking/<path:token>/pdf')
def download_booking_pdf(token):
    """Download PDF for booking with token verification - Status-based PDF generation"""
    
    # ตรวจสอบ token และ get booking
    booking = Booking.verify_share_token(token)
    if not booking:
        abort(404)

    # Generate appropriate PDF based on booking status
    try:
        logger = logging.getLogger(__name__)
        logger.info(f"🔍 PDF ROUTE CALLED: token={token[:20]}...")
        logger.info(f"✅ PDF ROUTE: Booking {booking.id} status='{booking.status}' type='{booking.booking_type}'")
        
        pdf_bytes = None
        
        # Status-based PDF generation
        if booking.status in ['pending', 'confirmed']:
            # Service Proposal PDF
            logger.info(f"Generating Service Proposal PDF for booking {booking.id}")
            from services.booking_pdf_generator import BookingPDFGenerator
            pdf_service = BookingPDFGenerator()
            pdf_bytes = pdf_service.generate_pdf(booking)
            
        elif booking.status == 'quoted':
            # Quote PDF
            logger.info(f"Generating Quote PDF for booking {booking.id}")
            from services.quote_pdf_generator import QuotePDFGenerator
            pdf_service = QuotePDFGenerator()
            pdf_bytes = pdf_service.generate_pdf(booking)
            
        elif booking.status == 'paid':
            # Quote / Provisional Receipt PDF
            logger.info(f"Generating Quote/Provisional Receipt PDF for booking {booking.id}")
            from services.quote_pdf_generator import QuotePDFGenerator
            pdf_service = QuotePDFGenerator()
            pdf_bytes = pdf_service.generate_pdf(booking)  # Could add provisional receipt header
            
        elif booking.status == 'vouchered':
            # Tour Voucher PDF
            logger.info(f"Generating Tour Voucher PDF for booking {booking.id}")
            from services.tour_voucher_weasyprint_v2 import TourVoucherWeasyPrintV2
            pdf_service = TourVoucherWeasyPrintV2()
            
            # Check for generate_pdf method
            if hasattr(pdf_service, 'generate_pdf'):
                pdf_bytes = pdf_service.generate_pdf(booking)
            elif hasattr(pdf_service, 'generate_tour_voucher_v2'):
                # This returns filename, need to read file
                filename = pdf_service.generate_tour_voucher_v2(booking)
                if filename:
                    output_dir = getattr(pdf_service, 'output_dir', '/Applications/python/voucher-ro_v1.0/static/generated')
                    pdf_path = os.path.join(output_dir, filename)
                    if os.path.exists(pdf_path):
                        with open(pdf_path, 'rb') as f:
                            pdf_bytes = f.read()
        else:
            # Default: Service Proposal PDF for unknown statuses
            logger.info(f"Using default Service Proposal PDF for status '{booking.status}'")
            from services.booking_pdf_generator import BookingPDFGenerator
            pdf_service = BookingPDFGenerator()
            pdf_bytes = pdf_service.generate_pdf(booking)
        
        logger.info(f"PDF generated, size: {len(pdf_bytes) if pdf_bytes else 'None'} bytes")
        
        if pdf_bytes:
            # Generate appropriate filename based on booking status
            import time
            timestamp = int(time.time())
            token_short = token[:12] if len(token) > 12 else token
            
            if booking.status in ['pending', 'confirmed']:
                filename = f"Service_Proposal_{booking.booking_reference}_{timestamp}_{token_short}.pdf"
            elif booking.status == 'quoted':
                filename = f"Quote_{booking.booking_reference}_{timestamp}_{token_short}.pdf"
            elif booking.status == 'paid':
                filename = f"Quote_ProvisionalReceipt_{booking.booking_reference}_{timestamp}_{token_short}.pdf"
            elif booking.status == 'vouchered':
                filename = f"Tour_Voucher_{booking.booking_reference}_{timestamp}_{token_short}.pdf"
            else:
                filename = f"Service_Proposal_{booking.booking_reference}_{timestamp}_{token_short}.pdf"
            
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
    """Download PNG for booking with token verification - Status-based PNG generation"""
    
    logger = logging.getLogger(__name__)
    logger.info(f"🔍 PNG ROUTE CALLED: token={token[:20]}...")
    
    # ตรวจสอบ token และ get booking
    booking = Booking.verify_share_token(token)
    if not booking:
        logger.error(f"❌ PNG ROUTE: Invalid token")
        abort(404)
    
    logger.info(f"✅ PNG ROUTE: Booking {booking.id} status='{booking.status}' type='{booking.booking_type}'")

    # Status-based PNG generation
    try:
        from services.pdf_image import pdf_to_png_bytes_list
        logger.info(f"PNG generation available for booking {booking.id}")
        
        pdf_bytes = None
        
        # Generate appropriate PDF first based on booking status
        if booking.status in ['pending', 'confirmed']:
            # Service Proposal PDF
            logger.info(f"Generating Service Proposal PNG for booking {booking.id}")
            from services.booking_pdf_generator import BookingPDFGenerator
            pdf_service = BookingPDFGenerator()
            pdf_bytes = pdf_service.generate_pdf(booking)
            
        elif booking.status == 'quoted':
            # Quote PDF
            logger.info(f"Generating Quote PNG for booking {booking.id}")
            from services.quote_pdf_generator import QuotePDFGenerator
            pdf_service = QuotePDFGenerator()
            pdf_bytes = pdf_service.generate_pdf(booking)
            
        elif booking.status == 'paid':
            # Quote / Provisional Receipt PDF
            logger.info(f"Generating Quote/Provisional Receipt PNG for booking {booking.id}")
            from services.quote_pdf_generator import QuotePDFGenerator
            pdf_service = QuotePDFGenerator()
            pdf_bytes = pdf_service.generate_pdf(booking)
            
        elif booking.status == 'vouchered':
            # Tour Voucher PDF
            logger.info(f"Generating Tour Voucher PNG for booking {booking.id}")
            from services.tour_voucher_weasyprint_v2 import TourVoucherWeasyPrintV2
            pdf_service = TourVoucherWeasyPrintV2()
            
            if hasattr(pdf_service, 'generate_pdf'):
                pdf_bytes = pdf_service.generate_pdf(booking)
            elif hasattr(pdf_service, 'generate_tour_voucher_v2'):
                filename = pdf_service.generate_tour_voucher_v2(booking)
                if filename:
                    output_dir = getattr(pdf_service, 'output_dir', '/Applications/python/voucher-ro_v1.0/static/generated')
                    pdf_path = os.path.join(output_dir, filename)
                    if os.path.exists(pdf_path):
                        with open(pdf_path, 'rb') as f:
                            pdf_bytes = f.read()
        else:
            # Default: Service Proposal PDF
            logger.info(f"Using default Service Proposal PNG for status '{booking.status}'")
            from services.booking_pdf_generator import BookingPDFGenerator
            pdf_service = BookingPDFGenerator()
            pdf_bytes = pdf_service.generate_pdf(booking)
            
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
    """Secure public view for booking with token"""
    booking = Booking.verify_share_token(token)
    if not booking:
        abort(404)
    
    return render_template('public/booking_view_secure.html', 
                         booking=booking,
                         token=token,
                         config=Config)