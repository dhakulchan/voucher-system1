#!/usr/bin/env python3
"""
Upload Thai content files to production server
"""

import base64
import requests

def upload_files():
    """Upload template and generator files"""
    
    # Read template file
    with open('templates/pdf/quote_thai_forced.html', 'r', encoding='utf-8') as f:
        template_content = f.read()
    
    # Read generator file  
    with open('services/weasyprint_quote_generator.py', 'r', encoding='utf-8') as f:
        generator_content = f.read()
    
    print(f"📄 Template size: {len(template_content)} chars")
    print(f"🔧 Generator size: {len(generator_content)} chars")
    
    # Create manual upload instructions
    instructions = f"""
🚀 MANUAL UPLOAD INSTRUCTIONS:

=== 1. Upload Template File ===
File: templates/pdf/quote_thai_forced.html
Size: {len(template_content)} characters
Action: Use Adminer file manager or SCP to upload

=== 2. Upload Generator File ===  
File: services/weasyprint_quote_generator.py
Size: {len(generator_content)} characters
Action: Use Adminer file manager or SCP to upload

=== 3. Restart Server ===
Command: sudo supervisorctl restart voucher_app

=== 4. Test URLs ===
Test PDF: https://service.dhakulchan.net/booking/test-quote-pdf/3
Debug Data: https://service.dhakulchan.net/debug/quote/3

🎯 EXPECTED RESULT:
- PDF should display Thai content from database
- Service Detail: ที่พักขึ้นใหม่ 3 วัน 2 คืน - เดินทางโดยรถปรับอากาศ...
- Guest List: นายสมชาย โจดี 2. นางสาวสุคา สวยงาม...
- Flight Info: เที่ยวบิน: Thai Airways TG118 เส้นทาง: กรุงเทพฯ...

📁 FILES READY FOR UPLOAD:
- templates/pdf/quote_thai_forced.html
- services/weasyprint_quote_generator.py
"""
    
    print(instructions)
    
    with open('upload_instructions.txt', 'w', encoding='utf-8') as f:
        f.write(instructions)
    
    print("💾 Instructions saved to: upload_instructions.txt")

if __name__ == '__main__':
    upload_files()