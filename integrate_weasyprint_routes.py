#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration helper - add WeasyPrint routes to booking
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def get_weasyprint_routes():
    """Get WeasyPrint route code to add to booking.py"""
    
    route_code = '''
# ============================================================================
# WeasyPrint PDF Generation Routes (Thai Font Support)
# ============================================================================

@booking_bp.route('/<int:booking_id>/pdf/weasyprint')
@login_required
def generate_booking_pdf_weasyprint(booking_id):
    """Generate Service Proposal PDF using WeasyPrint (Thai Font Support)"""
    from services.weasyprint_generator import WeasyPrintGenerator
    from flask import send_file, abort
    import os
    
    booking = Booking.query.get_or_404(booking_id)

    try:
        # Prepare booking data for WeasyPrint
        booking_data = {
            'booking_reference': booking.booking_reference,
            'customer_name': booking.customer.name if booking.customer else 'N/A',
            'customer_email': booking.customer.email if booking.customer else 'N/A',
            'customer_phone': booking.customer.phone if booking.customer else 'N/A',
            'adults': booking.adults or 0,
            'children': booking.children or 0,
            'infants': booking.infants or 0,
            'admin_notes': booking.admin_notes or '',
            'manager_memos': booking.manager_memos or '',
            'internal_note': booking.internal_note or ''
        }
        
        # Get products (if any)
        products = []
        if hasattr(booking, 'products') and booking.products:
            try:
                import json
                products_data = json.loads(booking.products) if booking.products else []
                for product in products_data:
                    products.append({
                        'name': product.get('name', 'Unknown Service'),
                        'quantity': product.get('quantity', 1),
                        'price': float(product.get('price', 0))
                    })
            except (json.JSONDecodeError, ValueError):
                # Fallback - create sample products
                products = [
                    {
                        'name': 'Tour Service (บริการทัวร์)',
                        'quantity': booking.adults + booking.children,
                        'price': 1500.00
                    }
                ]
        
        # Generate PDF using WeasyPrint
        weasyprint_generator = WeasyPrintGenerator()
        pdf_path = weasyprint_generator.generate_service_proposal(
            booking_data=booking_data,
            products=products
        )
        
        if os.path.exists(pdf_path):
            return send_file(pdf_path, 
                           as_attachment=True, 
                           download_name=f"Service_Proposal_Thai_{booking.booking_reference}.pdf",
                           mimetype='application/pdf')
        else:
            flash('Error generating WeasyPrint PDF file', 'error')
            return redirect(url_for('booking.view', id=booking_id))
            
    except Exception as e:
        flash(f'Error generating WeasyPrint PDF: {str(e)}', 'error')
        return redirect(url_for('booking.view', id=booking_id))


@booking_bp.route('/test/<int:booking_id>/pdf/weasyprint')
def test_generate_booking_pdf_weasyprint(booking_id):
    """TEMPORARY: Generate WeasyPrint PDF without authentication for testing"""
    from services.weasyprint_generator import WeasyPrintGenerator
    from flask import send_file, abort, Response
    import os
    from datetime import datetime
    import json
    
    booking = Booking.query.get_or_404(booking_id)

    try:
        # Prepare booking data for WeasyPrint
        booking_data = {
            'booking_reference': booking.booking_reference,
            'customer_name': booking.customer.name if booking.customer else 'N/A',
            'customer_email': booking.customer.email if booking.customer else 'N/A',
            'customer_phone': booking.customer.phone if booking.customer else 'N/A',
            'adults': booking.adults or 0,
            'children': booking.children or 0,
            'infants': booking.infants or 0,
            'admin_notes': booking.admin_notes or '',
            'manager_memos': booking.manager_memos or '',
            'internal_note': booking.internal_note or ''
        }
        
        # Sample products for testing
        products = [
            {
                'name': 'Bangkok City Tour (ทัวร์เมืองกรุงเทพฯ)',
                'quantity': booking.adults,
                'price': 1500.00
            },
            {
                'name': 'Temple Visit (เยี่ยมชมวัด)',
                'quantity': booking.adults + booking.children,
                'price': 800.00
            },
            {
                'name': 'Thai Lunch (อาหารไทยกลางวัน)',
                'quantity': booking.adults + booking.children,
                'price': 400.00
            }
        ]
        
        # Generate PDF using WeasyPrint
        weasyprint_generator = WeasyPrintGenerator()
        pdf_path = weasyprint_generator.generate_service_proposal(
            booking_data=booking_data,
            products=products
        )
        
        if os.path.exists(pdf_path):
            # Add cache-busting headers
            response = send_file(pdf_path, 
                               as_attachment=True, 
                               download_name=f"WeasyPrint_Thai_{booking.booking_reference}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                               mimetype='application/pdf')
            
            # Anti-cache headers
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '-1'
            response.headers['Last-Modified'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')
            response.headers['ETag'] = f'"{datetime.now().timestamp()}"'
            
            return response
        else:
            return f"Error: PDF file not found at {pdf_path}", 500
            
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return f"Error generating WeasyPrint PDF: {str(e)}\\n\\nDetails:\\n{error_details}", 500

# ============================================================================
'''
    
    return route_code

if __name__ == "__main__":
    print("WeasyPrint Route Integration Code:")
    print("=" * 60)
    print(get_weasyprint_routes())
    print("=" * 60)
    print("\\nTo integrate:")
    print("1. Add this code to routes/booking.py")
    print("2. Test with: /booking/test/{booking_id}/pdf/weasyprint")
    print("3. Production: /booking/{booking_id}/pdf/weasyprint")
