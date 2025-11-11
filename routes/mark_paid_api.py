from flask import Blueprint, request, jsonify, current_app
from models.booking import Booking, db
from datetime import datetime
import logging

# Create a separate blueprint for this API to avoid conflicts
mark_paid_bp = Blueprint('mark_paid_api', __name__)

logger = logging.getLogger(__name__)

def create_invoice_from_booking(booking, amount_float, bank_name):
    """Create invoice record from booking when marking as paid"""
    try:
        print(f"🧾 create_invoice_from_booking called for booking {booking.id}", flush=True)
        # Try to import Invoice model
        try:
            from models.invoice import Invoice
            print("✅ Invoice model imported successfully", flush=True)
            current_app.logger.info("✅ Invoice model imported successfully")
        except ImportError as e:
            print(f"❌ Invoice model not found: {e}", flush=True)
            current_app.logger.error(f"❌ Invoice model not found: {e}")
            return None
        
        # Check if invoice already exists for this booking
        existing_invoice = Invoice.query.filter_by(booking_id=booking.id).first()
        if existing_invoice:
            print(f"📋 Invoice already exists for booking {booking.id}: {existing_invoice.invoice_number}", flush=True)
            current_app.logger.info(f"📋 Invoice already exists for booking {booking.id}: {existing_invoice.invoice_number}")
            return existing_invoice
        
        print(f"🆕 No existing invoice for booking {booking.id}, creating new one", flush=True)
        
        # Generate invoice number (same format as quote numbers)
        invoice_number = generate_invoice_number()
        print(f"🔢 Generated invoice number: {invoice_number}", flush=True)
        current_app.logger.info(f"🔢 Generated invoice number: {invoice_number}")
        
        # Create new invoice
        invoice = Invoice(
            booking_id=booking.id,
            quote_id=booking.quote_id if hasattr(booking, 'quote_id') else None,
            invoice_number=invoice_number,
            invoice_date=datetime.now().date(),
            due_date=datetime.now().date(),  # Due immediately for paid bookings
            status='paid',  # Since we're marking as paid
            title=f"Invoice for Booking #{booking.id}",
            description=getattr(booking, 'description', f'Services for booking {booking.booking_reference}'),
            subtotal=amount_float,
            tax_rate=0.0,  # Default 0% tax
            tax_amount=0.0,
            discount_amount=0.0,
            total_amount=amount_float,
            payment_method=f'Bank Transfer - {bank_name}',
            paid_amount=amount_float,
            paid_date=datetime.now().date(),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        db.session.add(invoice)
        db.session.flush()  # Get the invoice ID
        print(f"💾 Added invoice to session, ID: {invoice.id}", flush=True)
        
        # Update booking with invoice_id if the field exists
        if hasattr(booking, 'invoice_id'):
            booking.invoice_id = invoice.id
            print(f"🔗 Linked booking {booking.id} to invoice {invoice.id}", flush=True)
            current_app.logger.info(f"🔗 Linked booking {booking.id} to invoice {invoice.id}")
        
        print(f"✅ Created invoice {invoice_number} for booking {booking.id}", flush=True)
        current_app.logger.info(f"✅ Created invoice {invoice_number} for booking {booking.id}")
        return invoice
        
    except Exception as e:
        current_app.logger.error(f"❌ Error creating invoice for booking {booking.id}: {e}")
        import traceback
        current_app.logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        return None

def generate_invoice_number():
    """Generate invoice number in format INV25110001"""
    try:
        from models.invoice import Invoice
        
        # Find the highest existing invoice number with new format INV251100XX
        latest_invoice = Invoice.query.filter(
            Invoice.invoice_number.like('INV2511%')
        ).order_by(Invoice.invoice_number.desc()).first()
        
        if latest_invoice and latest_invoice.invoice_number.startswith('INV2511'):
            try:
                # Extract numeric part from invoice number (last 4 digits)
                numeric_part = latest_invoice.invoice_number[7:]  # Remove 'INV2511' prefix
                last_number = int(numeric_part)
                new_number = last_number + 1
                print(f"🔢 Last invoice: {latest_invoice.invoice_number}, next number: {new_number}", flush=True)
            except (ValueError, IndexError):
                # If parsing fails, start from 0001
                new_number = 1
                print(f"🔢 Error parsing last invoice number, starting from 1", flush=True)
        else:
            # No existing invoice with new format, start from 0001
            new_number = 1
            print(f"🔢 No existing invoices, starting from 1", flush=True)
        
        # Make sure the number is unique
        max_attempts = 100
        attempts = 0
        while attempts < max_attempts:
            candidate_number = f'INV2511{new_number:04d}'
            existing = Invoice.query.filter(Invoice.invoice_number == candidate_number).first()
            if not existing:
                print(f"✅ Generated unique invoice number: {candidate_number}", flush=True)
                return candidate_number
            new_number += 1
            attempts += 1
            print(f"⚠️  Invoice {candidate_number} exists, trying {new_number}", flush=True)
        
        # If we can't find a unique number, fallback
        print(f"❌ Could not generate unique invoice number after {max_attempts} attempts", flush=True)
        import time
        fallback = f'INV2511{int(time.time()) % 10000:04d}'
        print(f"🔄 Using fallback: {fallback}", flush=True)
        return fallback
            
    except Exception as e:
        print(f"❌ Error generating invoice number: {e}", flush=True)
        # Fallback to timestamp-based number
        import time
        return f'INV2511{int(time.time()) % 10000:04d}'

@mark_paid_bp.route('/booking/api/<int:booking_id>/mark-paid-v2', methods=['POST'])
def api_mark_as_paid_v2(booking_id):
    """Simple API endpoint to mark booking as paid"""
    try:
        print(f"🔔 API mark-paid-v2 called for booking {booking_id}", flush=True)
        current_app.logger.info(f"🔔 API mark-paid-v2 called for booking {booking_id}")
        
        booking = Booking.query.get_or_404(booking_id)
        print(f"📋 Found booking {booking_id} with status: {booking.status}", flush=True)
        current_app.logger.info(f"📋 Found booking {booking_id} with status: {booking.status}")
        
        # Get payment data from request
        data = request.get_json()
        current_app.logger.info(f"📦 Received payment data: {data}")
        
        if not data:
            return jsonify({'success': False, 'error': 'ไม่พบข้อมูลการชำระเงิน'}), 400
        
        # Check booking status first
        if booking.status != 'quoted':
            return jsonify({
                'success': False, 
                'error': f'ไม่สามารถชำระเงินได้ Booking ต้องมีสถานะ Quoted ก่อน (สถานะปัจจุบัน: {booking.status})'
            }), 400
        
        # Basic data extraction
        amount = data.get('amount', '0')
        bank_name = data.get('bank_name', 'Unknown')
        product_type = data.get('product_type', 'tour')
        
        try:
            amount_float = float(str(amount).replace(',', ''))
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'จำนวนเงินไม่ถูกต้อง'}), 400
        
        current_app.logger.info(f"💰 Processing payment: {amount_float} THB via {bank_name}")
        
        # Create invoice automatically when marking as paid (before updating booking)
        print(f"🧾 Attempting to create invoice for booking {booking_id}", flush=True)
        current_app.logger.info(f"🧾 Attempting to create invoice for booking {booking_id}")
        
        invoice = None
        try:
            invoice = create_invoice_from_booking(booking, amount_float, bank_name)
            print(f"📋 Invoice creation result: {invoice}", flush=True)
            if invoice:
                print(f"✅ Invoice created: {invoice.invoice_number}", flush=True)
            else:
                print(f"❌ Invoice creation returned None", flush=True)
        except Exception as invoice_error:
            print(f"❌ Invoice creation failed: {invoice_error}", flush=True)
            current_app.logger.error(f"❌ Invoice creation failed: {invoice_error}")
            import traceback
            print(f"❌ Invoice creation traceback: {traceback.format_exc()}", flush=True)
        
        # Update booking status after invoice creation
        booking.status = 'paid'
        booking.is_paid = True
        booking.invoice_paid_date = datetime.now()
        
        # Commit all changes together
        db.session.commit()
        
        success_message = f'ชำระเงินเรียบร้อยแล้ว! จำนวน {amount_float:,.2f} บาท ผ่าน {bank_name}'
        if invoice:
            success_message += f' (Invoice: {invoice.invoice_number})'
        
        print(f"✅ Booking {booking_id} marked as paid with amount {amount_float} THB via {bank_name}")
        current_app.logger.info(f"✅ Booking {booking_id} marked as paid with amount {amount_float} THB via {bank_name}")
        if invoice:
            print(f"✅ Invoice {invoice.invoice_number} created automatically")
            current_app.logger.info(f"✅ Invoice {invoice.invoice_number} created automatically")
        else:
            print(f"⚠️  Invoice creation failed for booking {booking_id}")
            current_app.logger.warning(f"⚠️  Invoice creation failed for booking {booking_id}")
        
        return jsonify({
            'success': True, 
            'message': success_message,
            'status': booking.status,
            'is_paid': booking.is_paid,
            'paid_at': booking.invoice_paid_date.isoformat() if booking.invoice_paid_date else None,
            'invoice_number': invoice.invoice_number if invoice else None
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ Error marking booking {booking_id} as paid: {str(e)}")
        import traceback
        current_app.logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': f'เกิดข้อผิดพลาด: {str(e)}'}), 500