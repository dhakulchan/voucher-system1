#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Force Thai font registration and test
"""

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
import os

def force_thai_font_test():
    print("🔧 Force Thai Font Test")
    
    # Clear all existing registrations
    print("🧹 Clearing font registrations...")
    
    # Register Thai font with FORCE
    thai_font_path = "static/fonts/NotoSansThai-Regular.ttf"
    
    print("📝 Force registering NotoSansThai...")
    pdfmetrics.registerFont(TTFont('NotoSansThai', thai_font_path))
    
    # ALSO register as DEFAULT fonts
    print("🔄 Overriding default fonts...")
    pdfmetrics.registerFont(TTFont('Helvetica', thai_font_path))
    pdfmetrics.registerFont(TTFont('Times-Roman', thai_font_path))
    pdfmetrics.registerFont(TTFont('Courier', thai_font_path))
    
    # Test 1: Direct canvas approach (most basic)
    print("\n🎨 Test 1: Direct Canvas")
    pdf_path1 = "static/generated/force_canvas_test.pdf"
    c = canvas.Canvas(pdf_path1, pagesize=A4)
    
    # Set font explicitly
    c.setFont('NotoSansThai', 14)
    
    # Draw Thai text directly
    thai_text = "วันใหม่ ใจดี"
    c.drawString(100, 750, f"Canvas Direct: {thai_text}")
    
    # Also test with Helvetica (which should now be NotoSansThai)
    c.setFont('Helvetica', 14) 
    c.drawString(100, 720, f"Canvas Helvetica: {thai_text}")
    
    c.save()
    print(f"✅ Canvas PDF created: {pdf_path1}")
    
    # Test 2: Platypus with explicit font
    print("\n📄 Test 2: Platypus Explicit")
    pdf_path2 = "static/generated/force_platypus_test.pdf"
    doc = SimpleDocTemplate(pdf_path2, pagesize=A4)
    
    story = []
    
    # Force Thai font style
    thai_style = ParagraphStyle(
        'ForceThaiStyle',
        fontName='NotoSansThai',
        fontSize=14,
        leading=18
    )
    
    # Force Helvetica style (should be Thai now)
    helvetica_style = ParagraphStyle(
        'ForceHelveticaStyle', 
        fontName='Helvetica',
        fontSize=14,
        leading=18
    )
    
    story.append(Paragraph(f"Explicit NotoSansThai: {thai_text}", thai_style))
    story.append(Paragraph(f"Helvetica Override: {thai_text}", helvetica_style))
    
    # Raw font tags
    from reportlab.lib.styles import getSampleStyleSheet
    styles = getSampleStyleSheet()
    normal_style = styles['Normal']
    
    tagged_text = f'<font name="NotoSansThai" size="14">Font Tag: {thai_text}</font>'
    story.append(Paragraph(tagged_text, normal_style))
    
    doc.build(story)
    print(f"✅ Platypus PDF created: {pdf_path2}")
    
    # Analyze both PDFs
    for pdf_path, test_name in [(pdf_path1, "Canvas"), (pdf_path2, "Platypus")]:
        print(f"\n🔍 {test_name} PDF Analysis:")
        
        import subprocess
        try:
            result = subprocess.run(['strings', pdf_path], capture_output=True, text=True)
            content = result.stdout
            
            # Check for Thai text
            thai_found = any(char in content for char in ['วัน', 'ใหม่', 'ใจ', 'ดี'])
            print(f"   Thai characters found: {thai_found}")
            
            # Check font info
            fonts_found = []
            for line in content.split('\n'):
                if 'FontName' in line or 'BaseFont' in line:
                    fonts_found.append(line.strip())
            
            print(f"   Fonts in PDF: {len(fonts_found)}")
            for font in fonts_found:
                print(f"     {font}")
                
        except Exception as e:
            print(f"   ❌ Analysis failed: {e}")
    
    # Open the files
    os.system(f"open {pdf_path1}")
    os.system(f"open {pdf_path2}")

if __name__ == "__main__":
    force_thai_font_test()
