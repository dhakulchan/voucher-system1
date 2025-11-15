#!/usr/bin/env python3
"""
Fix and verify booking #79 quote data
"""

import sys
sys.path.append('/Applications/python/voucher-ro_v1.0')

from app import create_app
from models.booking import Booking
from models.quote import Quote
from extensions import db

def verify_booking_quote_fix():
    """Verify that booking #79 has been properly fixed"""
    app = create_app()
    
    with app.app_context():
        try:
            # Get booking #79
            booking = Booking.query.filter_by(id=79).first()
            
            if not booking:
                print("❌ Booking #79 not found")
                return False
            
            print("=" * 60)
            print("BOOKING #79 VERIFICATION REPORT")
            print("=" * 60)
            
            print(f"📋 Booking ID: {booking.id}")
            print(f"📋 Booking Reference: {booking.booking_reference}")
            print(f"📋 Customer ID: {booking.customer_id}")
            print(f"📋 Status: {booking.status}")
            print(f"📋 Quote Number: {booking.quote_number}")
            print(f"📋 Quote ID: {booking.quote_id}")
            
            # Verify the fix
            expected_quote_number = "QT25110034"
            expected_quote_id = 52
            
            print("\n" + "=" * 60)
            print("VERIFICATION CHECKS")
            print("=" * 60)
            
            # Check 1: Quote number
            if booking.quote_number == expected_quote_number:
                print(f"✅ Quote Number: {booking.quote_number} (CORRECT)")
            else:
                print(f"❌ Quote Number: {booking.quote_number} (Expected: {expected_quote_number})")
            
            # Check 2: Quote ID
            if booking.quote_id == expected_quote_id:
                print(f"✅ Quote ID: {booking.quote_id} (CORRECT)")
            else:
                print(f"❌ Quote ID: {booking.quote_id} (Expected: {expected_quote_id})")
            
            # Check 3: Quote exists and links back
            if booking.quote_id:
                quote = Quote.query.filter_by(id=booking.quote_id).first()
                if quote:
                    print(f"✅ Quote Record Found: ID {quote.id}")
                    
                    if quote.booking_id == booking.id:
                        print(f"✅ Quote Links Back to Booking: {quote.booking_id}")
                    else:
                        print(f"❌ Quote Links to Wrong Booking: {quote.booking_id}")
                    
                    if quote.quote_number == booking.quote_number:
                        print(f"✅ Quote Numbers Match: {quote.quote_number}")
                    else:
                        print(f"❌ Quote Numbers Don't Match: Quote={quote.quote_number}, Booking={booking.quote_number}")
                else:
                    print(f"❌ Quote Record Not Found for ID {booking.quote_id}")
            else:
                print("❌ No Quote ID assigned to booking")
            
            print("\n" + "=" * 60)
            print("DATABASE TABLE REPRESENTATION")
            print("=" * 60)
            print("| id | customer_id | booking_reference | quote_id | quote_number | quote_status | invoice_number |")
            print("|----+-------------+-------------------+----------+--------------+--------------+----------------|")
            
            quote_status = "NULL"
            if booking.quote_id:
                quote = Quote.query.filter_by(id=booking.quote_id).first()
                if quote:
                    quote_status = quote.status or "NULL"
            
            invoice_number = "NULL"  # Would need to check if invoice exists
            
            print(f"| {booking.id:2d} | {booking.customer_id:11d} | {booking.booking_reference:17s} | {booking.quote_id or 'NULL':>8} | {booking.quote_number or 'NULL':12s} | {quote_status:12s} | {invoice_number:14s} |")
            
            print("\n" + "=" * 60)
            print("SUMMARY")
            print("=" * 60)
            
            all_checks_passed = (
                booking.quote_number == expected_quote_number and
                booking.quote_id == expected_quote_id and
                booking.quote_id is not None
            )
            
            if all_checks_passed:
                print("🎉 ALL CHECKS PASSED! Booking #79 has been successfully fixed.")
                print(f"   - Quote Number: {booking.quote_number}")
                print(f"   - Quote ID: {booking.quote_id}")
                print("   - Quote record exists and links properly")
                return True
            else:
                print("❌ Some checks failed. Review the issues above.")
                return False
                
        except Exception as e:
            print(f"❌ Error during verification: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = verify_booking_quote_fix()
    exit(0 if success else 1)