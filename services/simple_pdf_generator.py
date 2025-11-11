"""Simple Service Proposal PDF generator with Thai font support.

Clean rebuild with proper Thai font handling for bilingual content.
"""
from typing import Optional, List, Union

import os
import re
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Flowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from config import Config
from services.pdf_common import build_header, append_terms
from utils.pdf_sanitize import sanitize_text_block
from utils.logging_config import get_logger

FORBIDDEN_GLYPHS = {"■", "▪", "□", "•", "●", "◦"}


def _has_thai_text(text: Optional[str]) -> bool:
    """Check if text contains Thai characters."""
    if not text:
        return False
    import re
    # Clean HTML first
    clean_text = re.sub(r'<[^>]+>', '', text).replace('&nbsp;', ' ').strip()
    # Thai character detection - use safe ranges
    return bool(re.search(r'[ก-๙]|[เ-ไ]|[็-์]|[ำ]', clean_text))


def _scrub(text: Optional[str]) -> str:
    """Remove forbidden glyphs but preserve Thai characters."""
    if not text:
        return ""
    # Only replace actual forbidden glyphs, not Thai characters
    for g in FORBIDDEN_GLYPHS:
        if g in text:
            text = text.replace(g, '-')
    return text


class SimplePDFGenerator:
    OUTPUT_DIR = 'static/generated'

    def __init__(self):
        self.logger = get_logger(__name__)
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)
        self.output_dir = self.OUTPUT_DIR
        self._register_thai_fonts()
        self._init_styles()

    def _register_thai_fonts(self) -> bool:
        """Register Thai fonts for proper Thai text rendering."""
        if 'NotoSansThai' in pdfmetrics.getRegisteredFontNames():
            return True
            
        try:
            # Try to register from font files
            font_files = [
                ('NotoSansThai-Regular.ttf', 'NotoSansThai'),
                ('NotoSansThai-Bold.ttf', 'NotoSansThai-Bold'),
            ]
            
            font_dirs = ['static/fonts', 'fonts', '.']
            registered = False
            
            for font_file, font_name in font_files:
                for font_dir in font_dirs:
                    font_path = os.path.join(font_dir, font_file)
                    if os.path.exists(font_path):
                        try:
                            pdfmetrics.registerFont(TTFont(font_name, font_path))
                            registered = True
                            self.logger.info(f'Registered Thai font: {font_name}')
                        except Exception as e:
                            self.logger.warning(f'Failed to register {font_name}: {e}')
                        break
            
            return 'NotoSansThai' in pdfmetrics.getRegisteredFontNames()
            
        except Exception as e:
            self.logger.warning(f'Thai font registration failed: {e}')
            return False

    def _ensure_fonts_registered(self):
        """FORCE override Helvetica fonts with NotoSansThai - ULTIMATE FIX"""
        from reportlab.pdfbase import pdfmetrics
        from reportlab.lib.fonts import addMapping
        
        thai_font_registered = False
        
        # Register NotoSansThai first
        for font_name, font_file in [('NotoSansThai', 'NotoSansThai-Regular.ttf'), 
                                   ('NotoSansThai-Bold', 'NotoSansThai-Bold.ttf')]:
            for font_dir in ['static/fonts/', 'fonts/', './']:
                font_path = os.path.join(font_dir, font_file)
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont(font_name, font_path, validate=True))
                        thai_font_registered = True
                        self.logger.info(f'Registered Thai font: {font_name}')
                    except Exception as e:
                        self.logger.warning(f'Failed to register {font_name}: {e}')
                    break
        
        # THE KEY FIX: Register Helvetica AS NotoSansThai font files
        if thai_font_registered:
            try:
                font_path = None
                font_bold_path = None
                
                # Find font paths
                for font_dir in ['static/fonts/', 'fonts/', './']:
                    path = os.path.join(font_dir, 'NotoSansThai-Regular.ttf')
                    if os.path.exists(path):
                        font_path = path
                    path_bold = os.path.join(font_dir, 'NotoSansThai-Bold.ttf')
                    if os.path.exists(path_bold):
                        font_bold_path = path_bold
                
                if font_path and font_bold_path:
                    # FORCE OVERRIDE: Register Helvetica fonts with NotoSansThai files
                    pdfmetrics.registerFont(TTFont('Helvetica', font_path))
                    pdfmetrics.registerFont(TTFont('Helvetica-Bold', font_bold_path))
                    pdfmetrics.registerFont(TTFont('Helvetica-Oblique', font_path))
                    pdfmetrics.registerFont(TTFont('Helvetica-BoldOblique', font_bold_path))
                    
                    # Add font family mappings
                    addMapping('Helvetica', 0, 0, 'Helvetica')  # Now points to NotoSansThai
                    addMapping('Helvetica', 1, 0, 'Helvetica-Bold')  # Now points to NotoSansThai-Bold
                    addMapping('Helvetica', 0, 1, 'Helvetica-Oblique')  # Now points to NotoSansThai
                    addMapping('Helvetica', 1, 1, 'Helvetica-BoldOblique')  # Now points to NotoSansThai-Bold
                    
                    self.logger.info('🚀 HELVETICA OVERRIDDEN WITH NOTOSANSTHAI - ULTIMATE FIX APPLIED!')
                
            except Exception as e:
                self.logger.warning(f'Helvetica override failed: {e}')
        
        return thai_font_registered

    def _init_styles(self):
        """Initialize paragraph styles with proper font mixing for Thai + English."""
        sheet = getSampleStyleSheet()
        base = sheet['BodyText']
        
        # Register and validate fonts
        self._ensure_fonts_registered()
        
        # FORCE use NotoSansThai for all fonts since Helvetica is not available  
        registered_fonts = pdfmetrics.getRegisteredFontNames()
        
        if 'NotoSansThai' in registered_fonts:
            # Use NotoSansThai for everything (it handles Latin characters too)
            self.latin_font = 'NotoSansThai'
            self.latin_font_bold = 'NotoSansThai-Bold'
            self.thai_font = 'NotoSansThai'
            self.thai_font_bold = 'NotoSansThai-Bold'
            self.primary_font = 'NotoSansThai'
            self.primary_font_bold = 'NotoSansThai-Bold'
        else:
            # Fallback - shouldn't happen
            self.latin_font = 'Symbol'
            self.latin_font_bold = 'Symbol'
            self.thai_font = 'Symbol'
            self.thai_font_bold = 'Symbol'
            self.primary_font = 'Symbol'
            self.primary_font_bold = 'Symbol'
        
        self.logger.info(f'Using fonts - Primary: {self.primary_font}, Latin: {self.latin_font}, Thai: {self.thai_font}')
        
        # Modern color palette
        colors_modern = {
            'primary': '#1e40af',      # Modern blue
            'secondary': '#374151',    # Dark gray
            'text': '#111827',         # Near black
            'muted': '#6b7280',        # Medium gray
            'light': '#f3f4f6',        # Light gray
            'accent': '#3b82f6',       # Bright blue
            'success': '#059669'       # Green
        }
        
        # FORCE ALL STYLES TO USE NotoSansThai
        self.style_normal = ParagraphStyle(
            'SPNormal', parent=base, fontName='NotoSansThai', 
            fontSize=10, leading=14, textColor=colors.HexColor(colors_modern['text']),
            spaceBefore=2, spaceAfter=2
        )
        self.style_small = ParagraphStyle(
            'SPSmall', parent=self.style_normal, fontSize=9, leading=12, fontName='NotoSansThai'
        )
        self.style_small_gray = ParagraphStyle(
            'SPSmallGray', parent=self.style_small, 
            textColor=colors.HexColor(colors_modern['muted']), fontName='NotoSansThai'
        )
        self.style_title = ParagraphStyle(
            'SPTitle', parent=self.style_normal, fontSize=28, leading=34, 
            fontName='NotoSansThai-Bold', alignment=TA_CENTER, 
            textColor=colors.HexColor(colors_modern['primary']), 
            spaceBefore=8, spaceAfter=12
        )
        # Use NotoSansThai for everything
        self.style_company_name = ParagraphStyle(
            'SPCompanyName', parent=self.style_normal, fontSize=14, leading=18,
            fontName='NotoSansThai-Bold', textColor=colors.HexColor(colors_modern['primary']),
            spaceBefore=4, spaceAfter=2
        )
        self.style_company_address = ParagraphStyle(
            'SPCompanyAddress', parent=self.style_normal, fontSize=10, leading=14,
            textColor=colors.HexColor(colors_modern['secondary']), spaceAfter=4, fontName='NotoSansThai'
        )
        self.style_contact_info = ParagraphStyle(
            'SPContactInfo', parent=self.style_normal, fontSize=9, leading=11,
            textColor=colors.HexColor('#2d3748'), spaceAfter=6, fontName='NotoSansThai'
        )
        self.style_section_header = ParagraphStyle(
            'SPSection', parent=self.style_normal, fontName='NotoSansThai-Bold', 
            fontSize=11, leading=13, spaceBefore=8, spaceAfter=6,
            textColor=colors.HexColor(colors_modern['primary'])
        )
        # Enhanced style for content - ALL use NotoSansThai
        self.style_english_content = ParagraphStyle(
            'SPEnglishContent', parent=self.style_normal, fontName='NotoSansThai', 
            fontSize=10, leading=14, textColor=colors.HexColor(colors_modern['text'])
        )
        self.style_number_display = ParagraphStyle(
            'SPNumberDisplay', parent=self.style_normal, fontName='NotoSansThai-Bold', 
            fontSize=11, leading=14, textColor=colors.HexColor(colors_modern['primary'])
        )
        self.style_terms = ParagraphStyle(
            'SPTerms', parent=self.style_small, fontSize=9, leading=11, 
            leftIndent=10, textColor=colors.HexColor(colors_modern['muted']),
            fontName='NotoSansThai'
        )
        self.style_footer = ParagraphStyle(
            'SPFooter', parent=self.style_small_gray, fontSize=8, leading=10, 
            alignment=TA_CENTER, textColor=colors.HexColor(colors_modern['muted']),
            fontName='NotoSansThai'  # Use NotoSansThai for footer too
        )
        
        # Aliases needed by append_terms - ALL use NotoSansThai
        self.style_plain_ascii = ParagraphStyle(
            'SPPlainASCII', parent=self.style_small, fontName='NotoSansThai', 
            fontSize=8.5, leading=10
        )
        self.style_section = self.style_section_header
        
        # Legacy compatibility aliases - FORCE NotoSansThai
        self.base_font = 'NotoSansThai'
        self.base_font_bold = 'NotoSansThai-Bold'

    def _create_mixed_content_paragraph(self, text: str, font_size: int = 10) -> Paragraph:
        """Create paragraph that handles mixed Thai/English content properly."""
        import re
        
        # Check if text contains Thai characters
        has_thai = _has_thai_text(text)
        
        if has_thai:
            # For mixed content, wrap English parts with font tags
            # This allows mixing fonts within the same paragraph
            english_pattern = r'([A-Za-z0-9\s\.,\+\-\(\)]+)'
            
            def replace_english(match):
                english_text = match.group(1)
                return f'<font name="{self.latin_font}">{english_text}</font>'
            
            # Replace English sections with font tags while keeping Thai as primary
            modified_text = re.sub(english_pattern, replace_english, text)
            font_name = self.primary_font  # Thai font as base
            self.logger.info(f"Mixed content detected, using hybrid approach: {text[:50]}...")
        else:
            # Pure English content
            modified_text = text
            font_name = self.latin_font
            self.logger.info(f"Pure English content, using Latin font: {text[:50]}...")
        
        # Create style with primary font
        style = ParagraphStyle('MixedContent', 
                             fontName=font_name, 
                             fontSize=font_size,
                             leading=font_size * 1.2,
                             alignment=TA_LEFT)
        
        modified_text = _scrub(modified_text or '')
        modified_text = ''.join(ch if ch >= ' ' or ch == '\n' else ' ' for ch in modified_text)
        return Paragraph(modified_text, style)
        
    def _create_text_with_explicit_font(self, text: str, font_name: str, font_size: int) -> str:
        """Create text with explicit font tag and verify font availability"""
        # Debug: Verify font is registered
        from reportlab.pdfbase import pdfmetrics
        registered_fonts = pdfmetrics.getRegisteredFontNames()
        
        if font_name not in registered_fonts:
            self.logger.warning(f"⚠️ Font '{font_name}' not in registered fonts: {registered_fonts}")
            # Fallback to a known font
            if 'NotoSansThai' in registered_fonts:
                font_name = 'NotoSansThai'
            else:
                font_name = 'NotoSansThai'
        
        # Create font tag with explicit specification
        result = f'<font name="{font_name}" size="{font_size}">{text}</font>'
        self.logger.debug(f"🔤 Font tag: {font_name} for text: '{text[:30]}...'")
        return result

    def _create_forced_latin_para(self, text: str, style: Union[ParagraphStyle, None] = None) -> Paragraph:
        """Create paragraph with forced Latin font for numbers and English text."""
        if style is None:
            style = ParagraphStyle('ForcedLatin', parent=self.style_english_content,
                                 fontName=self.latin_font, fontSize=10)
        text = _scrub(text or '')
        text = ''.join(ch if ch >= ' ' or ch == '\n' else ' ' for ch in text)
        return Paragraph(text, style)
    
    def _create_thai_safe_para(self, text: str, style: Union[ParagraphStyle, None] = None) -> Paragraph:
        """Create paragraph with proper Thai font handling."""
        import re
        
        # Check if text contains Thai characters
        has_thai = bool(re.search(r'[ก-๙]', text or ''))
        
        if style is None:
            if has_thai:
                # Use Thai font for Thai content
                style = ParagraphStyle('ThaiSafe', parent=self.style_normal,
                                     fontName=self.thai_font, fontSize=10)
            else:
                # Use Latin font for English/numbers
                style = ParagraphStyle('LatinSafe', parent=self.style_english_content,
                                     fontName=self.latin_font, fontSize=10)
        
        text = _scrub(text or '')
        text = ''.join(ch if ch >= ' ' or ch == '\n' else ' ' for ch in text)
        return Paragraph(text, style)

    def _para(self, text: str, style: Union[ParagraphStyle, None] = None) -> Paragraph:
        """Create a paragraph with glyph scrubbing and smart font selection."""
        import re
        
        # Clean HTML first to get actual text content
        clean_text = re.sub(r'<[^>]+>', '', text or '')
        clean_text = clean_text.replace('&nbsp;', ' ').strip()
        
        # Check if text contains Thai characters (use individual character classes)
        has_thai = _has_thai_text(text)
        
        # Check if text contains numbers (including mixed Thai+numbers)
        has_numbers = bool(re.search(r'[0-9]', clean_text))
        
        # Check if text is primarily numbers/English (references, amounts, etc.)
        is_numeric_content = bool(re.search(r'^[A-Za-z0-9\s\-\.\,\:\(\)\+\|\/\%\$]+$', clean_text))
        
        # Debug Thai content detection
        if has_thai:
            print(f"🇹🇭 THAI DETECTED: '{clean_text[:50]}...' - using Thai font")
            self.logger.info(f"Thai content detected: '{clean_text[:50]}...' - using Thai font")
        else:
            print(f"🇺🇸 NO THAI: '{clean_text[:50]}...' - using Latin font")  
            self.logger.info(f"No Thai detected: '{clean_text[:50]}...' - using Latin font")
        
        if style is None:
            # Auto-select style based on content
            if has_thai:
                # Any Thai content: use NotoSansThai (handles English/numbers too)
                style = ParagraphStyle('AutoThai', parent=self.style_normal,
                                     fontName=self.thai_font, fontSize=10)
            elif is_numeric_content or has_numbers:
                # Pure English/numbers: use NotoSansThai
                style = ParagraphStyle('AutoLatin', parent=self.style_english_content,
                                     fontName=self.latin_font, fontSize=10)
            else:
                # Default to Latin for pure English content
                style = ParagraphStyle('AutoLatin', parent=self.style_english_content,
                                     fontName=self.latin_font, fontSize=10)
        
        text = _scrub(text or '')
        # Clean control characters but preserve Thai text
        text = ''.join(ch if ch >= ' ' or ch == '\n' else ' ' for ch in text)
        return Paragraph(text, style)

    def _para_with_font_tags(self, text: str) -> Paragraph:
        """Create paragraph with explicit font tags - ultimate Thai fix"""
        if not text or not text.strip():
            return Paragraph('', self.style_normal)
        
        # Clean the text
        text = str(text).strip()
        has_thai = _has_thai_text(text)
        
        # FORCE use raw font tags for everything
        formatted_text = f'<font name="NotoSansThai" size="10">{text}</font>'
        
        if has_thai:
            print(f'🇹🇭 FONT TAG: \'{text[:50]}...\' - NotoSansThai')
            self.logger.info(f'Thai with font tag: \'{text[:50]}...\'')
        else:
            print(f'🔤 FONT TAG: \'{text[:50]}...\' - NotoSansThai')
            self.logger.info(f'English with font tag: \'{text[:50]}...\'')
        
        # Use minimal base style 
        base_style = ParagraphStyle('FontTag', fontName='NotoSansThai', fontSize=10)
        return Paragraph(formatted_text, base_style)

    def _clean_html(self, html: str) -> str:
        """Clean HTML to allowed tags only."""
        import re
        allowed = ['b', 'i', 'u', 'br']
        html = re.sub(r'<br\s*/?>', '<br/>', html, flags=re.I)
        
        def _keep(m):
            tag = m.group(1).lower()
            return m.group(0) if tag in allowed else ''
        
        return re.sub(r'</?([a-zA-Z0-9]+)(?:\s+[^>]*)?>', _keep, html)

    def generate_simple_pdf(self, booking) -> str:
        """Generate the service proposal PDF."""
        ref = getattr(booking, 'booking_reference', None) or 'UNK'
        
        # Use microseconds for unique filename every time
        import time
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        microseconds = int(time.time() * 1000000) % 1000000  # Get last 6 digits
        
        filename = f"service_proposal_{ref}_{timestamp}_{microseconds}.pdf"
        path = os.path.join(self.output_dir, filename)
        
        doc = SimpleDocTemplate(
            path, pagesize=A4, leftMargin=28, rightMargin=28, 
            topMargin=7, bottomMargin=34,  # Keep minimal top margin
            invariant=1  # Force consistent font embedding
        )
        avail_width = A4[0] - doc.leftMargin - doc.rightMargin
        story: List = []

        # Header with content positioned directly below website/license line
        try:
            header, _ = build_header(self, avail_width)
            story.append(header)
            # Remove spacing - content should be right below website/license line
        except Exception as e:
            self.logger.warning('Header build failed: %s', e)

        # New layout matching the reference image
        # Row 1: Party Name/Status | Service Proposal (centered) | Reference/Booking Type
        party = getattr(booking, 'party_name', '') or getattr(
            getattr(booking, 'customer', None), 'name', ''
        )
        status = getattr(booking, 'status', '') or '-'
        btype = getattr(booking, 'booking_type', '') or 'tour'
        ref = getattr(booking, 'booking_reference', '') or '-'
        
        # Left: Party Name and Status
        left_text = f'Party Name: {party}<br/>Status: {status}'
        
        # Center: Service Proposal title
        center_text = '<b>Service Proposal</b>'
        
        # Right: Reference and Booking Type  
        right_text = f'Reference: {ref}<br/>Booking Type: {btype}'
        
        # Create the 3-column header table
        header_data = [[
            self._create_text_with_explicit_font(left_text, self.latin_font, 10),
            self._create_text_with_explicit_font(center_text, self.latin_font_bold, 16),
            self._create_text_with_explicit_font(right_text, self.latin_font, 10)
        ]]
        
        header_table = Table(header_data, colWidths=[avail_width*0.3, avail_width*0.4, avail_width*0.3])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (0,0), 'LEFT'),     # Left align Party Name/Status
            ('ALIGN', (1,0), (1,0), 'CENTER'),   # Center Service Proposal
            ('ALIGN', (2,0), (2,0), 'RIGHT'),    # Right align Reference/Type
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 2),    # Reduced from 12 to 2
            ('BOTTOMPADDING', (0,0), (-1,-1), 2)  # Reduced from 12 to 2
        ]))
        
        story.append(header_table)
        # Remove spacer to make content closer

        # Service Details table matching the reference image
        created_disp = (
            getattr(booking, 'created_at', None) or datetime.now(timezone.utc)
        ).strftime('%d.%b.%Y').upper()
        
        # Get travel period
        if getattr(booking, 'arrival_date', None) and getattr(booking, 'departure_date', None):
            period = f"{booking.arrival_date.strftime('%d %b %Y')} - {booking.departure_date.strftime('%d %b %Y')}"
        else:
            period = 'Details to be confirmed'
        
        # Get customer info with proper font handling
        cust = getattr(booking, 'customer', None)
        cust_name = getattr(cust, 'name', '') if cust else getattr(booking, 'customer_name', '')
        cust_phone = getattr(cust, 'phone', '') if cust else getattr(booking, 'customer_phone', '')
        
        # Build customer display as separate lines with proper fonts
        has_thai_name = _has_thai_text(cust_name)
        
        # Create customer name paragraph
        if has_thai_name:
            cust_name_para = self._create_text_with_explicit_font(cust_name or 'Customer name', self.primary_font, 10)
        else:
            cust_name_para = self._create_text_with_explicit_font(cust_name or 'Customer name', self.latin_font, 10)
        
        # Create phone paragraph separately (always in Latin font)
        if cust_phone:
            cust_phone_para = self._create_text_with_explicit_font(f'Tel. {cust_phone}', self.latin_font, 9)
        else:
            cust_phone_para = self._create_text_with_explicit_font('', self.latin_font, 9)
        
        # Combine as table cell content with line break
        from reportlab.platypus import Paragraph
        if cust_phone:
            # Use simple approach: NotoSansThai for all content
            if has_thai_name:
                # Thai customer: Use NotoSansThai for everything (phone numbers work in NotoSansThai)
                cust_display = f'{cust_name}<br/>Tel. {cust_phone}'
                cust_base_font = self.primary_font  # NotoSansThai
            else:
                # English customer: Use NotoSansThai for everything  
                cust_display = f'{cust_name}<br/>Tel. {cust_phone}'
                cust_base_font = self.latin_font  # NotoSansThai
        else:
            cust_display = cust_name or 'Customer name'
            cust_base_font = self.primary_font if has_thai_name else self.latin_font
        
        # Debug customer data
        self.logger.info(f"Customer Debug - Name: '{cust_name}', Phone: '{cust_phone}', HasThai: {has_thai_name}")
        self.logger.info(f"Customer Display: '{cust_display}'")
        
        # Get PAX info
        pax_total = getattr(booking, 'total_pax', None) or (
            getattr(booking, 'adults', 0) + getattr(booking, 'children', 0) + 
            getattr(booking, 'infants', 0)
        )
        adults = getattr(booking, 'adults', 0) or 1
        children = getattr(booking, 'children', 0)
        infants = getattr(booking, 'infants', 0)
        
        pax_display = f"{pax_total or adults} pax"
        if adults or children or infants:
            pax_display += f"<br/>Adult {adults} / Child {children}<br/>/ Infant {infants}"
        
        # Create the service details table with rounded border
        service_col_width = avail_width / 4
        
        # Table headers
        service_headers = [[
            self._create_text_with_explicit_font('<b>Create Date</b>', self.latin_font_bold, 10),
            self._create_text_with_explicit_font('<b>Traveling Period</b>', self.latin_font_bold, 10),
            self._create_text_with_explicit_font('<b>Customer</b>', self.latin_font_bold, 10),
            self._create_text_with_explicit_font('<b>PAX</b>', self.latin_font_bold, 10)
        ]]
        
        # Table data
        created_date_text = f"{created_disp}<br/><font color='#666666'>By: admin</font>"
        
        service_data = [[
            self._create_text_with_explicit_font(created_date_text, self.latin_font, 10),
            self._create_text_with_explicit_font(period, self.latin_font, 10),
            self._create_text_with_explicit_font(cust_display, cust_base_font, 10),  # Use determined base font
            self._create_text_with_explicit_font(pax_display, self.latin_font, 10)
        ]]
        
        # Combine headers and data
        service_table = Table(service_headers + service_data, colWidths=[service_col_width] * 4)
        service_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            # Rounded border
            ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor('#d1d5db')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
            # Header background
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f9fafb')),
            # Data background
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ]))
        
        story.append(service_table)
        story.append(Spacer(1, 4))  # Very small space after table        # Itinerary / service detail
        story.append(self._para_with_font_tags('Service Detail / Itinerary:'))  # Use font tags
        raw_desc = getattr(booking, 'description', '') or getattr(booking, 'tour_name', '') or ''
        raw_desc = sanitize_text_block(raw_desc)
        cleaned = self._clean_html(raw_desc).replace('<br/>', '\n')
        lines = [l.strip() for l in cleaned.split('\n') if l.strip()] or ['Details to be confirmed.']
        
        skip = {'•', '●', '◦'}
        for line in lines:
            if line in skip:
                continue
            story.append(self._para_with_font_tags(self._clean_html(line)))  # Use font tags
        story.append(Spacer(1, 6))

        # Flight Information - เพิ่มด้านล่างของ Service Detail / Itinerary
        flight_info = getattr(booking, 'flight_info', '')
        if flight_info and flight_info.strip():
            flight_info = sanitize_text_block(flight_info)
            cleaned_flight = self._clean_html(flight_info).replace('<br/>', '\n')
            flight_lines = [l.strip() for l in cleaned_flight.split('\n') if l.strip()]
            
            if flight_lines:
                story.append(self._para('Flight Information:'))  # Use auto-detection
                for line in flight_lines:
                    story.append(self._para(self._clean_html(line)))
                story.append(Spacer(1, 6))

        # Payment Information with Products & Calculation
        story.append(self._para('Payment Information:'))  # Use auto-detection
        
        # Products & Calculation table
        products = booking.get_products() if hasattr(booking, 'get_products') else []
        if products:
            # Create products table data
            table_data = [
                ['No.', 'Products', 'Quantity', 'Price (THB)', 'Amount (THB)']
            ]
            
            total_amount = 0
            for i, product in enumerate(products, 1):
                if isinstance(product, dict):
                    name = product.get('name', f'Product {i}')
                    quantity = float(product.get('quantity', 0))
                    price = float(product.get('price', 0))
                    amount = quantity * price
                    total_amount += amount
                    
                    # Format numbers with 2 decimal places
                    table_data.append([
                        str(i),
                        self._clean_html(name),
                        f"{quantity:,.0f}" if quantity == int(quantity) else f"{quantity:,.2f}",
                        f"{price:,.2f}",
                        f"{amount:,.2f}"
                    ])
            
            # Create the products table
            products_table = Table(table_data, colWidths=[30, 180, 60, 80, 80])
            products_table.setStyle(TableStyle([
                # Header row styling
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5aa0')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), self.latin_font),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTWEIGHT', (0, 0), (-1, 0), 'bold'),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                
                # Data rows styling
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), self.latin_font),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # No. column
                ('ALIGN', (1, 1), (1, -1), 'LEFT'),    # Products column
                ('ALIGN', (2, 1), (2, -1), 'CENTER'),  # Quantity column
                ('ALIGN', (3, 1), (3, -1), 'RIGHT'),   # Price column
                ('ALIGN', (4, 1), (4, -1), 'RIGHT'),   # Amount column
                ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
                
                # Borders
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
                
                # Alternating row colors
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
            ]))
            
            story.append(products_table)
            story.append(Spacer(1, 8))
            
            # Grand Total
            total_text = f"<b>Grand Total: THB {total_amount:,.2f}</b>"
            total_para = Paragraph(self._create_text_with_explicit_font(total_text, self.latin_font, 11), self.style_small)
            story.append(total_para)
        else:
            # Fallback to simple total display if no products
            amount = getattr(booking, 'total_amount', None) or getattr(booking, 'price', None) or 0
            if amount:
                amount_str = f"{float(amount):,.2f}"
                payment_text = f"<b>Total:</b> THB {amount_str}"
            else:
                payment_text = "<b>Total:</b> THB 0.00"
            
            payment_para = Paragraph(self._create_text_with_explicit_font(payment_text, self.latin_font, 10), self.style_small)
            story.append(payment_para)
        
        story.append(Spacer(1, 8))

        # Guest List - เพิ่มด้านบนของ Special Requests
        guest_list = booking.get_guest_list() if hasattr(booking, 'get_guest_list') else []
        if guest_list:
            story.append(self._para('Name List / Rooming List:'))  # Use auto-detection
            for i, guest in enumerate(guest_list, 1):
                if isinstance(guest, dict):
                    guest_name = guest.get('name', f'Guest {i}')
                else:
                    guest_name = str(guest) if guest else f'Guest {i}'
                story.append(self._para(f"{i}. {self._clean_html(guest_name)}"))
            story.append(Spacer(1, 6))

        # Special Requests
        sreq = getattr(booking, 'special_request', '')
        sreq = re.sub(r'<[^>]+>', '', sreq or '').strip()
        if sreq and sreq.lower() not in {'none', 'n/a', 'na'}:
            # Use font tags for Special Requests
            story.append(self._para_with_font_tags('Special Requests:'))  # Use font tags
            story.append(self._para_with_font_tags(self._clean_html(sreq)))  # Use font tags
            story.append(Spacer(1, 6))

        # Terms & Conditions
        append_terms(story, self, getattr(Config, 'DEFAULT_LANGUAGE', 'en'))

        # Footer with new text
        story.append(Spacer(1, 12))
        footer_text = "Dhakul Chan Nice Holidays Group - System DCTS V1.0"
        footer_style = ParagraphStyle(
            'Footer',
            parent=self.style_english_content,
            fontName=self.latin_font,
            fontSize=8,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#64748B')
        )
        story.append(Paragraph(footer_text, footer_style))

        # Page callback with explicit Latin font
        def _on_page(canvas, _doc):
            canvas.saveState()
            canvas.setFont('NotoSansThai', 8)  # Use NotoSansThai instead of Helvetica
            canvas.setFillColor(colors.HexColor('#64748B'))
            canvas.drawRightString(A4[0] - 40, 15, f"Page {canvas.getPageNumber()}")
            canvas.restoreState()

        # Optional font embedding
        if getattr(Config, 'PDF_FORCE_EMBED_FONTS', False):
            for ef in [f for f in getattr(Config, 'PDF_FALLBACK_FONTS', []) 
                      if f in pdfmetrics.getRegisteredFontNames()]:
                story.append(Paragraph(
                    ' ', ParagraphStyle(f'Embed_{ef}', parent=self.style_normal, 
                                      fontName=ef, fontSize=1, leading=1)
                ))

        # Final glyph scrub
        try:
            from reportlab.platypus import Paragraph as _P, Table as _T
            for fl in story:
                if isinstance(fl, _P) and hasattr(fl, '_text'):
                    fl._text = _scrub(fl._text)
                elif isinstance(fl, _T):
                    for row in fl._cellvalues:
                        for val in row:
                            if isinstance(val, _P) and hasattr(val, '_text'):
                                val._text = _scrub(val._text)
        except Exception:
            pass

        doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
        self.logger.info('Simple PDF generated %s', filename)
        return filename


__all__ = ['SimplePDFGenerator']
