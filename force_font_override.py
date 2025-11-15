#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Final solution: Force register Helvetica as NotoSansThai to override system
"""

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping
import os

def force_helvetica_override():
    """Force override Helvetica fonts at system level"""
    print("🚀 Force overriding Helvetica fonts...")
    
    font_path = "static/fonts/NotoSansThai-Regular.ttf"
    font_bold_path = "static/fonts/NotoSansThai-Bold.ttf"
    
    if not os.path.exists(font_path):
        print("❌ Font files not found")
        return False
    
    try:
        # Register NotoSansThai first
        pdfmetrics.registerFont(TTFont('NotoSansThai', font_path))
        pdfmetrics.registerFont(TTFont('NotoSansThai-Bold', font_bold_path))
        
        # FORCE REGISTER Helvetica AS NotoSansThai - this is the key trick
        pdfmetrics.registerFont(TTFont('Helvetica', font_path))  # Override!
        pdfmetrics.registerFont(TTFont('Helvetica-Bold', font_bold_path))  # Override!
        pdfmetrics.registerFont(TTFont('Helvetica-Oblique', font_path))  # Override!
        pdfmetrics.registerFont(TTFont('Helvetica-BoldOblique', font_bold_path))  # Override!
        
        print("✅ Helvetica fonts overridden with NotoSansThai")
        
        # Add font family mappings
        addMapping('Helvetica', 0, 0, 'Helvetica')  # Now points to NotoSansThai
        addMapping('Helvetica', 1, 0, 'Helvetica-Bold')  # Now points to NotoSansThai-Bold
        addMapping('Helvetica', 0, 1, 'Helvetica-Oblique')  # Now points to NotoSansThai
        addMapping('Helvetica', 1, 1, 'Helvetica-BoldOblique')  # Now points to NotoSansThai-Bold
        
        print("✅ Font mappings completed")
        
        # Show registered fonts
        registered = pdfmetrics.getRegisteredFontNames()
        print(f"📋 Registered fonts: {registered}")
        
        return True
        
    except Exception as e:
        print(f"❌ Font override failed: {e}")
        return False

if __name__ == "__main__":
    force_helvetica_override()
