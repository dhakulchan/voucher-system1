#!/usr/bin/env python3
"""
Verify that PDF/PNG generation uses latest booking data
Compare generated content with database content
"""

from app import create_app
import os
from datetime import datetime

def verify_latest_data():
    app = create_app()
    with app.app_context():
        from models.booking import Booking
        from services.tour_voucher_weasyprint import TourVoucherWeasyPrintGenerator
        
        # Test with booking 174
        booking = Booking.query.get(174)
        if not booking:
            print("❌ Booking 174 not found!")
            return
        
        print(f"🔍 Verifying latest data for booking {booking.id}")
        print("=" * 60)
        
        # Check what data should be in the PDF
        print("📋 Expected Data in PDF:")
        print(f"  - Booking Reference: {booking.booking_reference}")
        print(f"  - Quote Number: {booking.quote_number}")
        print(f"  - Invoice Number: {booking.invoice_number}")
        print(f"  - Party Name: {booking.party_name}")
        print(f"  - Updated At: {booking.updated_at}")
        
        voucher_rows = booking.get_voucher_rows()
        print(f"  - Voucher Rows: {len(voucher_rows)} items")
        for i, row in enumerate(voucher_rows[:2]):  # Show first 2 rows
            print(f"    {i+1}. {row.get('arrival')} → {row.get('departure')}")
            print(f"       Service: {row.get('service_by', '')[:50]}...")
            print(f"       Type: {row.get('type', '')}")
        
        voucher_images = booking.get_voucher_images()
        print(f"  - Voucher Images: {len(voucher_images)} items")
        
        # Generate HTML and check content
        try:
            weasy_gen = TourVoucherWeasyPrintGenerator()
            html_content = weasy_gen._generate_html(booking)
            
            # Save HTML for verification
            html_filename = f"verify_html_{booking.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            html_path = os.path.join('static/generated', html_filename)
            os.makedirs('static/generated', exist_ok=True)
            
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"\n📝 HTML Content Verification:")
            print(f"   Saved to: {html_path}")
            
            # Check specific content
            checks = [
                (booking.booking_reference, "Booking Reference"),
                (booking.quote_number, "Quote Number"),
                (booking.invoice_number, "Invoice Number"),
                (booking.party_name, "Party Name"),
                ("16/09/2025", "First Arrival Date"),
                ("T33333333333", "First Service Type"),
                ("Dhakul Chan Nice Holidays Group", "First Service Provider"),
                ("voucher-image-item", "Voucher Images Section")
            ]
            
            all_found = True
            for check_value, check_name in checks:
                if check_value and str(check_value) in html_content:
                    print(f"   ✅ {check_name}: Found")
                else:
                    print(f"   ❌ {check_name}: Missing '{check_value}'")
                    all_found = False
            
            # Generate PDF
            print(f"\n📄 PDF Generation:")
            pdf_filename = weasy_gen.generate_tour_voucher(booking)
            pdf_path = os.path.join('static/generated', pdf_filename)
            
            if os.path.exists(pdf_path):
                pdf_size = os.path.getsize(pdf_path)
                pdf_mtime = datetime.fromtimestamp(os.path.getmtime(pdf_path))
                print(f"   ✅ PDF created: {pdf_filename}")
                print(f"   📊 Size: {pdf_size:,} bytes")
                print(f"   🕐 Modified: {pdf_mtime}")
                print(f"   📍 Path: {pdf_path}")
            else:
                print(f"   ❌ PDF not found: {pdf_path}")
                all_found = False
            
            if all_found:
                print(f"\n🎉 SUCCESS: PDF contains latest booking data!")
            else:
                print(f"\n⚠️  WARNING: Some data may be missing from PDF")
                
        except Exception as e:
            print(f"❌ Error during verification: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "=" * 60)
        print("🔍 Verification completed.")

if __name__ == "__main__":
    verify_latest_data()
