"""Shared PDF generation helpers (header, terms) to DRY generators."""
from __future__ import annotations

import os
from reportlab.platypus import Table, TableStyle, Image, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from config import Config

def build_header(generator, avail_width: float, header_type: str = 'booking'):
    """Return (flowable, logo_width) header table using Config sizing.
    generator is expected to provide style_small_gray.
    header_type: 'booking' for DHAKUL CHAN text header, 'voucher' for image header
    """
    
    # Choose header approach based on type
    if header_type == 'voucher':
        return build_voucher_image_header(generator, avail_width)
    else:
        return build_booking_text_header(generator, avail_width)


def build_booking_text_header(generator, avail_width: float):
    """Build traditional text-based header for Booking PDFs."""
    logo_candidates = ['dcts-logo-vou.png', os.path.join('static','images','dcts-logo-vou.png')]
    try:
        from flask import current_app
        if current_app:
            logo_candidates += [
                os.path.join(current_app.root_path, 'dcts-logo-vou.png'),
                os.path.join(current_app.root_path, 'static','images','dcts-logo-vou.png')
            ]
    except Exception:
        pass
    logo_flow = Spacer(1, Config.PDF_LOGO_TARGET_HEIGHT)
    scaled_w = 150.0
    for lp in logo_candidates:
        if os.path.exists(lp):
            try:
                from PIL import Image as PILImage
                with PILImage.open(lp) as im:
                    target_h = Config.PDF_LOGO_TARGET_HEIGHT
                    max_w = Config.PDF_LOGO_MAX_WIDTH
                    scale = target_h / im.height
                    w_scaled = im.width * scale
                    if w_scaled > max_w:
                        scale = max_w / im.width
                        w_scaled = im.width * scale
                        target_h = im.height * scale
                    logo_flow = Image(lp, width=w_scaled, height=target_h)
                    scaled_w = w_scaled
                    break
            except Exception:
                continue
    contact_parts = [f"Tel: {Config.COMPANY_PHONE}"]
    line_oa = getattr(Config, 'COMPANY_LINE_OA', '')
    if line_oa:
        contact_parts.append(f"Line OA: {line_oa}")
    contact_parts.append(f"Website: {Config.COMPANY_WEBSITE}")
    contact_line = " | ".join(contact_parts)
    
    # Get basic styles and ensure proper fonts
    from reportlab.lib.styles import getSampleStyleSheet
    basic_styles = getSampleStyleSheet()
    
    # Modern color palette
    colors_modern = {
        'primary': '#1e40af',      # Modern blue
        'secondary': '#374151',    # Dark gray
        'text': '#111827',         # Near black
        'muted': '#6b7280',        # Medium gray
        'accent': '#3b82f6',       # Bright blue
        'border': '#e5e7eb'        # Light border
    }
    
    # Calculate proper column widths with better proportions
    license_width = 140  # Wider for better license display
    logo_padding = 20
    # Simple header layout without license box - matching reference image
    # Logo + Company info only (2 columns)
    logo_padding = 12
    company_width = avail_width - (scaled_w + logo_padding)
    
    # Enhanced company information block matching reference style
    # Single line format: Company Name + Address + Contact + License
    header_text = (
        f"<b><font size='12'>{Config.COMPANY_NAME_EN}</font></b><br/>"  # Increased 10% from size 10
        f"{Config.COMPANY_ADDRESS_EN}<br/>"
        f"Tel: {Config.COMPANY_PHONE} | +662 0266525 Fax: +662 0266525 Press 5 | Line: @dhakulchan<br/>"
        f"Website: www.dhakulchan.net | T.A.T License {Config.PDF_LICENSE_VALUE}"  # Removed <u> tags
    )
    
    company_block = Table([
        [Paragraph(header_text, 
                  ParagraphStyle('headerText', parent=basic_styles['Normal'], 
                               fontSize=10, leading=13, fontName='Helvetica',
                               textColor=colors.black,
                               spaceBefore=4, spaceAfter=4))]
    ], colWidths=[company_width])
    
    # Simple company block styling without background
    company_block.setStyle(TableStyle([
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),
        ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
    ]))
    
    # Simple header table - Logo + Company info only (no license box)
    header_tbl = Table([[logo_flow, company_block]], 
                      colWidths=[scaled_w, company_width])
    header_tbl.setStyle(TableStyle([
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('ALIGN',(0,0),(0,0),'LEFT'),    # Logo alignment
        ('ALIGN',(1,0),(1,0),'LEFT'),    # Company info alignment
        ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
        ('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),12),
        ('BACKGROUND',(0,0),(-1,-1),colors.white),
    ]))
    return header_tbl, scaled_w


def build_voucher_image_header(generator, avail_width: float):
    """Build image-based header for Tour Voucher PDFs using Tour-voucher-header250822-up.png."""
    
    # Look for Tour voucher header image
    voucher_header_candidates = [
        'Tour-voucher-header250822-up.png',
        os.path.join('static', 'images', 'Tour-voucher-header250822-up.png')
    ]
    
    try:
        from flask import current_app
        if current_app:
            voucher_header_candidates += [
                os.path.join(current_app.root_path, 'Tour-voucher-header250822-up.png'),
                os.path.join(current_app.root_path, 'static', 'images', 'Tour-voucher-header250822-up.png')
            ]
    except Exception:
        pass
    
    # Try to find and load the voucher header image
    header_image = None
    header_width = avail_width
    header_height = 100  # Default height
    
    for img_path in voucher_header_candidates:
        if os.path.exists(img_path):
            try:
                from PIL import Image as PILImage
                with PILImage.open(img_path) as im:
                    # Scale to fit available width while maintaining aspect ratio
                    aspect_ratio = im.width / im.height
                    if aspect_ratio > (avail_width / 100):  # Too wide
                        header_width = avail_width
                        header_height = avail_width / aspect_ratio
                    else:  # Scale by height
                        header_height = 100
                        header_width = header_height * aspect_ratio
                    
                    header_image = Image(img_path, width=header_width, height=header_height)
                    break
            except Exception as e:
                print(f"Could not load voucher header image {img_path}: {e}")
                continue
    
    if header_image is None:
        # Fallback to text header if image not found
        print("Tour voucher header image not found, falling back to text header")
        return build_booking_text_header(generator, avail_width)
    
    # Create simple table with just the header image
    header_table = Table([[header_image]], colWidths=[avail_width])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    
    return header_table, header_width


def append_terms(story: list, generator, lang: str):
    """Append terms section to story using generator styles.
    Includes ASCII header + Thai terms + optional voucher terms if enabled.
    """
    from utils.locale_labels import get_label
    from services.terms_constants import THAI_TERMS_BOOKING, THAI_TERMS_VOUCHER
    from reportlab.lib.styles import ParagraphStyle
    
    # Use simple English header to avoid font issues
    story.append(Paragraph('Terms & Conditions:', generator.style_section))
    
    # Create Thai-specific style for terms with Thai font support
    thai_terms_style = ParagraphStyle(
        'ThaiTerms', 
        parent=generator.style_terms,
        fontName='NotoSansThai',  # Use Thai font for Thai text
        fontSize=9,
        leading=11,
        leftIndent=10
    )
    
    terms = list(THAI_TERMS_BOOKING)
    if getattr(Config, 'PDF_TERMS_INCLUDE_VOUCHER', True):
        # Add specific voucher terms we want with consistent Thai font
        voucher_terms_to_add = [
            "โปรดตรวจสอบข้อมูลเที่ยวบิน โรงแรม และบริการทุกประเภทให้ถูกต้องก่อนใช้งาน",
            'หากมีการเปลี่ยนแปลง กรุณาแจ้งล่วงหน้าอย่างน้อย 24 ชั่วโมง',
            "ในกรณีฉุกเฉินโปรดติดต่อหมายเลขประสานงานที่ระบุในเอกสารนี้",
        ]
        
        for v in voucher_terms_to_add:
            if v not in terms:
                terms.append(v)
    
    # Use numbered list for Terms & Conditions with NotoSansThai font
    for i, raw in enumerate(terms, 1):
        base = raw
        
        # Use Thai font for both numbers and text to avoid font mapping issues
        number_text = f"{i}."
        
        # Use single font to avoid font family mapping conflicts
        txt = f'{number_text} {base}'
        
        # Use Thai font style consistently
        thai_style = ParagraphStyle(
            f'ThaiTerms_{i}', 
            parent=generator.style_terms,
            fontName='NotoSansThai',  # Use NotoSansThai consistently
            fontSize=9,
            leading=11,
            leftIndent=10
        )
        story.append(Paragraph(txt, thai_style))
    # Remove spacing after Terms & Conditions

__all__ = ['build_header', 'build_booking_text_header', 'build_voucher_image_header', 'append_terms']