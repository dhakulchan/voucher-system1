#!/usr/bin/env python3
"""
Generate PNG from Status field test PDFs
"""

import sys
import os
sys.path.append('/Applications/python/voucher-ro_v1.0')

import subprocess
from PIL import Image
import fitz  # PyMuPDF

def pdf_to_png(pdf_path, png_path):
    """Convert PDF to PNG using PyMuPDF"""
    try:
        # Open PDF
        doc = fitz.open(pdf_path)
        page = doc[0]  # First page
        
        # Render page to pixmap with high resolution
        mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
        pix = page.get_pixmap(matrix=mat)
        
        # Save as PNG
        pix.save(png_path)
        doc.close()
        
        return True
    except Exception as e:
        print(f"❌ Error converting {pdf_path}: {str(e)}")
        return False

def generate_status_pngs():
    """Generate PNG previews from Status test PDFs"""
    
    pdf_files = [
        "static/generated/test_status_confirmed_1.pdf",
        "static/generated/test_status_pending_2.pdf", 
        "static/generated/test_status_cancelled_3.pdf",
        "static/generated/real_db_status_1_confirmed.pdf",
        "static/generated/real_db_status_2_pending.pdf"
    ]
    
    successful_conversions = 0
    
    for pdf_path in pdf_files:
        if os.path.exists(pdf_path):
            # Create PNG filename
            png_path = pdf_path.replace('.pdf', '.png')
            
            print(f"🔄 Converting: {os.path.basename(pdf_path)}")
            
            if pdf_to_png(pdf_path, png_path):
                file_size = os.path.getsize(png_path)
                print(f"   ✅ PNG created: {os.path.basename(png_path)} ({file_size:,} bytes)")
                successful_conversions += 1
            else:
                print(f"   ❌ Failed to convert: {os.path.basename(pdf_path)}")
        else:
            print(f"❌ PDF not found: {pdf_path}")
    
    print(f"\n📊 Conversion Summary:")
    print(f"   ✅ Successful: {successful_conversions}")
    print(f"   📄 Total PDFs: {len(pdf_files)}")
    
    if successful_conversions > 0:
        print(f"\n🎯 Status Field Verification:")
        print(f"   - Check PNG files in static/generated/")
        print(f"   - Look for 'Status: [value]' under Party Name")
        print(f"   - Confirm different status values are displayed correctly")
        
        # List generated PNG files
        print(f"\n📸 Generated PNG Files:")
        for pdf_path in pdf_files:
            png_path = pdf_path.replace('.pdf', '.png')
            if os.path.exists(png_path):
                print(f"   📄 {os.path.basename(png_path)}")

if __name__ == '__main__':
    generate_status_pngs()
