"""
Enhanced Quote routes for social media sharing and PDF/PNG generation
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, abort, send_file, current_app, Response
from flask_login import login_required, current_user
from models.booking import Booking
from models.quote import Quote, QuoteLineItem
from models.user import User
from extensions import db
from services.quote_service import QuoteService
import logging
import os
from datetime import timedelta, datetime
import tempfile
try:
    import fitz  # PyMuPDF for PNG conversion
    PDF_TO_PNG_AVAILABLE = True
except ImportError:
    PDF_TO_PNG_AVAILABLE = False
    fitz = None

quote_bp = Blueprint('quote', __name__, url_prefix='/quote')
logger = logging.getLogger(__name__)

@quote_bp.route('/')
@login_required
def list_quotes():
    """List all bookings with status='quoted' instead of listing quotes"""
    try:
        # Get bookings with status 'quoted' instead of quotes
        from models.booking import Booking
        from models.customer import Customer
        
        bookings = Booking.query.filter_by(status='quoted').order_by(Booking.created_at.desc()).all()
        
        # Calculate total amount safely
        total_amount = 0
        for booking in bookings:
            if booking.total_amount:
                try:
                    total_amount += float(booking.total_amount)
                except (ValueError, TypeError):
                    pass  # Skip invalid amounts
        
        return render_template('quote/list_bookings.html', bookings=bookings, total_quoted_amount=total_amount)
    except Exception as e:
        import traceback
        logger.error(f"Error listing quoted bookings: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        flash(f'Error loading quoted bookings: {str(e)}')
        return redirect(url_for('dashboard.index'))

@quote_bp.route('/<int:quote_id>')
@login_required  
def view_quote(quote_id):
    """View quote details (authenticated users only)"""
    try:
        # Use raw SQL to get quote data with MariaDB connection
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
            SELECT id, quote_number, booking_id, quote_date, valid_until, status,
                   title, description, subtotal, tax_rate, tax_amount, discount_amount, 
                   total_amount, currency, terms_conditions, notes, converted_to_invoice,
                   share_token, is_public, created_at, updated_at
            FROM quotes 
            WHERE id = ?
        """, (quote_id,))
        
        quote_row = cursor.fetchone()
        conn.close()
        
        if not quote_row:
            abort(404)
            
        # Get booking using SQLAlchemy (simpler fields)
        from models.booking import Booking
        booking = Booking.query.get_or_404(quote_row[2])  # booking_id
        
        # Check permissions
        if not current_user.can_view_financial_data():
            # Staff can only view quotes for bookings they created
            if current_user.role == 'Staff' and booking.created_by != current_user.id:
                abort(403)
        
        # Create quote dict for template with proper datetime conversion
        from datetime import datetime
        
        # Parse datetime strings
        quote_date = None
        valid_until = None
        created_at = None
        updated_at = None
        
        if quote_row[3]:  # quote_date
            try:
                quote_date = datetime.fromisoformat(quote_row[3].replace('Z', '+00:00'))
            except:
                quote_date = quote_row[3]
                
        if quote_row[4]:  # valid_until
            try:
                valid_until = datetime.fromisoformat(quote_row[4].replace('Z', '+00:00'))
            except:
                valid_until = quote_row[4]
                
        if quote_row[19]:  # created_at
            try:
                created_at = datetime.fromisoformat(quote_row[19].replace('Z', '+00:00'))
            except:
                created_at = quote_row[19]
                
        if quote_row[20]:  # updated_at
            try:
                updated_at = datetime.fromisoformat(quote_row[20].replace('Z', '+00:00'))
            except:
                updated_at = quote_row[20]
        
        quote_dict = {
            'id': quote_row[0],
            'quote_number': quote_row[1],
            'booking_id': quote_row[2],
            'quote_date': quote_date,
            'valid_until': valid_until,
            'status': quote_row[5],
            'title': quote_row[6],
            'description': quote_row[7],
            'subtotal': quote_row[8],
            'tax_rate': quote_row[9],
            'tax_amount': quote_row[10],
            'discount_amount': quote_row[11],
            'total_amount': quote_row[12],
            'currency': quote_row[13],
            'terms_conditions': quote_row[14],
            'notes': quote_row[15],
            'converted_to_invoice': quote_row[16],
            'share_token': quote_row[17],
            'is_public': quote_row[18],
            'created_at': created_at,
            'updated_at': updated_at,
            'booking': booking
        }
        
        return render_template('quote/enhanced_view.html', 
                             quote=quote_dict, 
                             booking=booking)
    except Exception as e:
        logger.error(f"Error viewing quote {quote_id}: {str(e)}")
        flash('Error loading quote')
        return redirect(url_for('quote.list_quotes'))

@quote_bp.route('/booking/<int:booking_id>/create', methods=['GET', 'POST'])
@login_required
def create_quote_from_booking(booking_id):
    """Create quote from booking - Enhanced workflow with PDF/PNG/Share"""
    try:
        from services.quote_pdf_generator import QuotePDFGenerator
        from services.public_share_service import PublicShareService
        from models.quote import QuoteLineItem
        from utils.datetime_utils import naive_utc_now
        
        booking = Booking.query.get_or_404(booking_id)
        
        if request.method == 'POST':
            # Create new quote
            quote = Quote(
                booking_id=booking.id,
                title=request.form.get('title', f'Travel Quote for {booking.booking_reference}'),
                description=request.form.get('description', ''),
                quote_date=naive_utc_now().date(),
                valid_until=naive_utc_now().date() + timedelta(days=30),
                terms_conditions=request.form.get('terms_conditions', ''),
                notes=request.form.get('notes', '')
            )
            
            db.session.add(quote)
            db.session.flush()  # Get quote ID
            
            # Add line items
            line_items_data = request.form.getlist('line_items')
            total_amount = 0
            
            for i, description in enumerate(request.form.getlist('descriptions')):
                if description.strip():
                    quantity = float(request.form.getlist('quantities')[i] or 1)
                    unit_price = float(request.form.getlist('unit_prices')[i] or 0)
                    
                    line_item = QuoteLineItem(
                        quote_id=quote.id,
                        description=description,
                        quantity=quantity,
                        unit_price=unit_price,
                        sort_order=i
                    )
                    db.session.add(line_item)
                    total_amount += line_item.total_amount
            
            # Calculate totals
            quote.subtotal = total_amount
            quote.tax_rate = float(request.form.get('tax_rate', 7.0))
            quote.tax_amount = (quote.subtotal * quote.tax_rate / 100) if quote.tax_rate else 0
            quote.discount_amount = float(request.form.get('discount_amount', 0))
            quote.total_amount = quote.subtotal + quote.tax_amount - quote.discount_amount
            
            db.session.commit()
            
            # Generate PDF and PNG
            pdf_generator = QuotePDFGenerator()
            pdf_path, png_path = pdf_generator.generate_quote_pdf(quote, booking, booking.customer)
            
            quote.pdf_path = pdf_path
            quote.png_path = png_path
            
            # Create sharing package
            share_service = PublicShareService()
            document_data = {
                'customer_name': booking.customer.full_name,
                'total_amount': float(quote.total_amount)
            }
            
            sharing_package = share_service.create_shareable_content('quote', quote, document_data)
            
            # Update booking workflow status
            booking.status = Booking.STATUS_QUOTED
            booking.quoted_at = naive_utc_now()
            
            db.session.commit()
            
            flash(f'✅ Quote {quote.quote_number} created successfully with sharing capabilities!')
            logger.info(f"Quote {quote.quote_number} created for booking {booking.booking_reference}")
            
            return redirect(url_for('quote.view_quote', quote_id=quote.id))
        
        # GET request - show form
        return render_template('quote/create.html', booking=booking)
        
    except Exception as e:
        logger.error(f"Error creating quote for booking {booking_id}: {str(e)}")
        db.session.rollback()
        flash('❌ Error creating quote')
        return redirect(url_for('booking.view_booking', booking_id=booking_id))
        booking = Booking.query.get_or_404(booking_id)
        
        if request.method == 'POST':
            # Create quote using service
            quote_service = QuoteService()
            quote = quote_service.create_quote_from_booking(booking)
            
            flash(f'Quote {quote.quote_number} created successfully!')
            return redirect(url_for('quote.view_quote', quote_id=quote.id))
            
        return render_template('quote/create.html', booking=booking)
        
    except Exception as e:
        logger.error(f"Error creating quote from booking {booking_id}: {str(e)}")
        flash(f'Error creating quote: {str(e)}')
        return redirect(url_for('booking.view_booking', booking_id=booking_id))

@quote_bp.route('/<int:quote_id>/download/pdf')
@login_required
def download_quote_pdf(quote_id):
    """Download quote PDF using new QuoteService"""
    try:
        quote = Quote.query.get_or_404(quote_id)
        
        # Use new QuoteService for PDF generation
        quote_service = QuoteService()
        pdf_result = quote_service.generate_quote_pdf(quote)
        
        if isinstance(pdf_result, tuple) and len(pdf_result) == 2:
            pdf_bytes, filename = pdf_result
            
            # Return PDF as direct response
            return Response(
                pdf_bytes,
                mimetype='application/pdf',
                headers={
                    'Content-Disposition': f'inline; filename="Quote_{quote.booking.booking_reference}_{quote.quote_number}.pdf"',
                    'Content-Type': 'application/pdf'
                }
            )
        else:
            # Fallback: treat as filename and serve from directory
            return send_from_directory(
                quote_service.output_dir,
                pdf_result,
                as_attachment=False,
                download_name=f'Quote_{quote.booking.booking_reference}_{quote.quote_number}.pdf'
            )
        
    except Exception as e:
        logger.error(f"Error downloading quote PDF {quote_id}: {str(e)}")
        flash('❌ Error downloading PDF')
        return redirect(url_for('quote.view_quote', quote_id=quote_id))

@quote_bp.route('/<int:quote_id>/download/png')
@login_required  
def download_quote_png(quote_id):
    """Download quote PNG"""
    try:
        quote = Quote.query.get_or_404(quote_id)
        
        if not quote.png_path or not os.path.exists(quote.png_path):
            # Generate PNG if not exists using WeasyPrint
            from services.quote_weasyprint_generator import QuoteWeasyPrintGenerator
            pdf_generator = QuoteWeasyPrintGenerator()
            pdf_path = pdf_generator.generate_quote_pdf(quote.booking)
            png_path = pdf_generator.generate_quote_png(quote.booking)
            
            quote.pdf_path = pdf_path
            quote.png_path = png_path
            db.session.commit()
        
        directory = os.path.dirname(quote.png_path)
        filename = os.path.basename(quote.png_path)
        
        return send_from_directory(directory, filename, as_attachment=True)
        
    except Exception as e:
        logger.error(f"Error downloading quote PNG {quote_id}: {str(e)}")
        flash('❌ Error downloading PNG')
        return redirect(url_for('quote.view_quote', quote_id=quote_id))

@quote_bp.route('/<int:quote_id>/share')
@login_required
def share_quote(quote_id):
    """Get quote sharing information"""
    try:
        quote = Quote.query.get_or_404(quote_id)
        
        # Ensure sharing is set up
        if not quote.share_token or not quote.public_url:
            from services.public_share_service import PublicShareService
            share_service = PublicShareService()
            
            document_data = {
                'customer_name': quote.booking.customer.full_name,
                'total_amount': float(quote.total_amount)
            }
            
            sharing_package = share_service.create_shareable_content('quote', quote, document_data)
        
        return jsonify({
            'success': True,
            'quote_number': quote.quote_number,
            'share_token': quote.share_token,
            'public_url': quote.public_url,
            'social_urls': {
                'facebook': f"https://www.facebook.com/sharer/sharer.php?u={quote.public_url}",
                'twitter': f"https://twitter.com/intent/tweet?text=Check%20out%20my%20travel%20quote%20{quote.quote_number}&url={quote.public_url}",
                'whatsapp': f"https://api.whatsapp.com/send?text=Check%20out%20my%20travel%20quote%20{quote.quote_number}%20{quote.public_url}",
                'line': f"https://social-plugins.line.me/lineit/share?url={quote.public_url}"
            }
        })
        
    except Exception as e:
        logger.error(f"Error sharing quote {quote_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@quote_bp.route('/<int:quote_id>/convert-to-invoice', methods=['POST'])
@login_required
def convert_quote_to_invoice(quote_id):
    """Convert quote to invoice"""
    try:
        from models.invoice import Invoice, InvoiceLineItem
        from utils.datetime_utils import naive_utc_now
        
        quote = Quote.query.get_or_404(quote_id)
        
        if quote.converted_to_invoice:
            flash('❌ Quote already converted to invoice')
            return redirect(url_for('quote.view_quote', quote_id=quote_id))
        
        # Create invoice from quote
        invoice = Invoice(
            booking_id=quote.booking_id,
            quote_id=quote.id,
            title=quote.title.replace('Quote', 'Invoice'),
            description=quote.description,
            subtotal=quote.subtotal,
            tax_rate=quote.tax_rate,
            tax_amount=quote.tax_amount,
            discount_amount=quote.discount_amount,
            total_amount=quote.total_amount,
            invoice_date=naive_utc_now().date(),
            due_date=naive_utc_now().date() + timedelta(days=30),
            terms_conditions=quote.terms_conditions,
            notes=quote.notes
        )
        
        db.session.add(invoice)
        db.session.flush()
        
        # Copy line items
        for quote_item in quote.line_items:
            invoice_item = InvoiceLineItem(
                invoice_id=invoice.id,
                description=quote_item.description,
                quantity=quote_item.quantity,
                unit_price=quote_item.unit_price,
                sort_order=quote_item.sort_order
            )
            db.session.add(invoice_item)
        
        # Update quote status
        quote.converted_to_invoice = True
        quote.converted_invoice_number = invoice.invoice_number
        
        # Update booking workflow
        quote.booking.status = Booking.STATUS_INVOICED
        quote.booking.invoiced_at = naive_utc_now()
        
        db.session.commit()
        
        flash(f'✅ Quote converted to Invoice {invoice.invoice_number}')
        logger.info(f"Quote {quote.quote_number} converted to invoice {invoice.invoice_number}")
        
        return redirect(url_for('invoice.view_invoice', invoice_id=invoice.id))
        
    except Exception as e:
        logger.error(f"Error converting quote {quote_id} to invoice: {str(e)}")
        db.session.rollback()
        flash('❌ Error converting quote to invoice')
        return redirect(url_for('quote.view_quote', quote_id=quote_id))

@quote_bp.route('/<int:quote_id>/accept', methods=['POST'])
@login_required
def accept_quote(quote_id):
    """Accept quote - enables conversion to invoice"""
    try:
        quote = Quote.query.get_or_404(quote_id)
        
        if quote.is_expired:
            flash('Cannot accept expired quote')
            return redirect(url_for('quote.view_quote', quote_id=quote_id))
        
        quote.status = 'accepted'
        db.session.commit()
        
        logger.info(f"Quote {quote.quote_number} accepted")
        flash(f'Quote {quote.quote_number} accepted! Ready for invoice conversion.')
        return redirect(url_for('quote.view_quote', quote_id=quote_id))
        
    except Exception as e:
        logger.error(f"Error accepting quote {quote_id}: {str(e)}")
        flash(f'Error accepting quote: {str(e)}')
        return redirect(url_for('quote.view_quote', quote_id=quote_id))

@quote_bp.route('/<int:quote_id>/pdf')
@login_required
def generate_quote_pdf(quote_id):
    """Generate Quote PDF using TourVoucherGeneratorV2 format"""
    try:
        quote = Quote.query.get_or_404(quote_id)
        
        quote_service = QuoteService()
        pdf_result = quote_service.generate_quote_pdf(quote)
        
        # Handle tuple return from QuoteService
        if isinstance(pdf_result, tuple) and len(pdf_result) == 2:
            pdf_bytes, filename = pdf_result
            
            # Return PDF as direct response
            return Response(
                pdf_bytes,
                mimetype='application/pdf',
                headers={
                    'Content-Disposition': f'inline; filename="quote_{quote.quote_number}.pdf"',
                    'Content-Type': 'application/pdf'
                }
            )
        else:
            # Fallback: treat as filename and serve from directory
            return send_from_directory(
                quote_service.output_dir,
                pdf_result,
                as_attachment=False,
                download_name=f'quote_{quote.quote_number}.pdf'
            )
        
    except Exception as e:
        logger.error(f"Error generating quote PDF {quote_id}: {str(e)}")
        flash(f'Error generating PDF: {str(e)}')
        return redirect(url_for('quote.view_quote', quote_id=quote_id))

@quote_bp.route('/<int:quote_id>/png')
@login_required
def generate_quote_png(quote_id):
    """Generate Quote PNG using TourVoucherGeneratorV2 format"""
    try:
        quote = Quote.query.get_or_404(quote_id)
        
        # Generate PDF first
        quote_service = QuoteService()
        pdf_file = quote_service.generate_quote_pdf(quote)
        
        # Convert to PNG
        pdf_path = os.path.join(quote_service.output_dir, pdf_file)
        pdf_doc = fitz.open(pdf_path)
        page = pdf_doc[0]
        
        mat = fitz.Matrix(2, 2)  # High quality
        pix = page.get_pixmap(matrix=mat)
        
        png_filename = pdf_file.replace('.pdf', '.png')
        png_path = os.path.join(quote_service.output_dir, png_filename)
        pix.save(png_path)
        
        pdf_doc.close()
        
        return send_from_directory(
            quote_service.output_dir,
            png_filename,
            as_attachment=True,
            download_name=f'quote_{quote.quote_number}.png'
        )
        
    except Exception as e:
        logger.error(f"Error generating quote PNG {quote_id}: {str(e)}")
        flash(f'Error generating PNG: {str(e)}')
        return redirect(url_for('quote.view_quote', quote_id=quote_id))

# Enhanced Routes for Social Media Sharing and Public Access

@quote_bp.route('/public/<share_token>')
def public_view(share_token):
    """Public quote view using share token"""
    try:
        # Simple database query with MariaDB connection
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
        
        # Get quote by share token
        cursor.execute("SELECT * FROM quotes WHERE share_token = %s AND is_public = 1", (share_token,))
        quote_row = cursor.fetchone()
        
        if not quote_row:
            conn.close()
            abort(404)
            
        # Get column names
        columns = [description[0] for description in cursor.description]
        quote_dict = dict(zip(columns, quote_row))
        
        # Get booking info
        cursor.execute("SELECT * FROM bookings WHERE id = ?", (quote_dict['booking_id'],))
        booking_row = cursor.fetchone()
        booking_columns = [description[0] for description in cursor.description]
        booking_dict = dict(zip(booking_columns, booking_row))
        
        conn.close()
        
        # Return simple HTML for now
        return f"""
        <h1>Quote {quote_dict['quote_number']}</h1>
        <p>Booking ID: {quote_dict['booking_id']}</p>
        <p>Total: {quote_dict['total_amount']} {quote_dict['currency']}</p>
        <p>Status: {quote_dict['status']}</p>
        <p>Valid Until: {quote_dict['valid_until']}</p>
        """
        
    except Exception as e:
        current_app.logger.error(f"Error viewing public quote {share_token}: {str(e)}")
        return f"Error: {str(e)}", 500
    
@quote_bp.route('/public-test/<share_token>')  
def public_view_full(share_token):
    """Public quote view using share token - FULL VERSION"""
    current_app.logger.info(f"🔍 Public quote view requested for token: {share_token}")
    try:
        quote = Quote.query.filter_by(share_token=share_token).first_or_404()
        current_app.logger.info(f"✅ Quote found: {quote.id} - {quote.quote_number}")
        
        # Check if public access is allowed and not expired
        if not quote.is_public:
            current_app.logger.warning(f"❌ Quote {quote.id} is not public")
            abort(404)
        
        if quote.public_expiry and datetime.utcnow() > quote.public_expiry:
            current_app.logger.warning(f"❌ Quote {quote.id} has expired")
            abort(404)
        
        current_app.logger.info(f"✅ Public access allowed for quote {quote.id}")
        
        # Track public view
        quote.increment_view()
        db.session.commit()
        
        booking = quote.booking

        # Use public template (without admin features)
        return render_template('quote/public_view.html', 
                             quote=quote, 
                             booking=booking)
    except Exception as e:
        current_app.logger.error(f"Error viewing public quote {share_token}: {str(e)}")
        abort(404)@quote_bp.route('/<int:quote_id>/track-view', methods=['POST'])
def track_view(quote_id):
    """Track quote view"""
    try:
        quote = Quote.query.get_or_404(quote_id)
        
        # Only track authenticated views to avoid spam
        if current_user.is_authenticated:
            quote.increment_view()
            db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error tracking view for quote {quote_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@quote_bp.route('/<int:quote_id>/track-share', methods=['POST'])
def track_share(quote_id):
    """Track quote share"""
    try:
        quote = Quote.query.get_or_404(quote_id)
        platform = request.json.get('platform') if request.json else request.form.get('platform')
        
        quote.increment_share(platform)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error tracking share for quote {quote_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@quote_bp.route('/<int:quote_id>/send', methods=['POST'])
@login_required
def send_quote(quote_id):
    """Send quote to customer"""
    try:
        quote = Quote.query.get_or_404(quote_id)
        
        # Check permissions
        if not current_user.can_manage_quotes():
            abort(403)
        
        # Mark quote as sent and enable public access
        quote.mark_as_sent()
        db.session.commit()
        
        # Here you would integrate with email service
        # send_email_notification(quote)
        
        return jsonify({
            'success': True,
            'message': 'Quote sent successfully',
            'public_url': quote.get_public_url(request.host_url)
        })
        
    except Exception as e:
        logger.error(f"Error sending quote {quote_id}: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@quote_bp.route('/<int:quote_id>/convert-to-invoice', methods=['POST'])
@login_required
def convert_to_invoice(quote_id):
    """Convert quote to invoice"""
    try:
        quote = Quote.query.get_or_404(quote_id)
        
        # Check permissions
        if not current_user.can_manage_quotes():
            abort(403)
        
        # Check if quote can be converted
        if not quote.can_convert_to_invoice():
            return jsonify({
                'success': False,
                'error': 'Quote cannot be converted to invoice'
            }), 400
        
        # Update booking workflow
        booking = quote.booking
        
        # Apply quote to invoice in booking workflow
        if booking.can_apply_to_invoice():
            booking.apply_to_invoice()
            
            # Mark quote as converted
            quote.mark_as_converted()
            quote.converted_invoice_number = booking.invoice_number
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Quote converted to invoice successfully',
                'redirect_url': url_for('booking.view', id=booking.id)
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Booking is not ready for invoice'
            }), 400
            
    except Exception as e:
        logger.error(f"Error converting quote {quote_id} to invoice: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@quote_bp.route('/<int:quote_id>/extend-expiry', methods=['POST'])
@login_required
def extend_expiry(quote_id):
    """Extend quote expiry date"""
    try:
        quote = Quote.query.get_or_404(quote_id)
        
        # Check permissions
        if not current_user.can_manage_quotes():
            abort(403)
        
        days = request.json.get('days', 30) if request.json else int(request.form.get('days', 30))
        
        quote.extend_expiry(days)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Quote expiry extended by {days} days',
            'new_expiry': quote.valid_until.isoformat() if quote.valid_until else None
        })
        
    except Exception as e:
        logger.error(f"Error extending expiry for quote {quote_id}: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@quote_bp.route('/<int:quote_id>/toggle-public-access', methods=['POST'])
@login_required
def toggle_public_access(quote_id):
    """Toggle public access to quote"""
    try:
        quote = Quote.query.get_or_404(quote_id)
        
        # Check permissions
        if not current_user.can_manage_quotes():
            abort(403)
        
        if quote.is_public:
            quote.revoke_public_access()
            message = 'Public access revoked'
        else:
            days = request.json.get('days', 30) if request.json else int(request.form.get('days', 30))
            quote.grant_public_access(days)
            message = f'Public access granted for {days} days'
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': message,
            'is_public': quote.is_public,
            'public_url': quote.get_public_url(request.host_url) if quote.is_public else None
        })
        
    except Exception as e:
        logger.error(f"Error toggling public access for quote {quote_id}: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@quote_bp.route('/<int:quote_id>/share-legacy')
@login_required
def share_quote_legacy(quote_id):
    """Share quote with multi-platform support - Legacy version"""
    try:
        quote = Quote.query.get_or_404(quote_id)
        
        # Generate share URLs
        share_data = {
            'quote': quote,
            'pdf_url': url_for('quote.generate_quote_pdf', quote_id=quote.id, _external=True),
            'png_url': url_for('quote.generate_quote_png', quote_id=quote.id, _external=True),
            'view_url': url_for('quote.view_quote', quote_id=quote.id, _external=True),
            'platforms': ['whatsapp', 'line', 'facebook', 'email', 'telegram', 'twitter']
        }
        
        return render_template('quote/share.html', **share_data)
        
    except Exception as e:
        logger.error(f"Error sharing quote {quote_id}: {str(e)}")
        flash('Error generating share links')
        return redirect(url_for('quote.view_quote', quote_id=quote_id))

@quote_bp.route('/api/<int:quote_id>')
@login_required
def quote_api(quote_id):
    """Quote API endpoint"""
    try:
        quote = Quote.query.get_or_404(quote_id)
        return jsonify(quote.to_dict())
    except Exception as e:
        logger.error(f"Error in quote API {quote_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

# API endpoint for getting quote ID by booking ID (for View Quote button)
@quote_bp.route('/api/booking/<int:booking_id>/quote-id')
@login_required
def get_booking_quote_id(booking_id):
    """Get quote ID for a booking - used by View Quote button"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        # Use raw SQL to find the latest quote for this booking with MariaDB
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
        logger.error(f"Error getting quote ID for booking {booking_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500
