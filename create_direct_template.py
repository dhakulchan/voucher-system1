#!/usr/bin/env python3
"""
Create a direct booking data template that forces data display.
"""

template_content = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700&display=swap');
        body { 
            font-family: 'Sarabun', 'Noto Sans Thai', Arial, sans-serif; 
            margin: 0; 
            padding: 20px; 
            line-height: 1.4;
        }
        .header { text-align: center; margin-bottom: 20px; }
        .company-name { font-size: 16px; font-weight: bold; }
        .section { margin: 15px 0; border-bottom: 1px solid #ddd; padding-bottom: 10px; }
        .section-title { font-size: 14px; font-weight: bold; color: #0066cc; margin-bottom: 5px; }
        .content { font-size: 12px; }
        .thai-text { font-family: 'Sarabun', 'Noto Sans Thai', Arial, sans-serif; }
        .terms-section {
            margin-top: 20px;
            padding: 15px;
            border: 2px solid #cc0000;
            background-color: #ffffcc;
            font-size: 11px;
        }
        .terms-title { font-size: 14px; font-weight: bold; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div class="header">
        <div class="company-name">DHAKUL CHAN TRAVEL SERVICE (THAILAND) CO.,LTD.</div>
        <h1>QUOTE</h1>
        <p>Reference: {{ booking.booking_reference if booking else 'N/A' }} | Quote Number: QT2509010</p>
    </div>
    
    <div class="section">
        <div class="section-title">Service Detail / Itinerary:</div>
        <div class="content thai-text">
            <strong>Direct Booking Description:</strong><br>
            {{ booking.description|replace('\\n', '<br>')|safe if booking and booking.description else 'No description available' }}
        </div>
    </div>
    
    <div class="section">
        <div class="section-title">Name List / Rooming List:</div>
        <div class="content thai-text">
            <strong>Direct Booking Guest List:</strong><br>
            {{ booking.guest_list|replace('\\n', '<br>')|safe if booking and booking.guest_list else 'No guest list available' }}
        </div>
    </div>
    
    <div class="section">
        <div class="section-title">Flight Information:</div>
        <div class="content thai-text">
            <strong>Direct Booking Flight Info:</strong><br>
            {{ booking.flight_info|replace('\\n', '<br>')|safe if booking and booking.flight_info else 'No flight info available' }}
        </div>
    </div>
    
    <div class="terms-section">
        <div class="terms-title">ข้อกำหนดและเงื่อนไข</div>
        <div class="thai-text">
            • เอกสารฉบับนี้ ไม่ใช่การยืนยันการจอง เป็นเพียงการสรุปรายการบริการและราคาเบื้องต้นเท่านั้น<br><br>
            • ราคาและเงื่อนไขต่าง ๆ อาจมีการเปลี่ยนแปลงได้โดยไม่ต้องแจ้งให้ทราบล่วงหน้า ทั้งนี้ราคาสุดท้ายจะยืนยันอีกครั้งในวันที่ทำการจองและออกบริการ<br><br>
            • กรุณาตรวจสอบรายละเอียด รายการเดินทาง และข้อมูลต่าง ๆ ให้ครบถ้วน บริษัทฯ ไม่รับผิดชอบต่อข้อมูลที่แจ้งไม่ถูกต้องหรือไม่ครบถ้วน ในการขอจอง<br><br>
            • ในกรณีที่มีการปรับราคา หรือมีค่าใช้จ่ายเพิ่มเติมจากทางผู้ให้บริการ บริษัทฯ ขอสงวนสิทธิ์ในการปรับราคา ตามความเหมาะสม<br><br>
            • การเปลี่ยนแปลงชื่อผู้เดินทาง จำนวนผู้เดินทาง วันเดินทาง หรือรายละเอียดบริการต่าง ๆ อาจมีผลต่อราคา และเงื่อนไขที่เสนอไว้<br><br>
            • ใบเสนอราคามีอายุ 4 ชั่วโมง หรือ เป็นไปตามระยะเวลาที่บริษัทกำหนดเป็นครั้ง ๆ ไป หากพ้นกำหนด บริษัทฯ ขอสงวนสิทธิ์ในการปรับราคาใหม่
        </div>
    </div>
    
    <div style="margin-top: 20px; font-size: 10px; text-align: center;">
        Dhakul Chan Nice Holidays Group - System V 1.0 Page. 1 of 1
    </div>
</body>
</html>'''

with open('direct_booking_template.html', 'w', encoding='utf-8') as f:
    f.write(template_content)

print("✓ Created direct booking data template")