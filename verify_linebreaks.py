#!/usr/bin/env python3
"""
สร้าง PDF ทดสอบและแสดงข้อมูลสำหรับเปรียบเทียบ
"""
import sys
import os
sys.path.insert(0, '/Applications/python/voucher-ro_v1.0')

import sqlite3
from services.classic_pdf_generator import ClassicPDFGenerator
from datetime import datetime

# เชื่อมต่อฐานข้อมูล
conn = sqlite3.connect('/Applications/python/voucher-ro_v1.0/app.db')
cursor = conn.cursor()

# ดึงข้อมูลการจอง
cursor.execute('''
    SELECT booking_reference, special_request, flight_info, description 
    FROM bookings WHERE id = 162
''')
result = cursor.fetchone()

if result:
    booking_ref, special_request, flight_info, description = result
    
    print("🎯 ข้อมูลที่จะทดสอบ Line Breaks:")
    print("=" * 60)
    
    print(f"\n1. Booking Reference: {booking_ref}")
    
    print(f"\n2. Special Request (มี \\r\\n):")
    print(f"   Raw: {repr(special_request)}")
    
    print(f"\n3. Flight Info (มี \\r\\n):")
    print(f"   Raw: {repr(flight_info)}")
    
    print(f"\n4. Description (มี <br> tags):")
    print(f"   Raw: {repr(description[:150])}...")
    
    # ทดสอบ clean_html_tags
    generator = ClassicPDFGenerator()
    
    print("\n" + "=" * 60)
    print("🔧 ผลการประมวลผล clean_html_tags:")
    print("=" * 60)
    
    if special_request:
        cleaned_sr = generator.clean_html_tags(special_request)
        print(f"\nSpecial Request → {repr(cleaned_sr)}")
        
    if flight_info:
        cleaned_fi = generator.clean_html_tags(flight_info)
        print(f"\nFlight Info → {repr(cleaned_fi)}")
        
    if description:
        cleaned_desc = generator.clean_html_tags(description)
        print(f"\nDescription → {repr(cleaned_desc[:100])}...")
    
    print("\n" + "=" * 60)
    print("✅ หาก line breaks แสดงเป็น \\n แสดงว่าการแปลงสำเร็จ!")
    print("✅ ตอนนี้ PDF ควรจะแสดง line breaks ได้ถูกต้องด้วย Preformatted")

else:
    print("❌ ไม่พบข้อมูลการจอง ID 162")

conn.close()
