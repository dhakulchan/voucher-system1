#!/usr/bin/env python3
"""
Verify booking 170 fix via web interface
Should now show AR0388588 instead of INV32956
"""

import sys
import os
sys.path.append('/Applications/python/voucher-ro_v1.0')

from app import create_app
from models.booking import Booking

def main():
    app = create_app()
    
    with app.app_context():
        print("✅ === VERIFYING BOOKING 170 FIX ===")
        
        # Get booking 170
        booking = Booking.query.get(170)
        if not booking:
            print("❌ Booking 170 not found!")
            return
            
        print(f"📋 BOOKING #170 - {booking.booking_reference}")
        print(f"   Quote ID: {booking.quote_id}")
        print(f"   Quote Number: {booking.quote_number}")
        print("")
        
        print("📊 CURRENT DATABASE STATE:")
        print(f"   Invoice Number: {booking.invoice_number}")
        print(f"   Invoice Status: {booking.invoice_status}")
        print(f"   Invoice Amount: {booking.invoice_amount}")
        print(f"   Is Paid: {booking.is_paid}")
        print(f"   Last Sync: {booking.last_sync_date}")
        print("")
        
        # Check if the fix was successful
        if booking.invoice_number == "AR0388588":
            print("✅ SUCCESS! Invoice number is now correct")
            print("   Expected: AR0388588")
            print(f"   Actual: {booking.invoice_number}")
            print("")
            
            # Check payment status
            if booking.is_paid:
                print("💰 PAYMENT STATUS: PAID ✅")
                print("🎫 VOUCHER CREATION: Available ✅")
            else:
                print("⏳ PAYMENT STATUS: Not Paid")
                print("🎫 VOUCHER CREATION: Not Available")
                
            print("")
            print("🌐 WEB INTERFACE ACCESS:")
            print("   URL: http://localhost:5003/booking/view/170")
            print("   Should display:")
            print("   - Invoice Number: AR0388588")
            print("   - Invoice Status: PAID")
            print("   - Voucher Creation Available")
            
        else:
            print("❌ FAILED! Invoice number is still incorrect")
            print("   Expected: AR0388588")
            print(f"   Actual: {booking.invoice_number}")
            
        print("")
        print("🔗 INVOICE NINJA REFERENCE:")
        print("   Invoice ID: Wjneg5YbwZ")
        print("   URL: https://booking.dhakulchan.net/invoices/Wjneg5YbwZ/edit")

if __name__ == "__main__":
    main()
