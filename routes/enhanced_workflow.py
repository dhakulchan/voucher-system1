#!/usr/bin/env python3
"""
Enhanced Booking Workflow System
จัดการ workflow: quoted → Make as Paid → Sync to Invoice → Paid → Vouchered
"""

from flask import Blueprint, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from models.booking import Booking
from models.invoice import Invoice, InvoiceLineItem
from extensions import db
from datetime import datetime, date
import logging
import json
from decimal import Decimal

# สร้าง blueprint สำหรับ enhanced workflow
enhanced_workflow_bp = Blueprint('enhanced_workflow', __name__)
logger = logging.getLogger(__name__)

@enhanced_workflow_bp.route('/<int:booking_id>/workflow-make-paid', methods=['POST'])
@login_required
def workflow_make_paid(booking_id):
    """
    Step 1: Mark booking as Paid (from quoted status) + Auto Sync to Invoice
    - เปลี่ยน status จาก 'quoted' เป็น 'paid'
    - ตั้งค่า payment information
    - AUTO SYNC ข้อมูลทั้งหมดไปยัง Invoice system
    - Complete workflow in one step
    """
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        # ตรวจสอบ status ปัจจุบัน
        if booking.status != 'quoted':
            message = f'❌ Booking must be quoted to mark as paid. Current status: {booking.status}'
            if request.is_json:
                return jsonify({'success': False, 'message': message}), 400
            flash(message, 'error')
            return redirect(url_for('booking.view', id=booking_id))
        
        # รับข้อมูลจาก form/API
        payment_data = {}
        if request.is_json:
            payment_data = request.get_json() or {}
        else:
            payment_data = {
                'payment_method': request.form.get('payment_method', 'bank_transfer'),
                'payment_reference': request.form.get('payment_reference', ''),
                'payment_amount': request.form.get('payment_amount', ''),
                'payment_notes': request.form.get('payment_notes', ''),
                'invoice_number': request.form.get('invoice_number', ''),
                'auto_sync': request.form.get('auto_sync', 'true') == 'true',  # Auto sync by default
            }
        
        # อัปเดต booking status และ payment information
        booking.status = 'paid'
        booking.is_paid = True
        booking.paid_at = datetime.now()
        booking.invoice_paid_date = datetime.now()
        
        # ตั้งค่า invoice information
        if payment_data.get('invoice_number'):
            booking.invoice_number = payment_data['invoice_number']
        elif not booking.invoice_number:
            # สร้าง invoice number อัตโนมัติ
            booking.invoice_number = f"INV-{booking.booking_reference}"
        
        booking.invoice_status = 'paid'
        
        # บันทึกข้อมูล payment
        if payment_data.get('payment_amount'):
            booking.invoice_amount = str(payment_data['payment_amount'])
        
        # เพิ่ม notes ถ้ามี
        if payment_data.get('payment_notes'):
            current_notes = booking.admin_notes or ''
            payment_note = f"Payment: {payment_data['payment_notes']} (at {datetime.now().strftime('%Y-%m-%d %H:%M')})"
            booking.admin_notes = f"{current_notes}\n{payment_note}".strip()
        
        # 🚀 AUTO SYNC TO INVOICE SYSTEM
        if payment_data.get('auto_sync', True):
            try:
                # ตรวจสอบว่ามี invoice อยู่แล้วหรือไม่
                existing_invoice = Invoice.query.filter_by(booking_id=booking.id).first()
                
                if existing_invoice:
                    # อัปเดต invoice ที่มีอยู่แล้ว
                    invoice = existing_invoice
                    logger.info(f"🔄 Updating existing invoice {invoice.invoice_number} for booking {booking_id}")
                else:
                    # สร้าง invoice ใหม่
                    invoice = Invoice(
                        booking_id=booking.id,
                        quote_id=booking.quote_id,
                        invoice_number=booking.invoice_number,
                        title=f"Invoice for {booking.booking_reference}",
                        invoice_date=date.today(),
                        due_date=date.today(),  # Same day for paid invoices
                    )
                    db.session.add(invoice)
                    logger.info(f"✨ Creating new invoice {invoice.invoice_number} for booking {booking_id}")
                
                # อัปเดต invoice ด้วยข้อมูลจาก booking
                invoice.description = f"""Service: {booking.description or 'Tour Service'}
Flight Information: {booking.flight_info or 'N/A'}
Special Requests: {booking.special_request or 'None'}
Guest Details: {booking.adults} Adults, {booking.children} Children, {booking.infants} Infants
Arrival: {booking.arrival_date.strftime('%Y-%m-%d') if booking.arrival_date else 'TBD'}
Departure: {booking.departure_date.strftime('%Y-%m-%d') if booking.departure_date else 'TBD'}"""
                
                # ตั้งค่าราคา
                invoice.subtotal = Decimal(str(booking.total_amount)) if booking.total_amount else Decimal('0')
                invoice.tax_rate = Decimal('7.0')  # 7% VAT
                invoice.tax_amount = invoice.subtotal * invoice.tax_rate / 100
                invoice.total_amount = invoice.subtotal + invoice.tax_amount
                
                # ตั้งค่าสถานะ payment
                invoice.status = 'paid'
                invoice.payment_status = 'paid'
                invoice.paid_amount = invoice.total_amount
                invoice.balance_due = Decimal('0')
                invoice.paid_date = date.today()
                
                # ตั้งค่า payment information
                invoice.payment_method = payment_data.get('payment_method', 'Bank Transfer')
                invoice.payment_reference = payment_data.get('payment_reference', booking.booking_reference)
                
                # เพิ่ม notes
                sync_notes = f"Auto-synced from enhanced workflow at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                if payment_data.get('payment_notes'):
                    sync_notes += f"\nPayment Notes: {payment_data['payment_notes']}"
                invoice.notes = sync_notes
                
                # สร้าง line items สำหรับ products/services
                # ลบ line items เก่าก่อน
                if invoice.id:
                    InvoiceLineItem.query.filter_by(invoice_id=invoice.id).delete()
                
                # เพิ่ม main service line item
                main_service = InvoiceLineItem(
                    invoice_id=invoice.id if invoice.id else None,
                    description=booking.description or f"Tour Service - {booking.booking_reference}",
                    quantity=1,
                    unit_price=invoice.subtotal,
                    total_amount=invoice.subtotal
                )
                
                if invoice.id:  # Invoice มีอยู่แล้ว
                    db.session.add(main_service)
                else:  # Invoice ใหม่
                    invoice.line_items.append(main_service)
                
                # เพิ่ม products ถ้ามี
                if booking.products:
                    try:
                        products_data = json.loads(booking.products) if isinstance(booking.products, str) else booking.products
                        if isinstance(products_data, list):
                            for product in products_data:
                                if isinstance(product, dict) and 'name' in product:
                                    product_item = InvoiceLineItem(
                                        invoice_id=invoice.id if invoice.id else None,
                                        description=f"Product: {product.get('name', 'Unknown')}",
                                        quantity=product.get('quantity', 1),
                                        unit_price=Decimal(str(product.get('price', 0))),
                                        total_amount=Decimal(str(product.get('quantity', 1))) * Decimal(str(product.get('price', 0)))
                                    )
                                    
                                    if invoice.id:
                                        db.session.add(product_item)
                                    else:
                                        invoice.line_items.append(product_item)
                    except (json.JSONDecodeError, ValueError) as e:
                        logger.warning(f"Could not parse products data: {e}")
                
                # อัปเดต timestamps
                invoice.updated_at = datetime.now()
                
                # Commit เพื่อให้ได้ invoice.id สำหรับ line items
                db.session.commit()
                
                # อัปเดต booking invoice status
                booking.invoice_status = 'synchronized'
                booking.invoiced_at = datetime.now()
                
                # เพิ่ม auto sync note
                auto_sync_note = f"✅ Auto-synced to invoice table: {invoice.invoice_number} (ID: {invoice.id}) with complete data at {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                current_notes = booking.admin_notes or ''
                booking.admin_notes = f"{current_notes}\n{auto_sync_note}".strip()
                
                logger.info(f"✅ Auto-sync successful: booking {booking_id} → invoice {invoice.invoice_number} (ID: {invoice.id})")
                
            except Exception as sync_error:
                logger.error(f"❌ Auto-sync to invoice table failed for booking {booking_id}: {sync_error}")
                # ยังคงทำงานต่อ แต่บันทึก error
                sync_error_note = f"❌ Auto-sync to invoice table failed: {str(sync_error)} at {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                current_notes = booking.admin_notes or ''
                booking.admin_notes = f"{current_notes}\n{sync_error_note}".strip()
        
        db.session.commit()
        
        # Log activity
        activity_msg = f"Booking marked as PAID via enhanced workflow. Invoice: {booking.invoice_number}"
        if booking.invoice_status == 'synchronized':
            activity_msg += " (Auto-synced to invoice system)"
            
        # ActivityLog.log_activity(
        #     'booking', booking_id, 'workflow_paid_and_synced',
        #     activity_msg,
        #     current_user.id
        # )
        
        success_message = f'✅ Booking {booking.booking_reference} marked as PAID'
        if booking.invoice_status == 'synchronized':
            success_message += ' and auto-synced to invoice system. Ready for vouchering!'
        else:
            success_message += '. Manual invoice sync may be required.'
        
        if request.is_json:
            return jsonify({
                'success': True, 
                'message': success_message,
                'next_step': 'mark_vouchered' if booking.invoice_status == 'synchronized' else 'manual_sync',
                'booking_status': booking.status,
                'invoice_status': booking.invoice_status,
                'invoice_number': booking.invoice_number,
                'auto_synced': booking.invoice_status == 'synchronized'
            })
        
        flash(success_message, 'success')
        return redirect(url_for('booking.view', id=booking_id))
        
    except Exception as e:
        logger.error(f"Error in workflow_make_paid for booking {booking_id}: {e}")
        message = f'❌ Error marking booking as paid: {str(e)}'
        
        if request.is_json:
            return jsonify({'success': False, 'message': message}), 500
        
        flash(message, 'error')
        return redirect(url_for('booking.view', id=booking_id))


@enhanced_workflow_bp.route('/<int:booking_id>/workflow-sync-invoice', methods=['POST'])
@login_required
def workflow_sync_invoice(booking_id):
    """
    Manual Sync to Invoice System (when auto sync failed)
    - สร้าง/อัปเดต invoice record ใน invoices table
    - ส่งข้อมูลทั้งหมดไปยัง Invoice system
    """
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        # ตรวจสอบ status ปัจจุบัน
        if booking.status != 'paid':
            message = f'❌ Booking must be paid to sync to invoice. Current status: {booking.status}'
            if request.is_json:
                return jsonify({'success': False, 'message': message}), 400
            flash(message, 'error')
            return redirect(url_for('booking.view', id=booking_id))
        
        # รับข้อมูล invoice configuration
        invoice_data = {}
        if request.is_json:
            invoice_data = request.get_json() or {}
        else:
            invoice_data = {
                'invoice_number': request.form.get('invoice_number', booking.invoice_number),
                'invoice_due_date': request.form.get('invoice_due_date', ''),
                'force_sync': request.form.get('force_sync', 'false') == 'true',
                'include_products': request.form.get('include_products', 'true') == 'true',
                'include_services': request.form.get('include_services', 'true') == 'true',
            }
        
        # 🚀 MANUAL SYNC TO INVOICE TABLE
        try:
            # ตรวจสอบว่ามี invoice อยู่แล้วหรือไม่
            existing_invoice = Invoice.query.filter_by(booking_id=booking.id).first()
            
            if existing_invoice:
                # อัปเดต invoice ที่มีอยู่แล้ว
                invoice = existing_invoice
                logger.info(f"🔄 Manual sync - Updating existing invoice {invoice.invoice_number} for booking {booking_id}")
            else:
                # สร้าง invoice ใหม่
                invoice_number = invoice_data.get('invoice_number', booking.invoice_number)
                if not invoice_number:
                    invoice_number = f"INV-{booking.booking_reference}"
                
                invoice = Invoice(
                    booking_id=booking.id,
                    quote_id=booking.quote_id,
                    invoice_number=invoice_number,
                    title=f"Manual Invoice for {booking.booking_reference}",
                    invoice_date=date.today(),
                    due_date=datetime.strptime(invoice_data.get('invoice_due_date'), '%Y-%m-%d').date() if invoice_data.get('invoice_due_date') else date.today(),
                )
                db.session.add(invoice)
                logger.info(f"✨ Manual sync - Creating new invoice {invoice.invoice_number} for booking {booking_id}")
            
            # อัปเดต invoice ด้วยข้อมูลจาก booking
            invoice.description = f"""Manual Sync - Service: {booking.description or 'Tour Service'}
Flight Information: {booking.flight_info or 'N/A'}
Special Requests: {booking.special_request or 'None'}
Guest Details: {booking.adults} Adults, {booking.children} Children, {booking.infants} Infants
Arrival: {booking.arrival_date.strftime('%Y-%m-%d') if booking.arrival_date else 'TBD'}
Departure: {booking.departure_date.strftime('%Y-%m-%d') if booking.departure_date else 'TBD'}"""
            
            # ตั้งค่าราคา
            invoice.subtotal = Decimal(str(booking.total_amount)) if booking.total_amount else Decimal('0')
            invoice.tax_rate = Decimal('7.0')  # 7% VAT
            invoice.tax_amount = invoice.subtotal * invoice.tax_rate / 100
            invoice.total_amount = invoice.subtotal + invoice.tax_amount
            
            # ตั้งค่าสถานะ payment
            invoice.status = 'paid'
            invoice.payment_status = 'paid'
            invoice.paid_amount = invoice.total_amount
            invoice.balance_due = Decimal('0')
            invoice.paid_date = date.today()
            
            # ตั้งค่า payment information
            invoice.payment_method = 'Manual Sync'
            invoice.payment_reference = booking.booking_reference
            
            # เพิ่ม notes
            sync_notes = f"Manual sync from enhanced workflow at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            sync_notes += f"\nSync includes: Products={invoice_data.get('include_products', True)}, Services={invoice_data.get('include_services', True)}"
            invoice.notes = sync_notes
            
            # สร้าง/อัปเดต line items
            if invoice.id:  # Invoice มีอยู่แล้ว
                InvoiceLineItem.query.filter_by(invoice_id=invoice.id).delete()
            
            # เพิ่ม main service line item
            main_service = InvoiceLineItem(
                description=booking.description or f"Tour Service - {booking.booking_reference}",
                quantity=1,
                unit_price=invoice.subtotal,
                total_amount=invoice.subtotal
            )
            
            if invoice.id:
                main_service.invoice_id = invoice.id
                db.session.add(main_service)
            else:
                invoice.line_items.append(main_service)
            
            # เพิ่ม products ถ้า include_products = true
            if invoice_data.get('include_products', True) and booking.products:
                try:
                    products_data = json.loads(booking.products) if isinstance(booking.products, str) else booking.products
                    if isinstance(products_data, list):
                        for product in products_data:
                            if isinstance(product, dict) and 'name' in product:
                                product_item = InvoiceLineItem(
                                    description=f"Product: {product.get('name', 'Unknown')}",
                                    quantity=product.get('quantity', 1),
                                    unit_price=Decimal(str(product.get('price', 0))),
                                    total_amount=Decimal(str(product.get('quantity', 1))) * Decimal(str(product.get('price', 0)))
                                )
                                
                                if invoice.id:
                                    product_item.invoice_id = invoice.id
                                    db.session.add(product_item)
                                else:
                                    invoice.line_items.append(product_item)
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Could not parse products data: {e}")
            
            # อัปเดต timestamps
            invoice.updated_at = datetime.now()
            
            # Commit เพื่อให้ได้ invoice.id
            db.session.commit()
            
            # อัปเดต booking invoice status
            booking.invoice_status = 'synchronized'
            booking.invoiced_at = datetime.now()
            booking.invoice_number = invoice.invoice_number
            
            # เพิ่ม manual sync note
            manual_sync_note = f"✅ Manual sync to invoice table: {invoice.invoice_number} (ID: {invoice.id}) at {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            current_notes = booking.admin_notes or ''
            booking.admin_notes = f"{current_notes}\n{manual_sync_note}".strip()
            
            db.session.commit()
            
            success_message = f'✅ Manual sync successful! Invoice {invoice.invoice_number} created/updated'
            logger.info(f"✅ Manual sync successful: booking {booking_id} → invoice {invoice.invoice_number} (ID: {invoice.id})")
            
        except Exception as sync_error:
            logger.error(f"❌ Manual sync to invoice table failed for booking {booking_id}: {sync_error}")
            db.session.rollback()
            raise sync_error
        
        # Log activity
        # ActivityLog.log_activity(
        #     'booking', booking_id, 'workflow_manual_sync',
        #     f"Manual sync to invoice table: {invoice.invoice_number} (ID: {invoice.id})",
        #     current_user.id
        # )
        
        if request.is_json:
            return jsonify({
                'success': True, 
                'message': success_message,
                'next_step': 'mark_vouchered',
                'invoice_number': invoice.invoice_number,
                'invoice_id': invoice.id
            })
        
        flash(success_message, 'success')
        return redirect(url_for('booking.view', id=booking_id))
        
    except Exception as e:
        logger.error(f"Error in workflow_sync_invoice for booking {booking_id}: {e}")
        message = f'❌ Error syncing to invoice: {str(e)}'
        
        if request.is_json:
            return jsonify({'success': False, 'message': message}), 500
        
        flash(message, 'error')
        return redirect(url_for('booking.view', id=booking_id))


@enhanced_workflow_bp.route('/<int:booking_id>/workflow-mark-vouchered', methods=['POST'])
@login_required  
def workflow_mark_vouchered(booking_id):
    """
    Step 3: Mark as Vouchered (final step)
    - เปลี่ยน status เป็น 'vouchered'
    - สร้าง voucher documents
    - Complete workflow
    """
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        # ตรวจสอบ status ปัจจุบัน
        if booking.status != 'paid' or booking.invoice_status != 'synchronized':
            message = f'❌ Booking must be paid and invoice synchronized. Status: {booking.status}, Invoice: {booking.invoice_status}'
            if request.is_json:
                return jsonify({'success': False, 'message': message}), 400
            flash(message, 'error')
            return redirect(url_for('booking.view', id=booking_id))
        
        # รับข้อมูล voucher configuration
        voucher_data = {}
        if request.is_json:
            voucher_data = request.get_json() or {}
        else:
            voucher_data = {
                'generate_voucher_pdf': request.form.get('generate_voucher_pdf', 'true') == 'true',
                'send_confirmation_email': request.form.get('send_confirmation_email', 'false') == 'true',
                'voucher_notes': request.form.get('voucher_notes', ''),
            }
        
        # อัปเดต booking เป็น vouchered
        booking.status = 'vouchered'
        booking.vouchered_at = datetime.now()
        
        # เพิ่ม voucher notes
        if voucher_data.get('voucher_notes'):
            voucher_note = f"Vouchered: {voucher_data['voucher_notes']} (at {datetime.now().strftime('%Y-%m-%d %H:%M')})"
            current_notes = booking.admin_notes or ''
            booking.admin_notes = f"{current_notes}\n{voucher_note}".strip()
        
        db.session.commit()
        
        # Log activity
        # ActivityLog.log_activity(
        #     'booking', booking_id, 'workflow_vouchered',
        #     f"Booking completed workflow: {booking.booking_reference} → VOUCHERED",
        #     current_user.id
        # )
        
        # TODO: Generate voucher documents if requested
        voucher_files = []
        if voucher_data.get('generate_voucher_pdf', True):
            # สร้าง voucher PDF
            # voucher_files.append(generate_voucher_pdf(booking))
            pass
        
        message = f'✅ Booking {booking.booking_reference} marked as VOUCHERED. Workflow completed!'
        if request.is_json:
            return jsonify({
                'success': True, 
                'message': message,
                'workflow_status': 'completed',
                'booking_status': booking.status,
                'voucher_files': voucher_files
            })
        
        flash(message, 'success')
        return redirect(url_for('booking.view', id=booking_id))
        
    except Exception as e:
        logger.error(f"Error in workflow_mark_vouchered for booking {booking_id}: {e}")
        message = f'❌ Error marking as vouchered: {str(e)}'
        
        if request.is_json:
            return jsonify({'success': False, 'message': message}), 500
        
        flash(message, 'error')
        return redirect(url_for('booking.view', id=booking_id))


@enhanced_workflow_bp.route('/<int:booking_id>/workflow-status', methods=['GET'])
@login_required
def get_workflow_status(booking_id):
    """Get current workflow status and available next steps"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        # กำหนด workflow steps สำหรับ auto sync workflow
        workflow_steps = {
            'quoted': {
                'current': True if booking.status == 'quoted' else False,
                'completed': True if booking.status in ['paid', 'vouchered'] else False,
                'next_action': 'make_paid_auto_sync' if booking.status == 'quoted' else None,
                'description': 'Booking has been quoted and ready for payment'
            },
            'paid_and_synced': {
                'current': True if booking.status == 'paid' and booking.invoice_status == 'synchronized' else False,
                'completed': True if booking.status == 'vouchered' else False,
                'next_action': 'mark_vouchered' if booking.status == 'paid' and booking.invoice_status == 'synchronized' else None,
                'description': 'Payment received and automatically synchronized to invoice system'
            },
            'vouchered': {
                'current': True if booking.status == 'vouchered' else False,
                'completed': True if booking.status == 'vouchered' else False,
                'next_action': None,
                'description': 'Voucher generated and workflow completed'
            }
        }
        
        # เพิ่ม fallback steps สำหรับ manual sync (ถ้า auto sync ล้มเหลว)
        if booking.status == 'paid' and booking.invoice_status != 'synchronized':
            workflow_steps['manual_sync_required'] = {
                'current': True,
                'completed': False,
                'next_action': 'sync_invoice',
                'description': 'Manual invoice synchronization required (auto-sync failed)'
            }
        
        return jsonify({
            'success': True,
            'booking_id': booking.id,
            'booking_reference': booking.booking_reference,
            'current_status': booking.status,
            'invoice_status': booking.invoice_status,
            'workflow_steps': workflow_steps,
            'timestamps': {
                'quoted_at': booking.quoted_at.isoformat() if booking.quoted_at else None,
                'paid_at': booking.paid_at.isoformat() if booking.paid_at else None,
                'invoiced_at': booking.invoiced_at.isoformat() if booking.invoiced_at else None,
                'vouchered_at': booking.vouchered_at.isoformat() if booking.vouchered_at else None,
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting workflow status for booking {booking_id}: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


if __name__ == '__main__':
    print("Enhanced Booking Workflow System")
    print("=" * 50)
    print("Workflow Steps:")
    print("1. quoted → workflow_make_paid → paid")
    print("2. paid → workflow_sync_invoice → invoice_synced") 
    print("3. invoice_synced → workflow_mark_vouchered → vouchered")
    print("=" * 50)