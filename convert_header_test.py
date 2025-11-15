#!/usr/bin/env python3
"""
Convert header/footer test PDF to PNG for visual verification
"""

import sys
import os
sys.path.append('/Applications/python/voucher-ro_v1.0')

def convert_header_test_to_png():
    """Convert header/footer test PDF to PNG"""
    
    pdf_file = "static/generated/header_footer_test.pdf"
    
    if not os.path.exists(pdf_file):
        print(f"❌ PDF file not found: {pdf_file}")
        return
    
    try:
        from pdf2image import convert_from_path
        
        print(f"🔄 Converting {pdf_file} to PNG...")
        
        # Convert PDF to images with high quality
        pages = convert_from_path(pdf_file, dpi=150, fmt='png')
        
        for i, page in enumerate(pages, 1):
            png_path = f"static/generated/header_footer_test_page_{i}.png"
            page.save(png_path, 'PNG')
            
            file_size = os.path.getsize(png_path)
            print(f"   ✅ Page {i} saved: {png_path} ({file_size:,} bytes)")
        
        print(f"\n📸 Header/Footer Visual Check:")
        print(f"   📄 Total pages: {len(pages)}")
        print(f"   🔍 Check each page for:")
        print(f"     • Smaller logo (35mm x 17mm)")
        print(f"     • Original company info from Prachauthit Road")
        print(f"     • Footer with 'Dhakul Chan Nice Holidays Group - System DCTS V1.0'")
        print(f"     • Page numbers on the right")
        print(f"     • Header appears on every page")
        
    except ImportError:
        print(f"❌ pdf2image not available, using alternative method...")
        
        # Alternative: Use reportlab canvas to create comparison
        try:
            import subprocess
            result = subprocess.run(['which', 'convert'], capture_output=True, text=True)
            if result.returncode == 0:
                cmd = f"convert -density 150 '{pdf_file}' 'static/generated/header_footer_test_page.png'"
                os.system(cmd)
                print(f"   ✅ Converted using ImageMagick")
            else:
                print(f"   ⚠️  PDF conversion tools not available")
                print(f"   📄 Please check PDF manually: {pdf_file}")
        except Exception as e:
            print(f"   ⚠️  Could not convert: {str(e)}")
            print(f"   📄 Please check PDF manually: {pdf_file}")
    
    except Exception as e:
        print(f"❌ Error converting PDF: {str(e)}")

if __name__ == '__main__':
    convert_header_test_to_png()
