"""Simple Service Proposal PDF generator.

Clean rebuild - provides a minimal PDF generator with shared header & terms.
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import List

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Flowable

from config import Config
from services.pdf_common import build_header, append_terms
from utils.pdf_sanitize import sanitize_text_block
from utils.logging_config import get_logger

FORBIDDEN_GLYPHS = {"■", "▪", "□", "•", "●", "◦"}


def _scrub(text: str | None) -> str:
    """Remove forbidden glyphs from text."""
    if not text:
        return ""
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
        self._init_styles()

    def _init_styles(self):
        """Initialize paragraph styles."""
        sheet = getSampleStyleSheet()
        base = sheet['BodyText']
        self.base_font = 'Helvetica'
        self.base_font_bold = 'Helvetica-Bold'
        
        self.style_normal = ParagraphStyle(
            'SPNormal', parent=base, fontName=self.base_font, 
            fontSize=9.5, leading=11.5
        )
        self.style_small = ParagraphStyle(
            'SPSmall', parent=self.style_normal, fontSize=8.5, leading=10
        )
        self.style_small_gray = ParagraphStyle(
            'SPSmallGray', parent=self.style_small, 
            textColor=colors.HexColor('#555555')
        )
        self.style_title = ParagraphStyle(
            'SPTitle', parent=self.style_normal, fontSize=24, leading=28, 
            alignment=TA_CENTER, textColor=colors.HexColor('#1d5fe9')
        )
        self.style_section_header = ParagraphStyle(
            'SPSection', parent=self.style_normal, fontName=self.base_font_bold, 
            fontSize=10.5, leading=13, spaceBefore=6, spaceAfter=4
        )
        self.style_terms = ParagraphStyle(
            'SPTerms', parent=self.style_small, fontSize=9, leading=11, leftIndent=10
        )
        self.style_footer = ParagraphStyle(
            'SPFooter', parent=self.style_small_gray, fontSize=7.5, leading=9, 
            alignment=TA_CENTER
        )
        
        # Aliases needed by append_terms
        self.style_plain_ascii = ParagraphStyle(
            'SPPlainASCII', parent=self.style_small, fontName='Helvetica', 
            fontSize=8.5, leading=10
        )
        self.style_section = self.style_section_header

    def _para(self, text: str, style: ParagraphStyle | None = None) -> Paragraph:
        """Create a paragraph with glyph scrubbing."""
        style = style or self.style_normal
        text = _scrub(text or '')
        text = ''.join(ch if ch >= ' ' else ' ' for ch in text)
        return Paragraph(text, style)

    def _clean_html(self, html: str) -> str:
        """Clean HTML to allowed tags only."""
        allowed = getattr(Config, 'PDF_ALLOWED_TAGS', ['b', 'i', 'u', 'br'])
        html = re.sub(r'<br\s*/?>', '<br/>', html, flags=re.I)
        
        def _keep(m):
            tag = m.group(1).lower()
            return m.group(0) if tag in allowed else ''
        
        return re.sub(r'</?([a-zA-Z0-9]+)(?:\s+[^>]*)?>', _keep, html)

    def generate_simple_pdf(self, booking) -> str:
        """Generate the service proposal PDF."""
        ref = getattr(booking, 'booking_reference', None) or 'UNK'
        filename = f"service_proposal_{ref}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        path = os.path.join(self.output_dir, filename)
        
        doc = SimpleDocTemplate(
            path, pagesize=A4, leftMargin=28, rightMargin=28, 
            topMargin=28, bottomMargin=34
        )
        avail_width = A4[0] - doc.leftMargin - doc.rightMargin
        story: List = []

        # Header
        try:
            header, _ = build_header(self, avail_width)
            story.append(header)
            story.append(Spacer(1, 8))
        except Exception as e:
            self.logger.warning('Header build failed: %s', e)

        # Meta row (party / title / reference + booking type)
        party = getattr(booking, 'party_name', '') or getattr(
            getattr(booking, 'customer', None), 'name', ''
        )
        status = getattr(booking, 'status', '') or '-'
        btype = getattr(booking, 'booking_type', '') or '-'
        
        title_p = Paragraph('Service Proposal', self.style_title)
        party_block = self._para(
            f"Party Name: {party}<br/><font color='#555555'>Status: <b>{status}</b></font>"
        )
        ref_p = self._para(f"Reference: {ref}")
        btype_p = self._para(
            f"Booking Type: <b>{btype}</b>", 
            ParagraphStyle('SPBT', parent=self.style_small_gray, alignment=TA_LEFT)
        )
        
        meta_tbl = Table([
            [party_block, title_p, ref_p],
            ['', '', btype_p]
        ], colWidths=[160, 219, 160])
        
        meta_tbl.setStyle(TableStyle([
            ('SPAN', (0, 0), (0, 1)), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'), ('ALIGN', (2, 0), (2, 0), 'RIGHT'), 
            ('ALIGN', (2, 1), (2, 1), 'LEFT'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (2, 0), (2, 0), 0), ('TOPPADDING', (2, 1), (2, 1), 0),
        ]))
        
        story.append(meta_tbl)
        story.append(Spacer(1, 1))

        # Info panel
        created_disp = (
            getattr(booking, 'created_at', None) or datetime.now(timezone.utc)
        ).strftime('%d.%b.%Y').upper()
        
        if getattr(booking, 'arrival_date', None) and getattr(booking, 'departure_date', None):
            period = f"{booking.arrival_date.strftime('%d %b %Y')} - {booking.departure_date.strftime('%d %b %Y')}"
        else:
            period = ''
        
        cust = getattr(booking, 'customer', None)
        cust_name = getattr(cust, 'name', '') if cust else getattr(booking, 'customer_name', '')
        cust_phone = getattr(cust, 'phone', '') if cust else getattr(booking, 'customer_phone', '')
        cust_block = cust_name + (
            f"<br/><font color='#555555'>Tel. {cust_phone}</font>" if cust_phone else ''
        )
        
        pax_total = getattr(booking, 'total_pax', None) or (
            getattr(booking, 'adults', 0) + getattr(booking, 'children', 0) + 
            getattr(booking, 'infants', 0)
        )
        pax_block = (
            f"{pax_total} pax<br/>Adult {getattr(booking, 'adults', 0)} / "
            f"Child {getattr(booking, 'children', 0)} / Infant {getattr(booking, 'infants', 0)}"
        )
        
        labels = [
            self._para('<b>Create Date</b>'), 
            self._para('<b>Traveling Period</b>'), 
            self._para('<b>Customer</b>'), 
            self._para('<b>PAX</b>')
        ]
        values = [
            self._para(
                f"{created_disp}<br/><font color='#555555'>By: admin</font>", 
                ParagraphStyle('SPCD', parent=self.style_normal, leading=11)
            ),
            self._para(period), 
            self._para(cust_block), 
            self._para(pax_block)
        ]
        
        info_tbl = Table([labels, values], colWidths=[125, 165, 160, 80])
        info_tbl.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('INNERGRID', (0, 0), (-1, -1), 0, colors.white), 
            ('BOX', (0, 0), (-1, -1), 0, colors.white)
        ]))

        class RoundedPanel(Flowable):
            def __init__(self, inner, width, padding=6, radius=10, bg='#FFFFFF', border='#E2E8F0'):
                super().__init__()
                self.inner = inner
                self.width = width
                self.padding = padding
                self.radius = radius
                self.bg = colors.HexColor(bg)
                self.border = colors.HexColor(border)
                iw, ih = self.inner.wrap(width - padding * 2, 10000)
                self.height = ih + padding * 2
                self.inner_w, self.inner_h = iw, ih

            def wrap(self, aw, ah):
                return self.width, self.height

            def draw(self):
                c = self.canv
                c.saveState()
                c.setFillColor(self.bg)
                c.setStrokeColor(self.border)
                c.setLineWidth(0.7)
                c.roundRect(0, 0, self.width, self.height, self.radius, fill=1, stroke=1)
                c.restoreState()
                self.inner.drawOn(c, self.padding, self.padding)

        story.append(RoundedPanel(info_tbl, avail_width, padding=8, radius=12, bg='#FFFFFF', border='#CBD5E1'))
        story.append(Spacer(1, 8))

        # Itinerary / service detail
        story.append(self._para('Service Detail / Itinerary:', self.style_section_header))
        raw_desc = getattr(booking, 'description', '') or getattr(booking, 'tour_name', '') or ''
        raw_desc = sanitize_text_block(raw_desc)
        cleaned = self._clean_html(raw_desc).replace('<br/>', '\n')
        lines = [l.strip() for l in cleaned.split('\n') if l.strip()] or ['Details to be confirmed.']
        
        skip = {'•', '●', '◦'}
        for line in lines:
            if line in skip:
                continue
            story.append(self._para(self._clean_html(line)))
        story.append(Spacer(1, 6))

        # Payment
        amount = getattr(booking, 'total_amount', None) or getattr(booking, 'price', None) or 0
        story.append(self._para(f"Payment Information: <b>Total:</b> THB {amount:,.2f}"))
        story.append(Spacer(1, 4))

        # Special Requests
        sreq = getattr(booking, 'special_request', '')
        sreq = re.sub(r'<[^>]+>', '', sreq or '').strip()
        if sreq and sreq.lower() not in {'none', 'n/a', 'na'}:
            story.append(self._para(
                'Special Requests:', 
                ParagraphStyle('SPSR', parent=self.style_normal, fontName=self.base_font_bold)
            ))
            story.append(self._para(self._clean_html(sreq)))
            story.append(Spacer(1, 6))

        # Terms & Conditions
        append_terms(story, self, getattr(Config, 'DEFAULT_LANGUAGE', 'en'))

        # Footer
        story.append(Spacer(1, 6))
        gen_ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        story.append(Paragraph(f"Generated: {gen_ts} | System: DCTS", self.style_footer))
        story.append(Paragraph(
            f"{Config.COMPANY_NAME} | {Config.COMPANY_PHONE} | {Config.COMPANY_EMAIL}", 
            self.style_footer
        ))

        # Page callback
        def _on_page(canvas, _doc):
            canvas.saveState()
            canvas.setFont(self.base_font, 8)
            canvas.setFillColor(colors.HexColor('#64748B'))
            canvas.drawRightString(A4[0] - 40, 15, f"Page {canvas.getPageNumber()}")
            canvas.restoreState()

        # Optional font embedding
        if getattr(Config, 'PDF_FORCE_EMBED_FONTS', False):
            from reportlab.pdfbase import pdfmetrics
            for ef in [f for f in getattr(Config, 'PDF_FALLBACK_FONTS', []) 
                      if f in pdfmetrics.getRegisteredFontNames()]:
                story.append(Paragraph(
                    ' ', ParagraphStyle(f'Embed_{ef}', parent=self.style_normal, 
                                      fontName=ef, fontSize=1, leading=1)
                ))

        # Final scrub of any embedded paragraphs in story
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
