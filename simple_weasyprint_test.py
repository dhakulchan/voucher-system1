#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple WeasyPrint test without complex styling
"""

import weasyprint
import os

def simple_weasyprint_test():
    print("🔬 Simple WeasyPrint Test")
    
    # Very basic HTML with Thai text
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {
                size: A4;
                margin: 2cm;
            }
            
            body {
                font-family: Arial, sans-serif;
                font-size: 16px;
                line-height: 1.5;
            }
            
            .thai {
                font-size: 18px;
                color: blue;
            }
            
            .english {
                font-size: 16px;
                color: green;
            }
        </style>
    </head>
    <body>
        <h1>Simple Test</h1>
        
        <p class="english">English Text: Hello World!</p>
        <p class="thai">Thai Text: วันใหม่ ใจดี</p>
        <p class="thai">More Thai: ทดสอบการจองทัวร์สำหรับลูกค้าไทย</p>
        
        <h2>Customer Information</h2>
        <p>Name: วันใหม่ ใจดี</p>
        <p>Email: wanmai@email.com</p>
        <p>Phone: +66-2-234-5678</p>
        
        <h2>Mixed Content</h2>
        <p>Customer วันใหม่ ใจดี has booked Adult 2, Child 1</p>
        <p>บริการทัวร์ Bangkok City Tour ราคา ฿1,500</p>
        
        <h2>Thai Numbers</h2>
        <p>๐ ๑ ๒ ๓ ๔ ๕ ๖ ๗ ๘ ๙</p>
    </body>
    </html>
    """
    
    try:
        print("📄 Converting HTML to PDF...")
        
        # Convert using WeasyPrint
        base_url = f"file://{os.path.abspath('.')}"
        html = weasyprint.HTML(string=html_content, base_url=base_url)
        
        pdf_path = "static/generated/simple_weasyprint_test.pdf"
        html.write_pdf(pdf_path)
        
        print(f"✅ Simple PDF created: {pdf_path}")
        
        # Check file size
        size = os.path.getsize(pdf_path)
        print(f"📏 File size: {size:,} bytes")
        
        # Analyze content with pdftotext if available
        print("\n🔍 Trying pdftotext analysis...")
        import subprocess
        
        try:
            # Try pdftotext (better for extracting actual text)
            result = subprocess.run(['pdftotext', pdf_path, '-'], capture_output=True, text=True)
            if result.returncode == 0:
                text_content = result.stdout
                print("📝 Extracted text content:")
                print("=" * 40)
                print(text_content)
                print("=" * 40)
                
                # Check for specific content
                checks = [
                    ('วันใหม่', 'Thai name'),
                    ('ใจดี', 'Thai surname'),
                    ('ทดสอบ', 'Thai test word'),
                    ('Hello World', 'English text'),
                    ('Customer', 'English label'),
                    ('Bangkok', 'Mixed content')
                ]
                
                print("\n✅ Content verification:")
                for text, desc in checks:
                    found = text in text_content
                    status = "✅" if found else "❌"
                    print(f"  {status} {desc}: '{text}' - {found}")
                    
            else:
                print("❌ pdftotext failed")
                
        except FileNotFoundError:
            print("⚠️ pdftotext not available, trying strings...")
            
            # Fallback to strings
            result = subprocess.run(['strings', pdf_path], capture_output=True, text=True)
            content = result.stdout
            
            if 'วันใหม่' in content or 'Hello' in content:
                print("✅ Some text found in strings output")
            else:
                print("❌ No readable text found in strings output")
        
        # Open PDF for visual inspection
        print(f"\n👀 Opening PDF for visual inspection...")
        os.system(f"open '{pdf_path}'")
        
        return pdf_path
        
    except Exception as e:
        print(f"❌ WeasyPrint failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = simple_weasyprint_test()
    if result:
        print(f"\n🎯 Simple test completed!")
        print(f"If you can see Thai characters in the opened PDF,")
        print(f"then WeasyPrint is working and we just need to fix our complex template.")
    else:
        print(f"\n💔 Simple test failed!")
