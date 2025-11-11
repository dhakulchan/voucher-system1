# Quick fix for PNG endpoint - use only ClassicPDFGenerator
from flask import Response, abort, send_file
from services.classic_pdf_generator import ClassicPDFGenerator
from datetime import datetime
import os

def fixed_test_generate_booking_png(booking_id):
    """Fixed PNG endpoint using ClassicPDFGenerator only"""
    from extensions import db
    from models.booking import Booking
    from utils.logging_config import get_logger
    
    logger = get_logger(__name__)
    
    # Force refresh from database
    db.session.expire_all()
    booking = Booking.query.get_or_404(booking_id)
    
    try:
        # Prepare complete booking data including guest_list
        guest_list = booking.guest_list if booking.guest_list else ''
        
        booking_data = {
            'id': booking.id,
            'booking_reference': booking.booking_reference,
            'client_name': booking.client_name,
            'total_amount': booking.total_amount,
            'total_persons': booking.total_persons,
            'checkin_date': booking.checkin_date,
            'checkout_date': booking.checkout_date,
            'guest_list': guest_list,
            'manager_notes': booking.manager_notes,
            'rooms': [
                {
                    'room_name': room.room_name,
                    'room_type': room.room_type,
                    'guests': room.guests,
                    'nights': room.nights,
                    'adults': room.adults if hasattr(room, 'adults') else 2,
                    'children': room.children if hasattr(room, 'children') else 0,
                    'infants': room.infants if hasattr(room, 'infants') else 0
                } for room in booking.rooms
            ],
            'products': [
                {
                    'product_name': product.product_name,
                    'price_per_person': product.price_per_person,
                    'total_persons': product.total_persons,
                    'total_price': product.total_price
                } for product in booking.products
            ]
        }
        
        # Generate PDF using ClassicPDFGenerator
        classic_generator = ClassicPDFGenerator()
        pdf_path = classic_generator.generate_service_proposal(booking_data)
        
        # Return PDF file instead of PNG for now
        return send_file(pdf_path, as_attachment=True, download_name=f'booking_{booking.booking_reference}.pdf')
            
    except Exception as e:
        logger.error(f"Error generating booking document: {str(e)}")
        abort(500, description=f"Error generating document: {str(e)}")
