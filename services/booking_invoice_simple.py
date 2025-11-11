"""
Booking Invoice Service (Invoice Ninja integration removed)
Handles basic booking invoice operations without external integration
"""

from datetime import datetime, timedelta
from models.booking import Booking
from models.customer import Customer
import logging

logger = logging.getLogger(__name__)

class BookingInvoiceService:
    def __init__(self):
        # Invoice Ninja integration removed - now simple booking invoice service
        pass
    
    def get_or_create_client(self, customer):
        """Simple client handling without external API"""
        # Just return customer data - no external integration
        return {
            'id': customer.id,
            'name': f"{customer.first_name} {customer.last_name}",
            'email': customer.email,
            'phone': customer.phone
        }
    
    def sync_booking_numbers(self, booking: Booking):
        """Simple sync - just return True (no external sync needed)"""
        # No external sync required anymore
        return True
    
    def create_invoice_from_booking(self, booking, quote_id=None):
        """Create internal invoice record (no external API call)"""
        try:
            # Generate invoice number if not exists
            if not booking.invoice_number:
                booking.invoice_number = self._generate_invoice_number()
            
            # Set basic invoice data
            booking.invoice_status = 'draft'
            
            logger.info(f"Created internal invoice {booking.invoice_number} for booking {booking.id}")
            
            return {
                'number': booking.invoice_number,
                'status': booking.invoice_status,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error creating internal invoice: {e}")
            return {'success': False, 'error': str(e)}
    
    def create_quote_from_booking(self, booking):
        """Create internal quote record (no external API call)"""
        try:
            # Generate quote number if not exists
            if not booking.quote_number:
                booking.quote_number = self._generate_quote_number()
            
            logger.info(f"Created internal quote {booking.quote_number} for booking {booking.id}")
            
            return {
                'number': booking.quote_number,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error creating internal quote: {e}")
            return {'success': False, 'error': str(e)}
    
    def convert_quote_to_invoice(self, booking):
        """Convert quote to invoice (internal only)"""
        try:
            if not booking.quote_number:
                return {'success': False, 'error': 'No quote to convert'}
            
            # Create invoice from quote
            return self.create_invoice_from_booking(booking)
            
        except Exception as e:
            logger.error(f"Error converting quote to invoice: {e}")
            return {'success': False, 'error': str(e)}
    
    def mark_booking_paid(self, booking, payment_amount=None):
        """Mark booking as paid (internal only)"""
        try:
            booking.is_paid = True
            booking.invoice_status = 'paid'
            booking.invoice_paid_date = datetime.now()
            
            if payment_amount:
                booking.invoice_amount = payment_amount
            
            logger.info(f"Marked booking {booking.id} as paid")
            
            return {'success': True, 'status': 'paid'}
            
        except Exception as e:
            logger.error(f"Error marking booking as paid: {e}")
            return {'success': False, 'error': str(e)}
    
    def send_invoice_to_customer(self, booking):
        """Send invoice to customer (placeholder - no external integration)"""
        # No external sending required
        logger.info(f"Invoice {booking.invoice_number} ready for customer")
        return {'success': True, 'message': 'Invoice ready for manual sending'}
    
    def _generate_invoice_number(self):
        """Generate internal invoice number"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"AR{timestamp}"
    
    def _generate_quote_number(self):
        """Generate internal quote number starting from QT2509001"""
        from models.quote import Quote
        
        # Minimum starting number
        min_number = 2509001
        
        # Find the highest existing quote number
        last_quote = Quote.query.filter(
            Quote.quote_number.like('QT%')
        ).order_by(Quote.quote_number.desc()).first()
        
        if last_quote and last_quote.quote_number.startswith('QT'):
            try:
                # Extract numeric part from quote number
                numeric_part = last_quote.quote_number[2:]  # Remove 'QT' prefix
                last_number = int(numeric_part)
                # Use the higher value between last_number+1 and min_number
                new_number = max(last_number + 1, min_number)
            except (ValueError, IndexError):
                # If parsing fails, start from QT2509001
                new_number = min_number
        else:
            # No existing quote, start from QT2509001
            new_number = min_number
            
        return f'QT{new_number}'
