"""Public routes for sharing booking information without authentication."""

from flask import Blueprint, render_template, abort, url_for, redirect, send_from_directory
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

@public_bp.route('/booking/<path:token>/png')
def download_booking_png(token):
    """Download PNG for booking with token verification - Simplified approach"""
    
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"🔍 PNG ROUTE CALLED: token={token[:20]}...")
    
    # ตรวจสอบ token และ get booking
    booking = Booking.verify_share_token(token)
    if not booking:
        logger.error(f"❌ PNG ROUTE: Invalid token")
        abort(404)
    
    logger.info(f"✅ PNG ROUTE: Booking {booking.id} status='{booking.status}' type='{booking.booking_type}'")

    # Check if booking status is 'paid' - use Quote PDF/PNG with "Provisional Receipt" header
    if booking.status == 'paid':
        # For paid bookings, generate PNG from Quote PDF (Provisional Receipt)
        return download_quote_png(token)
    
    # Check if booking status is 'vouchered' - use Voucher PDF/PNG with "Travel Service Voucher" header
    elif booking.status == 'vouchered':
        # For vouchered bookings, generate PNG from Voucher PDF (Travel Service Voucher)
        pass  # Continue to voucher generation below

    # Default: Generate PNG from Voucher PDF
    # ตรวจสอบว่ามี PDF image module ไหม
    logger = logging.getLogger(__name__)
    try:
        from services.pdf_image import pdf_to_png_bytes_list, pdf_page_to_png_bytes
        logger.info(f"PNG generation available for booking {booking.id}")
        
        # แทนที่จะ redirect ไปหา voucher system ให้สร้าง PNG โดยตรง
        from flask import make_response
        
        # พยายามสร้าง PDF ก่อน จากนั้นแปลงเป็น PNG
        logger.info(f"Generating {booking.booking_type} voucher PNG for booking {booking.id}")
        
        try:
            pdf_bytes = None
            
            if booking.booking_type in ['tour', 'transport']:
                # ใช้ TourVoucherWeasyPrintV2 สำหรับทั้ง Tour และ Transport Voucher
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
                            logger.error(f"PDF file not found: {pdf_path}")
                else:
                    logger.error("No suitable PDF generation method found")
                    
            else:
                # สำหรับ booking type อื่นๆ ลองใช้ TourVoucherWeasyPrintV2
                logger.info(f"Unknown booking type '{booking.booking_type}', trying TourVoucherWeasyPrintV2")
                from services.tour_voucher_weasyprint_v2 import TourVoucherWeasyPrintV2
                pdf_service = TourVoucherWeasyPrintV2()
                
                if hasattr(pdf_service, 'generate_tour_voucher_v2'):
                    filename = pdf_service.generate_tour_voucher_v2(booking)
                    if filename:
                        output_dir = getattr(pdf_service, 'output_dir', '/Applications/python/voucher-ro_v1.0/static/generated')
                        pdf_path = os.path.join(output_dir, filename)
                        if os.path.exists(pdf_path):
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
                    token_short = token[:12] if len(token) > 12 else token  # Use first 12 chars of token
                    
                    # Debug: log the actual status
                    logger.info(f"PNG - Booking status: '{booking.status}', type: '{booking.booking_type}'")
                    
                    # Determine filename based on booking status and type
                    if booking.status == 'pending':
                        filename = f"Proposal_service_{booking.booking_reference}_{timestamp}_{token_short}.png"
                    elif booking.status == 'paid':
                        if booking.booking_type == 'quote':
                            filename = f"Quote_ProvisionalReceipt_{booking.booking_reference}_{timestamp}_{token_short}.png"
                        else:
                            filename = f"Quote_{booking.booking_reference}_{timestamp}_{token_short}.png"
                    elif booking.status == 'vouchered':
                        filename = f"Tour_voucher_{booking.booking_reference}_{timestamp}_{token_short}.png"
                    else:
                        # Default fallback
                        logger.info(f"PNG - Using default filename for status: '{booking.status}'")
                        filename = f"Service_proposal_{booking.booking_reference}_{timestamp}_{token_short}.png"
                    
                    # ส่ง PNG แรก (หรือรวมหลายหน้าก็ได้)
                    response = make_response(png_images[0])
                    response.headers['Content-Type'] = 'image/png'
                    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
                    return response
                else:
                    logger.error("PNG conversion failed - no images generated")
            else:
                logger.error("PDF generation failed - no bytes returned")
                
        except Exception as e:
            logger.error(f"Error generating {booking.booking_type} voucher PNG: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
                
        # Fallback: redirect to public booking page
        return redirect(url_for('public.view_booking_secure', token=token))
        
    except ImportError:
        logger.warning("PDF image module not available, redirecting to booking page")
        return redirect(url_for('public.view_booking_secure', token=token))


@public_bp.route('/booking/<path:token>/pdf')
def download_booking_pdf(token):
    """Download PDF for booking with token verification - Status-based PDF generation"""
    
    # ตรวจสอบ token และ get booking
    booking = Booking.verify_share_token(token)
    if not booking:
        abort(404)

    # Generate appropriate PDF based on booking status
    try:
        from flask import make_response
        import logging
        
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
        abort(500)


@public_bp.route('/booking/<path:token>/quote-png')        if pdf_bytes:
            # Generate filename with timestamp and token based on booking status
            import time
            timestamp = int(time.time())
            token_short = token[:12] if len(token) > 12 else token
            
            # Debug: log the actual status
            logger.info(f"Booking status: '{booking.status}', type: '{booking.booking_type}'")
            
            # Determine filename based on booking status and type
            if booking.status == 'pending':
                filename = f"Proposal_service_{booking.booking_reference}_{timestamp}_{token_short}.pdf"
            elif booking.status in ['confirmed', 'paid']:
                if booking.booking_type == 'quote':
                    filename = f"Quote_ProvisionalReceipt_{booking.booking_reference}_{timestamp}_{token_short}.pdf"
                else:
                    filename = f"Service_Proposal_{booking.booking_reference}_{timestamp}_{token_short}.pdf"
            elif booking.status == 'vouchered':
                filename = f"Tour_voucher_{booking.booking_reference}_{timestamp}_{token_short}.pdf"
            else:
                # Default fallback for any other status
                logger.info(f"Using default filename for status: '{booking.status}'")
                filename = f"Service_proposal_{booking.booking_reference}_{timestamp}_{token_short}.pdf"
            
            response = make_response(pdf_bytes)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        else:
            logger.error("PDF generation failed - no bytes returned")
    
    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
    
    # Fallback: redirect to public booking page
    return redirect(url_for('public.view_booking_secure', token=token))


@public_bp.route('/booking/<path:token>')
def view_booking_secure(token):
    """Secure public view for booking with token verification (30-day expiry)"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"Public booking access attempt with token: {token[:20]}...")
    
    # ตรวจสอบ token และ get booking
    booking = Booking.verify_share_token(token)
    if not booking:
        logger.warning(f"Invalid or expired token: {token[:20]}...")
        abort(404)  # Token invalid, expired, or booking not found
    
    logger.info(f"Successfully verified token for booking {booking.id}")
    
    try:
        return render_template('public/enhanced_booking_view.html', 
                             booking=booking, 
                             token=token,
                             config=Config)
    except Exception as e:
        logger.error(f"Error rendering template: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        abort(500)

@public_bp.route('/booking/<path:token>/quote/pdf')
def download_quote_pdf(token):
    """Download Quote PDF for booking with token verification (no login required) - Simplified Version"""
    from flask import current_app as app
    
    # ตรวจสอบ token และ get booking
    booking = Booking.verify_share_token(token)
    if not booking:
        abort(404)
    
    # ตรวจสอบว่ามี quotes หรือไม่
    from models.quote import Quote
    quote = Quote.query.filter_by(booking_id=booking.id).first()
    if not quote:
        app.logger.warning(f"⚠️ No quote found for booking {booking.id}")
        # Fallback to regular voucher if no quote
        return redirect(url_for('public.download_booking_pdf', token=token))
    
    try:
        # สร้าง PDF โดยใช้ TourVoucherGeneratorV2 โดยตรง
        from services.tour_voucher_generator_v2 import TourVoucherGeneratorV2
        from flask import Response
        
        app.logger.info(f"📄 Generating quote PDF for {quote.quote_number}")
        
        generator = TourVoucherGeneratorV2()
        
        # Generate PDF with the booking data we have
        pdf_result = generator.generate_quote_pdf_v2(quote, booking)
        
        if isinstance(pdf_result, tuple) and len(pdf_result) == 2:
            pdf_bytes, filename = pdf_result
            app.logger.info(f"✅ Quote PDF generated: {filename} ({len(pdf_bytes)} bytes)")
            
            # Generate filename with timestamp and token
            import time
            timestamp = int(time.time())
            token_short = token[:12] if len(token) > 12 else token  # Use first 12 chars of token
            download_filename = f"Quote_{booking.id}_{timestamp}_{token_short}.pdf"
            
            # Return PDF as direct response
            return Response(
                pdf_bytes,
                mimetype='application/pdf',
                headers={
                    'Content-Disposition': f'attachment; filename="{download_filename}"',
                    'Content-Type': 'application/pdf'
                }
            )
        else:
            app.logger.error(f"❌ Unexpected PDF result type: {type(pdf_result)}")
            # Fallback to regular voucher
            return redirect(url_for('public.download_booking_pdf', token=token))
        
    except Exception as e:
        app.logger.error(f"❌ Error generating Quote PDF: {e}")
        # Fallback to regular voucher
        return redirect(url_for('public.download_booking_pdf', token=token))

@public_bp.route('/booking/<path:token>/quote/png')
def download_quote_png(token):
    """Download Quote PNG for booking with token verification (no login required) - Simplified Version"""
    from flask import current_app as app
    
    # ตรวจสอบ token และ get booking
    booking = Booking.verify_share_token(token)
    if not booking:
        abort(404)
    
    # ตรวจสอบว่ามี quotes หรือไม่
    from models.quote import Quote
    quote = Quote.query.filter_by(booking_id=booking.id).first()
    if not quote:
        app.logger.warning(f"⚠️ No quote found for booking {booking.id}")
        # Fallback to regular voucher PNG
        return redirect(url_for('public.download_booking_png', token=token))
    
    try:
        # สร้าง PDF โดยใช้ TourVoucherGeneratorV2 โดยตรง
        from services.tour_voucher_generator_v2 import TourVoucherGeneratorV2
        import fitz  # PyMuPDF
        import tempfile
        import os
        from flask import Response
        
        app.logger.info(f"📄 Generating quote PNG for {quote.quote_number}")
        
        generator = TourVoucherGeneratorV2()
        
        # Generate PDF first with the booking data we have
        pdf_result = generator.generate_quote_pdf_v2(quote, booking)
        
        if isinstance(pdf_result, tuple) and len(pdf_result) == 2:
            pdf_bytes, filename = pdf_result
            app.logger.info(f"✅ Quote PDF generated: {filename} ({len(pdf_bytes)} bytes)")
            
            # Create temporary file for PDF bytes
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
                temp_pdf.write(pdf_bytes)
                temp_pdf_path = temp_pdf.name
                
            # Convert to PNG
            pdf_doc = fitz.open(temp_pdf_path)
            
            # Convert all pages to single long PNG
            images = []
            total_height = 0
            max_width = 0
            
            for page_num in range(len(pdf_doc)):
                page = pdf_doc[page_num]
                mat = fitz.Matrix(2.0, 2.0)  # 2x scale for better quality
                pix = page.get_pixmap(matrix=mat)
                total_height += pix.height
                max_width = max(max_width, pix.width)
                images.append(pix)
            
            # Create combined image (if multiple pages) or use single page
            if len(images) == 1:
                final_pix = images[0]
            else:
                # Combine multiple pages vertically
                from PIL import Image
                import io
                
                combined_img = Image.new('RGB', (max_width, total_height), 'white')
                y_offset = 0
                
                for pix in images:
                    img_data = pix.tobytes("png")
                    img = Image.open(io.BytesIO(img_data))
                    combined_img.paste(img, (0, y_offset))
                    y_offset += img.height
                
                # Convert back to bytes
                img_bytes = io.BytesIO()
                combined_img.save(img_bytes, format='PNG')
                png_data = img_bytes.getvalue()
            
            if len(images) == 1:
                png_data = images[0].tobytes("png")
            
            # Cleanup
            pdf_doc.close()
            os.unlink(temp_pdf_path)
            
            # Generate filename with timestamp and token
            import time
            timestamp = int(time.time())
            token_short = token[:12] if len(token) > 12 else token  # Use first 12 chars of token
            download_filename = f"Quote_{booking.id}_{timestamp}_{token_short}.png"
            
            # Return PNG as response
            return Response(
                png_data,
                mimetype='image/png',
                headers={
                    'Content-Disposition': f'attachment; filename="{download_filename}"',
                    'Content-Type': 'image/png'
                }
            )
        else:
            app.logger.error(f"❌ Unexpected PDF result type: {type(pdf_result)}")
            # Fallback to regular voucher PNG
            return redirect(url_for('public.download_booking_png', token=token))
        
    except Exception as e:
        app.logger.error(f"❌ Error generating Quote PNG: {e}")
        # Fallback to regular voucher PNG
        return redirect(url_for('public.download_booking_png', token=token))
        print(f"Error generating Quote PNG: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        abort(500)

# Backward compatibility routes
@public_bp.route('/booking/<int:booking_id>/<old_token>')
def view_booking_secure_old(booking_id, old_token):
    """Legacy route for old token format - redirect to new format if valid"""
    
    # Try old verification method for backward compatibility
    booking = Booking.query.get_or_404(booking_id)
    new_token = booking.generate_secure_token(expires_days=30)
    return redirect(url_for('public.view_booking_secure', token=new_token))

@public_bp.route('/voucher-file/<int:file_id>/<path:token>')
def download_voucher_file(file_id, token):
    """Download voucher file with token verification"""
    
    # ตรวจสอบ token
    booking = Booking.verify_share_token(token)
    if not booking:
        abort(404)
    
    from models.voucher_sharing import VoucherFile
    voucher_file = VoucherFile.query.filter_by(id=file_id, voucher_id=booking.id).first_or_404()
    
    # Extract directory and filename from file_path
    import os
    file_directory = os.path.dirname(voucher_file.file_path)
    file_name = os.path.basename(voucher_file.file_path)
    
    # Determine download filename with proper extension
    if voucher_file.title:
        # Get file extension from original filename
        _, original_ext = os.path.splitext(voucher_file.original_filename)
        # Check if title already has an extension
        title_name, title_ext = os.path.splitext(voucher_file.title)
        if title_ext:
            # Title already has extension, use as is
            download_filename = voucher_file.title
        else:
            # Title doesn't have extension, append from original
            download_filename = voucher_file.title + original_ext
    else:
        # No title, use original filename
        download_filename = voucher_file.original_filename
    
    return send_from_directory(
        file_directory,
        file_name,
        as_attachment=True,
        download_name=download_filename
    )

@public_bp.route('/booking/<int:booking_id>/quote-pdf')
def download_quote_pdf_by_id(booking_id):
    """Download Quote PDF with booking ID + token verification (v parameter)"""
    from flask import request, current_app as app
    
    # ดึง token จาก query parameter 'v'
    token_param = request.args.get('v')
    if not token_param:
        abort(404)  # No token provided
    
    # ตรวจสอบ booking
    booking = Booking.query.get_or_404(booking_id)
    
    # ตรวจสอบว่า booking.status = 'paid'
    if booking.status != 'paid':
        abort(404)  # Only paid bookings can access quote format
    
    # ตรวจสอบ token (แยกจาก + ถ้ามี)
    if '+' in token_param:
        token_parts = token_param.split('+')
        timestamp_str = token_parts[0]
        token = token_parts[1] if len(token_parts) > 1 else None
    else:
        timestamp_str = token_param
        token = None
    
    try:
        # Generate token with departure_date + 120 days expiry
        expected_token = booking.generate_quote_share_token()
        
        # ตรวจสอบ token หรือใช้ timestamp validation
        import time
        current_timestamp = int(time.time())
        provided_timestamp = int(timestamp_str)
        
        # ตรวจสอบว่า token ยังไม่หมดอายุ (departure_date + 120 days)
        if booking.departure_date:
            from datetime import timedelta
            expiry_date = booking.departure_date + timedelta(days=120)
            expiry_timestamp = int(expiry_date.timestamp())
            
            if current_timestamp > expiry_timestamp:
                app.logger.warning(f"Quote token expired for booking {booking_id}")
                abort(404)  # Token expired
        
        app.logger.info(f"📄 Generating Quote PDF for paid booking {booking_id}")
        
        # ใช้ WeasyPrint Quote Generator
        from services.tour_voucher_generator_v2 import TourVoucherGeneratorV2
        from models.quote import Quote
        from flask import Response
        
        # ดึง quote สำหรับ booking นี้
        quote = Quote.query.filter_by(booking_id=booking.id).first()
        if not quote:
            app.logger.warning(f"⚠️ No quote found for paid booking {booking_id}")
            abort(404)
        
        generator = TourVoucherGeneratorV2()
        pdf_result = generator.generate_quote_pdf_v2(quote, booking)
        
        if isinstance(pdf_result, tuple) and len(pdf_result) == 2:
            pdf_bytes, filename = pdf_result
            app.logger.info(f"✅ Quote PDF generated: {filename} ({len(pdf_bytes)} bytes)")
            
            # Generate filename with timestamp and token parameter
            import time
            timestamp = int(time.time())
            token_short = timestamp_str[:8] if timestamp_str else str(timestamp)[:8]  # Use timestamp as token reference
            download_filename = f"Quote_{booking_id}_{timestamp}_{token_short}.pdf"
            
            return Response(
                pdf_bytes,
                mimetype='application/pdf',
                headers={
                    'Content-Disposition': f'attachment; filename="{download_filename}"',
                    'Content-Type': 'application/pdf'
                }
            )
        else:
            app.logger.error(f"❌ Unexpected PDF result for booking {booking_id}")
            abort(500)
            
    except Exception as e:
        app.logger.error(f"❌ Error generating Quote PDF for booking {booking_id}: {e}")
        abort(500)

@public_bp.route('/booking/<int:booking_id>/quote-png')
def download_quote_png_by_id(booking_id):
    """Download Quote PNG with booking ID + token verification (v parameter)"""
    from flask import request, current_app as app
    
    # ดึง token จาก query parameter 'v'
    token_param = request.args.get('v')
    if not token_param:
        abort(404)  # No token provided
    
    # ตรวจสอบ booking
    booking = Booking.query.get_or_404(booking_id)
    
    # ตรวจสอบว่า booking.status = 'paid'
    if booking.status != 'paid':
        abort(404)  # Only paid bookings can access quote format
    
    # ตรวจสอบ token (same validation as PDF route)
    if '+' in token_param:
        token_parts = token_param.split('+')
        timestamp_str = token_parts[0]
        token = token_parts[1] if len(token_parts) > 1 else None
    else:
        timestamp_str = token_param
        token = None
    
    try:
        # Generate token with departure_date + 120 days expiry
        expected_token = booking.generate_quote_share_token()
        
        # ตรวจสอบ token หรือใช้ timestamp validation
        import time
        current_timestamp = int(time.time())
        provided_timestamp = int(timestamp_str)
        
        # ตรวจสอบว่า token ยังไม่หมดอายุ (departure_date + 120 days)
        if booking.departure_date:
            from datetime import timedelta
            expiry_date = booking.departure_date + timedelta(days=120)
            expiry_timestamp = int(expiry_date.timestamp())
            
            if current_timestamp > expiry_timestamp:
                app.logger.warning(f"Quote token expired for booking {booking_id}")
                abort(404)  # Token expired
        
        app.logger.info(f"🖼️ Generating Quote PNG for paid booking {booking_id}")
        
        # ใช้ WeasyPrint Quote Generator to create PDF first, then convert to PNG
        from services.tour_voucher_generator_v2 import TourVoucherGeneratorV2
        from models.quote import Quote
        from flask import Response
        
        # ดึง quote สำหรับ booking นี้
        quote = Quote.query.filter_by(booking_id=booking.id).first()
        if not quote:
            app.logger.warning(f"⚠️ No quote found for paid booking {booking_id}")
            abort(404)
        
        generator = TourVoucherGeneratorV2()
        pdf_result = generator.generate_quote_pdf_v2(quote, booking)
        
        if isinstance(pdf_result, tuple) and len(pdf_result) == 2:
            pdf_bytes, filename = pdf_result
            
            # Convert PDF to PNG using PyMuPDF
            try:
                from services.pdf_image import pdf_page_to_png_bytes
                png_bytes = pdf_page_to_png_bytes(pdf_bytes, page_num=0, dpi=150)
                
                app.logger.info(f"✅ Quote PNG generated: {filename} ({len(png_bytes)} bytes)")
                
                # Generate filename with timestamp and token parameter
                import time
                timestamp = int(time.time())
                token_short = timestamp_str[:8] if timestamp_str else str(timestamp)[:8]  # Use timestamp as token reference
                download_filename = f"Quote_{booking_id}_{timestamp}_{token_short}.png"
                
                return Response(
                    png_bytes,
                    mimetype='image/png',
                    headers={
                        'Content-Disposition': f'attachment; filename="{download_filename}"',
                        'Content-Type': 'image/png'
                    }
                )
            except Exception as png_error:
                app.logger.error(f"❌ Error converting Quote PDF to PNG: {png_error}")
                abort(500)
        else:
            app.logger.error(f"❌ Unexpected PDF result for booking {booking_id}")
            abort(500)
            
    except Exception as e:
        app.logger.error(f"❌ Error generating Quote PNG for booking {booking_id}: {e}")
        abort(500)

@public_bp.route('/test-syntax')
def test_syntax():
    """Test JavaScript syntax and error handling"""
    return render_template('test_syntax.html')

@public_bp.route('/voucher/<int:voucher_id>/png/<path:token>')
def download_public_voucher_png(voucher_id, token):
    """Download voucher PNG with public token verification"""
    
    # ตรวจสอบ token
    booking = Booking.verify_share_token(token)
    if not booking or booking.id != voucher_id:
        abort(404)
    
    # Import ที่จำเป็น
    from flask import current_app, Response
    from services.pdf_image import pdf_to_long_png_bytes
    
    # Check PDF image module availability
    try:
        import fitz  # PyMuPDF
    except ImportError:
        current_app.logger.error('PyMuPDF not available for PNG generation')
        abort(500)
    
    try:
        # Generate PDF bytes
        if booking.booking_type == 'tour':
            from services.tour_voucher_weasyprint_v2 import TourVoucherWeasyPrintV2
            tour_generator = TourVoucherWeasyPrintV2()
            pdf_bytes = tour_generator.generate_tour_voucher_v2_bytes(booking)
        else:
            from services.pdf_generator import PDFGenerator
            gen = PDFGenerator()
            pdf_bytes = gen.generate_tour_voucher_bytes(booking)
        
        if not pdf_bytes:
            current_app.logger.error('PDF generation failed')
            abort(500)
        
        # Convert PDF to PNG (combined long image)
        png_bytes = pdf_to_long_png_bytes(pdf_bytes)
        
        if png_bytes:
            # Generate filename with timestamp and token
            import time
            timestamp = int(time.time())
            token_short = token[:12] if len(token) > 12 else token  # Use first 12 chars of token
            filename = f"Voucher_{booking.id}_{timestamp}_{token_short}.png"
            
            response = Response(png_bytes, mimetype='image/png')
            response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        else:
            current_app.logger.error('PNG conversion failed')
            abort(500)
            
    except Exception as e:
        current_app.logger.error(f'Error generating voucher PNG: {e}')
        abort(500)

@public_bp.route('/voucher/<int:voucher_id>/pdf/<path:token>')
def download_public_voucher_pdf(voucher_id, token):
    """Download voucher PDF with public token verification"""
    
    # ตรวจสอบ token
    booking = Booking.verify_share_token(token)
    if not booking or booking.id != voucher_id:
        abort(404)
    
    from flask import current_app, Response
    
    try:
        # Generate PDF bytes
        if booking.booking_type == 'tour':
            from services.tour_voucher_weasyprint_v2 import TourVoucherWeasyPrintV2
            tour_generator = TourVoucherWeasyPrintV2()
            pdf_bytes = tour_generator.generate_tour_voucher_v2_bytes(booking)
        else:
            from services.pdf_generator import PDFGenerator
            gen = PDFGenerator()
            pdf_bytes = gen.generate_tour_voucher_bytes(booking)
        
        if not pdf_bytes:
            current_app.logger.error('PDF generation failed')
            abort(500)
        
        # Generate filename with timestamp and token
        import time
        timestamp = int(time.time())
        token_short = token[:12] if len(token) > 12 else token  # Use first 12 chars of token
        filename = f"Voucher_{booking.id}_{timestamp}_{token_short}.pdf"
        
        response = Response(pdf_bytes, mimetype='application/pdf')
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
            
    except Exception as e:
        current_app.logger.error(f'Error generating voucher PDF: {e}')
        abort(500)
