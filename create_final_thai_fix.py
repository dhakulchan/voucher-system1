#!/usr/bin/env python3

"""
DEFINITIVE THAI FONT FIX
========================
This creates the final solution for Thai font issues in WeasyPrint PDFs
"""

import os
import shutil
from pathlib import Path

def create_definitive_template():
    """Create the ultimate Thai font template that WILL work"""
    
    print("🔧 CREATING DEFINITIVE THAI FONT TEMPLATE")
    print("=" * 50)
    
    template_content = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Quote - {{ booking.booking_reference }}</title>
    <style>
        /* WeasyPrint CSS Reset for Thai fonts */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        /* Force all elements to use Thai fonts */
        html, body, div, span, h1, h2, h3, h4, h5, h6, p, 
        table, thead, tbody, tr, th, td, ul, ol, li {
            font-family: "Tahoma", "MS Sans Serif", Arial, sans-serif !important;
            font-size: 13px;
            line-height: 1.6;
        }
        
        @page {
            size: A4;
            margin: 2.5cm 2cm;
        }
        
        body {
            font-family: "Tahoma", "MS Sans Serif", Arial, sans-serif;
            color: #000;
            background: #fff;
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid #333;
            padding-bottom: 15px;
        }
        
        .quote-title {
            font-size: 24px;
            font-weight: bold;
            color: #2c5aa0;
            margin-bottom: 10px;
        }
        
        .quote-number {
            font-size: 16px;
            color: #666;
        }
        
        .info-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        
        .info-table td {
            padding: 8px 12px;
            border: 1px solid #ccc;
            vertical-align: top;
        }
        
        .info-table .label {
            background-color: #f8f9fa;
            font-weight: bold;
            width: 40%;
        }
        
        .price-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        
        .price-table th {
            background-color: #2c5aa0;
            color: white;
            padding: 10px;
            text-align: center;
            border: 1px solid #1e4084;
        }
        
        .price-table td {
            padding: 10px;
            border: 1px solid #ddd;
            text-align: center;
        }
        
        .price-amount {
            text-align: right !important;
            font-weight: bold;
        }
        
        .terms {
            margin-top: 30px;
            font-size: 11px;
            line-height: 1.5;
        }
        
        .terms-title {
            font-weight: bold;
            margin-bottom: 10px;
            text-decoration: underline;
        }
        
        .footer {
            margin-top: 40px;
            text-align: center;
            font-size: 11px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="quote-title">ใบเสนอราคา / QUOTE</div>
        <div class="quote-number">{{ quote_number or 'Q-' + (booking.booking_reference or 'DRAFT') }}</div>
    </div>
    
    <table class="info-table">
        <tr>
            <td class="label">ชื่อลูกค้า / Customer Name:</td>
            <td>{{ booking.customer_name or 'ไม่ระบุ' }}</td>
        </tr>
        <tr>
            <td class="label">อีเมล / Email:</td>
            <td>{{ booking.customer_email or 'N/A' }}</td>
        </tr>
        <tr>
            <td class="label">เบอร์โทร / Phone:</td>
            <td>{{ booking.customer_phone or 'N/A' }}</td>
        </tr>
        <tr>
            <td class="label">จำนวนผู้โดยสาร / Passengers:</td>
            <td>{{ booking.total_guests or 0 }} คน</td>
        </tr>
        <tr>
            <td class="label">วันที่เดินทาง / Travel Date:</td>
            <td>{{ booking.tour_date if booking.tour_date else 'ไม่ระบุ' }}</td>
        </tr>
        <tr>
            <td class="label">โปรแกรมทัวร์ / Tour Program:</td>
            <td>{{ booking.tour_name or 'ไม่ระบุโปรแกรม' }}</td>
        </tr>
    </table>
    
    {% if booking.tour_programs and booking.tour_programs|length > 0 %}
    <table class="info-table">
        <tr>
            <td class="label" style="background-color: #e3f2fd; color: #1565c0;">รายการกิจกรรม / Activities</td>
            <td>&nbsp;</td>
        </tr>
        {% for program in booking.tour_programs %}
        <tr>
            <td style="background-color: #f5f5f5;">วันที่ {{ loop.index }}</td>
            <td>{{ program.description or 'ไม่ระบุรายละเอียด' }}</td>
        </tr>
        {% endfor %}
    </table>
    {% endif %}
    
    <table class="price-table">
        <thead>
            <tr>
                <th>รายการ / Description</th>
                <th>จำนวน / Qty</th>
                <th>ราคาต่อหน่วย / Unit Price</th>
                <th>รวม / Total</th>
            </tr>
        </thead>
        <tbody>
            {% if quote and quote.quote_items %}
            {% for item in quote.quote_items %}
            <tr>
                <td style="text-align: left;">{{ item.description or 'รายการทัวร์' }}</td>
                <td>{{ item.quantity or 1 }}</td>
                <td class="price-amount">{{ '{:,.0f}'.format(item.unit_price or 0) }}</td>
                <td class="price-amount">{{ '{:,.0f}'.format((item.unit_price or 0) * (item.quantity or 1)) }}</td>
            </tr>
            {% endfor %}
            {% else %}
            <tr>
                <td style="text-align: left;">{{ booking.tour_name or 'แพ็คเกจทัวร์' }}</td>
                <td>{{ booking.total_guests or 1 }}</td>
                <td class="price-amount">{{ '{:,.0f}'.format(booking.total_price_per_person or 0) }}</td>
                <td class="price-amount">{{ '{:,.0f}'.format(booking.total_price or 0) }}</td>
            </tr>
            {% endif %}
            <tr style="background-color: #f8f9fa;">
                <td colspan="3" style="font-weight: bold; text-align: left;">รวมทั้งสิ้น / Grand Total:</td>
                <td class="price-amount" style="font-weight: bold;">฿ {{ '{:,.0f}'.format(quote.total_amount if quote else booking.total_price or 0) }}</td>
            </tr>
        </tbody>
    </table>
    
    <div class="terms">
        <div class="terms-title">ข้อกำหนดและเงื่อนไข / Terms & Conditions</div>
        <div>
            • การจองจะสมบูรณ์เมื่อได้รับเงินมัดจำแล้วเท่านั้น / Booking is confirmed only upon receipt of deposit<br>
            • เงินมัดจำ 50% ของราคาทัวร์ทั้งหมด / Deposit required: 50% of total tour price<br>
            • ชำระเงินส่วนที่เหลือก่อนวันเดินทาง 7 วัน / Final payment due 7 days before departure<br>
            • การยกเลิกก่อนเดินทาง 15 วัน หักค่าใช้จ่าย 25% / Cancellation 15+ days: 25% charge<br>
            • การยกเลิกก่อนเดินทาง 7-14 วัน หักค่าใช้จ่าย 50% / Cancellation 7-14 days: 50% charge<br>
            • การยกเลิกก่อนเดินทางน้อยกว่า 7 วัน หักค่าใช้จ่าย 100% / Cancellation &lt;7 days: 100% charge<br>
            • ราคาไม่รวมค่าทิปไกด์และคนขับรถ / Price excludes guide and driver tips<br>
            • บริษัทฯ ขอสงวนสิทธิ์ในการเปลี่ยนแปลงรายการโดยไม่แจ้งให้ทราบล่วงหน้า / Company reserves the right to modify itinerary without prior notice
        </div>
    </div>
    
    <div class="footer">
        ขอบคุณที่ไว้วางใจในบริการของเรา<br>
        Thank you for choosing our services
    </div>
</body>
</html>'''
    
    # Save the definitive template
    template_path = "/Applications/python/voucher-ro_v1.0/templates/pdf/quote_template_final_thai_fix.html"
    
    with open(template_path, 'w', encoding='utf-8') as f:
        f.write(template_content)
    
    print(f"✅ Created definitive template: {template_path}")
    
    # Also replace the existing system fonts template
    system_fonts_path = "/Applications/python/voucher-ro_v1.0/templates/pdf/quote_template_system_fonts.html"
    shutil.copy2(template_path, system_fonts_path)
    print(f"✅ Updated system fonts template: {system_fonts_path}")
    
    return template_path

def create_final_deployment_package():
    """Create the final deployment package"""
    
    print("\n📦 CREATING FINAL DEPLOYMENT PACKAGE")
    print("=" * 50)
    
    # Create deployment directory
    deploy_dir = "/tmp/thai_font_final_fix"
    os.makedirs(deploy_dir, exist_ok=True)
    
    # Copy templates
    templates = [
        "/Applications/python/voucher-ro_v1.0/templates/pdf/quote_template_system_fonts.html",
        "/Applications/python/voucher-ro_v1.0/templates/pdf/quote_template_final_thai_fix.html",
        "/Applications/python/voucher-ro_v1.0/templates/pdf/quote_template_emergency_thai.html"
    ]
    
    for template in templates:
        if os.path.exists(template):
            shutil.copy2(template, deploy_dir)
    
    # Create deployment instructions
    instructions = '''THAI FONT FIX - FINAL DEPLOYMENT
================================

🎯 PROBLEM: Thai fonts still showing as Arial in PDF
✅ SOLUTION: Simplified template using Tahoma (universal Thai support)

📁 FILES TO UPLOAD:
- quote_template_system_fonts.html (primary)
- quote_template_final_thai_fix.html (alternative)
- quote_template_emergency_thai.html (backup)

🚀 DEPLOYMENT STEPS:

1. Upload files to server:
   scp *.html ubuntu@52.220.243.237:/tmp/

2. SSH to server:
   ssh ubuntu@52.220.243.237

3. Deploy templates:
   sudo cp /tmp/quote_template_*.html /var/www/html/templates/pdf/
   sudo chown www-data:www-data /var/www/html/templates/pdf/quote_template_*.html
   sudo chmod 644 /var/www/html/templates/pdf/quote_template_*.html

4. Restart services:
   sudo systemctl restart gunicorn
   sudo systemctl restart nginx

5. Test:
   https://service.dhakulchan.net/booking/3/quote-pdf

🔧 KEY CHANGES:
- Uses Tahoma font (better Thai support than Arial)
- Simplified CSS structure
- Removed complex font fallbacks
- WeasyPrint optimized

✅ EXPECTED RESULT:
Thai text will render clearly with Tahoma font
which has excellent Thai character support.

If still not working, check server has Tahoma installed:
fc-list | grep -i tahoma
'''
    
    with open(f"{deploy_dir}/DEPLOYMENT_INSTRUCTIONS.txt", 'w') as f:
        f.write(instructions)
    
    print(f"✅ Created deployment package: {deploy_dir}")
    
    # List contents
    print("\n📋 Package contents:")
    for item in os.listdir(deploy_dir):
        print(f"  - {item}")
    
    return deploy_dir

def main():
    print("🎯 DEFINITIVE THAI FONT FIX")
    print("=" * 40)
    print()
    
    # Create the definitive template
    template_path = create_definitive_template()
    
    # Create deployment package
    deploy_dir = create_final_deployment_package()
    
    print(f"\n✅ FINAL SOLUTION READY")
    print("=" * 30)
    print(f"📁 Deployment package: {deploy_dir}")
    print(f"📄 Template created: {template_path}")
    print()
    print("🚀 DEPLOYMENT COMMAND:")
    print(f"cd {deploy_dir}")
    print("# Then follow DEPLOYMENT_INSTRUCTIONS.txt")
    print()
    print("🎯 This solution uses Tahoma font which has")
    print("   excellent Thai support and should work")
    print("   even on basic server installations.")

if __name__ == "__main__":
    main()