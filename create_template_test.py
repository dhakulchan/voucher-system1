#!/usr/bin/env python3
"""
Create a direct template test to check Thai content display
"""

template_test_code = '''
@app.route('/test/template-debug/<int:booking_id>')
def test_template_debug(booking_id):
    """Test template rendering with Thai content"""
    from models.booking import Booking
    from extensions import db
    from jinja2 import Environment, FileSystemLoader
    import os
    
    try:
        booking = db.session.get(Booking, booking_id)
        if not booking:
            return f"Booking {booking_id} not found", 404
        
        # Test template rendering directly
        template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates', 'pdf')
        jinja_env = Environment(loader=FileSystemLoader(template_dir))
        
        try:
            template = jinja_env.get_template('quote_template_final_v2.html')
            template_name = 'quote_template_final_v2.html'
        except:
            try:
                template = jinja_env.get_template('quote_test_simple.html')
                template_name = 'quote_test_simple.html'
            except Exception as e:
                return f"No template found: {e}", 500
        
        # Force Thai data into template
        template_data = {
            'booking': booking,
            'quote_number': f'QT{booking.id}',
            'quote_date': '14/11/2025',
            'customer_name': 'Test Customer',
            'service_detail': booking.description or 'ไม่มีรายละเอียดบริการ',
            'name_list': booking.guest_list or 'ไม่มีรายชื่อผู้โดยสาร',
            'flight_info': booking.flight_info or 'ไม่มีข้อมูลเที่ยวบิน',
            'total_amount': '7,100.00'
        }
        
        html_content = template.render(**template_data)
        
        # Return HTML to see what's being rendered
        debug_html = f"""
        <html><head><meta charset="UTF-8"><title>Template Debug</title></head>
        <body style="font-family: Arial; margin: 20px;">
        <h2>Template Debug - {template_name}</h2>
        
        <h3>Raw Data:</h3>
        <p><b>booking.description:</b> {repr(booking.description)}</p>
        <p><b>booking.guest_list:</b> {repr(booking.guest_list)}</p>
        <p><b>booking.flight_info:</b> {repr(booking.flight_info)}</p>
        
        <h3>Template Data:</h3>
        <p><b>service_detail:</b> {repr(template_data['service_detail'])}</p>
        <p><b>name_list:</b> {repr(template_data['name_list'])}</p>
        <p><b>flight_info:</b> {repr(template_data['flight_info'])}</p>
        
        <h3>Rendered Template (first 2000 chars):</h3>
        <textarea style="width: 100%; height: 300px;">{html_content[:2000]}</textarea>
        
        <h3>Actions:</h3>
        <a href="/booking/test-quote-pdf/{booking_id}" target="_blank">Generate PDF</a>
        
        <hr>
        <h3>Full Rendered HTML:</h3>
        <div style="border: 1px solid #ccc; padding: 10px; background: #f9f9f9;">
        {html_content}
        </div>
        </body></html>
        """
        
        return debug_html
        
    except Exception as e:
        return f"Template debug error: {str(e)}", 500
'''

print("Template debug code generated. Add this to app.py:")
print("=" * 60)
print(template_test_code)
print("=" * 60)
print("\nThen restart server and access:")
print("https://service.dhakulchan.net/test/template-debug/3")