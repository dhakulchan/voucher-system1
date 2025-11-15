"""
Invoice Ninja integration routes for the Tour Voucher system
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from services.booking_invoice import BookingInvoiceService
from models.booking import Booking
from models.customer import Customer
from extensions import db
from datetime import timedelta

invoice_bp = Blueprint('invoice', __name__)

@invoice_bp.route('/booking/<int:booking_id>/create-quote', methods=['POST'])
@invoice_bp.route('/create-quote/<int:booking_id>', methods=['GET', 'POST'])  # Alternative route for template compatibility
@login_required
def create_quote(booking_id):
    """Create Invoice Ninja quote for booking and redirect to quote view"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        booking_invoice_service = BookingInvoiceService()
        
        quote_data = booking_invoice_service.create_quote_from_booking(booking)
        
        if quote_data:
            db.session.commit()
            quote_number = quote_data.get("number")
            
            if quote_number:
                # Redirect to internal quote view instead of external
                flash(f'Quote {quote_number} created successfully!', 'success')
                return redirect(url_for('invoice.view_quote', booking_id=booking_id))
            else:
                flash('Quote created but no quote number returned', 'warning')
                return redirect(url_for('booking.view', id=booking_id))
        else:
            flash('Failed to create quote in Invoice Ninja', 'error')
            
    except Exception as e:
        flash(f'Error creating quote: {str(e)}', 'error')
    
    return redirect(url_for('booking.view', id=booking_id))


@invoice_bp.route('/booking/<int:booking_id>/quote')
@login_required
def view_quote(booking_id):
    """View quote details for booking"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        if not booking.quote_number:
            flash('No quote found for this booking', 'warning')
            return redirect(url_for('booking.view', id=booking_id))
        
        # Prepare quote data for display
        quote_data = {
            'booking': booking,
            'quote_number': booking.quote_number,
            'quote_id': booking.quote_id,
            'status': booking.quote_status or 'Draft',
            'created_date': booking.created_at,
            'valid_until': booking.created_at + timedelta(days=30) if booking.created_at else None,
            'total_amount': booking.total_amount,
            'products': booking.get_products() if hasattr(booking, 'get_products') else []
        }
        
        return render_template('quote/view.html', **quote_data)
        
    except Exception as e:
        flash(f'Error viewing quote: {str(e)}', 'error')
        return redirect(url_for('booking.view', id=booking_id))

@invoice_bp.route('/booking/<int:booking_id>/create-invoice', methods=['POST'])
@login_required
def create_invoice(booking_id):
    """Create Invoice Ninja invoice for booking"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        booking_invoice_service = BookingInvoiceService()
        
        invoice_data = booking_invoice_service.create_invoice_from_booking(booking)
        
        if invoice_data:
            db.session.commit()
            flash(f'Invoice {invoice_data.get("number")} created successfully in Invoice Ninja!', 'success')
        else:
            flash('Failed to create invoice in Invoice Ninja', 'error')
            
    except Exception as e:
        flash(f'Error creating invoice: {str(e)}', 'error')
    
    return redirect(url_for('booking.view', id=booking_id))

@invoice_bp.route('/booking/<int:booking_id>/send-invoice', methods=['POST'])
@login_required
def send_invoice(booking_id):
    """Send invoice via email"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        booking_invoice_service = BookingInvoiceService()
        
        if booking_invoice_service.send_invoice_to_customer(booking):
            flash('Invoice sent successfully via email!', 'success')
        else:
            flash('Failed to send invoice via email', 'warning')
            
    except Exception as e:
        flash(f'Error sending invoice: {str(e)}', 'error')
    
    return redirect(url_for('booking.view', id=booking_id))

@invoice_bp.route('/booking/<int:booking_id>/mark-paid', methods=['POST'])
@login_required
def mark_paid(booking_id):
    """Mark booking invoice as paid"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        booking_invoice_service = BookingInvoiceService()
        
        payment_amount = request.form.get('amount')
        if payment_amount:
            payment_amount = float(payment_amount)
        
        payment_data = booking_invoice_service.mark_booking_paid(booking, payment_amount)
        
        if payment_data:
            db.session.commit()
            flash('Invoice marked as paid successfully!', 'success')
        else:
            flash('Failed to mark invoice as paid', 'error')
            
    except Exception as e:
        flash(f'Error marking invoice as paid: {str(e)}', 'error')
    
    return redirect(url_for('booking.view', id=booking_id))

@invoice_bp.route('/invoice-ninja/status')
@login_required
def status():
    """Show Invoice Ninja integration status"""
    try:
        booking_invoice_service = BookingInvoiceService()
        # Test connection
        test_result = booking_invoice_service.invoice_service._make_request('GET', 'ping')
        
        if test_result:
            status_info = {
                'connected': True,
                'company_name': test_result.get('company_name', 'Unknown'),
                'user_name': test_result.get('user_name', 'Unknown')
            }
        else:
            status_info = {'connected': False}
            
    except Exception as e:
        status_info = {
            'connected': False,
            'error': str(e)
        }
    
    return jsonify(status_info)

@invoice_bp.route('/bookings-with-invoices')
@login_required
def bookings_with_invoices():
    """Show bookings that have Invoice Ninja integration"""
    bookings = Booking.query.filter(
        (Booking.quote_id.isnot(None)) | (Booking.invoice_id.isnot(None))
    ).order_by(Booking.created_at.desc()).all()
    
    return render_template('invoice/bookings_list.html', bookings=bookings)

@invoice_bp.route('/booking/<int:booking_id>/sync-from-ninja', methods=['POST'])
@login_required
def sync_invoice_from_ninja(booking_id):
    """Sync invoice data from Invoice Ninja (no creation)"""
    
    from services.invoice_sync_service import invoice_sync_service
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        sync_result = invoice_sync_service.sync_invoice_for_quote(booking_id)
        
        if sync_result['success']:
            if sync_result.get('invoice_found'):
                if sync_result['is_paid']:
                    flash(f'✅ Invoice {sync_result["invoice_number"]} is PAID! Voucher creation is now available.', 'success')
                else:
                    flash(f'📄 Invoice {sync_result["invoice_number"]} found - Status: {sync_result["new_status"].upper()}', 'info')
                
                if sync_result.get('old_status') != sync_result.get('new_status'):
                    flash(f'🔄 Status updated: {sync_result.get("old_status") or "None"} → {sync_result["new_status"]}', 'info')
            else:
                flash('ℹ️ No invoice found yet. Please create invoice in Invoice Ninja first.', 'warning')
        else:
            flash(f'❌ Sync failed: {sync_result["error"]}', 'error')
        
        return redirect(url_for('booking.view', id=booking_id))
        
    except Exception as e:
        logger.error(f"Error in sync route for booking {booking_id}: {e}")
        flash('An error occurred during sync. Please try again.', 'error')
        return redirect(url_for('booking.view', id=booking_id))
