#!/usr/bin/env python3
"""
Create debug route to see what data is being passed to template
"""

debug_route_code = '''
@app.route('/debug/template-data/<int:booking_id>')
def debug_template_data(booking_id):
    """Debug what data is passed to WeasyPrint template"""
    from models.booking import Booking
    from extensions import db
    from services.weasyprint_quote_generator import WeasyPrintQuoteGenerator
    import json
    
    try:
        booking = db.session.get(Booking, booking_id)
        if not booking:
            return f"Booking {booking_id} not found", 404
        
        # Create generator and get template data
        generator = WeasyPrintQuoteGenerator()
        
        # Extract the same data that would be passed to template
        from services.universal_booking_extractor import UniversalBookingExtractor
        from services.smart_price_calculator import ProductDataExtractor
        
        # Get fresh booking data
        all_booking_fields = UniversalBookingExtractor.extract_all_booking_fields(booking)
        customer_info = UniversalBookingExtractor.extract_customer_info(booking)
        product_data = ProductDataExtractor.extract_complete_product_data(booking)
        
        # Prepare template data (similar to generator._prepare_template_data)
        service_detail = (all_booking_fields.get('service_details_current') or
                         all_booking_fields.get('itinerary_current') or
                         all_booking_fields.get('special_request_html') or
                         all_booking_fields.get('description_html') or
                         all_booking_fields.get('special_request') or
                         all_booking_fields.get('description') or
                         'Service details not specified')
        
        name_list = generator._format_guest_list(booking, all_booking_fields)
        flight_info = generator._format_flight_info(booking, all_booking_fields)
        
        template_data = {
            'booking_id': booking.id,
            'booking_reference': booking.booking_reference,
            'raw_description': booking.description,
            'raw_guest_list': booking.guest_list,
            'raw_flight_info': booking.flight_info,
            'processed_service_detail': service_detail,
            'processed_name_list': name_list,
            'processed_flight_info': flight_info,
            'all_booking_fields_keys': list(all_booking_fields.keys()),
            'customer_info': customer_info
        }
        
        html = f"""
        <html><head><meta charset="UTF-8"><title>Template Data Debug</title></head>
        <body style="font-family: Arial; margin: 20px;">
        <h2>Template Data Debug - Booking {booking_id}</h2>
        
        <h3>🔥 Raw Booking Data (Direct from DB)</h3>
        <table border="1" style="border-collapse: collapse; width: 100%; margin-bottom: 20px;">
        <tr style="background: #f0f0f0;">
            <td><b>Field</b></td>
            <td><b>Value</b></td>
            <td><b>Length</b></td>
        </tr>
        <tr>
            <td>booking.description</td>
            <td style="background: #ffeb3b; max-width: 400px; word-wrap: break-word;"><pre>{repr(booking.description)}</pre></td>
            <td>{len(booking.description) if booking.description else 0}</td>
        </tr>
        <tr>
            <td>booking.guest_list</td>
            <td style="background: #ffeb3b; max-width: 400px; word-wrap: break-word;"><pre>{repr(booking.guest_list)}</pre></td>
            <td>{len(booking.guest_list) if booking.guest_list else 0}</td>
        </tr>
        <tr>
            <td>booking.flight_info</td>
            <td style="background: #ffeb3b; max-width: 400px; word-wrap: break-word;"><pre>{repr(booking.flight_info)}</pre></td>
            <td>{len(booking.flight_info) if booking.flight_info else 0}</td>
        </tr>
        </table>
        
        <h3>🔧 Processed Data (What Generator Creates)</h3>
        <table border="1" style="border-collapse: collapse; width: 100%; margin-bottom: 20px;">
        <tr style="background: #f0f0f0;">
            <td><b>Variable</b></td>
            <td><b>Value</b></td>
            <td><b>Length</b></td>
        </tr>
        <tr>
            <td>service_detail</td>
            <td style="background: #c8e6c9; max-width: 400px; word-wrap: break-word;"><pre>{repr(service_detail)}</pre></td>
            <td>{len(str(service_detail))}</td>
        </tr>
        <tr>
            <td>name_list</td>
            <td style="background: #c8e6c9; max-width: 400px; word-wrap: break-word;"><pre>{repr(name_list)}</pre></td>
            <td>{len(str(name_list)) if name_list else 0}</td>
        </tr>
        <tr>
            <td>flight_info</td>
            <td style="background: #c8e6c9; max-width: 400px; word-wrap: break-word;"><pre>{repr(flight_info)}</pre></td>
            <td>{len(str(flight_info)) if flight_info else 0}</td>
        </tr>
        </table>
        
        <h3>📋 Template Logic Test</h3>
        <div style="background: #e3f2fd; padding: 15px; margin: 10px 0;">
            <h4>Service Detail Priority:</h4>
            <p>1. booking.description: {'✅ HAS DATA' if booking.description else '❌ EMPTY'}</p>
            <p>2. service_detail: {'✅ HAS DATA' if service_detail and service_detail != 'Service details not specified' else '❌ FALLBACK'}</p>
            
            <h4>Name List Priority:</h4>
            <p>1. booking.guest_list: {'✅ HAS DATA' if booking.guest_list else '❌ EMPTY'}</p>
            <p>2. name_list: {'✅ HAS DATA' if name_list else '❌ EMPTY'}</p>
            
            <h4>Flight Info Priority:</h4>
            <p>1. booking.flight_info: {'✅ HAS DATA' if booking.flight_info else '❌ EMPTY'}</p>
            <p>2. flight_info: {'✅ HAS DATA' if flight_info else '❌ EMPTY'}</p>
        </div>
        
        <h3>🎯 Actions</h3>
        <p><a href="/booking/test-quote-pdf/{booking_id}" target="_blank">Generate Test PDF</a></p>
        <p><a href="/booking/{booking_id}/quote-pdf" target="_blank">Generate Production PDF</a></p>
        
        <h3>📊 All Booking Fields Available</h3>
        <p>Available keys: {len(all_booking_fields.keys())} fields</p>
        <details>
            <summary>Click to see all field names</summary>
            <pre>{json.dumps(list(all_booking_fields.keys()), indent=2)}</pre>
        </details>
        
        </body></html>
        """
        
        return html
        
    except Exception as e:
        return f"Debug error: {str(e)}", 500
'''

print("Template data debug route:")
print("=" * 60)
print(debug_route_code)
print("=" * 60)
print("\nAdd this to app.py, then access:")
print("https://service.dhakulchan.net/debug/template-data/3")