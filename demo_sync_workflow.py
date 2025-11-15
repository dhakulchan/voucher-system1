#!/usr/bin/env python3
"""
Demo: Pure Sync-based Invoice Ninja Workflow
Shows complete sync process and status mapping
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from models.booking import Booking
from services.invoice_sync_service import InvoiceSyncService

def demo_sync_workflow():
    """Demonstrate the complete sync workflow"""
    
    app = create_app()
    
    with app.app_context():
        sync_service = InvoiceSyncService()
        
        print("🎯 === PURE SYNC-BASED INVOICE NINJA WORKFLOW DEMO ===")
        print()
        
        # Get booking 168
        booking = Booking.query.get(168)
        if not booking:
            print("❌ Booking 168 not found")
            return
            
        print(f"📋 BOOKING #{booking.id} - {booking.booking_reference}")
        print(f"   Quote ID: {booking.quote_id}")
        print(f"   Quote Number: {booking.quote_number}")
        print()
        
        print("📊 BEFORE SYNC:")
        print(f"   Invoice Number: {booking.invoice_number or 'None'}")
        print(f"   Invoice Status: {booking.invoice_status or 'None'}")
        print(f"   Invoice Amount: {booking.invoice_amount or 'None'}")
        print(f"   Is Paid: {getattr(booking, 'is_paid', 'None')}")
        print(f"   Can Create Voucher: {booking.can_create_voucher()}")
        print()
        
        # Test sync multiple times to show different mock scenarios
        for i in range(3):
            print(f"🔄 SYNC ATTEMPT #{i+1}:")
            result = sync_service.sync_invoice_for_quote(booking.id)
            
            print(f"   Success: {result.get('success', False)}")
            
            if result.get('success') and result.get('invoice_data'):
                invoice_data = result['invoice_data']
                print(f"   📄 Invoice Found: {invoice_data.get('number', 'N/A')}")
                print(f"   🏷️  Status ID: {invoice_data.get('status_id', 'N/A')}")
                print(f"   📝 Status Name: {invoice_data.get('status_name', 'N/A')}")
                print(f"   💰 Amount: ${invoice_data.get('amount', 'N/A')}")
                print(f"   💳 Paid Amount: ${invoice_data.get('paid_amount', 'N/A')}")
                print(f"   ✅ Is Paid: {invoice_data.get('is_paid', False)}")
                print(f"   🎫 Can Create Voucher: {booking.can_create_voucher()}")
                
                # Show status evolution
                db.session.refresh(booking)
                print(f"   📈 Status Evolution: {booking.invoice_status}")
            else:
                print(f"   ❌ Error: {result.get('error', 'Unknown')}")
            
            print()
        
        print("🎯 FINAL STATE:")
        db.session.refresh(booking)
        print(f"   Invoice Number: {booking.invoice_number}")
        print(f"   Invoice Status: {booking.invoice_status}")
        print(f"   Invoice Amount: {booking.invoice_amount}")
        print(f"   Is Paid: {getattr(booking, 'is_paid', False)}")
        print(f"   Payment Status Display: {booking.get_payment_status_display()}")
        print(f"   Can Create Voucher: {booking.can_create_voucher()}")
        print()
        
        print("✅ === SYNC WORKFLOW DEMO COMPLETE ===")
        print()
        print("📌 Key Features Demonstrated:")
        print("   • Pure Sync-based workflow (invoices created in Invoice Ninja)")
        print("   • Enhanced status mapping (no more 'UNKNOWN' status)")
        print("   • Multiple search methods for finding invoices")
        print("   • Mock data simulation for development/testing")
        print("   • Automatic booking record updates")
        print("   • Voucher creation eligibility checking")

if __name__ == "__main__":
    demo_sync_workflow()
