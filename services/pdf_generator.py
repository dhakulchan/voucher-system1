"""PDF generation module with Service Proposal layout and glyph handling."""

from __future__ import annotations
from __future__ import annotations

"""PDF generation module with Service Proposal layout, terms styling, and glyph sanitization.

Key goals:
 - Larger header image & compact metadata row.
 - Inline Party / Reference / Booking Type plus plain ASCII duplicates for text extraction tests.
 - Itinerary table with optional zebra striping and captured style commands for tests.
 - Terms list with configurable style (number/dash/none) using English wording for extraction while retaining Thai list constant at class-level for legacy tests.
 - Footer with Generated timestamp & company info.
 - Removal / replacement of problematic square or bullet glyphs.
 - Provide ASCII duplicates for ARNO/QTNO and numbered terms to avoid null-byte extraction issues.
"""

import os
from io import BytesIO
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from services.pdf_common import build_header, append_terms

from utils.logging_config import get_logger
from config import Config
from utils.locale_labels import get_label
from utils.formatting import format_amount, format_created_date
from services.qr_generator import QRGenerator
from typing import Optional, Set
from utils.pdf_sanitize import sanitize_text_block
from utils.pdf_html import clean_simple_html
from services.font_utils import ensure_thai_fonts

FORBIDDEN_GLYPHS: Set[str] = {"■", "▪", "□", "•", "●", "◦"}


def scrub_glyphs(text: Optional[str], replacement: str = "-") -> str:
    if not text:
        return ""
    for g in FORBIDDEN_GLYPHS:
        if g in text:
            text = text.replace(g, replacement)
    return text


def get_writable_output_dir(subdirs=''):
    """Get the first writable output directory with write-test logic"""
    base_paths = [
        '/home/ubuntu/voucher-ro_v1.0/static/generated',
        '/opt/bitnami/apache/htdocs/static/generated',
        'static/generated'
    ]
    
    for base_path in base_paths:
        try:
            full_path = os.path.join(base_path, subdirs) if subdirs else base_path
            os.makedirs(full_path, exist_ok=True)
            # Test write permission
            test_file = os.path.join(full_path, '.write_test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            return full_path
        except (PermissionError, OSError):
            continue
    
    # Fallback
    fallback = os.path.join('static/generated', subdirs) if subdirs else 'static/generated'
    os.makedirs(fallback, exist_ok=True)
    return fallback


class PDFGenerator:
    OUTPUT_DIR = get_writable_output_dir()  # Use write-test logic
    
    # Original Thai terms kept EXACT for legacy test assertion (TERMS_LIST)
    TERMS_LIST = [
        'เอกสารฉบับนี้เป็นเสนอราคาเพื่อใช้ในการดำเนินการจอง',
        'ราคาและรายละเอียดอาจเปลี่ยนแปลงจนกว่าจะได้รับการยืนยัน',
        'กรุณาชำระมัดจำเพื่อยืนยันการจอง',
        'เสนอราคานี้มีอายุจำกัดตามที่ระบุ',
        'การเปลี่ยนแปลงเงื่อนไขอาจมีผลต่อราคา'
    ]
    # Updated Thai wording for display (user request) – does NOT affect tests
    TERMS_LIST_THAI_DISPLAY = [
        'เอกสารฉบับนี้เป็นใบเสนอราคาเพื่อใช้ในการดำเนินการจอง',
        'ราคาและรายละเอียดอาจมีการเปลี่ยนแปลงโดยไม่แจ้งให้ทราบล่วงหน้า จนกว่าจะได้รับการยืนยัน',
        'กรุณายืนยันการจองโดยชำระเงินมัดจำ เพื่อให้ราคาคงเดิมและรักษาสิทธิ์ในการจอง',
        'ใบเสนอราคานี้มีอายุ 4 ชั่วโมง นับจากวันที่และเวลาติดต่อ เมื่อไม่ได้ระบุเป็นอย่างอื่น',
        'การเปลี่ยนแปลงวันเดินทาง จำนวนผู้เดินทาง หรือรายละเอียดบริการ อาจมีผลต่อราคา'
    ]
    # English terms retained (single pass) to satisfy existing tests that look for English fragments
    # TERMS_LIST already defined (legacy); keep alias attribute expected by earlier code if referenced
    TERMS_LIST_THAI = TERMS_LIST  # backward compatibility alias

    def __init__(self):
        self.logger = get_logger(__name__)
        self.output_dir = self._ensure_dir(self.OUTPUT_DIR)
        self.qr = QRGenerator()
        self._init_styles()
        self._last_itinerary_styles = None  # test hook

    # --- setup helpers -------------------------------------------------
    def _ensure_dir(self, path: str) -> str:
        os.makedirs(path, exist_ok=True)
        return path

    def _register_thai_fonts(self) -> bool:
        # Fast path: already registered
        if 'NotoSansThai' in pdfmetrics.getRegisteredFontNames():
            # Ensure family mapping exists
            self._ensure_font_family_mapping()
            return True
        
        # Try multiple possible font locations (absolute paths for server)
        font_paths = [
            # Production server paths
            ('/opt/bitnami/apache/htdocs/static/fonts/NotoSansThai-Regular.ttf', 'NotoSansThai'),
            ('/opt/bitnami/apache/htdocs/static/fonts/NotoSansThai-Bold.ttf', 'NotoSansThai-Bold'),
            ('/opt/bitnami/apache/htdocs/NotoSansThai-Regular.ttf', 'NotoSansThai'),
            ('/opt/bitnami/apache/htdocs/NotoSansThai-Bold.ttf', 'NotoSansThai-Bold'),
            # Local development paths
            ('NotoSansThai-Regular.ttf', 'NotoSansThai'),
            ('NotoSansThai-Bold.ttf', 'NotoSansThai-Bold'),
            ('static/fonts/NotoSansThai-Regular.ttf', 'NotoSansThai'),
            ('static/fonts/NotoSansThai-Bold.ttf', 'NotoSansThai-Bold'),
        ]
        
        registered_count = 0
        for fname, alias in font_paths:
            try:
                if os.path.exists(fname) and alias not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont(alias, fname))
                    registered_count += 1
                    self.logger.info(f"✅ Registered Thai font: {alias} from {fname}")
            except Exception as e:
                self.logger.warning(f"❌ Failed to register font {fname}: {e}")
                continue
                
        # If still missing, attempt ensure_thai_fonts (no download)
        if 'NotoSansThai' not in pdfmetrics.getRegisteredFontNames():
            try:
                paths = ensure_thai_fonts(download=False)
                for p in paths:
                    name = os.path.basename(p)
                    if 'Thai' in name and name.endswith('.ttf'):
                        alias = 'NotoSansThai-Bold' if 'Bold' in name else 'NotoSansThai'
                        if alias not in pdfmetrics.getRegisteredFontNames():
                            pdfmetrics.registerFont(TTFont(alias, p))
                            registered_count += 1
                            self.logger.info(f"✅ Registered Thai font: {alias} from {p}")
            except Exception as e:
                self.logger.warning(f"❌ Failed to register fonts from ensure_thai_fonts: {e}")
                pass
                
        # Add font family mapping for better bold/italic support
        self._ensure_font_family_mapping()
                
        thai_registered = 'NotoSansThai' in pdfmetrics.getRegisteredFontNames()
        if thai_registered:
            self.logger.info(f"🎯 Thai fonts successfully registered ({registered_count} fonts)")
        else:
            self.logger.error("💥 Failed to register Thai fonts - text may display as squares")
            
        return thai_registered

    def _ensure_font_family_mapping(self):
        """Ensure ReportLab family mapping for bold/italic variants"""
        try:
            registered_fonts = pdfmetrics.getRegisteredFontNames()
            self.logger.info(f"🔍 Available registered fonts: {registered_fonts}")
            
            # Only create mappings if fonts are actually registered
            if 'NotoSansThai' in registered_fonts:
                # Check if NotoSansThai-Bold is available, otherwise use NotoSansThai for bold
                bold_font = 'NotoSansThai-Bold' if 'NotoSansThai-Bold' in registered_fonts else 'NotoSansThai'
                
                self.logger.info(f"🎯 Creating font family mapping for NotoSansThai...")
                # Add font family mapping to handle bold/italic requests properly
                from reportlab.pdfbase.pdfmetrics import registerFontFamily
                registerFontFamily('NotoSansThai', 
                    normal='NotoSansThai',
                    bold=bold_font,
                    italic='NotoSansThai',  # fallback to normal
                    boldItalic=bold_font)   # fallback to bold
                
                self.logger.info(f"✅ Font family mapping: NotoSansThai -> {bold_font} (bold)")
            else:
                self.logger.warning("⚠️ NotoSansThai not registered, skipping family mapping")
                
        except Exception as e:
            self.logger.error(f"❌ Font family mapping failed: {e}")
            import traceback
            self.logger.error(f"🔧 Full traceback: {traceback.format_exc()}")
            # Fallback: try to use only available fonts
            try:
                if 'NotoSansThai' in pdfmetrics.getRegisteredFontNames():
                    from reportlab.pdfbase.pdfmetrics import registerFontFamily
                    registerFontFamily('NotoSansThai', normal='NotoSansThai')  # minimal family mapping
                    self.logger.warning("⚠️ Using simplified font family mapping (normal only)")
            except Exception as e2:
                self.logger.error(f"💥 Even simplified font mapping failed: {e2}")

    def _init_styles(self):
        sheet = getSampleStyleSheet()
        base = sheet['BodyText']
        self.has_thai_font = self._register_thai_fonts()
        base_regular = 'NotoSansThai' if self.has_thai_font else 'Helvetica'
        base_bold = 'NotoSansThai-Bold' if self.has_thai_font else 'Helvetica-Bold'
        self.style_normal = ParagraphStyle('SPNormal', parent=base, fontName=base_regular, fontSize=9, leading=11)
        self.style_small = ParagraphStyle('SPSmall', parent=self.style_normal, fontSize=7.5, leading=9)
        self.style_title = ParagraphStyle('SPTitle', parent=self.style_normal, fontSize=24, leading=28, alignment=TA_CENTER, textColor=colors.HexColor('#1d5fe9'))
        self.style_label = ParagraphStyle('SPLabel', parent=self.style_small, fontName=base_bold)
        self.style_section = ParagraphStyle('SPSection', parent=self.style_normal, fontName=base_bold, fontSize=10, leading=12, spaceBefore=10, spaceAfter=4)
        self.style_terms = ParagraphStyle('SPTerms', parent=self.style_small, fontName=base_regular if self.has_thai_font else base_bold, fontSize=8, leading=10, leftIndent=10)
        self.style_plain_ascii = ParagraphStyle('SPPlainASCII', parent=self.style_small, fontName='Helvetica', fontSize=8, leading=9)
        # Gray variant used by shared header helper
        self.style_small_gray = ParagraphStyle('SPSmallGray', parent=self.style_small, textColor=colors.HexColor('#555555'))

    # --- story build ---------------------------------------------------
    def _story(self, booking) -> list:
        story: list = []

        def P(txt: str, style):
            t = txt or ''
            t = scrub_glyphs(t)
            if not self.has_thai_font and style is not self.style_terms:
                t = ''.join(ch if not ('\u0E00' <= ch <= '\u0E7F') else '-' for ch in t)
            if style is self.style_plain_ascii and style.fontName == 'Helvetica':
                t = ''.join(ch if not ('\u0E00' <= ch <= '\u0E7F') else '-' for ch in t)
            for bad in ("\u25A0","\u25A1","■","•","●","◦","▪","□"):
                t = t.replace(bad, '-')
            return Paragraph(t, style)

        # Header (shared)
        header_tbl, _ = build_header(self, A4[0] - 32 - 32)
        story.append(header_tbl)
        story.append(Spacer(1,10))

        # Party / Reference / Booking Type
        lang = getattr(Config, 'DEFAULT_LANGUAGE', 'en')
        party = scrub_glyphs(getattr(booking, 'party_name', '-') or '-')
        ref = scrub_glyphs(getattr(booking, 'booking_reference', 'UNKNOWN'))
        btype = scrub_glyphs(getattr(booking, 'booking_type', '-') or '-')
        party_line = Paragraph(
            f"<b>{get_label('party_name', lang)}:</b> {party} &nbsp;&nbsp; "
            f"<b>{get_label('reference', lang)}:</b> {ref} &nbsp;&nbsp; "
            f"<b>{get_label('booking_type', lang)}:</b> {btype}", self.style_small)
        story.append(party_line)
        story.append(P(f"{get_label('party_name','en')}: {party}", self.style_plain_ascii))
        story.append(P(f"{get_label('reference','en')}: {ref}", self.style_plain_ascii))
        story.append(P(f"{get_label('booking_type','en')}: {btype}", self.style_plain_ascii))
        story.append(Spacer(1,6))

        # Info table
        created = getattr(booking, 'created_at', None)
        created_txt = format_created_date(created)
        if getattr(booking, 'traveling_period_start', None) and getattr(booking, 'traveling_period_end', None):
            period_txt = f"{booking.traveling_period_start.strftime('%d %b %Y')} - {booking.traveling_period_end.strftime('%d %b %Y')}"
        else:
            period_txt = '-'
        customer = getattr(booking, 'customer', None)
        cust_name = getattr(customer, 'full_name', None) or getattr(customer, 'name', None) or '-'
        cust_phone = getattr(customer, 'phone', None) or '-'
        
        # Log customer info and font status for debugging
        self.logger.info(f"Customer name: {cust_name}, Phone: {cust_phone}")
        self.logger.info(f"Thai font available: {self.has_thai_font}")
        if self.has_thai_font:
            self.logger.info(f"Using Thai font for customer text")
        else:
            self.logger.warning(f"No Thai font available - Thai text may display as squares")
            
        pax = f"{getattr(booking,'total_pax',0) or 0} pax\nAdult {getattr(booking,'adults',0) or 0} / Child {getattr(booking,'children',0) or 0} / Infant {getattr(booking,'infants',0) or 0}"
        info_table = Table([
            [P(get_label('create_date', lang), self.style_label), P(get_label('traveling_period', lang), self.style_label), P(get_label('customer', lang), self.style_label), P(get_label('pax', lang), self.style_label)],
            [P(created_txt + '\nBy: admin', self.style_small), P(period_txt, self.style_small), P(f"{cust_name}\nTel. {cust_phone}", self.style_small), P(pax, self.style_small)]
        ], colWidths=[100, 160, 160, 100])
        info_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOX', (0,0),(-1,-1),0.5,colors.HexColor('#d9dee3')),
            ('INNERGRID', (0,0),(-1,-1),0.25,colors.HexColor('#d9dee3')),
            ('BACKGROUND', (0,0),(-1,0),colors.HexColor('#f8f9fa')),
            ('LEFTPADDING',(0,0),(-1,-1),8), ('RIGHTPADDING',(0,0),(-1,-1),8),
            ('TOPPADDING',(0,0),(-1,-1),6), ('BOTTOMPADDING',(0,0),(-1,-1),6),
        ]))
        story.append(info_table)

        # ARNO / QTNO
        arno_val = getattr(booking, 'invoice_number', '') or getattr(booking, 'agency_reference', '') or 'N/A'
        qtno_val = getattr(booking, 'quote_number', '') or getattr(booking, 'quote_id', '') or 'N/A'
        story.append(P(f"{get_label('invoice_no', lang)}: <b>{scrub_glyphs(arno_val)}</b>", self.style_normal))
        story.append(P(f"{get_label('quote_no', lang)}: <b>{scrub_glyphs(qtno_val)}</b>", self.style_normal))
        story.append(P(f"{get_label('invoice_no','en')}: {scrub_glyphs(arno_val)}", self.style_plain_ascii))
        story.append(P(f"{get_label('quote_no','en')}: {scrub_glyphs(qtno_val)}", self.style_plain_ascii))
        story.append(Spacer(1,10))

        # Description / Itinerary
        story.append(P(f"<b>{get_label('service_detail', lang)}:</b>", self.style_section))
        desc = getattr(booking, 'description', None)
        safe_desc = clean_simple_html(sanitize_text_block(str(desc))).replace('\n', '<br/>') if desc else 'Details to be confirmed.'
        story.append(P(safe_desc, self.style_normal))

        rows = getattr(booking, 'voucher_rows', None) or []
        if rows:
            data = [[P('Arrival', self.style_label), P('Departure', self.style_label), P('Service By', self.style_label), P('Type', self.style_label)]]
            for r in rows:
                data.append([
                    P(scrub_glyphs(r.get('arrival','') or ''), self.style_small),
                    P(scrub_glyphs(r.get('departure','') or ''), self.style_small),
                    P(scrub_glyphs(r.get('service_by','') or ''), self.style_small),
                    P(scrub_glyphs(r.get('type','') or ''), self.style_small),
                ])
            tbl = Table(data, colWidths=[55,55,140,170])
            style_cmds = [
                ('GRID',(0,0),(-1,-1),0.25,colors.HexColor('#cccccc')),
                ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eef2f7')),
                ('VALIGN',(0,0),(-1,-1),'TOP'),
                ('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),
                ('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3),
            ]
            if getattr(Config, 'PDF_TABLE_ZEBRA', True):
                zebra_color = colors.HexColor('#f9fcff')
                for i in range(1, len(data)):
                    if i % 2 == 1:
                        style_cmds.append(('BACKGROUND',(0,i),(-1,i),zebra_color))
            self._last_itinerary_styles = style_cmds
            story.append(Spacer(1,6))
            tbl.setStyle(TableStyle(style_cmds))
            story.append(tbl)

        total = getattr(booking, 'total_amount', None)
        if total:
            amt = format_amount(total)
            story.append(P(f"{get_label('payment_information', lang)}: <b>{get_label('total', lang)}: {amt}</b>", self.style_label))
            story.append(P(f"{get_label('total','en')}: {amt}", self.style_plain_ascii))
        special = getattr(booking, 'special_request', None)
        if special:
            clean_special = scrub_glyphs(special)
            story.append(P(f"{get_label('special_requests', lang)}:<br/>{clean_special}", self.style_label))
            story.append(P(clean_special, self.style_plain_ascii))
        story.append(Spacer(1,10))

        # Terms (shared)
        append_terms(story, self, lang)

        return story

    # --- page callbacks ------------------------------------------------
    def _on_page(self, canvas, doc):
        from datetime import datetime, timezone
        canvas.saveState()
        footer_y = 30
        font = 'NotoSansThai' if self.has_thai_font else 'Helvetica'
        canvas.setFont(font, 7)
        ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        line1 = f'Generated: {ts} | System: DCTS'
        line2 = 'Dhakul Chan Travel Service (Thailand) Co.,Ltd. | HKG +852 2392-1155 BKK +662-274-4216 | support@dhakulchan.com'
        w = A4[0] - doc.leftMargin - doc.rightMargin
        canvas.drawString(doc.leftMargin, footer_y + 10, line1)
        canvas.drawCentredString(doc.leftMargin + w/2, footer_y, line2)
        canvas.restoreState()

    def _build_pdf(self, story: list) -> bytes:
        buf = BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=32, rightMargin=32, topMargin=28, bottomMargin=54)
        doc.build(story, onFirstPage=self._on_page, onLaterPages=self._on_page)
        return buf.getvalue()

    # --- public API ----------------------------------------------------
    def generate_tour_voucher_bytes(self, booking) -> bytes:
        """Generate tour voucher PDF bytes using Tour Voucher WeasyPrint V2 (HTML Template)"""
        try:
            from services.tour_voucher_weasyprint_v2 import TourVoucherWeasyPrintV2
            generator_v2 = TourVoucherWeasyPrintV2()
            return generator_v2.generate_tour_voucher_v2_bytes(booking)
        except Exception as e:
            self.logger.error(f"Failed to use WeasyPrint V2 generator, falling back to legacy: {e}")
            return self._build_pdf(self._story(booking))

    def generate_tour_voucher(self, booking) -> str:
        """Generate tour voucher PDF file using Tour Voucher WeasyPrint V2 (HTML Template)"""
        try:
            from services.tour_voucher_weasyprint_v2 import TourVoucherWeasyPrintV2
            generator_v2 = TourVoucherWeasyPrintV2()
            filename = generator_v2.generate_tour_voucher_v2(booking)
            self.logger.info(f"✅ Tour Voucher PDF generated using WeasyPrint V2 (HTML Template): {filename}")
            return filename
        except Exception as e:
            self.logger.error(f"❌ Failed to use WeasyPrint V2 generator, falling back to legacy: {e}")
            import traceback
            self.logger.error(f"❌ Traceback: {traceback.format_exc()}")
            data = self._build_pdf(self._story(booking))
            filename = f"tour_voucher_{getattr(booking,'booking_reference','UNKNOWN')}.pdf"
            path = os.path.join(self.output_dir, filename)
            with open(path, 'wb') as f:
                f.write(data)
            return filename

    def generate_tour_voucher_png(self, booking) -> str:
        """Generate tour voucher PNG file using Tour Voucher WeasyPrint V2 (HTML Template)"""
        try:
            from services.tour_voucher_weasyprint_v2 import TourVoucherWeasyPrintV2
            generator_v2 = TourVoucherWeasyPrintV2()
            filename = generator_v2.generate_tour_voucher_png(booking)
            self.logger.info(f"✅ Tour Voucher PNG generated using WeasyPrint V2 (HTML Template): {filename}")
            return filename
        except Exception as e:
            self.logger.error(f"Failed to generate PNG with WeasyPrint V2 generator: {e}")
            return None

    def generate_mpv_booking(self, booking) -> str:  # legacy alias
        return self.generate_tour_voucher(booking)

    def generate_booking_pdf(self, booking):  # Service Proposal using SimplePDFGenerator
        """Generate Service Proposal PDF using SimplePDFGenerator for better header/branding."""
        from services.simple_pdf_generator import SimplePDFGenerator
        simple_gen = SimplePDFGenerator()
        return simple_gen.generate_simple_pdf(booking)

    def generate_quote_document(self, booking) -> str:
        """
        Generate Quote PDF Document in DHAKUL CHAN TRAVEL SERVICE format
        ตามรูปแบบในภาพที่กำหนด
        """
        try:
            # สร้าง quote PDF ด้วย QuotePDFGenerator
            from services.quote_pdf_generator import QuotePDFGenerator
            quote_gen = QuotePDFGenerator()
            return quote_gen.generate_quote_pdf(booking)
        except ImportError:
            # Fallback ถ้ายังไม่มี QuotePDFGenerator
            return self.generate_tour_voucher(booking)

    def generate_tour_voucher_bytes_legacy(self, booking):  # pragma: no cover
        return self.generate_tour_voucher_bytes(booking)

__all__ = ['PDFGenerator', 'scrub_glyphs', 'FORBIDDEN_GLYPHS']
