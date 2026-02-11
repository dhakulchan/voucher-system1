"""
Patch for voucher.py to add better error handling and logging
Apply this to production to catch the actual error
"""

VOUCHER_VIEW_FIXED = '''
@voucher_bp.route('/<int:id>')
@login_required
def view(id):
    """Unified voucher view (English only while Thai disabled)"""
    try:
        current_app.logger.info(f'📋 Voucher view requested for booking #{id}')
        
        booking = Booking.query.get_or_404(id)
        current_app.logger.info(f'✅ Booking found: #{booking.id}, status={booking.status}')
        
        if booking.status not in ['confirmed', 'quoted', 'paid', 'vouchered', 'completed']:
            flash('Booking must be confirmed before viewing voucher', 'error')
            return redirect(url_for('booking.view', id=id))
        
        # Sync ARNO/QTNO from Invoice Ninja before displaying
        try:
            from services.booking_invoice import BookingInvoiceService
            bis = BookingInvoiceService()
            if bis.sync_booking_numbers(booking):
                db.session.commit()
            current_app.logger.info(f'✅ Invoice sync completed for booking #{id}')
        except Exception as e:
            # Non-fatal; continue rendering even if sync fails
            current_app.logger.warning(f'⚠️ Failed to sync booking numbers for voucher view: {e}')
        
        try:
            from models.vendor import Supplier, Vendor
            vendors = Vendor.query.filter_by(active=True).order_by(Vendor.name.asc()).all()
            suppliers = suppliers_list = Supplier.query.filter_by(active=True).order_by(Supplier.name.asc()).all()
            current_app.logger.info(f'✅ Loaded {len(vendors)} vendors, {len(suppliers)} suppliers')
        except Exception as e:
            current_app.logger.error(f'❌ Failed to load vendors/suppliers: {e}')
            vendors = []
            suppliers = []
        
        # Get voucher images for template
        try:
            voucher_images = booking.get_voucher_images()
            current_app.logger.info(f'✅ Loaded {len(voucher_images) if voucher_images else 0} voucher images')
        except Exception as e:
            current_app.logger.error(f'❌ Failed to get voucher images: {e}')
            voucher_images = []
        
        current_app.logger.info(f'🎨 Rendering template for booking #{id}')
        return render_template('voucher/unified_voucher.html', 
                             booking=booking, 
                             vendors=vendors, 
                             suppliers=suppliers,
                             voucher_images=voucher_images)
    
    except Exception as e:
        current_app.logger.error(f'❌ FATAL ERROR in voucher view for booking #{id}: {e}')
        current_app.logger.error(f'Exception type: {type(e).__name__}')
        import traceback
        current_app.logger.error(f'Traceback: {traceback.format_exc()}')
        raise
'''
