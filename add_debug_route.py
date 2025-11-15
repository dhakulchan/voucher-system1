#!/usr/bin/env python3
"""
Add debug route to Flask app to check template data.
"""

debug_route_code = '''
@app.route('/debug/quote/<int:booking_id>')
def debug_quote_data(booking_id):
    """Debug route to check quote template data."""
    try:
        from models.booking_enhanced import BookingEnhanced
        from services.weasyprint_quote_generator import WeasyPrintQuoteGenerator
        
        booking = BookingEnhanced.query.get(booking_id)
        if not booking:
            return f"Booking {booking_id} not found", 404
            
        # Get template data
        generator = WeasyPrintQuoteGenerator()
        template_data = generator._prepare_template_data_for_quote(None, booking, [])
        
        # Create HTML debug output
        html = f"""
        <!DOCTYPE html>
        <html><head><meta charset="UTF-8"><title>Debug Quote Data</title></head>
        <body style="font-family: Arial; margin: 20px;">
        <h1>Debug Quote Data - Booking {booking_id}</h1>
        
        <h2>Database Values:</h2>
        <p><strong>Booking ID:</strong> {booking.id}</p>
        <p><strong>Reference:</strong> {booking.booking_reference}</p>
        <p><strong>Description:</strong> {repr(booking.description)}</p>
        <p><strong>Guest List:</strong> {repr(booking.guest_list)}</p>
        <p><strong>Flight Info:</strong> {repr(booking.flight_info)}</p>
        
        <h2>Template Data Variables:</h2>
        <p><strong>service_detail:</strong> {repr(template_data.get('service_detail', 'N/A'))}</p>
        <p><strong>name_list:</strong> {repr(template_data.get('name_list', 'N/A'))}</p>
        <p><strong>flight_info:</strong> {repr(template_data.get('flight_info', 'N/A'))}</p>
        
        <h2>Thai Text Test:</h2>
        <div style="border: 2px solid red; padding: 10px; background: yellow;">
        <h3>ข้อกำหนดและเงื่อนไข</h3>
        <p>• เอกสารฉบับนี้ ไม่ใช่การยืนยันการจอง</p>
        <p>• ราคาและเงื่อนไขต่าง ๆ อาจมีการเปลี่ยนแปลง</p>
        </div>
        </body></html>
        """
        
        return html
        
    except Exception as e:
        return f"Error: {str(e)}", 500
'''

# Read app.py
with open('/opt/voucher-ro/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add debug route before the final line
if 'debug_quote_data' not in content:
    # Insert before the last line
    lines = content.split('\n')
    lines.insert(-1, debug_route_code)
    
    with open('/opt/voucher-ro/app.py', 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
        
    print("✓ Added debug route to app.py")
else:
    print("Debug route already exists")