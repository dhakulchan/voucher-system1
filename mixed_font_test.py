#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mixed font approach - use different fonts for Thai and English
"""

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import ParagraphStyle  
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
import re

def mixed_font_test():
    print("🌏 Mixed Font Test (Thai + English)")
    
    # Register Thai font
    thai_font_path = "static/fonts/NotoSansThai-Regular.ttf"
    pdfmetrics.registerFont(TTFont('NotoSansThai', thai_font_path))
    
    # Keep Helvetica for English
    print("✅ Fonts registered: NotoSansThai + Helvetica")
    
    # Test data
    test_texts = [
        "วันใหม่ ใจดี",  # Thai only
        "Customer Name",  # English only  
        "Customer: วันใหม่ ใจดี",  # Mixed
        "Tel. +66-2-234-5678",  # English with numbers
        "ทดสอบการจองทัวร์สำหรับลูกค้าไทย",  # Thai sentence
        "Adult 2, Child 1, วันใหม่ ใจดี"  # Complex mixed
    ]
    
    def has_thai(text):
        return bool(re.search(r'[ก-๙]', text))
    
    def make_mixed_text(text):
        """Convert text to use appropriate fonts"""
        if not has_thai(text):
            # English only - use Helvetica
            return f'<font name="Helvetica" size="12">{text}</font>'
        
        # Has Thai - use Thai font for everything
        return f'<font name="NotoSansThai" size="12">{text}</font>'
    
    # Create PDF
    doc = SimpleDocTemplate("static/generated/mixed_font_test.pdf", pagesize=A4)
    story = []
    
    # Basic style for font tags
    basic_style = ParagraphStyle('BasicStyle', fontSize=12, leading=16)
    
    story.append(Paragraph("=== Mixed Font Test ===", basic_style))
    
    for text in test_texts:
        print(f"📝 Processing: '{text}'")
        
        is_thai = has_thai(text)
        mixed_text = make_mixed_text(text)
        
        print(f"   Thai detected: {is_thai}")
        print(f"   Final markup: {mixed_text}")
        
        story.append(Paragraph(f"Original: {text}", basic_style))
        story.append(Paragraph(mixed_text, basic_style))
        
        from reportlab.platypus import Spacer
        story.append(Spacer(1, 10))
    
    # Build PDF
    print("\n📄 Building PDF...")
    doc.build(story)
    
    pdf_path = "static/generated/mixed_font_test.pdf"
    print(f"✅ Mixed font PDF created: {pdf_path}")
    
    # Analyze result
    print("\n🔍 PDF Analysis:")
    import subprocess
    try:
        result = subprocess.run(['strings', pdf_path], capture_output=True, text=True)
        content = result.stdout
        
        # Check for both Thai and English
        thai_found = any(char in content for char in ['วัน', 'ใหม่', 'ใจ', 'ดี'])
        english_found = any(word in content for word in ['Customer', 'Adult', 'Child', 'Tel'])
        
        print(f"   Thai text found: {thai_found}")
        print(f"   English text found: {english_found}")
        
        # Font analysis
        fonts = []
        for line in content.split('\n'):
            if 'FontName' in line or 'BaseFont' in line:
                fonts.append(line.strip())
        
        print(f"   Fonts used: {len(fonts)}")
        for font in fonts:
            print(f"     {font}")
            
    except Exception as e:
        print(f"   ❌ Analysis failed: {e}")
    
    # Open result
    os.system(f"open {pdf_path}")

if __name__ == "__main__":
    mixed_font_test()
