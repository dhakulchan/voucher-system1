"""
Invoice routes for enhanced booking workflow with payment tracking and sharing
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, current_app
from flask_login import login_required, current_user
from models.booking import Booking
from models.invoice import Invoice, InvoiceLineItem, InvoicePayment
from models.quote import Quote
from extensions import db
from utils.datetime_utils import naive_utc_now
import logging
import os
from datetime import timedelta
from decimal import Decimal

invoice_bp = Blueprint('invoice', __name__, url_prefix='/invoice')
logger = logging.getLogger(__name__)

@invoice_bp.route('/')
@login_required
def list_invoices():
    """List all invoices"""
    try:
        invoices = Invoice.query.order_by(Invoice.created_at.desc()).all()
        return render_template('invoice/list.html', invoices=invoices)
    except Exception as e:
        logger.error(f"Error listing invoices: {str(e)}")
        flash('Error loading invoices')
        return redirect(url_for('dashboard.index'))

@invoice_bp.route('/<int:invoice_id>')
@login_required  
def view_invoice(invoice_id):
    """View invoice details"""
    try:
        invoice = Invoice.query.get_or_404(invoice_id)
        return render_template('invoice/view.html', invoice=invoice)
    except Exception as e:
        logger.error(f"Error viewing invoice {invoice_id}: {str(e)}")
        flash('Error loading invoice')
        return redirect(url_for('invoice.list_invoices'))

@invoice_bp.route('/booking/<int:booking_id>/create', methods=['GET', 'POST'])
@login_required
def create_invoice_from_booking(booking_id):
    """Create invoice directly from booking (skip quote)"""
    try:
        from services.invoice_pdf_generator import InvoicePDFGenerator
        from services.public_share_service import PublicShareService
        from utils.datetime_utils import naive_utc_now
        
        booking = Booking.query.get_or_404(booking_id)
        
        if request.method == 'POST':
            # Create new invoice
            invoice = Invoice(
                booking_id=booking.id,
                title=request.form.get('title', f'Travel Invoice for {booking.booking_reference}'),
                description=request.form.get('description', ''),
                invoice_date=naive_utc_now().date(),
                due_date=naive_utc_now().date() + timedelta(days=30),
                terms_conditions=request.form.get('terms_conditions', ''),
                notes=request.form.get('notes', '')
            )
            
            db.session.add(invoice)
            db.session.flush()  # Get invoice ID
            
            # Add line items
            total_amount = 0
            
            for i, description in enumerate(request.form.getlist('descriptions')):
                if description.strip():
                    quantity = float(request.form.getlist('quantities')[i] or 1)
                    unit_price = float(request.form.getlist('unit_prices')[i] or 0)
                    
                    line_item = InvoiceLineItem(
                        invoice_id=invoice.id,
                        description=description,
                        quantity=quantity,
                        unit_price=unit_price,
                        sort_order=i
                    )
                    db.session.add(line_item)
                    total_amount += line_item.total_amount
            
            # Calculate totals
            invoice.subtotal = total_amount
            invoice.tax_rate = float(request.form.get('tax_rate', 7.0))
            invoice.tax_amount = (invoice.subtotal * invoice.tax_rate / 100) if invoice.tax_rate else 0
            invoice.discount_amount = float(request.form.get('discount_amount', 0))
            invoice.total_amount = invoice.subtotal + invoice.tax_amount - invoice.discount_amount
            invoice.balance_due = invoice.total_amount
            
            db.session.commit()
            
            # Generate PDF and PNG
            pdf_generator = InvoicePDFGenerator()
            pdf_path, png_path = pdf_generator.generate_invoice_pdf(invoice, booking, booking.customer)
            
            invoice.pdf_path = pdf_path
            invoice.png_path = png_path
            
            # Create sharing package
            share_service = PublicShareService()
            document_data = {
                'customer_name': booking.customer.full_name,
                'total_amount': float(invoice.total_amount)
            }
            
            sharing_package = share_service.create_shareable_content('invoice', invoice, document_data)
            
            # Update booking workflow status
            booking.status = Booking.STATUS_INVOICED
            booking.invoiced_at = naive_utc_now()
            
            db.session.commit()
            
            flash(f'✅ Invoice {invoice.invoice_number} created successfully with sharing capabilities!')
            logger.info(f"Invoice {invoice.invoice_number} created for booking {booking.booking_reference}")
            
            return redirect(url_for('invoice.view_invoice', invoice_id=invoice.id))
        
        # GET request - show form
        return render_template('invoice/create.html', booking=booking)
        
    except Exception as e:
        logger.error(f"Error creating invoice for booking {booking_id}: {str(e)}")
        db.session.rollback()
        flash('❌ Error creating invoice')
        return redirect(url_for('booking.view_booking', booking_id=booking_id))

@invoice_bp.route('/<int:invoice_id>/download/pdf')
@login_required
def download_invoice_pdf(invoice_id):
    """Download invoice PDF"""
    try:
        invoice = Invoice.query.get_or_404(invoice_id)
        
        if not invoice.pdf_path or not os.path.exists(invoice.pdf_path):
            # Generate PDF if not exists
            from services.invoice_pdf_generator import InvoicePDFGenerator
            pdf_generator = InvoicePDFGenerator()
            pdf_path, png_path = pdf_generator.generate_invoice_pdf(invoice, invoice.booking, invoice.booking.customer)
            
            invoice.pdf_path = pdf_path
            invoice.png_path = png_path
            db.session.commit()
        
        directory = os.path.dirname(invoice.pdf_path)
        filename = os.path.basename(invoice.pdf_path)
        
        return send_from_directory(directory, filename, as_attachment=True)
        
    except Exception as e:
        logger.error(f"Error downloading invoice PDF {invoice_id}: {str(e)}")
        flash('❌ Error downloading PDF')
        return redirect(url_for('invoice.view_invoice', invoice_id=invoice_id))

@invoice_bp.route('/<int:invoice_id>/download/png')
@login_required  
def download_invoice_png(invoice_id):
    """Download invoice PNG"""
    try:
        invoice = Invoice.query.get_or_404(invoice_id)
        
        if not invoice.png_path or not os.path.exists(invoice.png_path):
            # Generate PNG if not exists
            from services.invoice_pdf_generator import InvoicePDFGenerator
            pdf_generator = InvoicePDFGenerator()
            pdf_path, png_path = pdf_generator.generate_invoice_pdf(invoice, invoice.booking, invoice.booking.customer)
            
            invoice.pdf_path = pdf_path
            invoice.png_path = png_path
            db.session.commit()
        
        directory = os.path.dirname(invoice.png_path)
        filename = os.path.basename(invoice.png_path)
        
        return send_from_directory(directory, filename, as_attachment=True)
        
    except Exception as e:
        logger.error(f"Error downloading invoice PNG {invoice_id}: {str(e)}")
        flash('❌ Error downloading PNG')
        return redirect(url_for('invoice.view_invoice', invoice_id=invoice_id))

@invoice_bp.route('/<int:invoice_id>/share')
@login_required
def share_invoice(invoice_id):
    """Get invoice sharing information"""
    try:
        invoice = Invoice.query.get_or_404(invoice_id)
        
        # Ensure sharing is set up
        if not invoice.share_token or not invoice.public_url:
            from services.public_share_service import PublicShareService
            share_service = PublicShareService()
            
            document_data = {
                'customer_name': invoice.booking.customer.full_name,
                'total_amount': float(invoice.total_amount)
            }
            
            sharing_package = share_service.create_shareable_content('invoice', invoice, document_data)
        
        return jsonify({
            'success': True,
            'invoice_number': invoice.invoice_number,
            'share_token': invoice.share_token,
            'public_url': invoice.public_url,
            'payment_status': invoice.payment_status,
            'balance_due': float(invoice.balance_due) if invoice.balance_due else 0,
            'social_urls': {
                'facebook': f"https://www.facebook.com/sharer/sharer.php?u={invoice.public_url}",
                'twitter': f"https://twitter.com/intent/tweet?text=My%20travel%20invoice%20{invoice.invoice_number}&url={invoice.public_url}",
                'whatsapp': f"https://api.whatsapp.com/send?text=My%20travel%20invoice%20{invoice.invoice_number}%20{invoice.public_url}",
                'line': f"https://social-plugins.line.me/lineit/share?url={invoice.public_url}"
            }
        })
        
    except Exception as e:
        logger.error(f"Error sharing invoice {invoice_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@invoice_bp.route('/<int:invoice_id>/add-payment', methods=['POST'])
@login_required
def add_payment(invoice_id):
    """Add payment to invoice"""
    try:
        from utils.datetime_utils import naive_utc_now
        
        invoice = Invoice.query.get_or_404(invoice_id)
        
        amount = Decimal(request.form.get('amount', 0))
        payment_method = request.form.get('payment_method', '')
        reference = request.form.get('reference', '')
        payment_date_str = request.form.get('payment_date')
        
        if payment_date_str:
            from datetime import datetime
            payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d').date()
        else:
            payment_date = naive_utc_now().date()
        
        if amount <= 0:
            flash('❌ Payment amount must be greater than 0')
            return redirect(url_for('invoice.view_invoice', invoice_id=invoice_id))
        
        if amount > invoice.balance_due:
            flash('❌ Payment amount cannot exceed balance due')
            return redirect(url_for('invoice.view_invoice', invoice_id=invoice_id))
        
        # Add payment using invoice method
        payment = invoice.add_payment(
            amount=amount,
            payment_method=payment_method,
            reference=reference,
            payment_date=payment_date
        )
        
        # Update booking status if fully paid - use mark_as_paid() to trigger activity logging
        if invoice.payment_status == 'paid':
            if hasattr(invoice.booking, 'mark_as_paid'):
                invoice.booking.mark_as_paid()
            else:
                invoice.booking.status = Booking.STATUS_PAID
            invoice.booking.paid_at = naive_utc_now()
            invoice.booking.is_paid = True
            invoice.booking.invoice_paid_date = payment_date
            
            # Update Invoice Ninja integration fields
            invoice.booking.invoice_amount = invoice.total_amount
            
            db.session.commit()
            
            flash(f'✅ Payment recorded! Invoice fully paid. Booking ready for voucher generation.')
        else:
            flash(f'✅ Partial payment of ฿{amount:,.2f} recorded. Balance due: ฿{invoice.balance_due:,.2f}')
        
        logger.info(f"Payment of ฿{amount} added to invoice {invoice.invoice_number}")
        
        return redirect(url_for('invoice.view_invoice', invoice_id=invoice_id))
        
    except Exception as e:
        logger.error(f"Error adding payment to invoice {invoice_id}: {str(e)}")
        db.session.rollback()
        flash('❌ Error adding payment')
        return redirect(url_for('invoice.view_invoice', invoice_id=invoice_id))

@invoice_bp.route('/<int:invoice_id>/mark-paid', methods=['POST'])
@login_required
def mark_invoice_paid(invoice_id):
    """Mark invoice as fully paid (admin shortcut)"""
    try:
        from utils.datetime_utils import naive_utc_now
        
        invoice = Invoice.query.get_or_404(invoice_id)
        
        if invoice.payment_status == 'paid':
            flash('❌ Invoice already marked as paid')
            return redirect(url_for('invoice.view_invoice', invoice_id=invoice_id))
        
        # Create full payment record
        remaining_balance = invoice.balance_due
        payment = invoice.add_payment(
            amount=remaining_balance,
            payment_method='Admin Payment',
            reference=f'Admin marked paid - {naive_utc_now().strftime("%Y%m%d_%H%M")}',
            payment_date=naive_utc_now().date()
        )
        
        # Update booking workflow - use mark_as_paid() to trigger activity logging
        if hasattr(invoice.booking, 'mark_as_paid'):
            invoice.booking.mark_as_paid()
        else:
            invoice.booking.status = Booking.STATUS_PAID
        invoice.booking.paid_at = naive_utc_now()
        invoice.booking.is_paid = True
        invoice.booking.invoice_paid_date = naive_utc_now().date()
        invoice.booking.invoice_amount = invoice.total_amount
        
        db.session.commit()
        
        flash(f'✅ Invoice {invoice.invoice_number} marked as PAID! Booking ready for voucher generation.')
        logger.info(f"Invoice {invoice.invoice_number} marked as paid by admin")
        
        return redirect(url_for('invoice.view_invoice', invoice_id=invoice_id))
        
    except Exception as e:
        logger.error(f"Error marking invoice {invoice_id} as paid: {str(e)}")
        db.session.rollback()
        flash('❌ Error marking invoice as paid')
        return redirect(url_for('invoice.view_invoice', invoice_id=invoice_id))

@invoice_bp.route('/<int:invoice_id>/send-reminder', methods=['POST'])
@login_required
def send_payment_reminder(invoice_id):
    """Send payment reminder (placeholder for email integration)"""
    try:
        invoice = Invoice.query.get_or_404(invoice_id)
        
        if invoice.payment_status == 'paid':
            flash('❌ Invoice is already paid')
            return redirect(url_for('invoice.view_invoice', invoice_id=invoice_id))
        
        # In production, implement email sending here
        # For now, just log and flash message
        
        flash(f'✅ Payment reminder would be sent to {invoice.booking.customer.email}')
        logger.info(f"Payment reminder requested for invoice {invoice.invoice_number}")
        
        return redirect(url_for('invoice.view_invoice', invoice_id=invoice_id))
        
    except Exception as e:
        logger.error(f"Error sending reminder for invoice {invoice_id}: {str(e)}")
        flash('❌ Error sending reminder')
        return redirect(url_for('invoice.view_invoice', invoice_id=invoice_id))

@invoice_bp.route('/overdue')
@login_required
def list_overdue_invoices():
    """List overdue invoices"""
    try:
        from datetime import date
        
        overdue_invoices = Invoice.query.filter(
            Invoice.due_date < date.today(),
            Invoice.payment_status != 'paid'
        ).order_by(Invoice.due_date).all()
        
        return render_template('invoice/overdue.html', invoices=overdue_invoices)
        
    except Exception as e:
        logger.error(f"Error listing overdue invoices: {str(e)}")
        flash('❌ Error loading overdue invoices')
        return redirect(url_for('invoice.list_invoices'))

@invoice_bp.route('/unpaid')
@login_required
def list_unpaid_invoices():
    """List unpaid invoices"""
    try:
        unpaid_invoices = Invoice.query.filter(
            Invoice.payment_status.in_(['unpaid', 'partial'])
        ).order_by(Invoice.created_at.desc()).all()
        
        return render_template('invoice/unpaid.html', invoices=unpaid_invoices)
        
    except Exception as e:
        logger.error(f"Error listing unpaid invoices: {str(e)}")
        flash('❌ Error loading unpaid invoices')
        return redirect(url_for('invoice.list_invoices'))

@invoice_bp.route('/create_quote/<int:booking_id>', methods=['POST'])
@login_required
def create_quote(booking_id):
    """Create a quote for a booking"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        # Check if quote already exists
        if hasattr(booking, 'quote_id') and booking.quote_id:
            flash('❌ Quote already exists for this booking')
            return redirect(url_for('invoice.list_bookings'))
        
        # Create new quote
        quote = Quote(
            booking_id=booking.id,
            title=f'Quote for {booking.booking_reference}',
            description=booking.description or '',
            total_amount=booking.total_amount or 0,
            status='draft'
        )
        
        db.session.add(quote)
        db.session.flush()  # Get quote ID
        
        # Update booking with quote_id
        booking.quote_id = quote.id
        booking.status = 'quoted'
        
        db.session.commit()
        
        flash(f'✅ Quote created successfully for booking {booking.booking_reference}')
        logger.info(f"Quote {quote.id} created for booking {booking.booking_reference}")
        
        return redirect(url_for('invoice.list_bookings'))
        
    except Exception as e:
        logger.error(f"Error creating quote for booking {booking_id}: {str(e)}")
        db.session.rollback()
        flash('❌ Error creating quote')
        return redirect(url_for('invoice.list_bookings'))

@invoice_bp.route('/create_invoice/<int:booking_id>', methods=['POST'])
@login_required
def create_invoice(booking_id):
    """Create an invoice for a booking"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        # Check if invoice already exists
        if hasattr(booking, 'invoice_id') and booking.invoice_id:
            flash('❌ Invoice already exists for this booking')
            return redirect(url_for('invoice.list_bookings'))
        
        from utils.datetime_utils import naive_utc_now
        
        # Create new invoice
        invoice = Invoice(
            booking_id=booking.id,
            quote_id=getattr(booking, 'quote_id', None),  # Link to quote if exists
            title=f'Invoice for {booking.booking_reference}',
            description=booking.description or '',
            total_amount=booking.total_amount or 0,
            subtotal=booking.total_amount or 0,
            invoice_date=naive_utc_now().date(),
            due_date=naive_utc_now().date() + timedelta(days=30),
            status='draft'
        )
        
        db.session.add(invoice)
        db.session.flush()  # Get invoice ID
        
        # Update booking with invoice_id
        booking.invoice_id = invoice.id
        booking.status = 'invoiced'
        
        db.session.commit()
        
        flash(f'✅ Invoice created successfully for booking {booking.booking_reference}')
        logger.info(f"Invoice {invoice.id} created for booking {booking.booking_reference}")
        
        return redirect(url_for('invoice.list_bookings'))
        
    except Exception as e:
        logger.error(f"Error creating invoice for booking {booking_id}: {str(e)}")
        db.session.rollback()
        flash('❌ Error creating invoice')
        return redirect(url_for('invoice.list_bookings'))

@invoice_bp.route('/list_bookings')
@login_required
def list_bookings():
    """List all bookings for invoice management"""
    try:
        bookings = Booking.query.order_by(Booking.created_at.desc()).all()
        return render_template('invoice/bookings_list.html', bookings=bookings)
    except Exception as e:
        logger.error(f"Error listing bookings for invoices: {str(e)}")
        flash('❌ Error loading bookings')
        return redirect(url_for('dashboard.index'))

@invoice_bp.route('/send_invoice/<int:booking_id>', methods=['POST'])
@login_required
def send_invoice(booking_id):
    """Send invoice to customer (placeholder)"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        if not hasattr(booking, 'invoice_id') or not booking.invoice_id:
            flash('❌ No invoice found for this booking')
            return redirect(url_for('invoice.list_bookings'))
        
        # In production, implement email sending here
        flash(f'✅ Invoice would be sent to {booking.customer.email if booking.customer else "customer"}')
        logger.info(f"Invoice send requested for booking {booking.booking_reference}")
        
        return redirect(url_for('invoice.list_bookings'))
        
    except Exception as e:
        logger.error(f"Error sending invoice for booking {booking_id}: {str(e)}")
        flash('❌ Error sending invoice')
        return redirect(url_for('invoice.list_bookings'))

@invoice_bp.route('/mark_paid/<int:booking_id>', methods=['POST'])
@login_required
def mark_paid(booking_id):
    """Mark invoice as paid"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        if not hasattr(booking, 'invoice_id') or not booking.invoice_id:
            flash('❌ No invoice found for this booking')
            return redirect(url_for('invoice.list_bookings'))
        
        # Get the invoice and mark as paid
        invoice = Invoice.query.get(booking.invoice_id)
        if invoice:
            invoice.payment_status = 'paid'
            invoice.paid_amount = invoice.total_amount
            invoice.balance_due = 0
            invoice.paid_date = naive_utc_now().date()
            
            # Update booking status
            booking.status = 'paid'
            
            db.session.commit()
            
            flash(f'✅ Invoice marked as paid for booking {booking.booking_reference}')
            logger.info(f"Invoice {invoice.id} marked as paid for booking {booking.booking_reference}")
        else:
            flash('❌ Invoice not found')
        
        return redirect(url_for('invoice.list_bookings'))
        
    except Exception as e:
        logger.error(f"Error marking invoice as paid for booking {booking_id}: {str(e)}")
        db.session.rollback()
        flash('❌ Error marking invoice as paid')
        return redirect(url_for('invoice.list_bookings'))

@invoice_bp.route('/status')
@login_required
def status():
    """Check Invoice Ninja connection status"""
    try:
        # This is a placeholder - implement actual Invoice Ninja API check
        return jsonify({
            'connected': False,
            'error': 'Invoice Ninja integration not configured'
        })
    except Exception as e:
        logger.error(f"Error checking invoice status: {str(e)}")
        return jsonify({
            'connected': False,
            'error': str(e)
        })
