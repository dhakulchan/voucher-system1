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
    
    def _link_existing_client_if_any(self, customer: Customer):
        """Try to find an existing client in Invoice Ninja by email and link it locally to avoid duplicates.
        If another local customer is already linked to that client, do NOT assign to this customer to honor the unique index.
        """
        try:
            if not customer or not (customer.email and customer.email.strip()):
                return None
            existing = self.invoice_service.find_client_by_email(customer.email)
            if existing:
                existing_id = existing.get('id')
                # Check if another local customer already linked to this client
                already_linked = Customer.query.filter(
                    Customer.invoice_ninja_client_id == existing_id,
                    Customer.id != customer.id
                ).first()
                if already_linked:
                    # Return the client for use, but don't assign to avoid unique constraint violation
                    logger.info(
                        "Client %s already linked to local customer %s; skipping assignment for customer %s",
                        existing_id, already_linked.id, customer.id
                    )
                    return existing
                # Safe to link this customer
                customer.invoice_ninja_client_id = existing_id
                return existing
        except Exception as e:
            logger.warning(f"Failed to search existing client for {customer.email}: {e}")
        return None
    
    def create_client_from_customer(self, customer):
        """Create Invoice Ninja client from Tour Voucher customer"""
        try:
            # First, try to find & link an existing client by email
            existing = self._link_existing_client_if_any(customer)
            if existing:
                return existing

            # Ensure we have valid string values (not None)
            name = customer.name or customer.full_name or "Customer"
            email = customer.email or ""
            phone = customer.phone or ""
            address = getattr(customer, 'address', None) or ""
            
            client_data = self.invoice_service.create_client(
                name=name,
                email=email,
                phone=phone,
                address=address
            )
            
            if client_data:
                # Save Invoice Ninja client ID to customer record
                customer.invoice_ninja_client_id = client_data.get('id')
                return client_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating Invoice Ninja client: {e}")
            return None
    
    def get_or_create_client(self, customer):
        """Get existing or create new Invoice Ninja client for customer"""
        try:
            # Check if customer already has Invoice Ninja client ID
            if customer.invoice_ninja_client_id:
                client_data = self.invoice_service.get_client(customer.invoice_ninja_client_id)
                if client_data:
                    return client_data
            
            # If no ID or fetch failed, try to link by email before creating
            existing = self._link_existing_client_if_any(customer)
            if existing:
                return existing
            
            # Create new client
            return self.create_client_from_customer(customer)
            
        except Exception as e:
            logger.error(f"Error getting/creating Invoice Ninja client: {e}")
            return None
    
    def sync_booking_numbers(self, booking: Booking):
        """Fetch Quote/Invoice data from Invoice Ninja and persist number/status on booking.
        - Updates: booking.quote_number, booking.quote_status, booking.invoice_number
        Returns True if any update was made.
        """
        updated = False
        try:
            # Sync Quote
            if booking.quote_id:
                quote = self.invoice_service.get_quote(booking.quote_id) or {}
                q_number = quote.get('number') or quote.get('quote_number')
                q_status = (quote.get('status') or quote.get('status_name') or
                            str(quote.get('status_id') or '') or None)
                if q_number and q_number != booking.quote_number:
                    booking.quote_number = q_number
                    updated = True
                if q_status and q_status != booking.quote_status:
                    booking.quote_status = q_status
                    updated = True
            
            # Sync Invoice
            if booking.invoice_id:
                inv = self.invoice_service.get_invoice(booking.invoice_id) or {}
                i_number = inv.get('number') or inv.get('invoice_number')
                if i_number and i_number != booking.invoice_number:
                    booking.invoice_number = i_number
                    updated = True
        except Exception as e:
            logger.error(f"Error syncing booking numbers: {e}")
        return updated

    def create_invoice_from_booking(self, booking, quote_id=None):
        """Create invoice from booking - try new API first, fallback to old service"""
        logger.info(f"Converting quote {booking.quote_number or booking.quote_id} to invoice via new API")
        
        # Try new Invoice Ninja API first
        try:
            # Use existing quote_id from booking or provided quote_id
            target_quote_id = quote_id or booking.quote_id
            
            if target_quote_id:
                invoice_data = invoice_ninja_api.create_invoice_from_quote(target_quote_id)
                
                if invoice_data:
                    # Update booking with invoice information
                    booking.invoice_id = invoice_data['id']
                    booking.invoice_number = invoice_data['number']
                    logger.info(f"Invoice created successfully via new API: {invoice_data['number']}")
                    return invoice_data
                else:
                    logger.warning("New API returned None for invoice creation")
            else:
                logger.warning("No quote_id available for invoice creation")
                
        except Exception as e:
            logger.error(f"Error creating invoice via new API: {e}")
        
        # Fallback to old Invoice Ninja service
        logger.info("Falling back to old Invoice Ninja service for invoice creation")
        try:
            # Check if booking already has an invoice
            if booking.invoice_id and booking.invoice_number:
                logger.info(f"Invoice already exists: {booking.invoice_number}")
                return {
                    'id': booking.invoice_id,
                    'number': booking.invoice_number,
                    'status': 'existing'
                }
            
            # Create new invoice using old service
            client_data = self.service.create_or_get_client_from_booking(booking)
            if not client_data:
                logger.error("Failed to create/get Invoice Ninja client")
                return None
            
            # Create invoice from quote if available
            if booking.quote_id:
                invoice_data = self.service.create_invoice_from_quote(booking.quote_id)
            else:
                # Create invoice directly
                invoice_data = self.service.create_invoice_from_booking(booking, client_data['id'])
            
            if invoice_data:
                # Update booking with invoice information
                booking.invoice_id = invoice_data['id']
                booking.invoice_number = invoice_data['number']
                logger.info(f"Invoice created successfully via fallback: {invoice_data['number']}")
                return invoice_data
            else:
                logger.error("Failed to create invoice via fallback service")
                return None
                
        except Exception as e:
            logger.error(f"Error creating invoice from booking: {e}")
            return None
    
    def _create_invoice_old_method(self, booking, include_voucher_fee=True):
        """Fallback to old invoice creation method"""
        try:
            # Get or create client
            client = self.get_or_create_client(booking.customer)
            if not client:
                raise Exception("Failed to create/get Invoice Ninja client")
            
            # Prepare invoice line items
            items = []
            
            # Main tour item
            tour_item = {
                'product_key': f'TOUR-{booking.id}',
                'description': f'{booking.booking_type.title()} Booking - {booking.total_pax} Guests - {booking.hotel_name or "Tour Package"}',
                'cost': float(booking.total_amount),
                'quantity': 1,
                'tax_name': 'VAT',
                'tax_rate': 7.0  # 7% VAT for Thailand
            }
            items.append(tour_item)
            
            # Optional voucher processing fee
            if include_voucher_fee:
                voucher_fee = {
                    'product_key': 'VOUCHER-FEE',
                    'description': 'Voucher Processing Fee',
                    'cost': 100.0,  # 100 THB processing fee
                    'quantity': 1,
                    'tax_name': 'VAT',
                    'tax_rate': 7.0
                }
                items.append(voucher_fee)
            
            # Create invoice notes
            notes = f"""Booking ID: {booking.id}
Reference: {booking.booking_reference}
Travel Period: {booking.traveling_period_start.strftime('%d/%m/%Y') if booking.traveling_period_start else 'N/A'} - {booking.traveling_period_end.strftime('%d/%m/%Y') if booking.traveling_period_end else 'N/A'}
Hotel: {booking.hotel_name or 'N/A'}
Room Type: {booking.room_type or 'N/A'}
Special Requests: {booking.special_request or 'None'}

Generated automatically by Dhakul Chan Management System"""
            
            # Set due date (14 days from today)
            due_date = datetime.now() + timedelta(days=14)
            
            # Create the invoice
            invoice_data = self.invoice_service.create_invoice(
                client_id=client.get('id'),
                items=items,
                notes=notes,
                due_date=due_date.strftime('%Y-%m-%d')
            )
            
            if invoice_data:
                # Save Invoice Ninja invoice ID to booking record
                booking.invoice_id = invoice_data.get('id')
                booking.invoice_number = invoice_data.get('number') or booking.invoice_number
                return invoice_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating invoice from booking: {e}")
            return None
    
    def create_quote_from_booking(self, booking):
        """Create quote from booking - try new API first, fallback to old service"""
        logger.info(f"Creating quote for booking {booking.id}")
        
        # Try new Invoice Ninja API first
        try:
            booking_data = self._prepare_booking_data_for_api(booking)
            quote_data = invoice_ninja_api.create_quote(booking_data)
            
            if quote_data:
                # Update booking with quote information
                booking.quote_id = quote_data['id']
                booking.quote_number = quote_data['number']
                logger.info(f"Quote created successfully via new API: {quote_data['number']}")
                return quote_data
            else:
                logger.warning("New API returned None for quote creation")
                
        except Exception as e:
            logger.error(f"Error creating quote via new API: {e}")
        
        # Fallback to old Invoice Ninja service
        logger.info("Falling back to old Invoice Ninja service for quote creation")
        try:
            # Check if booking already has a quote
            if booking.quote_id and booking.quote_number:
                # Get existing quote
                client_data = self.service.get_client(booking.quote_id)
                if client_data:
                    logger.info(f"Quote already exists: {booking.quote_number}")
                    return {
                        'id': booking.quote_id,
                        'number': booking.quote_number,
                        'status': booking.quote_status or 'draft'
                    }
            
            # Create new quote using old service
            client_data = self.service.create_or_get_client_from_booking(booking)
            if not client_data:
                logger.error("Failed to create/get Invoice Ninja client")
                return None
            
            quote_data = self.service.create_quote_from_booking(booking, client_data['id'])
            
            if quote_data:
                # Update booking with quote information
                booking.quote_id = quote_data['id']
                booking.quote_number = quote_data['number']
                booking.quote_status = quote_data.get('status_name', 'draft')
                logger.info(f"Quote created successfully via fallback: {quote_data['number']}")
                return quote_data
            else:
                logger.error("Failed to create quote via fallback service")
                return None
                
        except Exception as e:
            logger.error(f"Error creating quote from booking: {e}")
            return None
    
    def _create_quote_old_method(self, booking):
        """Fallback to old quote creation method"""
        try:
            # Get or create client
            client = self.get_or_create_client(booking.customer)
            if not client:
                raise Exception("Failed to create/get Invoice Ninja client")
            
            # Prepare quote line items (same as invoice)
            items = []
            
            tour_item = {
                'product_key': f'TOUR-{booking.id}',
                'description': f'{booking.booking_type.title()} Booking - {booking.total_pax} Guests - {booking.hotel_name or "Tour Package"}',
                'cost': float(booking.total_amount),
                'quantity': 1,
                'tax_name': 'VAT',
                'tax_rate': 7.0
            }
            items.append(tour_item)
            
            # Create quote notes in the requested format
            total_amount = float(booking.total_amount) if booking.total_amount else 0
            notes = f"""Quote for Booking ID: {booking.id} 
Reference: {booking.booking_reference} 
Travel Period: {booking.traveling_period_start.strftime('%d/%m/%Y') if booking.traveling_period_start else 'Traveling from?'} - {booking.traveling_period_end.strftime('%d/%m/%Y') if booking.traveling_period_end else 'Traveling to?'}

Special Requests: {booking.special_request or 'None'}
Grand Total: THB {total_amount:,.2f}
----------------------------------------
Generated automatically by Dhakul Chan Management System 1.0"""
            
            # Set quote validity (30 days)
            valid_until = datetime.now() + timedelta(days=30)
            
            # Create the quote
            quote_data = self.invoice_service.create_quote(
                client_id=client.get('id'),
                items=items,
                notes=notes,
                due_date=valid_until.strftime('%Y-%m-%d')
            )
            
            if quote_data:
                # Save Quote ID to booking record
                booking.quote_id = quote_data.get('id')
                booking.quote_number = quote_data.get('number') or booking.quote_number
                booking.quote_status = (quote_data.get('status') or quote_data.get('status_name') or
                                        str(quote_data.get('status_id') or '') or booking.quote_status)
                return quote_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating quote from booking: {e}")
            return None
    
    def convert_quote_to_invoice(self, booking):
        """Convert booking quote to invoice"""
        try:
            if not booking.quote_id:
                raise Exception("No quote ID found for this booking")
            
            # Convert quote to invoice
            invoice_data = self.invoice_service.convert_quote_to_invoice(booking.quote_id)
            
            if invoice_data:
                booking.invoice_id = invoice_data.get('id')
                booking.invoice_number = invoice_data.get('number') or booking.invoice_number
                return invoice_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error converting quote to invoice: {e}")
            return None
    
    def send_invoice_to_customer(self, booking):
        """Send invoice via email to customer"""
        try:
            if not booking.invoice_id:
                raise Exception("No invoice ID found for this booking")
            
            result = self.invoice_service.send_invoice_email(booking.invoice_id)
            return result is not None
            
        except Exception as e:
            logger.error(f"Error sending invoice email: {e}")
            return False
    
    def mark_booking_paid(self, booking, payment_amount=None):
        """Mark booking invoice as paid"""
        try:
            if not booking.invoice_id:
                raise Exception("No invoice ID found for this booking")
            
            amount = payment_amount or booking.total_amount
            payment_data = self.invoice_service.mark_invoice_paid(
                booking.invoice_id,
                amount=float(amount)
            )
            
            if payment_data:
                booking.status = 'paid'
                return payment_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error marking invoice as paid: {e}")
            return None
    
    def _prepare_booking_data_for_api(self, booking):
        """Prepare booking data for Invoice Ninja API"""
        # Get products using the proper method
        products = []
        total_amount = 0
        
        # Use get_products() method to parse JSON string
        booking_products = booking.get_products()
        
        if booking_products and isinstance(booking_products, list):
            for product in booking_products:
                # Handle both dict and object formats
                if isinstance(product, dict):
                    product_data = {
                        'name': product.get('name', product.get('service_name', 'Unknown Service')),
                        'price': float(product.get('price', product.get('unit_price', 0))),
                        'quantity': int(product.get('quantity', product.get('qty', 1)))
                    }
                else:
                    # If it's an object, access attributes
                    product_data = {
                        'name': getattr(product, 'name', getattr(product, 'service_name', 'Unknown Service')),
                        'price': float(getattr(product, 'price', getattr(product, 'unit_price', 0))),
                        'quantity': int(getattr(product, 'quantity', getattr(product, 'qty', 1)))
                    }
                
                products.append(product_data)
                total_amount += product_data['price'] * product_data['quantity']
        else:
            # Fallback: use booking total_amount as single product
            products.append({
                'name': f'{booking.booking_type.title()} Package',
                'price': float(booking.total_amount or 0),
                'quantity': 1
            })
            total_amount = float(booking.total_amount or 0)
        
        # Get customer info
        customer_name = ''
        customer_email = ''
        customer_phone = ''
        
        if booking.customer:
            customer_name = booking.customer.name or booking.customer.full_name or ''
            customer_email = booking.customer.email or ''
            customer_phone = booking.customer.phone or ''
        elif booking.party_name:
            customer_name = booking.party_name
        
        return {
            'id': booking.id,
            'booking_reference': booking.booking_reference,
            'customer_name': customer_name,
            'customer_email': customer_email,
            'customer_phone': customer_phone,
            'arrival_date': booking.arrival_date.strftime('%Y-%m-%d') if booking.arrival_date else None,
            'departure_date': booking.departure_date.strftime('%Y-%m-%d') if booking.departure_date else None,
            'special_requests': booking.special_request or '',
            'products': products,
            'total_amount': f"{total_amount:.2f}"
        }
