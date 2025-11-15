#!/usr/bin/env python3
"""
Create debug route to check Thai content in booking 3
"""

debug_route_code = '''
@app.route('/debug/quote/<int:booking_id>')
def debug_quote_data(booking_id):
    """Debug route to check quote data and Thai content"""
    from models.booking import Booking
    from extensions import db
    import json
    
    try:
        booking = db.session.get(Booking, booking_id)
        if not booking:
            return f"Booking {booking_id} not found", 404
        
        debug_info = {
            'booking_id': booking.id,
            'booking_reference': booking.booking_reference,
            'description': booking.description,
            'description_length': len(booking.description) if booking.description else 0,
            'guest_list': booking.guest_list,
            'guest_list_length': len(booking.guest_list) if booking.guest_list else 0,
            'flight_info': booking.flight_info,
            'flight_info_length': len(booking.flight_info) if booking.flight_info else 0,
            'status': booking.status,
            'total_amount': str(booking.total_amount) if booking.total_amount else None
        }
        
        html = f"""
        <html><body style="font-family: Arial; margin: 20px;">
        <h2>Debug Booking {booking_id} - Thai Content Check</h2>
        <table border="1" style="border-collapse: collapse; width: 100%;">
        <tr><td><b>Field</b></td><td><b>Value</b></td><td><b>Length</b></td></tr>
        <tr><td>Booking ID</td><td>{debug_info['booking_id']}</td><td>-</td></tr>
        <tr><td>Reference</td><td>{debug_info['booking_reference']}</td><td>-</td></tr>
        <tr><td>Status</td><td>{debug_info['status']}</td><td>-</td></tr>
        <tr><td>Description</td><td><pre>{debug_info['description']}</pre></td><td>{debug_info['description_length']}</td></tr>
        <tr><td>Guest List</td><td><pre>{debug_info['guest_list']}</pre></td><td>{debug_info['guest_list_length']}</td></tr>
        <tr><td>Flight Info</td><td><pre>{debug_info['flight_info']}</pre></td><td>{debug_info['flight_info_length']}</td></tr>
        <tr><td>Total Amount</td><td>{debug_info['total_amount']}</td><td>-</td></tr>
        </table>
        
        <h3>Actions:</h3>
        <a href="/booking/test-quote-pdf/{booking_id}" target="_blank">Test Quote PDF</a> |
        <a href="/booking/{booking_id}/quote-pdf" target="_blank">Production Quote PDF</a> |
        <a href="/booking/{booking_id}" target="_blank">View Booking</a>
        
        <h3>Raw JSON:</h3>
        <pre>{json.dumps(debug_info, indent=2, ensure_ascii=False)}</pre>
        
        </body></html>
        """
        
        return html
        
    except Exception as e:
        return f"Debug error: {str(e)}", 500
'''

print("Debug route code generated. Add this to app.py:")
print("=" * 60)
print(debug_route_code)
print("=" * 60)
print("\nThen restart the server and access:")
print("https://service.dhakulchan.net/debug/quote/3")