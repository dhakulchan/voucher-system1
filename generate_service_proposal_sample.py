#!/usr/bin/env python3
"""
Generate Service Proposal PDF/PNG with sample data
ใช้สำหรับทดสอบการสร้าง PDF และ PNG ตามตัวอย่างที่ต้องการ
"""

import fitz  # PyMuPDF
import os
from services.classic_pdf_generator import ClassicPDFGenerator
from datetime import datetime

def generate_sample_proposal():
    """Generate sample service proposal matching the target format"""
    
    # Sample booking data matching the target layout
    booking_data = {
        'booking_id': 'BK20250830LNN7',
        'guest_name': 'วินไชย ใจดี',
        'guest_phone': '+66-83-456-7890',
        'guest_email': 'vinchai.jaidee@email.com',
        'booking_date': '30 AUG 2025',
        'tour_name': 'Hong Kong Disneyland Package',
        'start_date': '25 Nov 2025',
        'end_date': '28 Nov 2025',
        'pax': 3,
        'adults': 2,
        'children': 1,
        'infants': 1,
        'price': 13300.00,
        'status': 'pending',
        'description': 'Hong Kong Disneyland park tickets and accommodation package'
    }
    
    # Sample products matching the table format
    products = [
        {'name': 'ADT', 'quantity': 1, 'price': 5000.00},
        {'name': 'CHD', 'quantity': 1, 'price': 2500.00},
        {'name': 'INF', 'quantity': 1, 'price': 1000.00},
        {'name': 'Discount', 'quantity': 1, 'price': -200.00}
    ]
    
    # Generate PDF
    generator = ClassicPDFGenerator()
    pdf_path = generator.generate_pdf(booking_data, products)
    print(f"✅ Generated PDF: {pdf_path}")
    
    # Convert to PNG
    try:
        png_path = pdf_path.replace('.pdf', '.png')
        doc = fitz.open(pdf_path)
        page = doc[0]  # First page
        
        # High quality conversion
        mat = fitz.Matrix(2, 2)  # 2x scale for better quality
        pix = page.get_pixmap(matrix=mat)
        pix.save(png_path)
        
        doc.close()
        print(f"✅ Generated PNG: {png_path}")
        print(f"📄 PDF size: {os.path.getsize(pdf_path):,} bytes")
        print(f"🖼️ PNG size: {os.path.getsize(png_path):,} bytes")
        
        return pdf_path, png_path
        
    except Exception as e:
        print(f"❌ Error converting to PNG: {e}")
        return pdf_path, None

def generate_from_booking_id(booking_id):
    """Generate service proposal from specific booking ID"""
    import sqlite3
    
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    
    # Get booking by ID
    cursor.execute('''
        SELECT b.id, c.name, c.phone, c.email, 
               b.traveling_period_start, b.traveling_period_end, 
               b.party_name, b.description,
               b.total_pax, b.adults, b.children, b.infants, 
               b.total_amount, b.status, b.created_at
        FROM bookings b 
        JOIN customers c ON b.customer_id = c.id
        WHERE b.id = ?
    ''', (booking_id,))
    
    booking = cursor.fetchone()
    if not booking:
        print(f"❌ Booking ID {booking_id} not found")
        return None, None
    
    booking_data = {
        'booking_id': f'BK{booking[0]:04d}',
        'guest_name': booking[1],
        'guest_phone': booking[2], 
        'guest_email': booking[3],
        'start_date': booking[4],
        'end_date': booking[5],
        'tour_name': booking[6] or 'Tour Package',
        'description': booking[7] or 'Tour description not available',
        'pax': booking[8] or 1,
        'adults': booking[9] or 1,
        'children': booking[10] or 0,
        'infants': booking[11] or 0,
        'price': booking[12] or 0,
        'status': booking[13] or 'pending',
        'booking_date': booking[14] or datetime.now().strftime('%d %b %Y')
    }
    
    # Get products for this booking
    cursor.execute('''
        SELECT p.name, bp.quantity, bp.price 
        FROM booking_products bp
        JOIN products p ON bp.product_id = p.id
        WHERE bp.booking_id = ?
    ''', (booking_id,))
    
    products = []
    for row in cursor.fetchall():
        products.append({
            'name': row[0],
            'quantity': row[1],
            'price': row[2]
        })
    
    conn.close()
    
    # Generate PDF
    generator = ClassicPDFGenerator()
    pdf_path = generator.generate_pdf(booking_data, products)
    print(f"✅ Generated PDF for Booking {booking_id}: {pdf_path}")
    
    # Convert to PNG
    try:
        png_path = pdf_path.replace('.pdf', '.png')
        doc = fitz.open(pdf_path)
        page = doc[0]
        mat = fitz.Matrix(2, 2)
        pix = page.get_pixmap(matrix=mat)
        pix.save(png_path)
        doc.close()
        print(f"✅ Generated PNG: {png_path}")
        return pdf_path, png_path
    except Exception as e:
        print(f"❌ Error converting to PNG: {e}")
        return pdf_path, None

if __name__ == "__main__":
    print("🔥 Generating Service Proposal Sample...")
    print("=" * 50)
    
    # Generate sample
    pdf_path, png_path = generate_sample_proposal()
    
    print("\n✅ Sample generation complete!")
    print("📋 Files generated:")
    print(f"   PDF: {pdf_path}")
    if png_path:
        print(f"   PNG: {png_path}")
    
    print("\n💡 To generate from specific booking:")
    print("   python generate_service_proposal_sample.py [booking_id]")
