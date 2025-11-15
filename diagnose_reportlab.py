#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnose ReportLab Thai font support issue
"""

import reportlab
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

def diagnose_reportlab():
    print("🔍 ReportLab Diagnosis")
    print("=" * 50)
    
    print(f"📦 ReportLab version: {reportlab.Version}")
    
    # Check registered fonts
    print("\n📚 Currently registered fonts:")
    try:
        fonts = pdfmetrics.getRegisteredFontNames()
        for font in sorted(fonts):
            print(f"  - {font}")
    except Exception as e:
        print(f"  ❌ Error getting fonts: {e}")
    
    # Test font registration
    print("\n🔧 Font Registration Test:")
    thai_font = "static/fonts/NotoSansThai-Regular.ttf"
    
    if os.path.exists(thai_font):
        try:
            # Try different registration approaches
            print("  1. Basic registration...")
            pdfmetrics.registerFont(TTFont('TestThai', thai_font))
            print("  ✅ Basic registration OK")
            
            print("  2. Registration with encoding...")
            pdfmetrics.registerFont(TTFont('TestThai2', thai_font))
            print("  ✅ Encoding registration OK")
            
            # Test text rendering capability
            print("\n📝 Text Rendering Test:")
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph
            from reportlab.lib.styles import ParagraphStyle
            
            # Create minimal test
            doc = SimpleDocTemplate("static/generated/minimal_thai_test.pdf", pagesize=A4)
            
            # Test with different text types
            test_texts = [
                "Simple Latin text",
                "วันใหม่",  # Thai only
                "Mixed วันใหม่ text",  # Mixed
                "ABC123",  # ASCII only
            ]
            
            story = []
            style = ParagraphStyle('TestStyle', fontName='TestThai', fontSize=12)
            
            for text in test_texts:
                print(f"    Testing: '{text}'")
                try:
                    para = Paragraph(text, style)
                    story.append(para)
                    print(f"    ✅ Paragraph created for '{text}'")
                except Exception as e:
                    print(f"    ❌ Failed for '{text}': {e}")
            
            # Build PDF
            try:
                doc.build(story)
                print("  ✅ PDF build successful")
                
                # Check output
                pdf_path = "static/generated/minimal_thai_test.pdf"
                size = os.path.getsize(pdf_path)
                print(f"  📏 Output size: {size} bytes")
                
            except Exception as e:
                print(f"  ❌ PDF build failed: {e}")
                import traceback
                traceback.print_exc()
                
        except Exception as e:
            print(f"  ❌ Font registration failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"  ❌ Font file not found: {thai_font}")
    
    # Test character encoding
    print("\n🔤 Character Encoding Test:")
    thai_text = "วันใหม่ ใจดี"
    print(f"  Original: '{thai_text}'")
    print(f"  UTF-8 bytes: {thai_text.encode('utf-8')}")
    print(f"  Length: {len(thai_text)} characters")
    
    # Character by character
    for i, char in enumerate(thai_text):
        print(f"    [{i}] '{char}' = U+{ord(char):04X}")

if __name__ == "__main__":
    diagnose_reportlab()
