from flask import Blueprint, request, jsonify, current_app
from models.booking import Booking, db
from datetime import datetime
import logging

# Create a separate blueprint for this API to avoid conflicts
mark_paid_bp = Blueprint('mark_paid_api', __name__)

logger = logging.getLogger(__name__)

def create_invoice_from_booking(booking, amount_float, bank_name, paid_date=None, air_ticket_cost=0.0, notes=None, 
                                quote_number=None, transportation_fee=0.0, advance_expense=0.0, tour_fee=0.0, 
                                vat=0.0, withholding_tax=0.0, total_tour_fee=0.0):
    """Create invoice record from booking when marking as paid with auto-sync of booking data"""
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
            
            # Update existing invoice with booking sync data
            sync_booking_data_to_invoice(existing_invoice, booking, amount_float, bank_name, paid_date, air_ticket_cost, notes,
                                        quote_number, transportation_fee, advance_expense, tour_fee, vat, withholding_tax, total_tour_fee)
            return existing_invoice
        
        print(f"🆕 No existing invoice for booking {booking.id}, creating new one", flush=True)
        
        # Generate invoice number (same format as quote numbers)
        invoice_number = generate_invoice_number()
        print(f"🔢 Generated invoice number: {invoice_number}", flush=True)
        current_app.logger.info(f"🔢 Generated invoice number: {invoice_number}")
        
        # Get customer information
        customer_name = ""
        customer_id = booking.customer_id
        if hasattr(booking, 'customer') and booking.customer:
            customer_name = booking.customer.name if hasattr(booking.customer, 'name') else ""
        
        # Use provided paid_date or default to today
        actual_paid_date = paid_date if paid_date else datetime.now().date()
        
        # Create new invoice with auto-synced booking data
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
            paid_date=actual_paid_date,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            # Payment details
            air_ticket_cost=air_ticket_cost,
            notes=notes,
            # Calculation fields
            transportation_fee=transportation_fee,
            advance_expense=advance_expense,
            tour_fee=tour_fee,
            vat=vat,
            withholding_tax=withholding_tax,
            total_tour_fee=total_tour_fee,
            # Auto-sync booking data
            quote_number=quote_number or (booking.quote_number if hasattr(booking, 'quote_number') else None),
            customer_id=customer_id,
            cust_name=customer_name,
            booking_type=booking.booking_type if hasattr(booking, 'booking_type') else None,
            total_pax=booking.total_pax if hasattr(booking, 'total_pax') else None,
            arrival_date=booking.arrival_date if hasattr(booking, 'arrival_date') else None,
            departure_date=booking.departure_date if hasattr(booking, 'departure_date') else None,
            guest_list=booking.guest_list if hasattr(booking, 'guest_list') else None,
            flight_info=booking.flight_info if hasattr(booking, 'flight_info') else None
        )
        
        db.session.add(invoice)
        db.session.flush()  # Get the invoice ID
        print(f"💾 Added invoice to session, ID: {invoice.id}", flush=True)
        print(f"📊 Auto-synced data: customer={customer_name}, type={booking.booking_type}, pax={booking.total_pax}", flush=True)
        
        # Update booking with invoice_id if the field exists
        if hasattr(booking, 'invoice_id'):
            booking.invoice_id = invoice.id
            print(f"🔗 Linked booking {booking.id} to invoice {invoice.id}", flush=True)
            current_app.logger.info(f"🔗 Linked booking {booking.id} to invoice {invoice.id}")
        
        print(f"✅ Created invoice {invoice_number} for booking {booking.id} with auto-synced data", flush=True)
        current_app.logger.info(f"✅ Created invoice {invoice_number} for booking {booking.id} with auto-synced data")
        return invoice
        
    except Exception as e:
        current_app.logger.error(f"❌ Error creating invoice for booking {booking.id}: {e}")
        import traceback
        current_app.logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        return None

def sync_booking_data_to_invoice(invoice, booking, amount_float, bank_name, paid_date=None, air_ticket_cost=0.0, notes=None, quote_number=None, transportation_fee=0.0, advance_expense=0.0, tour_fee=0.0, vat=0.0, withholding_tax=0.0, total_tour_fee=0.0):
    """Sync booking data to existing invoice"""
    try:
        print(f"🔄 Syncing booking data to existing invoice {invoice.id}", flush=True)
        
        # Get customer information
        customer_name = ""
        if hasattr(booking, 'customer') and booking.customer:
            customer_name = booking.customer.name if hasattr(booking.customer, 'name') else ""
        
        # Update invoice with booking sync data
        invoice.quote_number = quote_number or (booking.quote_number if hasattr(booking, 'quote_number') else invoice.quote_number)
        invoice.customer_id = booking.customer_id
        invoice.cust_name = customer_name
        invoice.booking_type = booking.booking_type if hasattr(booking, 'booking_type') else invoice.booking_type
        invoice.total_pax = booking.total_pax if hasattr(booking, 'total_pax') else invoice.total_pax
        invoice.arrival_date = booking.arrival_date if hasattr(booking, 'arrival_date') else invoice.arrival_date
        invoice.departure_date = booking.departure_date if hasattr(booking, 'departure_date') else invoice.departure_date
        invoice.guest_list = booking.guest_list if hasattr(booking, 'guest_list') else invoice.guest_list
        invoice.flight_info = booking.flight_info if hasattr(booking, 'flight_info') else invoice.flight_info
        
        # Update payment info
        invoice.total_amount = amount_float
        invoice.paid_amount = amount_float
        invoice.payment_method = f'Bank Transfer - {bank_name}'
        invoice.air_ticket_cost = air_ticket_cost
        if notes:
            invoice.notes = notes
        if paid_date:
            invoice.paid_date = paid_date
        invoice.status = 'paid'
        invoice.updated_at = datetime.now()
        
        # Update calculation fields
        invoice.transportation_fee = transportation_fee
        invoice.advance_expense = advance_expense
        invoice.tour_fee = tour_fee
        invoice.vat = vat
        invoice.withholding_tax = withholding_tax
        invoice.total_tour_fee = total_tour_fee
        
        db.session.flush()
        print(f"✅ Synced booking data to invoice {invoice.id}", flush=True)
        current_app.logger.info(f"✅ Synced booking data to invoice {invoice.id}")
        
    except Exception as e:
        print(f"❌ Error syncing booking data to invoice: {e}", flush=True)
        current_app.logger.error(f"❌ Error syncing booking data to invoice: {e}")

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
        received_date_str = data.get('received_date', '')  # Format: DD/MM/YYYY
        air_ticket_cost_str = data.get('air_ticket_cost', '0')
        details = data.get('details', '')  # Will be saved to invoice.notes
        quote_number = data.get('quote_number', '')
        
        # Extract calculation fields
        transportation_fee_str = data.get('transportation_fee', '0')
        advance_expense_str = data.get('advance_expense', '0')
        tour_fee_str = data.get('tour_fee', '0')
        vat_str = data.get('vat', '0')
        withholding_tax_str = data.get('withholding_tax', '0')
        total_tour_fee_str = data.get('total_tour_fee', '0')
        
        # Parse air_ticket_cost
        try:
            air_ticket_cost = float(str(air_ticket_cost_str).replace(',', ''))
        except (ValueError, TypeError):
            air_ticket_cost = 0.0
        
        # Parse calculation fields
        try:
            transportation_fee = float(str(transportation_fee_str).replace(',', ''))
        except (ValueError, TypeError):
            transportation_fee = 0.0
        
        try:
            advance_expense = float(str(advance_expense_str).replace(',', ''))
        except (ValueError, TypeError):
            advance_expense = 0.0
        
        try:
            tour_fee = float(str(tour_fee_str).replace(',', ''))
        except (ValueError, TypeError):
            tour_fee = 0.0
        
        try:
            vat = float(str(vat_str).replace(',', ''))
        except (ValueError, TypeError):
            vat = 0.0
        
        try:
            withholding_tax = float(str(withholding_tax_str).replace(',', ''))
        except (ValueError, TypeError):
            withholding_tax = 0.0
        
        try:
            total_tour_fee = float(str(total_tour_fee_str).replace(',', ''))
        except (ValueError, TypeError):
            total_tour_fee = 0.0
        
        # Parse paid date from DD/MM/YYYY format
        paid_date = None
        if received_date_str:
            try:
                # Parse DD/MM/YYYY format
                parts = received_date_str.split('/')
                if len(parts) == 3:
                    day = int(parts[0])
                    month = int(parts[1])
                    year = int(parts[2])
                    paid_date = datetime(year, month, day).date()
                    
                    # Validate that paid_date is not in the future
                    if paid_date > datetime.now().date():
                        return jsonify({
                            'success': False, 
                            'error': 'วันที่รับเงินต้องไม่อยู่ในอนาคต'
                        }), 400
                    
                    print(f"📅 Parsed paid date: {paid_date}", flush=True)
            except (ValueError, IndexError) as e:
                return jsonify({
                    'success': False, 
                    'error': f'รูปแบบวันที่ไม่ถูกต้อง (ใช้รูปแบบ วว/ดด/ปปปป): {str(e)}'
                }), 400
        
        try:
            amount_float = float(str(amount).replace(',', ''))
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'จำนวนเงินไม่ถูกต้อง'}), 400
        
        current_app.logger.info(f"💰 Processing payment: {amount_float} THB via {bank_name} on {paid_date or 'today'}")
        
        # Create invoice automatically when marking as paid (before updating booking)
        print(f"🧾 Attempting to create invoice for booking {booking_id}", flush=True)
        current_app.logger.info(f"🧾 Attempting to create invoice for booking {booking_id}")
        
        invoice = None
        try:
            invoice = create_invoice_from_booking(
                booking, amount_float, bank_name, paid_date, air_ticket_cost, details, 
                quote_number, transportation_fee, advance_expense, tour_fee, vat, withholding_tax, total_tour_fee
            )
            print(f"📋 Invoice creation result: {invoice}", flush=True)
            if invoice:
                print(f"✅ Invoice created: {invoice.invoice_number}", flush=True)
                print(f"💵 Air ticket cost: {air_ticket_cost}, Transportation: {transportation_fee}, Advance: {advance_expense}", flush=True)
                print(f"💵 Tour fee: {tour_fee}, VAT: {vat}, WHT: {withholding_tax}, Total: {total_tour_fee}", flush=True)
                print(f"📝 Quote Number: {quote_number}, Notes: {details[:50] if details else 'None'}", flush=True)
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
        if paid_date:
            success_message += f' วันที่ {paid_date.strftime("%d/%m/%Y")}'
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