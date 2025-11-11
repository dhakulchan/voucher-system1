"""
Invoice Sync Service  
ระบบ sync สถานะ invoice จาก Invoice Ninja กลับมาที่ booking (Pure Sync - No Creation)
"""

from models.booking import Booking
from services.invoice_ninja_api import invoice_ninja_api
from extensions import db
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class InvoiceSyncService:
    """Service for syncing invoice data from Invoice Ninja (no creation)"""
    
    def sync_invoice_for_quote(self, booking_id: int) -> dict:
        """Sync invoice data from Invoice Ninja for a booking with quote"""
        booking = Booking.query.get(booking_id)
        
        if not booking:
            return {'success': False, 'error': 'Booking not found'}
        
        if not booking.quote_id:
            return {'success': False, 'error': 'No quote found - cannot sync invoice'}
        
        try:
            logger.info(f"Syncing invoice for booking {booking_id} with quote {booking.quote_id}")
            
            # Search for invoices related to this quote
            invoice_data = self._find_invoice_by_quote(booking.quote_id)
            
            if invoice_data:
                logger.info(f"Found invoice data: {invoice_data.get('number', 'Unknown')} - Status: {invoice_data.get('status_name', 'Unknown')}")
                
                # Update booking with invoice data
                old_status = booking.invoice_status
                old_number = booking.invoice_number
                
                booking.invoice_id = invoice_data['id']
                booking.invoice_number = invoice_data['number']
                booking.invoice_status = invoice_data['status_name']
                booking.invoice_amount = invoice_data['amount']
                booking.is_paid = invoice_data['is_paid']  # Update is_paid status
                booking.last_sync_date = datetime.now()
                
                # Set paid date if newly paid
                if invoice_data['is_paid'] and not booking.invoice_paid_date:
                    booking.invoice_paid_date = datetime.now()
                
                db.session.commit()
                
                # Prepare response
                result = {
                    'success': True,
                    'invoice_number': booking.invoice_number,
                    'is_paid': booking.is_paid or False,
                    'payment_status': booking.get_payment_status_display(),
                    'can_create_voucher': booking.can_create_voucher(),
                    'amount': float(booking.invoice_amount or 0),
                    'sync_date': booking.last_sync_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'message': f'Invoice {booking.invoice_number} synced successfully',
                    'invoice_data': invoice_data  # Include raw invoice data
                }
                
                if old_number != booking.invoice_number:
                    result['message'] += f' (new invoice found)'
                if old_status != booking.invoice_status:
                    result['message'] += f' - Status: {old_status or "None"} → {booking.invoice_status}'
                
                logger.info(f"Invoice sync successful: {result['message']}")
                return result
                
            else:
                # No invoice found yet
                booking.last_sync_date = datetime.now()
                db.session.commit()
                
                # Check if this is due to API not being configured
                if not invoice_ninja_api.enabled:
                    return {
                        'success': True,
                        'invoice_found': False,
                        'message': 'Demo Mode: Using mock data since Invoice Ninja API is not configured. In production, connect to real Invoice Ninja API.',
                        'sync_date': booking.last_sync_date.strftime('%Y-%m-%d %H:%M:%S')
                    }
                else:
                    return {
                        'success': True,
                        'invoice_found': False,
                        'message': 'No invoice found for this quote yet. Please create invoice in Invoice Ninja first.',
                        'sync_date': booking.last_sync_date.strftime('%Y-%m-%d %H:%M:%S')
                    }
                
        except Exception as e:
            logger.error(f"Error syncing invoice for booking {booking_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def _find_invoice_by_quote(self, quote_id: str) -> dict:
        """Find invoice associated with a quote"""
        try:
            logger.info(f"Searching for invoice related to quote {quote_id}")
            
            # Method 1: Get quote details and check for invoice_id
            quote_data = invoice_ninja_api.get_quote(quote_id)
            logger.info(f"Quote data: {quote_data}")
            
            if quote_data and quote_data.get('invoice_id'):
                logger.info(f"Found invoice_id in quote: {quote_data['invoice_id']}")
                invoice = invoice_ninja_api.get_invoice_status(quote_data['invoice_id'])
                if invoice:
                    logger.info(f"Successfully retrieved invoice from quote.invoice_id")
                    return invoice
            
            # Method 2: Search invoices by quote number
            if quote_data and quote_data.get('number'):
                logger.info(f"Searching invoices by quote number: {quote_data['number']}")
                invoices = self._search_invoices_by_quote(quote_data['number'])
                if invoices:
                    logger.info(f"Found {len(invoices)} invoices via quote number search")
                    return invoices[0]  # Return first match
            
            # Method 3: Search all invoices for converted quotes (broader search)
            logger.info(f"Performing comprehensive invoice search...")
            invoices = self._search_all_invoices_for_quote(quote_id, quote_data.get('number') if quote_data else None)
            if invoices:
                logger.info(f"Found {len(invoices)} invoices via comprehensive search")
                return invoices[0]
            
            # Method 4: Use mock data if API not available
            if not invoice_ninja_api.enabled:
                logger.info(f"API not enabled, generating mock data")
                return self._generate_mock_invoice_data(quote_id)
            
            logger.warning(f"No invoice found for quote {quote_id} after all search methods")
            return None
            
        except Exception as e:
            logger.error(f"Error finding invoice for quote {quote_id}: {e}")
            return None
    
    def _search_invoices_by_quote(self, quote_number: str) -> list:
        """Search for invoices that reference a quote number"""
        try:
            # Search invoices with quote number in notes
            result = invoice_ninja_api._make_request('GET', f'invoices?filter={quote_number}')
            
            # Handle string response from mock (return empty list)
            if isinstance(result, str):
                logger.info(f"Mock API returned string response, no invoices found")
                return []
            
            if 'data' in result and result['data']:
                invoices = []
                for invoice in result['data']:
                    # Check if quote number is mentioned in notes
                    notes = str(invoice.get('public_notes', '')) + str(invoice.get('private_notes', ''))
                    if quote_number in notes:
                        # Convert to standard format
                        invoices.append(self._format_invoice_data(invoice))
                
                return invoices
            
            return []
            
        except Exception as e:
            logger.error(f"Error searching invoices by quote {quote_number}: {e}")
            return []
    
    def _search_all_invoices_for_quote(self, quote_id: str, quote_number: str = None) -> list:
        """Comprehensive search for invoices related to a quote"""
        try:
            # Get all recent invoices and search for relationships
            result = invoice_ninja_api._make_request('GET', 'invoices?per_page=100&sort=id|desc')
            
            # Handle string response from mock (return empty list)
            if isinstance(result, str):
                logger.info(f"Mock API returned string response, no invoices found")
                return []
            
            if 'data' in result and result['data']:
                invoices = []
                for invoice in result['data']:
                    # Method 1: Check if quote_id is in any field
                    invoice_str = str(invoice)
                    if quote_id in invoice_str:
                        invoices.append(self._format_invoice_data(invoice))
                        continue
                    
                    # Method 2: Check quote number in notes or references
                    if quote_number:
                        notes = str(invoice.get('public_notes', '')) + str(invoice.get('private_notes', ''))
                        po_number = str(invoice.get('po_number', ''))
                        if quote_number in notes or quote_number in po_number:
                            invoices.append(self._format_invoice_data(invoice))
                            continue
                    
                    # Method 3: Check for converted quotes (often have similar amounts/dates)
                    # This is a fallback method when direct relationships aren't found
                
                return invoices
            
            return []
            
        except Exception as e:
            logger.error(f"Error in comprehensive invoice search for quote {quote_id}: {e}")
            return []
    
    def _format_invoice_data(self, invoice_raw: dict) -> dict:
        """Format raw invoice data to standard format"""
        # Invoice Ninja status mapping (comprehensive)
        status_map = {
            1: 'draft',
            2: 'sent', 
            3: 'viewed',
            4: 'paid',
            5: 'cancelled',
            6: 'reversed',
            7: 'partial',
            8: 'paid',  # alternative paid status
            10: 'overdue',
            11: 'pending',
            12: 'approved'
        }
        
        status_id = invoice_raw.get('status_id', 1)
        status_name = status_map.get(status_id, f'status_{status_id}')  # More informative fallback
        
        # Alternative: check for string status in response
        if 'status' in invoice_raw and isinstance(invoice_raw['status'], str):
            status_name = invoice_raw['status'].lower()
        
        paid_amount = float(invoice_raw.get('paid_to_date', 0))
        total_amount = float(invoice_raw.get('amount', 0))
        
        # Determine if paid based on multiple criteria
        is_paid = (
            status_id == 4 or 
            status_id == 8 or 
            status_name.lower() in ['paid', 'payment_complete', 'completed'] or
            (paid_amount > 0 and paid_amount >= total_amount)
        )
        
        formatted_data = {
            'id': invoice_raw['id'],
            'number': invoice_raw['number'],
            'status_id': status_id,
            'status_name': status_name,
            'amount': total_amount,
            'paid_amount': paid_amount,
            'is_paid': is_paid,
            'created_at': invoice_raw.get('created_at', ''),
            'updated_at': invoice_raw.get('updated_at', ''),
            'due_date': invoice_raw.get('due_date', ''),
            'quote_id': invoice_raw.get('quote_id'),
            'client_id': invoice_raw.get('client_id'),
            'public_notes': invoice_raw.get('public_notes', ''),
            'private_notes': invoice_raw.get('private_notes', '')
        }
        
        # Log detailed status information for debugging
        self.logger.info(f"Invoice {invoice_raw['number']} - Raw status_id: {status_id}, Mapped: {status_name}, Is Paid: {is_paid}")
        
        return formatted_data
    
    def _generate_mock_invoice_data(self, quote_id: str) -> dict:
        """Generate mock invoice data for testing"""
        import random
        
        # Simulate finding an invoice 90% of the time for quotes that exist
        if random.random() < 0.9:
            is_paid = random.random() < 0.3  # 30% chance of being paid (most are still pending)
            
            # Generate realistic invoice number
            invoice_num = f'INV{random.randint(10000, 99999)}'
            
            return {
                'id': f'inv_{quote_id[-8:]}',
                'number': invoice_num,
                'status_id': 4 if is_paid else 2,
                'status_name': 'paid' if is_paid else 'sent',
                'amount': 23800.00,
                'paid_to_date': 23800.00 if is_paid else 0,
                'is_paid': is_paid,
                'updated_at': datetime.now().isoformat(),
                'public_notes': f'Converted from Quote {quote_id}',
                'private_notes': f'System: Auto-converted from quote ID {quote_id}'
            }
        
        return None

# Initialize service
invoice_sync_service = InvoiceSyncService()
