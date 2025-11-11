from flask import Blueprint, render_template, request, redirect, url_for, flash, make_response, send_file
from flask_login import login_required
from models.booking import Booking
from extensions import db
import os
import random
import base64
from datetime import datetime

# Create pre-receipt blueprint
pre_receipt_bp = Blueprint('pre_receipt', __name__, url_prefix='/pre-receipt')

def get_logo_base64():
    """Get base64 encoded logo for PDF generation"""
    try:
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'dcts-logo-vou.png')
        if os.path.exists(logo_path):
            with open(logo_path, 'rb') as img_file:
                img_data = img_file.read()
                base64_string = base64.b64encode(img_data).decode('utf-8')
                return f"data:image/png;base64,{base64_string}"
    except Exception as e:
        print(f"Error loading logo: {e}")
    return None

@pre_receipt_bp.route('/')
@pre_receipt_bp.route('/list')
@login_required
def list():
    """List all bookings that can generate pre-receipts"""
    try:
        # Get bookings that are paid, vouchered, or completed (ready for pre-receipt)
        bookings = Booking.query.filter(
            Booking.status.in_(['paid', 'vouchered', 'completed'])
        ).order_by(Booking.created_at.desc()).all()
        
        return render_template('pre_receipt/list.html', 
                             bookings=bookings,
                             title='Pre-Receipt Management')
        
    except Exception as e:
        flash('Error loading pre-receipts: {}'.format(str(e)), 'error')
        return redirect(url_for('dashboard.index'))

@pre_receipt_bp.route('/view/<int:booking_id>')
@login_required
def view(booking_id):
    """View booking details for pre-receipt"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        # Check if booking is eligible for pre-receipt
        if booking.status not in ['paid', 'vouchered', 'completed']:
            flash('This booking is not eligible for pre-receipt generation', 'warning')
            return redirect(url_for('pre_receipt.list'))
            
        return render_template('pre_receipt/view.html', 
                             booking=booking,
                             title='Pre-Receipt - Booking #{}'.format(booking.id))
        
    except Exception as e:
        flash('Error viewing booking: {}'.format(str(e)), 'error')
        return redirect(url_for('pre_receipt.list'))

@pre_receipt_bp.route('/download/<int:booking_id>/<format>')
@login_required
def generate_receipt(booking_id, format):
    """Generate pre-receipt PDF or PNG"""
    def safe_float(value, default=0.0):
        """Safely convert value to float"""
        try:
            if value is None:
                return default
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def safe_int(value, default=1):
        """Safely convert value to int"""
        try:
            if value is None:
                return default
            return int(value)
        except (ValueError, TypeError):
            return default
    
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        # Check if booking is eligible for pre-receipt
        if booking.status not in ['paid', 'vouchered', 'completed']:
            flash('This booking is not eligible for pre-receipt generation', 'warning')
            return redirect(url_for('pre_receipt.list'))
        
        # Generate random receipt number if not exists
        if not hasattr(booking, 'receipt_number') or not booking.receipt_number:
            current_date = datetime.now().strftime('%y%m%d')
            random_num = str(random.randint(1000, 9999))
            receipt_number = "PR{}{}".format(current_date, random_num)
        else:
            receipt_number = booking.receipt_number
            
        # Get real booking items/products if available (safer version)
        booking_items = []
        
        # Try to get items from booking products/services with safe attribute access
        try:
            if hasattr(booking, 'products') and booking.products:
                # Check if products is iterable and not a string
                if hasattr(booking.products, '__iter__') and not isinstance(booking.products, str):
                    for idx, product in enumerate(booking.products, 1):
                        # Use getattr for safe attribute access with safe numeric conversion
                        quantity = safe_int(getattr(product, 'quantity', 1))
                        price = safe_float(getattr(product, 'price', 0))
                        booking_items.append({
                            'no': idx,
                            'name': getattr(product, 'name', 'Tour Package'),
                            'quantity': quantity,
                            'price': price,
                            'amount': quantity * price,
                            'is_negative': getattr(product, 'is_negative', False)
                        })
        except Exception as e:
            print(f"Warning: Error processing booking products: {e}")
        
        # If no products, create fallback item from booking info
        if not booking_items:
            total_amount = safe_float(getattr(booking, 'total_amount', 0))
            total_pax = safe_int(getattr(booking, 'total_pax', 1))
            booking_items = [
                {
                    'no': 1,
                    'name': 'Tour Package - {}'.format(getattr(booking, 'booking_type', 'Package Tour')),
                    'quantity': total_pax,
                    'price': total_amount / max(total_pax, 1),
                    'amount': total_amount,
                    'is_negative': False
                }
            ]

        # Prepare data for template with safe conversions
        receipt_data = {
            'booking': booking,
            'receipt_number': receipt_number,
            'receipt_date': datetime.now().strftime('%d/%m/%Y'),
            'company_name': 'DHAKUL CHAN TRAVEL SERVICE (THAILAND) CO.,LTD.',
            'company_address': '710, 716, 704, 706 Prachautthit Road, Samsennok, Huai Kwang, Bangkok 10310',
            'company_phone': '+662 2744218 | +662 0266525',
            'company_email': 'info@dhakulchan.net',
            'total_amount': safe_float(getattr(booking, 'total_amount', 0)),
            'items': booking_items,
            'quote': getattr(booking, 'quote', None),
            'quote_number': getattr(booking, 'quote_number', 'QT{}'.format(booking.id)),
            'customer': getattr(booking, 'customer', None),
            'customer_name': getattr(booking, 'customer_name', 'N/A'),
            'customer_phone': getattr(booking, 'customer_phone', ''),
            'generation_date': datetime.now().strftime('%d/%m/%Y'),
            'created_by': 'admin',
            'due_date': datetime.now().strftime('%d/%m/%Y'),
            'time_limit': datetime.now().strftime('%d/%m/%Y'),
            'name_list': getattr(booking, 'guest_list', ''),
            'guest_list_data': getattr(booking, 'guest_list', ''),
            'flight_info': getattr(booking, 'flight_info', ''),
            'voucher_title': 'PRE-RECEIPT'
        }
        
        # Render HTML template
        html_content = render_template('pdf/quote_template_final_v2_pre-receipt.html', **receipt_data)
        
        if format.lower() == 'pdf':
            return generate_pdf_response(html_content, 'pre-receipt-booking-{}.pdf'.format(booking_id))
        elif format.lower() == 'png':
            return generate_png_response(html_content, 'pre-receipt-booking-{}.png'.format(booking_id))
        else:
            flash('Invalid format. Please use PDF or PNG.', 'error')
            return redirect(url_for('pre_receipt.view', booking_id=booking_id))
            
    except Exception as e:
        flash('Error generating pre-receipt: {}'.format(str(e)), 'error')
        return redirect(url_for('pre_receipt.view', booking_id=booking_id))

def generate_pdf_response(html_content, filename):
    """Generate PDF response using WeasyPrint"""
    try:
        import weasyprint
        from io import BytesIO
        import os
        
        # Get base URL for static files
        base_url = os.path.abspath('.')
        
        # Create PDF
        pdf_buffer = BytesIO()
        weasyprint.HTML(string=html_content, base_url=base_url).write_pdf(pdf_buffer)
        pdf_buffer.seek(0)
        
        # Create response
        response = make_response(pdf_buffer.read())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
        
        return response
        
    except ImportError:
        flash('WeasyPrint is not installed. Please install it to generate PDFs.', 'error')
        raise Exception('WeasyPrint not available')
    except Exception as e:
        raise Exception('PDF generation failed: {}'.format(str(e)))

def generate_png_response(html_content, filename):
    """Generate PNG response using WeasyPrint + pdf2image conversion"""
    try:
        import weasyprint
        from io import BytesIO
        import os
        
        # Get base URL for static files
        base_url = os.path.abspath('.')
        
        # First generate PDF
        pdf_buffer = BytesIO()
        weasyprint.HTML(string=html_content, base_url=base_url).write_pdf(pdf_buffer)
        pdf_buffer.seek(0)
        
        # Convert PDF to PNG using pdf2image
        try:
            from pdf2image import convert_from_bytes
            from PIL import Image
            
            # Convert PDF to image (first page)
            images = convert_from_bytes(pdf_buffer.read(), first_page=1, last_page=1, dpi=300)
            
            if images:
                # Save as PNG
                png_buffer = BytesIO()
                images[0].save(png_buffer, format='PNG', optimize=True, quality=95)
                png_buffer.seek(0)
                
                # Create response
                response = make_response(png_buffer.read())
                response.headers['Content-Type'] = 'image/png'
                response.headers['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
                
                return response
            else:
                raise Exception('No images generated from PDF')
                
        except ImportError:
            flash('pdf2image is not installed. Please install it to generate PNG files.', 'error')
            # Fallback: redirect to view with notice
            booking_id = filename.split('-')[-1].split('.')[0] if '-' in filename else '1'
            from flask import redirect, url_for
            return redirect(url_for('pre_receipt.view', booking_id=booking_id))
        
    except ImportError:
        flash('WeasyPrint is not installed. Please install it to generate files.', 'error')
        raise Exception('WeasyPrint not available')
    except Exception as e:
        raise Exception('PNG generation failed: {}'.format(str(e)))

@pre_receipt_bp.route('/test-quote-template/<int:booking_id>')
@login_required
def test_quote_template(booking_id):
    """Test the quote template with updated formatting"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        # Check if booking is eligible for pre-receipt
        if booking.status not in ['paid', 'vouchered', 'completed']:
            flash('This booking is not eligible for pre-receipt generation', 'warning')
            return redirect(url_for('pre_receipt.list'))
        
        # Generate random receipt number if not exists
        if not hasattr(booking, 'receipt_number') or not booking.receipt_number:
            current_date = datetime.now().strftime('%y%m%d')
            random_num = str(random.randint(1000, 9999))
            receipt_number = "PR{}{}".format(current_date, random_num)
        else:
            receipt_number = booking.receipt_number
            
        # Get real booking items/products if available
        booking_items = []
        
        # Try to get items from booking products/services
        if hasattr(booking, 'products') and booking.products:
            for idx, product in enumerate(booking.products, 1):
                booking_items.append({
                    'no': idx,
                    'name': product.name or 'Tour Package',
                    'quantity': product.quantity or 1,
                    'price': product.price or 0,
                    'amount': (product.quantity or 1) * (product.price or 0),
                    'is_negative': False
                })
        
        # If no products, create item from booking info
        if not booking_items:
            booking_items = [
                {
                    'no': 1,
                    'name': 'Tour Package - {}'.format(booking.booking_type or 'Package Tour'),
                    'quantity': booking.total_pax or 1,
                    'price': booking.total_amount or 0,
                    'amount': booking.total_amount or 0,
                    'is_negative': False
                }
            ]
        
        receipt_data = {
            'booking': booking,
            'receipt_number': receipt_number,
            'receipt_date': datetime.now().strftime('%d/%m/%Y'),
            'company_name': 'DHAKUL CHAN TRAVEL SERVICE (THAILAND) CO.,LTD.',
            'company_address': '710, 716, 704, 706 Prachautthit Road, Samsennok, Huai Kwang, Bangkok 10310',
            'company_phone': '+662 2744218 | +662 0266525',
            'company_email': 'info@dhakulchan.net',
            'total_amount': booking.total_amount or 0,
            'items': booking_items,
            'quote': getattr(booking, 'quote', None),
            'quote_number': getattr(booking, 'quote_number', 'QT{}'.format(booking.id)),
            'customer': getattr(booking, 'customer', None),
            'customer_name': booking.customer_name or 'N/A',
            'customer_phone': getattr(booking, 'customer_phone', ''),
            'generation_date': datetime.now().strftime('%d/%m/%Y'),
            'created_by': 'admin',
            'due_date': datetime.now().strftime('%d/%m/%Y'),
            'time_limit': datetime.now().strftime('%d/%m/%Y'),
            'name_list': getattr(booking, 'guest_list', ''),
            'guest_list_data': getattr(booking, 'guest_list', ''),
            'flight_info': getattr(booking, 'flight_info', ''),
            'voucher_title': 'QUOTE / PRE-RECEIPT'
        }
        
        # Render HTML template for testing
        html_content = render_template('pdf/quote_template_final_v2_pre-receipt.html', **receipt_data)
        
        # Return HTML for browser preview
        from flask import Response
        return Response(html_content, mimetype='text/html')
        
    except Exception as e:
        flash('Error testing template: {}'.format(str(e)), 'error')
        return redirect(url_for('pre_receipt.view', booking_id=booking_id))

@pre_receipt_bp.route('/quote-pdf/<int:booking_id>/<format>')
@login_required
def generate_quote_pdf(booking_id, format):
    """Generate Quote PDF/PNG using the fixed template"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        # Check if booking is eligible for pre-receipt
        if booking.status not in ['paid', 'vouchered', 'completed']:
            flash('This booking is not eligible for quote generation', 'warning')
            return redirect(url_for('pre_receipt.list'))
        
        # Generate random receipt number if not exists
        if not hasattr(booking, 'receipt_number') or not booking.receipt_number:
            current_date = datetime.now().strftime('%y%m%d')
            random_num = str(random.randint(1000, 9999))
            receipt_number = "QT{}{}".format(current_date, random_num)
        else:
            receipt_number = getattr(booking, 'quote_number', 'QT{}'.format(booking.id))
            
        # Get real booking items/products if available
        quote_items = []
        
        # Try to get items from booking products/services
        if hasattr(booking, 'products') and booking.products:
            for idx, product in enumerate(booking.products, 1):
                quote_items.append({
                    'no': idx,
                    'name': product.name or 'Tour Package',
                    'quantity': product.quantity or 1,
                    'price': product.price or 0,
                    'amount': (product.quantity or 1) * (product.price or 0),
                    'is_negative': False
                })
        elif hasattr(booking, 'quote') and booking.quote and hasattr(booking.quote, 'items'):
            # Try to get items from quote relationship
            for idx, item in enumerate(booking.quote.items, 1):
                quote_items.append({
                    'no': idx,
                    'name': item.name or 'Tour Package',
                    'quantity': item.quantity or 1,
                    'price': item.price or 0,
                    'amount': (item.quantity or 1) * (item.price or 0),
                    'is_negative': getattr(item, 'is_negative', False)
                })
        
        # If no quote items, create item from booking info
        if not quote_items:
            quote_items = [
                {
                    'no': 1,
                    'name': 'Tour Package - {}'.format(booking.booking_type or 'Package Tour'),
                    'quantity': booking.total_pax or 1,
                    'price': booking.total_amount or 0,
                    'amount': booking.total_amount or 0,
                    'is_negative': False
                }
            ]
        
        # Prepare data for template
        quote_data = {
            'booking': booking,
            'receipt_number': receipt_number,
            'receipt_date': datetime.now().strftime('%d/%m/%Y'),
            'company_name': 'DHAKUL CHAN TRAVEL SERVICE (THAILAND) CO.,LTD.',
            'company_address': '710, 716, 704, 706 Prachautthit Road, Samsennok, Huai Kwang, Bangkok 10310',
            'company_phone': '+662 2744218 | +662 0266525',
            'company_email': 'info@dhakulchan.net',
            'total_amount': booking.total_amount or 0,
            'items': quote_items,
            'quote': getattr(booking, 'quote', None),
            'quote_number': getattr(booking, 'quote_number', 'QT{}'.format(booking.id)),
            'customer': getattr(booking, 'customer', None),
            'customer_name': booking.customer_name or 'N/A',
            'customer_phone': getattr(booking, 'customer_phone', ''),
            'generation_date': datetime.now().strftime('%d/%m/%Y'),
            'created_by': 'admin',
            'due_date': datetime.now().strftime('%d/%m/%Y'),
            'time_limit': datetime.now().strftime('%d/%m/%Y'),
            'name_list': getattr(booking, 'guest_list', ''),
            'guest_list_data': getattr(booking, 'guest_list', ''),
            'flight_info': getattr(booking, 'flight_info', ''),
            'voucher_title': 'QUOTE'
        }
        
        # Render HTML template
        html_content = render_template('pdf/quote_template_final_v2_pre-receipt.html', **quote_data)
        
        if format.lower() == 'pdf':
            return generate_pdf_response(html_content, 'quote-booking-{}.pdf'.format(booking_id))
        elif format.lower() == 'png':
            return generate_png_response(html_content, 'quote-booking-{}.png'.format(booking_id))
        else:
            flash('Invalid format. Please use PDF or PNG.', 'error')
            return redirect(url_for('pre_receipt.view', booking_id=booking_id))
            
    except Exception as e:
        flash('Error generating quote: {}'.format(str(e)), 'error')
        return redirect(url_for('pre_receipt.view', booking_id=booking_id))

@pre_receipt_bp.route('/debug-simple/<int:booking_id>')
def debug_simple_template(booking_id):
    """Debug simple template without login requirement"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        # Simple debug data
        debug_data = {
            'booking': booking,
            'receipt_number': 'PR25110501',
            'receipt_date': '05/11/2025',
            'company_name': 'DHAKUL CHAN TRAVEL SERVICE (THAILAND) CO.,LTD.',
            'company_address': '710, 716, 704, 706 Prachautthit Road, Samsennok, Huai Kwang, Bangkok 10310',
            'company_phone': '+662 2744218 | +662 0266525',
            'company_email': 'info@dhakulchan.net',
            'total_amount': booking.total_amount or 1500.00,
            'items': [
                {
                    'no': 1,
                    'name': 'Tour Package - Test',
                    'quantity': 2,
                    'price': 750.00,
                    'amount': 1500.00,
                    'is_negative': False
                }
            ],
            'quote_number': 'QT25110001',
            'customer': None,
            'customer_name': booking.customer_name or 'Test Customer',
            'customer_phone': '+66123456789',
            'generation_date': '05/11/2025',
            'created_by': 'admin',
            'due_date': '20/11/2025',
            'time_limit': '20/11/2025',
            'name_list': 'Test Guest 1\nTest Guest 2',
            'guest_list_data': 'Test Guest 1\nTest Guest 2',
            'flight_info': 'TG123 - 10:00 AM',
            'voucher_title': 'QUOTE'
        }
        
        # Render HTML template for testing
        html_content = render_template('pdf/quote_template_final_v2_pre-receipt.html', **debug_data)
        
        # Return HTML for browser preview
        from flask import Response
        return Response(html_content, mimetype='text/html')
        
    except Exception as e:
        return 'Error: {}'.format(str(e))

@pre_receipt_bp.route('/debug-pdf/<int:booking_id>')
def debug_pdf_generation(booking_id):
    """Debug PDF generation without login requirement"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        # Simple debug data
        debug_data = {
            'booking': booking,
            'receipt_number': 'PR25110501',
            'receipt_date': '05/11/2025',
            'company_name': 'DHAKUL CHAN TRAVEL SERVICE (THAILAND) CO.,LTD.',
            'company_address': '710, 716, 704, 706 Prachautthit Road, Samsennok, Huai Kwang, Bangkok 10310',
            'company_phone': '+662 2744218 | +662 0266525',
            'company_email': 'info@dhakulchan.net',
            'total_amount': booking.total_amount or 1500.00,
            'items': [
                {
                    'no': 1,
                    'name': 'Tour Package - {}'.format(booking.booking_type or 'Test'),
                    'quantity': booking.total_pax or 2,
                    'price': (booking.total_amount or 1500.00) / (booking.total_pax or 2),
                    'amount': booking.total_amount or 1500.00,
                    'is_negative': False
                }
            ],
            'quote_number': getattr(booking, 'quote_number', 'QT25110001'),
            'customer': getattr(booking, 'customer', None),
            'customer_name': booking.customer_name or 'Test Customer',
            'customer_phone': getattr(booking, 'customer_phone', '+66123456789'),
            'generation_date': '05/11/2025',
            'created_by': 'admin',
            'due_date': '20/11/2025',
            'time_limit': '20/11/2025',
            'name_list': getattr(booking, 'guest_list', 'Test Guest 1\nTest Guest 2'),
            'guest_list_data': getattr(booking, 'guest_list', 'Test Guest 1\nTest Guest 2'),
            'flight_info': getattr(booking, 'flight_info', 'TG123 - 10:00 AM'),
            'voucher_title': 'QUOTE'
        }
        
        # Render HTML template
        html_content = render_template('pdf/quote_template_final_v2_pre-receipt.html', **debug_data)
        
        # Generate PDF
        return generate_pdf_response(html_content, 'debug-quote-booking-{}.pdf'.format(booking_id))
        
    except Exception as e:
        return 'PDF Error: {}'.format(str(e))

@pre_receipt_bp.route('/debug-main-function/<int:booking_id>')
def debug_main_function(booking_id):
    """Debug main function logic without login requirement"""
    def safe_float(value, default=0.0):
        """Safely convert value to float"""
        try:
            if value is None:
                return default
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def safe_int(value, default=1):
        """Safely convert value to int"""
        try:
            if value is None:
                return default
            return int(value)
        except (ValueError, TypeError):
            return default
    
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        # Generate random receipt number if not exists
        if not hasattr(booking, 'receipt_number') or not booking.receipt_number:
            current_date = datetime.now().strftime('%y%m%d')
            random_num = str(random.randint(1000, 9999))
            receipt_number = "PR{}{}".format(current_date, random_num)
        else:
            receipt_number = booking.receipt_number
            
        # Get real booking items/products if available (safer version)
        booking_items = []
        
        # Try to get items from booking products/services with safe attribute access
        try:
            if hasattr(booking, 'products') and booking.products:
                # Check if products is iterable and not a string
                if hasattr(booking.products, '__iter__') and not isinstance(booking.products, str):
                    for idx, product in enumerate(booking.products, 1):
                        # Use getattr for safe attribute access with safe numeric conversion
                        quantity = safe_int(getattr(product, 'quantity', 1))
                        price = safe_float(getattr(product, 'price', 0))
                        booking_items.append({
                            'no': idx,
                            'name': getattr(product, 'name', 'Tour Package'),
                            'quantity': quantity,
                            'price': price,
                            'amount': quantity * price,
                            'is_negative': getattr(product, 'is_negative', False)
                        })
        except Exception as e:
            print(f"Warning: Error processing booking products: {e}")
        
        # If no products, create fallback item from booking info
        if not booking_items:
            total_amount = safe_float(getattr(booking, 'total_amount', 0))
            total_pax = safe_int(getattr(booking, 'total_pax', 1))
            booking_items = [
                {
                    'no': 1,
                    'name': 'Tour Package - {}'.format(getattr(booking, 'booking_type', 'Package Tour')),
                    'quantity': total_pax,
                    'price': total_amount / max(total_pax, 1),
                    'amount': total_amount,
                    'is_negative': False
                }
            ]

        # Prepare data for template with safe conversions
        receipt_data = {
            'booking': booking,
            'receipt_number': receipt_number,
            'receipt_date': datetime.now().strftime('%d/%m/%Y'),
            'company_name': 'DHAKUL CHAN TRAVEL SERVICE (THAILAND) CO.,LTD.',
            'company_address': '710, 716, 704, 706 Prachautthit Road, Samsennok, Huai Kwang, Bangkok 10310',
            'company_phone': '+662 2744218 | +662 0266525',
            'company_email': 'info@dhakulchan.net',
            'total_amount': safe_float(getattr(booking, 'total_amount', 0)),
            'items': booking_items,
            'quote': getattr(booking, 'quote', None),
            'quote_number': getattr(booking, 'quote_number', 'QT{}'.format(booking.id)),
            'customer': getattr(booking, 'customer', None),
            'customer_name': getattr(booking, 'customer_name', 'N/A'),
            'customer_phone': getattr(booking, 'customer_phone', ''),
            'generation_date': datetime.now().strftime('%d/%m/%Y'),
            'created_by': 'admin',
            'due_date': datetime.now().strftime('%d/%m/%Y'),
            'time_limit': datetime.now().strftime('%d/%m/%Y'),
            'name_list': getattr(booking, 'guest_list', ''),
            'guest_list_data': getattr(booking, 'guest_list', ''),
            'flight_info': getattr(booking, 'flight_info', ''),
            'voucher_title': 'PRE-RECEIPT'
        }
        
        # Render HTML template
        html_content = render_template('pdf/quote_template_final_v2_pre-receipt.html', **receipt_data)
        
        # Generate PDF
        return generate_pdf_response(html_content, 'debug-main-function-booking-{}.pdf'.format(booking_id))
        
    except Exception as e:
        return 'Debug Main Function Error: {}'.format(str(e))

@pre_receipt_bp.route('/debug-safe-pdf/<int:booking_id>')
def debug_safe_pdf_generation(booking_id):
    """Debug safe PDF generation without product attribute errors"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        # Simple debug data with safe fallback
        debug_data = {
            'booking': booking,
            'receipt_number': 'PR25110501',
            'receipt_date': '05/11/2025',
            'company_name': 'DHAKUL CHAN TRAVEL SERVICE (THAILAND) CO.,LTD.',
            'company_address': '710, 716, 704, 706 Prachautthit Road, Samsennok, Huai Kwang, Bangkok 10310',
            'company_phone': '+662 2744218 | +662 0266525',
            'company_email': 'info@dhakulchan.net',
            'total_amount': booking.total_amount or 1500.00,
            'items': [
                {
                    'no': 1,
                    'name': 'Tour Package - {}'.format(getattr(booking, 'booking_type', 'Test')),
                    'quantity': getattr(booking, 'total_pax', 2),
                    'price': (getattr(booking, 'total_amount', 1500.00)) / (getattr(booking, 'total_pax', 2)),
                    'amount': getattr(booking, 'total_amount', 1500.00),
                    'is_negative': False
                }
            ],
            'quote_number': getattr(booking, 'quote_number', 'QT25110001'),
            'customer': getattr(booking, 'customer', None),
            'customer_name': getattr(booking, 'customer_name', 'Test Customer'),
            'customer_phone': getattr(booking, 'customer_phone', '+66123456789'),
            'generation_date': '05/11/2025',
            'created_by': 'admin',
            'due_date': '20/11/2025',
            'time_limit': '20/11/2025',
            'name_list': getattr(booking, 'guest_list', 'Test Guest 1\nTest Guest 2'),
            'guest_list_data': getattr(booking, 'guest_list', 'Test Guest 1\nTest Guest 2'),
            'flight_info': getattr(booking, 'flight_info', 'TG123 - 10:00 AM'),
            'voucher_title': 'PRE-RECEIPT'
        }
        
        # Render HTML template
        html_content = render_template('pdf/quote_template_final_v2_pre-receipt.html', **debug_data)
        
        # Generate PDF
        return generate_pdf_response(html_content, 'safe-pre-receipt-booking-{}.pdf'.format(booking_id))
        
    except Exception as e:
        return 'Safe PDF Error: {}'.format(str(e))
    """Debug PNG generation without login requirement"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        # Simple debug data (same as PDF)
        debug_data = {
            'booking': booking,
            'receipt_number': 'PR25110501',
            'receipt_date': '05/11/2025',
            'company_name': 'DHAKUL CHAN TRAVEL SERVICE (THAILAND) CO.,LTD.',
            'company_address': '710, 716, 704, 706 Prachautthit Road, Samsennok, Huai Kwang, Bangkok 10310',
            'company_phone': '+662 2744218 | +662 0266525',
            'company_email': 'info@dhakulchan.net',
            'total_amount': booking.total_amount or 1500.00,
            'items': [
                {
                    'no': 1,
                    'name': 'Tour Package - {}'.format(booking.booking_type or 'Test'),
                    'quantity': booking.total_pax or 2,
                    'price': (booking.total_amount or 1500.00) / (booking.total_pax or 2),
                    'amount': booking.total_amount or 1500.00,
                    'is_negative': False
                }
            ],
            'quote_number': getattr(booking, 'quote_number', 'QT25110001'),
            'customer': getattr(booking, 'customer', None),
            'customer_name': booking.customer_name or 'Test Customer',
            'customer_phone': getattr(booking, 'customer_phone', '+66123456789'),
            'generation_date': '05/11/2025',
            'created_by': 'admin',
            'due_date': '20/11/2025',
            'time_limit': '20/11/2025',
            'name_list': getattr(booking, 'guest_list', 'Test Guest 1\nTest Guest 2'),
            'guest_list_data': getattr(booking, 'guest_list', 'Test Guest 1\nTest Guest 2'),
            'flight_info': getattr(booking, 'flight_info', 'TG123 - 10:00 AM'),
            'voucher_title': 'QUOTE'
        }
        
        # Render HTML template
        html_content = render_template('pdf/quote_template_final_v2_pre-receipt.html', **debug_data)
        
        # Generate PNG
        return generate_png_response(html_content, 'debug-quote-booking-{}.png'.format(booking_id))
        
    except Exception as e:
        return 'PNG Error: {}'.format(str(e))