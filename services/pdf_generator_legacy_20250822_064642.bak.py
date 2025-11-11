"""Clean reset stub for PDFGenerator after legacy corruption cleanup.

Incremental plan:
  1. Provide minimal import-safe class (this file).
  2. Reintroduce unified story builder `_build_voucher_story`.
  3. Implement `generate_tour_voucher` (file) + `generate_tour_voucher_bytes` (bytes) using same story.
  4. Layer fonts, glyph scrub, zebra stripes, QR code, itinerary, terms.
  5. Add MPV + proposal helpers (delegating until parity validated).
  6. Add tests for file/bytes parity & glyph absence.
"""
from __future__ import annotations

__all__ = ["PDFGenerator"]


class PDFGenerator:  # pragma: no cover - transitional stub
    """Minimal interface stub.

    Methods raise NotImplementedError intentionally so any premature runtime
    usage during refactor is explicit. Replace step‑wise with real logic.
    """

    def generate_tour_voucher(self, booking):  # pragma: no cover
        raise NotImplementedError("generate_tour_voucher not yet implemented (stub phase)")

    def generate_tour_voucher_bytes(self, booking):  # pragma: no cover
        raise NotImplementedError("generate_tour_voucher_bytes not yet implemented (stub phase)")

    # Placeholders for future API compatibility (existing code may call these)
    def generate_mpv_booking(self, booking):  # pragma: no cover
        raise NotImplementedError("generate_mpv_booking not yet implemented (stub phase)")

    def generate_booking_pdf(self, booking, **kwargs):  # pragma: no cover
        raise NotImplementedError("generate_booking_pdf not yet implemented (stub phase)")


# This file intentionally contains only a stub class to ensure imports succeed.
"""

class PDFGenerator:  # pragma: no cover - reset stub
    def generate_tour_voucher(self, booking):  # pragma: no cover
        raise NotImplementedError

    def generate_tour_voucher_bytes(self, booking):  # pragma: no cover
        raise NotImplementedError

__all__ = ["PDFGenerator"]

"""LEGACY_DEACTIVATED_START
The large legacy implementation block that previously followed has been intentionally
removed from execution. It is preserved only as a reference during phased refactor.
All code below this sentinel is inert (inside a triple-quoted string) and will be
deleted entirely once the new unified implementation is complete.
---
"""
        else:
            raw = getattr(booking,'guest_list',[])
            if isinstance(raw,str): guests = [g.strip() for g in raw.split('\n') if g.strip()]
            elif isinstance(raw,(list,tuple)): guests = list(raw)
        if guests:
            for i,g in enumerate(guests,1): story.append(self._dyn(f"{i}. {g}", self.normal_style))
        else: story.append(Paragraph('No guests specified', self.normal_style))
        story.append(Spacer(1,12))
        story.append(Paragraph('Hotel / Accommodation | Transfer | Others | Flight Detail', self.heading_style))
        rows = []
        if hasattr(booking,'get_voucher_rows'):
            try: rows = booking.get_voucher_rows() or []
            except Exception: rows = []
        else: rows = getattr(booking,'voucher_rows',[]) or []
        header_cells = [Paragraph(h,self.table_header_style) for h in ['No.','ARRIVAL','DEPARTURE','SERVICE BY','TYPE/CLASS/PAXS/PIECES']]
        data = [header_cells]
        if rows:
            for i,r in enumerate(rows,1):
                svc = clean_simple_html(str(r.get('service_by','')).replace('\n','<br/>'))
                typ = clean_simple_html(str(r.get('type','')).replace('\n','<br/>'))
                data.append([Paragraph(str(i),self.table_cell_style), Paragraph(self._format_date(r.get('arrival','')),self.table_cell_style), Paragraph(self._format_date(r.get('departure','')),self.table_cell_style), self._dyn(svc,self.table_cell_style), self._dyn(typ,self.table_cell_style)])
        else:
            pax = getattr(booking,'total_pax',None) or getattr(booking,'adults',1) or 1
            data.append([Paragraph('1',self.table_cell_style), Paragraph('',self.table_cell_style), Paragraph('',self.table_cell_style), Paragraph('Tour Service',self.table_cell_style), Paragraph(f"{pax} PAX",self.table_cell_style)])
        table = Table(data, colWidths=[0.4*inch,1.1*inch,1.1*inch,3.1*inch,2.4*inch])
        style_cmds = [('BACKGROUND',(0,0),(-1,0),colors.HexColor('#d9d9d9')),('LINEABOVE',(0,0),(-1,0),0.75,colors.HexColor('#b3b3b3')),('LINEBELOW',(0,0),(-1,0),0.75,colors.HexColor('#b3b3b3')),('ALIGN',(0,1),(2,-1),'CENTER'),('ALIGN',(3,1),(4,-1),'LEFT'),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),('GRID',(0,0),(-1,-1),0.25,colors.HexColor('#bfbfbf'))]
        if getattr(Config,'PDF_TABLE_ZEBRA', True):
            for idx in range(1,len(data)):
                if idx % 2 == 1: style_cmds.append(('BACKGROUND',(0,idx),(-1,idx),colors.HexColor('#f4f4f4')))
        table.setStyle(TableStyle(style_cmds))
        story.append(table); story.append(Spacer(1,14))
        img_rel = getattr(booking,'voucher_image_path',None)
        if img_rel:
            try:
                rel = img_rel.split('?')[0].lstrip('/')
                candidates = [rel, os.path.join('static', rel)] if not rel.startswith('static/') else [rel]
                img_abs = next((c for c in candidates if os.path.exists(c)), None)
                if img_abs:
                    story.append(Paragraph('Description:', self.heading_style))
                    pic = Image(img_abs); w,h = pic.wrap(0,0); max_w=440
                    if w>max_w: r=max_w/w; pic.drawWidth=max_w; pic.drawHeight=h*r
                    story.append(pic); story.append(Spacer(1,12))
            except Exception as e:
                if getattr(Config,'PDF_FONT_DEBUG', False): logger.warning('Voucher image load failed: %s', e)
        desc = getattr(booking,'description',None)
        if desc:
            story.append(Paragraph('Service Detail / Itinerary:', self.heading_style))
            sanitized = sanitize_text_block(str(desc)).replace('\n','<br/>')
            story.append(self._dyn(clean_simple_html(sanitized), self.normal_style)); story.append(Spacer(1,12))
        try:
            qr_path = self.qr_generator.generate_voucher_qr(booking)
            if qr_path and os.path.exists(qr_path): story.append(Image(qr_path, width=1.2*inch, height=1.2*inch))
        except Exception as e: logger.error('QR add failed: %s', e)
        story.append(Spacer(1,18))
        story.append(Paragraph('Terms & Conditions:', self.heading_style))
        terms = [
            'This document serves as an official confirmation of travel services and may be presented as a reference with relevant service providers.',
            'Service details and prices are subject to change in the event of any amendments to the travel dates or number of travelers.',
            'The customer is responsible for reviewing and ensuring the accuracy of all flight, hotel, and service information prior to use.',
            'Any request for changes must be submitted at least 72 business hours in advance, or at the earliest practicable time.',
            'In case of emergency, please contact the coordination number specified in this document or reach us via Line official @DHAKULCHAN.',
        ]
        bullet_style = ParagraphStyle('Terms', parent=self.normal_style, fontSize=8, leading=10, leftIndent=6)
        for t in terms: story.append(Paragraph(f"&bull;&nbsp;{_scrub(t)}", bullet_style))
        story.append(Spacer(1,14))
        foot = Table([['Confirmed By:','Accepted By:'],['_'*28,'_'*28],['Date: ___ / ___ / _____','Date: ___ / ___ / _____']], colWidths=[3*inch,3*inch])
        foot.setStyle(TableStyle([('ALIGN',(0,0),(-1,-1),'CENTER'),('FONTSIZE',(0,0),(-1,-1),8)]))
        story.append(foot)
        if getattr(Config,'PDF_FORCE_EMBED_FONTS', False):
            for f in getattr(Config,'PDF_FALLBACK_FONTS', []):
                if f in pdfmetrics.getRegisteredFontNames(): story.append(Paragraph(' ', ParagraphStyle(f'Embed_{f}', parent=self.normal_style, fontName=f, fontSize=1, leading=1)))
        return story

    def _header_footer(self, c, doc):  # pragma: no cover
        c.saveState(); c.setFillColorRGB(0.11,0.37,0.91)
        y_rule = A4[1]-doc.topMargin+4
        c.rect(doc.leftMargin, y_rule, A4[0]-doc.leftMargin-doc.rightMargin, 0.8, fill=1, stroke=0)
        c.setFont(self.default_font_bold,8); c.setFillColorRGB(0.15,0.15,0.15)
        c.drawString(doc.leftMargin, A4[1]-doc.topMargin+8, 'TOUR VOUCHER - SERVICE ORDER')
        c.setFont(self.default_font,8)
        page_txt = f'Page {doc.page}'; w = c.stringWidth(page_txt, self.default_font,8)
        c.drawString(A4[0]-doc.rightMargin-w, A4[1]-doc.topMargin+8, page_txt)
        c.setFont(self.default_font,7); c.setFillColorRGB(0.6,0.6,0.6)
        c.drawString(doc.leftMargin, doc.bottomMargin-14, f"Generated: {datetime.now().strftime('%d %b %Y %H:%M')} | Dhakul Chan Nice Holidays Group")
        c.restoreState()

    def generate_tour_voucher(self, booking):
        start = time.perf_counter()
        filename = f"tour_voucher_{getattr(booking,'booking_reference','UNKNOWN')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        doc = SimpleDocTemplate(filepath, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=30, bottomMargin=32)
        story = self._voucher_story(booking)
        doc.build(story, onFirstPage=self._header_footer, onLaterPages=self._header_footer)
        logger.info('Voucher PDF generated %s (%.1f ms)', filename, (time.perf_counter()-start)*1000)
        return filename

    def generate_tour_voucher_bytes(self, booking) -> bytes:
        buf = BytesIO(); doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=30, bottomMargin=32)
        story = self._voucher_story(booking)
        doc.build(story, onFirstPage=self._header_footer, onLaterPages=self._header_footer)
        return buf.getvalue()

    def generate_mpv_booking(self, booking):  # placeholder reuse
        return self.generate_tour_voucher(booking)
    def generate_booking_pdf(self, booking, **kwargs):  # placeholder reuse
        return self.generate_tour_voucher(booking)

__all__ = ['PDFGenerator']

        # Guests
        story.append(Paragraph("Guest Names:", self.heading_style))
        guests: List[str] = []
        if hasattr(booking, "get_guest_list"):
            try: guests = booking.get_guest_list() or []
            except Exception: guests = []
        else:
            raw = getattr(booking, "guest_list", [])
            if isinstance(raw, str): guests = [g.strip() for g in raw.split("\n") if g.strip()]
            elif isinstance(raw, (list, tuple)): guests = list(raw)
        if guests:
            for i,g in enumerate(guests,1): story.append(self._dyn(f"{i}. {g}", self.normal_style))
        else:
            story.append(Paragraph("No guests specified", self.normal_style))
        story.append(Spacer(1,12))

        # Services table
        story.append(Paragraph("Hotel / Accommodation | Transfer | Others | Flight Detail", self.heading_style))
        rows = []
        if hasattr(booking, "get_voucher_rows"):
            try: rows = booking.get_voucher_rows() or []
            except Exception: rows = []
        else: rows = getattr(booking, "voucher_rows", []) or []
        header_cells = [Paragraph(h, self.table_header_style) for h in ["No.", "ARRIVAL", "DEPARTURE", "SERVICE BY", "TYPE/CLASS/PAXS/PIECES"]]
        data = [header_cells]
        if rows:
            for i,r in enumerate(rows,1):
                svc = clean_simple_html(str(r.get("service_by", "")).replace("\n","<br/>"))
                typ = clean_simple_html(str(r.get("type", "")).replace("\n","<br/>"))
                data.append([
                    Paragraph(str(i), self.table_cell_style),
                    Paragraph(self._format_date(r.get("arrival","")), self.table_cell_style),
                    Paragraph(self._format_date(r.get("departure","")), self.table_cell_style),
                    self._dyn(svc, self.table_cell_style),
                    self._dyn(typ, self.table_cell_style),
                ])
        else:
            pax = getattr(booking, "total_pax", None) or getattr(booking, "adults", 1) or 1
            data.append([Paragraph("1", self.table_cell_style), Paragraph("", self.table_cell_style), Paragraph("", self.table_cell_style), Paragraph("Tour Service", self.table_cell_style), Paragraph(f"{pax} PAX", self.table_cell_style)])
        table = Table(data, colWidths=[0.4*inch,1.1*inch,1.1*inch,3.1*inch,2.4*inch])
        style_cmds = [
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#d9d9d9")),
            ("LINEABOVE", (0,0), (-1,0), 0.75, colors.HexColor("#b3b3b3")),
            ("LINEBELOW", (0,0), (-1,0), 0.75, colors.HexColor("#b3b3b3")),
            ("ALIGN", (0,1), (2,-1), "CENTER"),("ALIGN", (3,1), (4,-1), "LEFT"),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING", (0,0), (-1,-1),4),("RIGHTPADDING", (0,0), (-1,-1),4),
            ("TOPPADDING", (0,0), (-1,-1),4),("BOTTOMPADDING", (0,0), (-1,-1),4),
            ("GRID", (0,0), (-1,-1), 0.25, colors.HexColor("#bfbfbf")),
        ]
        if getattr(Config, "PDF_TABLE_ZEBRA", True):
            for idx in range(1,len(data)):
                if idx % 2 == 1:
                    style_cmds.append(("BACKGROUND", (0,idx), (-1,idx), colors.HexColor("#f4f4f4")))
        table.setStyle(TableStyle(style_cmds))
        story.append(table); story.append(Spacer(1,14))

        # Optional voucher image
        img_rel = getattr(booking, "voucher_image_path", None)
        if img_rel:
            try:
                rel = img_rel.split("?")[0].lstrip("/")
                candidates = [rel, os.path.join("static", rel)] if not rel.startswith("static/") else [rel]
                img_abs = next((c for c in candidates if os.path.exists(c)), None)
                if img_abs:
                    story.append(Paragraph("Description:", self.heading_style))
                    pic = Image(img_abs); w,h = pic.wrap(0,0); max_w = 440
                    if w > max_w: r = max_w / w; pic.drawWidth = max_w; pic.drawHeight = h * r
                    story.append(pic); story.append(Spacer(1,12))
            except Exception as e:  # pragma: no cover
                if getattr(Config, "PDF_FONT_DEBUG", False): logger.warning("Voucher image load failed: %s", e)

        # Description / Itinerary
        desc = getattr(booking, "description", None)
        if desc:
            story.append(Paragraph("Service Detail / Itinerary:", self.heading_style))
            sanitized = sanitize_text_block(str(desc)).replace("\n", "<br/>")
            story.append(self._dyn(clean_simple_html(sanitized), self.normal_style)); story.append(Spacer(1,12))

        # QR
        try:
            qr_path = self.qr_generator.generate_voucher_qr(booking)
            if qr_path and os.path.exists(qr_path): story.append(Image(qr_path, width=1.2*inch, height=1.2*inch))
        except Exception as e:  # pragma: no cover
            logger.error("QR add failed: %s", e)
        story.append(Spacer(1,18))

        # Terms
        story.append(Paragraph("Terms & Conditions:", self.heading_style))
        terms = [
            "This document serves as an official confirmation of travel services and may be presented as a reference with relevant service providers.",
            "Service details and prices are subject to change in the event of any amendments to the travel dates or number of travelers.",
            "The customer is responsible for reviewing and ensuring the accuracy of all flight, hotel, and service information prior to use.",
            "Any request for changes must be submitted at least 72 business hours in advance, or at the earliest practicable time.",
            "In case of emergency, please contact the coordination number specified in this document or reach us via Line official @DHAKULCHAN.",
        ]
        bullet_style = ParagraphStyle("Terms", parent=self.normal_style, fontSize=8, leading=10, leftIndent=6)
        for t in terms: story.append(Paragraph(f"&bull;&nbsp;{_scrub(t)}", bullet_style))
        story.append(Spacer(1,14))

        # Signatures
        foot = Table([["Confirmed By:", "Accepted By:"],["_"*28, "_"*28],["Date: ___ / ___ / _____", "Date: ___ / ___ / _____"]], colWidths=[3*inch,3*inch])
        foot.setStyle(TableStyle([("ALIGN", (0,0), (-1,-1), "CENTER"),("FONTSIZE", (0,0), (-1,-1), 8)]))
        story.append(foot)

        # Force embed fallback fonts (empty paragraphs) if configured
        if getattr(Config, "PDF_FORCE_EMBED_FONTS", False):
            for f in getattr(Config, "PDF_FALLBACK_FONTS", []):
                if f in pdfmetrics.getRegisteredFontNames():
                    story.append(Paragraph(" ", ParagraphStyle(f"Embed_{f}", parent=self.normal_style, fontName=f, fontSize=1, leading=1)))
        return story

    # Header/footer -----------------------------------------------------
    def _header_footer(self, c, doc):  # pragma: no cover
        c.saveState(); c.setFillColorRGB(0.11,0.37,0.91)
        y_rule = A4[1] - doc.topMargin + 4
        c.rect(doc.leftMargin, y_rule, A4[0]-doc.leftMargin-doc.rightMargin, 0.8, fill=1, stroke=0)
        c.setFont(self.default_font_bold, 8); c.setFillColorRGB(0.15,0.15,0.15)
        c.drawString(doc.leftMargin, A4[1]-doc.topMargin+8, "TOUR VOUCHER - SERVICE ORDER")
        c.setFont(self.default_font, 8)
        page_txt = f"Page {doc.page}"; w = c.stringWidth(page_txt, self.default_font, 8)
        c.drawString(A4[0]-doc.rightMargin-w, A4[1]-doc.topMargin+8, page_txt)
        c.setFont(self.default_font, 7); c.setFillColorRGB(0.6,0.6,0.6)
        c.drawString(doc.leftMargin, doc.bottomMargin-14, f"Generated: {datetime.now().strftime('%d %b %Y %H:%M')} | Dhakul Chan Nice Holidays Group")
        c.restoreState()

    # Public API --------------------------------------------------------
    def generate_tour_voucher(self, booking):
        start = time.perf_counter()
        filename = f"tour_voucher_{getattr(booking,'booking_reference','UNKNOWN')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        doc = SimpleDocTemplate(filepath, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=30, bottomMargin=32)
        story = self._voucher_story(booking)
        doc.build(story, onFirstPage=self._header_footer, onLaterPages=self._header_footer)
        logger.info("Voucher PDF generated %s (%.1f ms)", filename, (time.perf_counter()-start)*1000)
        return filename

    def generate_tour_voucher_bytes(self, booking) -> bytes:
        buf = BytesIO(); doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=30, bottomMargin=32)
        story = self._voucher_story(booking)
        doc.build(story, onFirstPage=self._header_footer, onLaterPages=self._header_footer)
        return buf.getvalue()

    def generate_mpv_booking(self, booking):
        filename = f"mpv_booking_{getattr(booking,'booking_reference','UNKNOWN')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        doc = SimpleDocTemplate(filepath, pagesize=A4, leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40)
        story = [Paragraph("MPV BOOKING CONFIRMATION", ParagraphStyle("MPVTitle", parent=self.normal_style, fontName=self.default_font_bold, fontSize=14, alignment=TA_CENTER, spaceAfter=12))]
        details = [
            ("Booking Reference", getattr(booking, "booking_reference", "")),
            ("Customer", getattr(getattr(booking, "customer", None), "name", "")),
            ("Vehicle Type", getattr(booking, "vehicle_type", "")),
            ("Pickup Point", getattr(booking, "pickup_point", "")),
            ("Destination", getattr(booking, "destination", "")),
            ("Pickup Date", str(getattr(booking, "arrival_date", ""))),
            ("Pickup Time", str(getattr(booking, "pickup_time", ""))),
            ("Number of PAX", str(getattr(booking, "total_pax", ""))),
            ("Contact Phone", getattr(getattr(booking, "customer", None), "phone", "")),
            ("Total Amount", f"{getattr(booking,'currency','')} {getattr(booking,'total_amount','')}")
        ]
        data = [[Paragraph(f"<b>{k}:</b>", self.table_cell_style), Paragraph(_scrub(str(v)), self.table_cell_style)] for k,v in details]
        tbl = Table(data, colWidths=[120, 340])
        tbl.setStyle(TableStyle([
            ("VALIGN", (0,0), (-1,-1), "TOP"),("GRID", (0,0), (-1,-1), 0.25, colors.grey),("BACKGROUND", (0,0), (0,-1), colors.HexColor("#f0f0f0")),
            ("LEFTPADDING", (0,0), (-1,-1),4),("RIGHTPADDING", (0,0), (-1,-1),4),("TOPPADDING", (0,0), (-1,-1),3),("BOTTOMPADDING", (0,0), (-1,-1),3)
        ]))
        story.append(tbl); story.append(Spacer(1,12))
        try:
            qr_path = self.qr_generator.generate_mpv_qr(booking)
            if qr_path and os.path.exists(qr_path): story.append(Image(qr_path, width=1.3*inch, height=1.3*inch))
        except Exception as e:  # pragma: no cover
            logger.error("MPV QR error: %s", e)
        story.append(Spacer(1,12)); story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", self.normal_style))
        doc.build(story)
        return filename

    def generate_booking_pdf(self, booking, **kwargs):
        try:
            from services.simple_pdf_generator import SimplePDFGenerator
            sp = SimplePDFGenerator(); fn = sp.generate_simple_pdf(booking)
            if fn: return fn
        except Exception: pass
        try:
            from services.thai_pdf_service import ThaiPDFService
            tp = ThaiPDFService(); fn = tp.generate_thai_service_proposal(booking)
            if fn: return fn
        except Exception: pass
        filename = f"service_proposal_{getattr(booking,'booking_reference','UNKNOWN')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        doc = SimpleDocTemplate(filepath, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=40, bottomMargin=40)
        story = [Paragraph("<b>Service Proposal</b>", ParagraphStyle("SPTitle", parent=self.normal_style, fontName=self.default_font_bold, fontSize=16, alignment=TA_CENTER, spaceAfter=12))]
        party_line = f"Party Name: {getattr(booking,'party_name', getattr(getattr(booking,'customer',None),'name',''))}" or 'Party Name: -'
        story.append(self._dyn(party_line, self.normal_style)); story.append(Spacer(1,6))
        desc = getattr(booking, 'description', None)
        if desc:
            safe = clean_simple_html(sanitize_text_block(desc)).replace('\n', '<br/>')
            story.append(self._dyn(safe, self.normal_style))
        else:
            story.append(Paragraph('No itinerary provided.', self.normal_style))
        story.append(Spacer(1,12)); story.append(Paragraph('Generated automatically by system.', ParagraphStyle('Foot', parent=self.normal_style, fontSize=7, textColor=colors.grey)))
        doc.build(story)
        return filename

__all__ = ["PDFGenerator"]"""Rebuilt PDF generator (clean deduplicated implementation).

Fully rewritten 2025-08-22 to remove corrupted duplicate code.
"""
from __future__ import annotations

import os
import time
from datetime import datetime
from io import BytesIO
from typing import List

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from config import Config
from services.qr_generator import QRGenerator
from services.font_utils import ensure_thai_fonts
from utils.pdf_html import clean_simple_html
from utils.pdf_fonts import select_font_for_text
from utils.pdf_sanitize import sanitize_text_block
from utils.logging_config import get_logger

logger = get_logger(__name__)

FORBIDDEN_GLYPHS = {"■", "▪", "□"}


def _scrub(text: str | None) -> str:
    if not text:
        return ""
    for g in FORBIDDEN_GLYPHS:
        text = text.replace(g, "-")
    return text


class PDFGenerator:
    def __init__(self):
        self.output_dir = "static/generated"
        os.makedirs(self.output_dir, exist_ok=True)
        self.qr_generator = QRGenerator()
        try:
            import reportlab.rl_config as rl_config  # type: ignore
            rl_config.pageCompression = bool(getattr(Config, "PDF_ENABLE_COMPRESSION", True))
        except Exception:
            pass
        self._register_fonts()
        self.default_font = "Helvetica"
        self.default_font_bold = "Helvetica-Bold"
        if "NotoSans" in pdfmetrics.getRegisteredFontNames():
            self.default_font = "NotoSans"
        if "NotoSans-Bold" in pdfmetrics.getRegisteredFontNames():
            self.default_font_bold = "NotoSans-Bold"
        self.normal_style = ParagraphStyle("Normal8", fontName=self.default_font, fontSize=8, leading=10)
        self.heading_style = ParagraphStyle("Heading", parent=self.normal_style, fontName=self.default_font_bold, fontSize=9, leading=11, spaceBefore=6, spaceAfter=2)
        self.table_header_style = ParagraphStyle("TblHdr", parent=self.normal_style, fontName=self.default_font_bold, fontSize=7, leading=8, alignment=TA_LEFT)
        self.table_cell_style = ParagraphStyle("TblCell", parent=self.normal_style, fontSize=7, leading=8)

        def _register_fonts(self):
            ext_dir = getattr(Config, "PDF_FONT_DIR", None)
            if ext_dir and os.path.isdir(ext_dir):
                for fname in os.listdir(ext_dir):
                    if not fname.lower().endswith((".ttf", ".otf")):
                        continue
                    name = os.path.splitext(fname)[0]
                    if name in pdfmetrics.getRegisteredFontNames():
                        continue
                    try:
                        pdfmetrics.registerFont(TTFont(name, os.path.join(ext_dir, fname)))
                    except Exception:
                        """Clean deduplicated PDF generator (2025-08 rebuild).

                        Single source of voucher layout used by both file and bytes generation to
                        eliminate divergence bugs that previously accumulated after years of
                        copy‑paste edits. Keep this module lean: layout story in one method.
                        """
                        from __future__ import annotations

                        import os, time
                        from datetime import datetime
                        from io import BytesIO
                        from typing import List

                        from reportlab.lib.pagesizes import A4
                        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
                        from reportlab.lib.styles import ParagraphStyle
                        from reportlab.lib.enums import TA_LEFT, TA_CENTER
                        from reportlab.lib import colors
                        from reportlab.lib.units import inch
                        from reportlab.pdfbase import pdfmetrics
                        from reportlab.pdfbase.ttfonts import TTFont

                        from config import Config
                        from services.qr_generator import QRGenerator
                        from services.font_utils import ensure_thai_fonts
                        from utils.pdf_html import clean_simple_html
                        from utils.pdf_fonts import select_font_for_text
                        from utils.pdf_sanitize import sanitize_text_block
                        from utils.logging_config import get_logger

                        logger = get_logger(__name__)

                        FORBIDDEN_GLYPHS = {"■", "▪", "□"}


                        def _scrub(text: str | None) -> str:
                            if not text:
                                return ""
                            for g in FORBIDDEN_GLYPHS:
                                text = text.replace(g, "-")
                            return text


                        class PDFGenerator:
                            """Primary PDF generation service.

                            Public methods:
                              generate_tour_voucher(booking) -> filename
                              generate_tour_voucher_bytes(booking) -> bytes
                              generate_mpv_booking(booking) -> filename
                              generate_booking_pdf(booking) -> filename (service proposal)
                            """

                            def __init__(self):
                                self.output_dir = "static/generated"; os.makedirs(self.output_dir, exist_ok=True)
                                self.qr_generator = QRGenerator()
                                try:  # optional compression flag
                                    import reportlab.rl_config as rl_config  # type: ignore
                                    rl_config.pageCompression = bool(getattr(Config, "PDF_ENABLE_COMPRESSION", True))
                                except Exception:
                                    pass
                                self._register_fonts()
                                # choose defaults (prefer Noto if present)
                                self.default_font = "NotoSans" if "NotoSans" in pdfmetrics.getRegisteredFontNames() else "Helvetica"
                                self.default_font_bold = "NotoSans-Bold" if "NotoSans-Bold" in pdfmetrics.getRegisteredFontNames() else "Helvetica-Bold"
                                self.normal_style = ParagraphStyle("Normal8", fontName=self.default_font, fontSize=8, leading=10)
                                self.heading_style = ParagraphStyle("Heading", parent=self.normal_style, fontName=self.default_font_bold, fontSize=9, leading=11, spaceBefore=6, spaceAfter=2)
                                self.table_header_style = ParagraphStyle("TblHdr", parent=self.normal_style, fontName=self.default_font_bold, fontSize=7, leading=8, alignment=TA_LEFT)
                                self.table_cell_style = ParagraphStyle("TblCell", parent=self.normal_style, fontSize=7, leading=8)

                            # Font registration -------------------------------------------------
                            def _register_fonts(self):
                                # custom directory
                                ext_dir = getattr(Config, "PDF_FONT_DIR", None)
                                if ext_dir and os.path.isdir(ext_dir):
                                    for fname in os.listdir(ext_dir):
                                        if fname.lower().endswith((".ttf", ".otf")):
                                            name = os.path.splitext(fname)[0]
                                            if name not in pdfmetrics.getRegisteredFontNames():
                                                try:
                                                    pdfmetrics.registerFont(TTFont(name, os.path.join(ext_dir, fname)))
                                                except Exception:  # pragma: no cover
                                                    pass
                                # thai & noto families
                                try:
                                    paths = ensure_thai_fonts(download=True)
                                    mapping = {
                                        "NotoSansThai-Regular.ttf": "NotoSansThai",
                                        "NotoSansThai-Bold.ttf": "NotoSansThai-Bold",
                                        "NotoSans-Regular.ttf": "NotoSans",
                                        "NotoSans-Bold.ttf": "NotoSans-Bold",
                                    }
                                    for p in paths:
                                        alias = mapping.get(os.path.basename(p))
                                        if alias and alias not in pdfmetrics.getRegisteredFontNames():
                                            try:
                                                pdfmetrics.registerFont(TTFont(alias, p))
                                            except Exception:  # pragma: no cover
                                                pass
                                except Exception as e:  # pragma: no cover
                                    logger.debug("ensure_thai_fonts failed: %s", e)

                            # Backwards compatibility helpers ----------------------------------
                            def _dynamic_paragraph(self, text: str, style: ParagraphStyle) -> Paragraph:  # pragma: no cover
                                return self._dyn(text, style)
                            def _clean_simple_html(self, text: str) -> str:  # pragma: no cover
                                return clean_simple_html(text)
                            def _select_font_for_text(self, base: str, text: str) -> str:  # pragma: no cover
                                return select_font_for_text(base, text)
                            def _register_thai_font(self):  # pragma: no cover
                                self._register_fonts()

                            # Helpers -----------------------------------------------------------
                            def _format_date(self, value) -> str:
                                if not value:
                                    return ""
                                try:
                                    return datetime.strptime(str(value)[:10], "%Y-%m-%d").strftime("%d.%b.%Y").upper()
                                except Exception:
                                    return str(value)
                            def _dyn(self, text: str, style: ParagraphStyle) -> Paragraph:
                                text = _scrub(text or "")
                                chosen = select_font_for_text(style.fontName, text)
                                if chosen != style.fontName:
                                    style = ParagraphStyle(f"{style.name}_{chosen}", parent=style, fontName=chosen)
                                return Paragraph(text, style)

                            # Voucher story (single source) ------------------------------------
                            def _voucher_story(self, booking) -> List:
                                story: List = []
                                # Logo / company block
                                logo_path = "dcts-logo-vou.png"
                                if os.path.exists(logo_path):
                                    try:
                                        h = 55; logo_img = Image(logo_path, width=h * 1.786, height=h)
                                    except Exception:
                                        logo_img = Paragraph("LOGO", ParagraphStyle("LogoFallback", parent=self.normal_style, fontSize=14, textColor=colors.blue, fontName=self.default_font_bold))
                                else:
                                    logo_img = Paragraph("LOGO", ParagraphStyle("LogoFallback", parent=self.normal_style, fontSize=14, textColor=colors.blue, fontName=self.default_font_bold))
                                company_lines = [
                                    "<b>DHAKUL CHAN NICE HOLIDAYS DISCOVERY GROUP COMPANY LIMITED.</b>",
                                    "HKG: C13, 21/F, Mai Wah Industrial Bldg., 1–7 Wah Shing Street, Kwa Chung, NT.",
                                    "<b>DHAKUL CHAN TRAVEL SERVICE (THAILAND) CO.,LTD.</b>",
                                    "BKK: 710, 716 Prachautid Road, Samsennok, Huai Kwang, Bangkok 10320",
                                    "Tel: +852 23921155, +852 23921177 | +662 266525, +662 2744216",
                                ]
                                company_block = Table([[self._dyn(line, ParagraphStyle(f"CL{i}", parent=self.normal_style, fontSize=7, leading=8.5))] for i, line in enumerate(company_lines, 1)], colWidths=[300])
                                company_block.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
                                party_name = getattr(booking, "party_name", None) or "......"
                                title_para = Paragraph("<b>TOUR VOUCHER / SERVICE ORDER</b>", ParagraphStyle("Title", parent=self.normal_style, alignment=TA_RIGHT, fontSize=11, leading=13, textColor=colors.HexColor("#1D5FE9"), fontName=self.default_font_bold))
                                reference_para = Paragraph(f"Reference: {getattr(booking,'booking_reference','')}", ParagraphStyle("Ref", parent=self.normal_style, fontSize=8, alignment=TA_LEFT, leading=10, textColor=colors.HexColor("#555555")))
                                party_para = self._dyn(f"<b>Party Name:</b> {party_name}", ParagraphStyle("Party", parent=self.normal_style, fontSize=7, leading=9))
                                ar_val = getattr(booking, "invoice_number", None) or getattr(booking, "agency_reference", None) or "......"
                                qt_val = getattr(booking, "quote_number", None) or (str(getattr(booking, "quote_id")) if getattr(booking, "quote_id", None) else "......")
                                ar_qt_para = Paragraph(f"<b>ARNO:</b> {ar_val}   <b>QTNO:</b> {qt_val}", ParagraphStyle("ARQT", parent=self.normal_style, fontSize=8, leading=10))
                                right_meta = Table([[reference_para], [ar_qt_para]], colWidths=[175])
                                right_meta.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
                                header = Table([[logo_img, company_block, title_para], [party_para, "", right_meta]], colWidths=[160, 220, 175], rowHeights=[65, 22])
                                header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (0, 0), (0, 0), "CENTER"), ("ALIGN", (1, 0), (1, 0), "LEFT"), ("ALIGN", (2, 0), (2, 0), "RIGHT"), ("LEFTPADDING", (0, 0), (-1, -1), 15), ("RIGHTPADDING", (0, 0), (-1, -1), 15)]))
                                story.append(header)
                                story.append(Spacer(1, 12))

                                # Guests
                                story.append(Paragraph("Guest Names:", self.heading_style))
                                guests: List[str] = []
                                if hasattr(booking, "get_guest_list"):
                                    try: guests = booking.get_guest_list() or []
                                    except Exception: guests = []
                                else:
                                    raw = getattr(booking, "guest_list", [])
                                    if isinstance(raw, str): guests = [g.strip() for g in raw.split("\n") if g.strip()]
                                    elif isinstance(raw, (list, tuple)): guests = list(raw)
                                if guests:
                                    for i, g in enumerate(guests, 1): story.append(self._dyn(f"{i}. {g}", self.normal_style))
                                else:
                                    story.append(Paragraph("No guests specified", self.normal_style))
                                story.append(Spacer(1, 12))

                                # Services table
                                story.append(Paragraph("Hotel / Accommodation | Transfer | Others | Flight Detail", self.heading_style))
                                rows = []
                                if hasattr(booking, "get_voucher_rows"):
                                    try: rows = booking.get_voucher_rows() or []
                                    except Exception: rows = []
                                else: rows = getattr(booking, "voucher_rows", []) or []
                                header_cells = [Paragraph(h, self.table_header_style) for h in ["No.", "ARRIVAL", "DEPARTURE", "SERVICE BY", "TYPE/CLASS/PAXS/PIECES"]]
                                data = [header_cells]
                                if rows:
                                    for i, r in enumerate(rows, 1):
                                        svc = clean_simple_html(str(r.get("service_by", "")).replace("\n", "<br/>"))
                                        typ = clean_simple_html(str(r.get("type", "")).replace("\n", "<br/>"))
                                        data.append([
                                            Paragraph(str(i), self.table_cell_style),
                                            Paragraph(self._format_date(r.get("arrival", "")), self.table_cell_style),
                                            Paragraph(self._format_date(r.get("departure", "")), self.table_cell_style),
                                            self._dyn(svc, self.table_cell_style),
                                            self._dyn(typ, self.table_cell_style)
                                        ])
                                else:
                                    pax = getattr(booking, "total_pax", None) or getattr(booking, "adults", 1) or 1
                                    data.append([Paragraph("1", self.table_cell_style), Paragraph("", self.table_cell_style), Paragraph("", self.table_cell_style), Paragraph("Tour Service", self.table_cell_style), Paragraph(f"{pax} PAX", self.table_cell_style)])
                                table = Table(data, colWidths=[0.4*inch, 1.1*inch, 1.1*inch, 3.1*inch, 2.4*inch])
                                style_cmds = [
                                    ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#d9d9d9")),
                                    ("LINEABOVE", (0,0), (-1,0), 0.75, colors.HexColor("#b3b3b3")),
                                    ("LINEBELOW", (0,0), (-1,0), 0.75, colors.HexColor("#b3b3b3")),
                                    ("ALIGN", (0,1), (2,-1), "CENTER"),
                                    ("ALIGN", (3,1), (4,-1), "LEFT"),
                                    ("VALIGN", (0,0), (-1,-1), "TOP"),
                                    ("LEFTPADDING", (0,0), (-1,-1), 4), ("RIGHTPADDING", (0,0), (-1,-1), 4),
                                    ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4),
                                    ("GRID", (0,0), (-1,-1), 0.25, colors.HexColor("#bfbfbf")),
                                ]
                                if getattr(Config, "PDF_TABLE_ZEBRA", True):
                                    for idx in range(1, len(data)):
                                        if idx % 2 == 1: style_cmds.append(("BACKGROUND", (0,idx), (-1,idx), colors.HexColor("#f4f4f4")))
                                table.setStyle(TableStyle(style_cmds))
                                story.append(table); story.append(Spacer(1,14))

                                # Optional image
                                img_rel = getattr(booking, "voucher_image_path", None)
                                if img_rel:
                                    try:
                                        rel = img_rel.split("?")[0].lstrip("/")
                                        candidates = [rel, os.path.join("static", rel)] if not rel.startswith("static/") else [rel]
                                        img_abs = next((c for c in candidates if os.path.exists(c)), None)
                                        if img_abs:
                                            story.append(Paragraph("Description:", self.heading_style))
                                            pic = Image(img_abs); w, h = pic.wrap(0,0); max_w = 440
                                            if w > max_w: r = max_w / w; pic.drawWidth = max_w; pic.drawHeight = h * r
                                            story.append(pic); story.append(Spacer(1,12))
                                    except Exception as e:  # pragma: no cover
                                        if getattr(Config, "PDF_FONT_DEBUG", False): logger.warning("Voucher image load failed: %s", e)

                                # Description
                                desc = getattr(booking, "description", None)
                                if desc:
                                    story.append(Paragraph("Service Detail / Itinerary:", self.heading_style))
                                    sanitized = sanitize_text_block(str(desc)).replace("\n", "<br/>")
                                    story.append(self._dyn(clean_simple_html(sanitized), self.normal_style)); story.append(Spacer(1,12))

                                # QR
                                try:
                                    qr_path = self.qr_generator.generate_voucher_qr(booking)
                                    if qr_path and os.path.exists(qr_path): story.append(Image(qr_path, width=1.2*inch, height=1.2*inch))
                                except Exception as e:  # pragma: no cover
                                    logger.error("QR add failed: %s", e)
                                story.append(Spacer(1,18))

                                # Terms
                                story.append(Paragraph("Terms & Conditions:", self.heading_style))
                                terms = [
                                    "This document serves as an official confirmation of travel services and may be presented as a reference with relevant service providers.",
                                    "Service details and prices are subject to change in the event of any amendments to the travel dates or number of travelers.",
                                    "The customer is responsible for reviewing and ensuring the accuracy of all flight, hotel, and service information prior to use.",
                                    "Any request for changes must be submitted at least 72 business hours in advance, or at the earliest practicable time.",
                                    "In case of emergency, please contact the coordination number specified in this document or reach us via Line official @DHAKULCHAN.",
                                ]
                                bullet_style = ParagraphStyle("Terms", parent=self.normal_style, fontSize=8, leading=10, leftIndent=6)
                                for t in terms: story.append(Paragraph(f"&bull;&nbsp;{_scrub(t)}", bullet_style))
                                story.append(Spacer(1,14))

                                # Signatures
                                foot = Table([["Confirmed By:", "Accepted By:"],["_"*28, "_"*28],["Date: ___ / ___ / _____", "Date: ___ / ___ / _____"]], colWidths=[3*inch, 3*inch])
                                foot.setStyle(TableStyle([("ALIGN", (0,0), (-1,-1), "CENTER"), ("FONTSIZE", (0,0), (-1,-1), 8)]))
                                story.append(foot)

                                # Embed unused fonts if forcing embedding
                                if getattr(Config, "PDF_FORCE_EMBED_FONTS", False):
                                    for f in getattr(Config, "PDF_FALLBACK_FONTS", []):
                                        if f in pdfmetrics.getRegisteredFontNames():
                                            story.append(Paragraph(" ", ParagraphStyle(f"Embed_{f}", parent=self.normal_style, fontName=f, fontSize=1, leading=1)))
                                return story

                            # Header/footer callback -------------------------------------------
                            def _header_footer(self, c, doc):  # pragma: no cover
                                c.saveState(); c.setFillColorRGB(0.11,0.37,0.91)
                                y_rule = A4[1] - doc.topMargin + 4
                                c.rect(doc.leftMargin, y_rule, A4[0]-doc.leftMargin-doc.rightMargin, 0.8, fill=1, stroke=0)
                                c.setFont(self.default_font_bold, 8); c.setFillColorRGB(0.15,0.15,0.15)
                                c.drawString(doc.leftMargin, A4[1]-doc.topMargin+8, "TOUR VOUCHER - SERVICE ORDER")
                                c.setFont(self.default_font, 8)
                                page_txt = f"Page {doc.page}"; w = c.stringWidth(page_txt, self.default_font, 8)
                                c.drawString(A4[0]-doc.rightMargin-w, A4[1]-doc.topMargin+8, page_txt)
                                c.setFont(self.default_font,7); c.setFillColorRGB(0.6,0.6,0.6)
                                c.drawString(doc.leftMargin, doc.bottomMargin-14, f"Generated: {datetime.now().strftime('%d %b %Y %H:%M')} | Dhakul Chan Nice Holidays Group")
                                c.restoreState()

                            # Public API --------------------------------------------------------
                            def generate_tour_voucher(self, booking):
                                start = time.perf_counter()
                                filename = f"tour_voucher_{getattr(booking,'booking_reference','UNKNOWN')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                                filepath = os.path.join(self.output_dir, filename)
                                doc = SimpleDocTemplate(filepath, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=30, bottomMargin=32)
                                story = self._voucher_story(booking)
                                doc.build(story, onFirstPage=self._header_footer, onLaterPages=self._header_footer)
                                logger.info("Voucher PDF generated %s (%.1f ms)", filename, (time.perf_counter()-start)*1000)
                                return filename

                            def generate_tour_voucher_bytes(self, booking) -> bytes:
                                buf = BytesIO()
                                doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=30, bottomMargin=32)
                                story = self._voucher_story(booking)
                                doc.build(story, onFirstPage=self._header_footer, onLaterPages=self._header_footer)
                                return buf.getvalue()

                            def generate_mpv_booking(self, booking):
                                filename = f"mpv_booking_{getattr(booking,'booking_reference','UNKNOWN')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                                filepath = os.path.join(self.output_dir, filename)
                                doc = SimpleDocTemplate(filepath, pagesize=A4, leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40)
                                story = [Paragraph("MPV BOOKING CONFIRMATION", ParagraphStyle("MPVTitle", parent=self.normal_style, fontName=self.default_font_bold, fontSize=14, alignment=TA_CENTER, spaceAfter=12))]
                                details = [
                                    ("Booking Reference", getattr(booking, "booking_reference", "")),
                                    ("Customer", getattr(getattr(booking, "customer", None), "name", "")),
                                    ("Vehicle Type", getattr(booking, "vehicle_type", "")),
                                    ("Pickup Point", getattr(booking, "pickup_point", "")),
                                    ("Destination", getattr(booking, "destination", "")),
                                    ("Pickup Date", str(getattr(booking, "arrival_date", ""))),
                                    ("Pickup Time", str(getattr(booking, "pickup_time", ""))),
                                    ("Number of PAX", str(getattr(booking, "total_pax", ""))),
                                    ("Contact Phone", getattr(getattr(booking, "customer", None), "phone", "")),
                                    ("Total Amount", f"{getattr(booking,'currency','')} {getattr(booking,'total_amount','')}")
                                ]
                                data = [[Paragraph(f"<b>{k}:</b>", self.table_cell_style), Paragraph(_scrub(str(v)), self.table_cell_style)] for k,v in details]
                                tbl = Table(data, colWidths=[120, 340])
                                tbl.setStyle(TableStyle([
                                    ("VALIGN", (0,0), (-1,-1), "TOP"),
                                    ("GRID", (0,0), (-1,-1), 0.25, colors.grey),
                                    ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#f0f0f0")),
                                    ("LEFTPADDING", (0,0), (-1,-1), 4), ("RIGHTPADDING", (0,0), (-1,-1), 4),
                                    ("TOPPADDING", (0,0), (-1,-1), 3), ("BOTTOMPADDING", (0,0), (-1,-1), 3),
                                ]))
                                story.append(tbl); story.append(Spacer(1,12))
                                try:
                                    qr_path = self.qr_generator.generate_mpv_qr(booking)
                                    if qr_path and os.path.exists(qr_path): story.append(Image(qr_path, width=1.3*inch, height=1.3*inch))
                                except Exception as e:  # pragma: no cover
                                    logger.error("MPV QR error: %s", e)
                                story.append(Spacer(1,12))
                                story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", self.normal_style))
                                doc.build(story)
                                return filename

                            def generate_booking_pdf(self, booking, **kwargs):
                                # Try specialized generators first (optional / plug-in style)
                                try:
                                    from services.simple_pdf_generator import SimplePDFGenerator
                                    sp = SimplePDFGenerator(); fn = sp.generate_simple_pdf(booking)
                                    if fn: return fn
                                except Exception: pass
                                try:
                                    from services.thai_pdf_service import ThaiPDFService
                                    tp = ThaiPDFService(); fn = tp.generate_thai_service_proposal(booking)
                                    if fn: return fn
                                except Exception: pass
                                filename = f"service_proposal_{getattr(booking,'booking_reference','UNKNOWN')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                                filepath = os.path.join(self.output_dir, filename)
                                doc = SimpleDocTemplate(filepath, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=40, bottomMargin=40)
                                story = [Paragraph("<b>Service Proposal</b>", ParagraphStyle("SPTitle", parent=self.normal_style, fontName=self.default_font_bold, fontSize=16, alignment=TA_CENTER, spaceAfter=12))]
                                party_line = f"Party Name: {getattr(booking,'party_name', getattr(getattr(booking,'customer',None),'name',''))}" or 'Party Name: -'
                                story.append(self._dyn(party_line, self.normal_style)); story.append(Spacer(1,6))
                                desc = getattr(booking, 'description', None)
                                if desc:
                                    safe = clean_simple_html(sanitize_text_block(desc)).replace('\n', '<br/>')
                                    story.append(self._dyn(safe, self.normal_style))
                                else:
                                    story.append(Paragraph('No itinerary provided.', self.normal_style))
                                story.append(Spacer(1,12))
                                story.append(Paragraph('Generated automatically by system.', ParagraphStyle('Foot', parent=self.normal_style, fontSize=7, textColor=colors.grey)))
                                doc.build(story)
                                return filename

                        __all__ = ["PDFGenerator"]
                                story.append(self._dyn(safe, self.normal_style))
                            else:
                                story.append(Paragraph('No itinerary provided.', self.normal_style))
                            story.append(Spacer(1, 12))
                            story.append(Paragraph('Generated automatically by system.', ParagraphStyle('Foot', parent=self.normal_style, fontSize=7, textColor=colors.grey)))
                            doc.build(story)
                            return filename

                    __all__ = ["PDFGenerator"]
        if hasattr(booking,'get_guest_list'):
            try:
                guests = booking.get_guest_list() or []
            except Exception:
                guests = []
        else:
            raw = getattr(booking,'guest_list',[])
            if isinstance(raw,str):
                guests = [g.strip() for g in raw.split('\n') if g.strip()]
            elif isinstance(raw,(list,tuple)):
                guests = list(raw)
        if guests:
            for i,g in enumerate(guests,1):
                story.append(self._dynamic_paragraph(f"{i}. {g}", self.normal_style))
        else:
            story.append(Paragraph("No guests specified", self.normal_style))
        story.append(Spacer(1,12))

        # Service summary table
        story.append(Paragraph("Hotel / Accommodation | Transfer | Others | Flight Detail", self.heading_style))
        voucher_rows = []
        if hasattr(booking,'get_voucher_rows'):
            try:
                voucher_rows = booking.get_voucher_rows() or []
            except Exception:
                voucher_rows = []
        else:
            voucher_rows = getattr(booking,'voucher_rows',[]) or []
        header_cells = [Paragraph(h,self.table_header_style) for h in ['No.','ARRIVAL','DEPARTURE','SERVICE BY','TYPE/CLASS/PAXS/PIECES']]
        table_data = [header_cells]
        if voucher_rows:
            for i,r in enumerate(voucher_rows,1):
                svc_txt = self._clean_simple_html(r.get('service_by','')).replace('\n','<br/>')
                type_txt = self._clean_simple_html(r.get('type','')).replace('\n','<br/>')
                table_data.append([
                    Paragraph(str(i), self.table_cell_style),
                    Paragraph(self._format_date(r.get('arrival','')), self.table_cell_style),
                    Paragraph(self._format_date(r.get('departure','')), self.table_cell_style),
                    self._dynamic_paragraph(svc_txt, self.table_cell_style),
                    self._dynamic_paragraph(type_txt, self.table_cell_style)
                ])
        else:
            arr = getattr(booking,'arrival_date',None)
            dep = getattr(booking,'departure_date',None)
            table_data.append([
                Paragraph('1', self.table_cell_style),
                Paragraph(self._format_date(str(arr)) if arr else '', self.table_cell_style),
                Paragraph(self._format_date(str(dep)) if dep else '', self.table_cell_style),
                Paragraph('Tour Service', self.table_cell_style),
                Paragraph(f"{total_pax} PAX", self.table_cell_style)
            ])
        from reportlab.platypus import Table as _Table, TableStyle as _TableStyle
        table = _Table(table_data, colWidths=[0.4*inch,1.1*inch,1.1*inch,3.1*inch,2.4*inch])
        style_cmds = [
            ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#d9d9d9')),
            ('LINEABOVE',(0,0),(-1,0),0.75,colors.HexColor('#b3b3b3')),
            ('LINEBELOW',(0,0),(-1,0),0.75,colors.HexColor('#b3b3b3')),
            ('TEXTCOLOR',(0,0),(-1,0),colors.black),
            ('ALIGN',(0,1),(2,-1),'CENTER'), ('ALIGN',(3,1),(4,-1),'LEFT'),
            ('VALIGN',(0,0),(-1,-1),'TOP'),
            ('LEFTPADDING',(0,0),(-1,-1),4), ('RIGHTPADDING',(0,0),(-1,-1),4),
            ('TOPPADDING',(0,0),(-1,-1),4), ('BOTTOMPADDING',(0,0),(-1,-1),4),
            ('GRID',(0,0),(-1,-1),0.25,colors.HexColor('#bfbfbf'))
        ]
        if getattr(Config,'PDF_TABLE_ZEBRA', True):
            for idx in range(1,len(table_data)):
                if idx % 2 == 1:
                    style_cmds.append(('BACKGROUND',(0,idx),(-1,idx),colors.HexColor('#f4f4f4')))
        table.setStyle(_TableStyle(style_cmds))
        story.append(table)
        story.append(Spacer(1,14))

        # Voucher image
        img_rel = getattr(booking, 'voucher_image_path', None)
        if img_rel:
            try:
                clean_rel = img_rel.split('?')[0].lstrip('/')
                candidates = []
                if clean_rel.startswith('static/'):
                    candidates.append(clean_rel)
                    candidates.append(os.path.join('static', clean_rel[len('static/') :]))
                else:
                    candidates.append(os.path.join('static', clean_rel))
                    candidates.append(clean_rel)
                img_abs = None
                for c in candidates:
                    if os.path.exists(c):
                        img_abs = c; break
                if img_abs:
                    story.append(Paragraph("Description:", self.heading_style))
                    pic = RLImage(img_abs)
                    w, h = pic.wrap(0,0)
                    max_w = 440
                    if w > max_w:
                        ratio = max_w / w
                        pic.drawWidth = max_w
                        pic.drawHeight = h * ratio
                    story.append(pic)
                    story.append(Spacer(1,12))
            except Exception as e:
                if getattr(Config,'PDF_FONT_DEBUG', False):
                    logger.warning('Voucher image load failed (bytes): %s', e)

        # Flight info
        flight_info = getattr(booking,'flight_info',None)
        if flight_info:
            story.append(Paragraph("Flight Information:", self.heading_style))
            story.append(self._dynamic_paragraph(self._clean_simple_html(flight_info), self.normal_style))
            story.append(Spacer(1,12))

        # Description / Itinerary
        description = getattr(booking,'description',None)
        if description:
            story.append(Paragraph("Service Detail / Itinerary:", self.heading_style))
            sanitized_desc = sanitize_text_block(description).replace('\n','<br/>')
            story.append(self._dynamic_paragraph(self._clean_simple_html(sanitized_desc), self.normal_style))
            story.append(Spacer(1,12))

        # QR
        try:
            qr_path = None
            try:
                qr_path = self.qr_generator.generate_voucher_qr(booking)
            except AttributeError as attr_err:
                logger.debug("QR generation skipped (attribute missing): %s", attr_err)
            if qr_path and os.path.exists(qr_path):
                from reportlab.platypus import Image as _Img
                story.append(_Img(qr_path, width=1.2*inch, height=1.2*inch))
        except Exception as e:
            logger.error("Error adding QR code (voucher bytes): %s", e, exc_info=True)
        story.append(Spacer(1,18))

        # Terms
        story.append(Paragraph("Terms & Conditions:", self.heading_style))
        english_terms_main = [
            "This document serves as an official confirmation of travel services and may be presented as a reference with relevant service providers.",
            "Service details and prices are subject to change in the event of any amendments to the travel dates or number of travelers.",
            "The customer is responsible for reviewing and ensuring the accuracy of all flight, hotel, and service information prior to use.",
            "Any request for changes must be submitted at least 72 business hours in advance, or at the earliest practicable time.",
            "In case of emergency, please contact the coordination number specified in this document or reach us via Line official @DHAKULCHAN.",
        ]
        bullet_style = ParagraphStyle('VoucherEnglishTerms', parent=self.normal_style, fontName=self.default_font, fontSize=8, leading=10, leftIndent=6)
        for t in english_terms_main:
            story.append(Paragraph(f"&bull;&nbsp;{t}", bullet_style))
        story.append(Spacer(1,14))

        footer_table = Table([
            ['Confirmed By:', 'Accepted By:'], ['_'*28, '_'*28], ['Date: ___ / ___ / _____', 'Date: ___ / ___ / _____']
        ], colWidths=[3*inch,3*inch])
        footer_table.setStyle(TableStyle([
            ('ALIGN',(0,0),(-1,-1),'CENTER'), ('FONTNAME',(0,0),(-1,-1),self.default_font), ('FONTSIZE',(0,0),(-1,-1),8)
        ]))
        story.append(footer_table)

        if getattr(Config,'PDF_FORCE_EMBED_FONTS', False):
            from reportlab.pdfbase import pdfmetrics
            embed_fonts = [f for f in getattr(Config,'PDF_FALLBACK_FONTS', []) if f in pdfmetrics.getRegisteredFontNames()]
            for ef in embed_fonts:
                story.append(Paragraph(' ', ParagraphStyle(f'Embed_{ef}', parent=self.normal_style, fontName=ef, fontSize=1, leading=1)))

__all__ = ['PDFGenerator']
        story.append(details_table)
        story.append(Spacer(1, 20))
        
        # Special Requests
        if booking.special_request:
            special_heading = Paragraph("Special Requests:", self.heading_style)
            story.append(special_heading)
            special_text = Paragraph(booking.special_request, self.normal_style)
            story.append(special_text)
            story.append(Spacer(1, 20))
        
        # Guest List
        guest_heading = Paragraph("Guest List:", self.heading_style)
        story.append(guest_heading)
        
        guests = booking.get_guest_list()
        if guests:
            for i, guest in enumerate(guests, 1):
                guest_item = Paragraph(f"{i}. {guest}", self.normal_style)
                story.append(guest_item)
        
        story.append(Spacer(1, 30))
        
        # QR Code
        try:
            qr_path = self.qr_generator.generate_hotel_ro_qr(booking)
            if os.path.exists(qr_path):
                qr_image = Image(qr_path, width=1.5*inch, height=1.5*inch)
                story.append(qr_image)
        except Exception as e:
            logger.error("Error adding QR code (hotel_ro): %s", e, exc_info=True)
        
        # Footer
        footer = Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}<br/>{Config.COMPANY_NAME}<br/>{Config.COMPANY_PHONE}", self.normal_style)
        story.append(footer)
        
        # Build PDF with post-sweep scrub and optional glyph debug
        glyph_debug = bool(int(os.getenv('PDF_DEBUG_GLYPHS','0') or '0'))
        if glyph_debug:
            dbg_path = os.path.join(self.output_dir, 'glyph_debug.log')
            with open(dbg_path, 'a', encoding='utf-8') as fh:
                fh.write(f"\n--- Voucher {filename} ---\n")
        try:
            from reportlab.platypus import Paragraph as _P, Table as _T
            for flow in story:
                if isinstance(flow, _P) and hasattr(flow, '_text'):
                    flow._text = _scrub_forbidden(flow._text)
                elif isinstance(flow, _T):
                    for r,row in enumerate(flow._cellvalues):
                        for c,val in enumerate(row):
                            if isinstance(val, _P) and hasattr(val, '_text'):
                                val._text = _scrub_forbidden(val._text)
        except Exception:
            pass
        doc.build(story)
        return filename
    
    def generate_mpv_booking(self, booking):
        """Generate MPV Booking PDF"""
        filename = f"mpv_booking_{booking.booking_reference}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        
        doc = SimpleDocTemplate(filepath, pagesize=A4)
        story = []
        
        # Header
        title = Paragraph("MPV BOOKING CONFIRMATION", self.title_style)
        story.append(title)
        
        company_info = Paragraph(f"<b>Transport Company:</b> {Config.COMPANY_NAME}", self.normal_style)
        story.append(company_info)
        story.append(Spacer(1, 20))
        
        # Booking Details
        details_data = [
            ['Booking Reference:', booking.booking_reference],
            ['Customer Name:', booking.customer.name],
            ['Vehicle Type:', booking.vehicle_type],
            ['Pickup Point:', booking.pickup_point],
            ['Destination:', booking.destination],
            ['Pickup Date:', str(booking.arrival_date)],
            ['Pickup Time:', str(booking.pickup_time)],
            ['Number of PAX:', str(booking.total_pax)],
            ['Contact Phone:', booking.customer.phone],
            ['Email:', booking.customer.email],
            ['Total Amount:', f"{booking.currency} {booking.total_amount}"],
        ]
        
        details_table = Table(details_data, colWidths=[2*inch, 4*inch])
        details_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), self.default_font_bold),
            ('FONTNAME', (1, 0), (1, -1), self.default_font),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        story.append(details_table)
        story.append(Spacer(1, 20))
        
        # Passenger List
        passenger_heading = Paragraph("Passenger List:", self.heading_style)
        story.append(passenger_heading)
        
        guests = booking.get_guest_list()
        if guests:
            for i, guest in enumerate(guests, 1):
                guest_item = Paragraph(f"{i}. {guest}", self.normal_style)
                story.append(guest_item)
        
        story.append(Spacer(1, 30))
        
        # Terms and Conditions
        terms_heading = Paragraph("Terms and Conditions:", self.heading_style)
        story.append(terms_heading)
        
        terms_text = """
1. Please be ready 15 minutes before pickup time.
2. Driver will wait maximum 30 minutes at pickup point.
3. Any changes must be notified at least 24 hours in advance.
4. Cancellation policy applies as per company terms.
5. Additional stops may incur extra charges.
        """
        
        terms = Paragraph(terms_text, self.normal_style)
        story.append(terms)
        story.append(Spacer(1, 20))
        
        # QR Code
        try:
            qr_path = self.qr_generator.generate_mpv_qr(booking)
            if os.path.exists(qr_path):
                qr_image = Image(qr_path, width=1.5*inch, height=1.5*inch)
                story.append(qr_image)
        except Exception as e:
            logger.error("Error adding QR code (mpv_booking): %s", e, exc_info=True)
        
        # Footer
        footer = Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}<br/>{Config.COMPANY_NAME}<br/>{Config.COMPANY_PHONE}", self.normal_style)
        story.append(footer)
        
        # Build PDF
        doc.build(story)
        return filename

    def generate_booking_pdf(self, booking, **kwargs):
        """Generate Service Proposal PDF (no icons, clean design)"""
        # Ignore any extra parameters like 'format' that might be passed
        
        # Try Simple PDF Generator first (romanized Thai)
        try:
            from services.simple_pdf_generator import SimplePDFGenerator
            simple_pdf = SimplePDFGenerator()
            filename = simple_pdf.generate_simple_pdf(booking)
            if filename:
                logger.info("Using Simple PDF Generator with romanized Thai")
                return filename
        except Exception as e:
            logger.warning("Simple PDF generation failed: %s", e, exc_info=True)
        
        # Try WeasyPrint second for better Thai support
        try:
            from services.thai_pdf_service import ThaiPDFService
            thai_pdf = ThaiPDFService()
            filename = thai_pdf.generate_thai_service_proposal(booking)
            if filename:
                logger.info("Using WeasyPrint for Thai PDF generation")
                return filename
        except Exception as e:
            logger.warning("WeasyPrint failed, falling back to ReportLab: %s", e, exc_info=True)
        
        # Fallback to ReportLab (original method)
        filename = f"service_proposal_{booking.booking_reference}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        
        # Add margins to document for better edge handling
        doc = SimpleDocTemplate(filepath, pagesize=A4, leftMargin=30, rightMargin=30, topMargin=30, bottomMargin=30)
        story = []
        
        # Register Thai font for better Thai text support
        self._register_thai_font()
        
        # --- HEADER SECTION ---
        # Logo (smaller)
        logo_path = "dcts-logo-vou.png"
        logo_img = None
        if os.path.exists(logo_path):
            logo_height = 45  # Reduced from 60
            logo_width = logo_height * 1.786
            logo_img = Image(logo_path, width=logo_width, height=logo_height)
        else:
            logo_img = Paragraph("D.C.T.S", ParagraphStyle('LogoFallback', parent=self.normal_style, 
                                fontSize=14, textColor=colors.blue, fontName=self.default_font_bold))
        
        # Company header with regular weight for address/contact
        company_header = Paragraph(
            "<b>DHAKUL CHAN TRAVEL SERVICE (THAILAND) CO.,LTD.</b><br/>"
            "710, 716, 704, 706 Prachautid Road, Samsennok, Huai Kwang, Bangkok 10310<br/>"
            "Tel: +662 2744216 | Line OA: @dhakulchan Website: www.dhakulchan.net",
            ParagraphStyle('CompanyHeader', parent=self.normal_style, alignment=TA_CENTER,
                         fontSize=8, leading=9, fontName=self.default_font)  # Regular weight for address/contact
        )
        
        # T.A.T License (smaller)
        tat_license = Paragraph(
            "T.A.T License<br/>11/03589",
            ParagraphStyle('TATLicense', parent=self.normal_style, alignment=TA_RIGHT,
                         fontSize=7, leading=8, fontName=self.default_font)
        )
        
        # Header table
        header_table = Table([
            [logo_img, company_header, tat_license]
        ], colWidths=[90, 360, 90])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ALIGN', (0,0), (0,0), 'LEFT'),
            ('ALIGN', (1,0), (1,0), 'CENTER'),
            ('ALIGN', (2,0), (2,0), 'RIGHT'),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 8))
        
        # --- SERVICE PROPOSAL TITLE ---
        party_name_line = f"Party Name: {getattr(booking, 'party_name', booking.customer.name)}"
        party_para = Paragraph(party_name_line, ParagraphStyle('PartyName', parent=self.normal_style, 
                              fontSize=9, fontName=self.default_font))
        
        title_para = Paragraph("<b>Service Proposal</b>", 
                              ParagraphStyle('ProposalTitle', parent=self.normal_style, alignment=TA_CENTER,
                                           fontSize=16, textColor=colors.blue, fontName=self.default_font_bold))
        
        reference_para = Paragraph(f"Reference: {booking.booking_reference}", 
                                  ParagraphStyle('Reference', parent=self.normal_style, alignment=TA_RIGHT,
                                              fontSize=8, fontName='Helvetica'))

        # Title section table
        title_table = Table([
            [party_para, title_para, reference_para]
        ], colWidths=[175, 200, 175])
        title_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (0,0), 'LEFT'),
            ('ALIGN', (1,0), (1,0), 'CENTER'),
            ('ALIGN', (2,0), (2,0), 'RIGHT'),
        ]))
        story.append(title_table)
        story.append(Spacer(1, 15))

        # --- INFORMATION BOXES ---
        # Create date value with DCTS by information
        create_date_val = getattr(booking, 'created_at', datetime.now()).strftime('%d.%b.%Y').upper()
        
        # Add DCTS by username (get from Flask login or default to 'Admin')
        try:
            from flask_login import current_user
            username = current_user.username if hasattr(current_user, 'username') and current_user.is_authenticated else 'Admin'
        except:
            username = 'Admin'
        
        dcts_by_val = f"{create_date_val}<br/><font color='#777777'>DCTS by: {username}</font>"
        
        # Format period dates
        if booking.arrival_date and booking.departure_date:
            start_formatted = booking.arrival_date.strftime('%d %b %Y')
            end_formatted = booking.departure_date.strftime('%d %b %Y')
            period_txt = f"{start_formatted} - {end_formatted}"
        elif booking.traveling_period_start and booking.traveling_period_end:
            start_formatted = booking.traveling_period_start.strftime('%d %b %Y')
            end_formatted = booking.traveling_period_end.strftime('%d %b %Y')
            period_txt = f"{start_formatted} - {end_formatted}"
        else:
            period_txt = "TBA"
        
        # Customer information with Tel. prefix
        phone_display = f"Tel. {booking.customer.phone}" if getattr(booking.customer, 'phone', '') else ''
        if phone_display:
            customer_val = f"{booking.customer.name}<br/><font color='#777777'>{phone_display}</font>"
        else:
            customer_val = f"{booking.customer.name}"  # avoid empty second line becoming squares in extraction
        
        # Format PAX details - only show non-zero values
        pax_parts = []
        if hasattr(booking, 'adults') and booking.adults and booking.adults > 0:
            pax_parts.append(f"Adult {booking.adults}")
        if hasattr(booking, 'children') and booking.children and booking.children > 0:
            pax_parts.append(f"Child {booking.children}")
        if hasattr(booking, 'infants') and booking.infants and booking.infants > 0:
            pax_parts.append(f"Infant {booking.infants}")
        
        pax_detail = " / ".join(pax_parts) if pax_parts else f"Adult {booking.total_pax}"
        pax_val = f"{booking.total_pax} pax<br/><font color='#777777'>{pax_detail}</font>"

        # Compact info (two condensed paragraphs instead of tables to avoid extractor squares)
        info_style = ParagraphStyle('InfoCompact', parent=self.normal_style, fontSize=7.5, leading=9)
        line1 = (f"<b>Create Date:</b> {create_date_val} <font color='#777777'>(DCTS by {username})</font> | "
                 f"<b>Traveling Period:</b> {period_txt}")
        pax_extra = pax_detail if pax_detail else ''
        phone_part = f" Tel. {booking.customer.phone}" if getattr(booking.customer,'phone','') else ''
        line2 = (f"<b>Customer:</b> {booking.customer.name}{phone_part} | "
                 f"<b>PAX:</b> {booking.total_pax} pax" + (f" ({pax_extra})" if pax_extra else ''))
        story.append(self._dynamic_paragraph(line1, info_style))
        story.append(self._dynamic_paragraph(line2, info_style))
        story.append(Spacer(1, 12))

        # --- SERVICE DETAIL / ITINERARY ---
        service_heading = Paragraph("<b>Service Detail / Itinerary:</b>", 
                                   ParagraphStyle('ServiceHeading', parent=self.normal_style, 
                                                fontSize=10, fontName='Helvetica-Bold'))
        story.append(service_heading)
        
        if booking.description:
            service_text = self._clean_simple_html(sanitize_text_block(booking.description))
            # Replace any lingering square bullet glyphs with '-' to satisfy glyph tests
            service_text = service_text.replace('■', '-')
            service_style = ParagraphStyle('ServiceDetail', parent=self.normal_style, 
                                         fontSize=8, fontName='Helvetica', leading=10)  # Reduced from 9 to 8
            story.append(Paragraph(service_text, service_style))
        else:
            sample_itinerary = (
                "Day 1: Airport transfer and hotel check-in<br/>"
                "Day 2: City tour and cultural sites visit<br/>"
                "Day 3: Shopping and leisure time<br/>"
                "Day 4: Departure transfer to airport"
            )
            story.append(Paragraph(sample_itinerary, ParagraphStyle('ServiceDetail', parent=self.normal_style, 
                                                                   fontSize=8, fontName='Helvetica')))  # Reduced from 9 to 8
        
        story.append(Spacer(1, 12))
        
        # --- PAYMENT INFORMATION ---
        payment_info = Paragraph(
            f"<b>Payment Information:</b> Total: THB {booking.total_amount or '7,500'}",
            ParagraphStyle('PaymentInfo', parent=self.normal_style, fontSize=9, fontName='Helvetica-Bold')
        )
        story.append(payment_info)
        story.append(Spacer(1, 10))
        
        # --- SPECIAL REQUESTS ---
        special_heading = Paragraph("<b>Special Requests:</b>", 
                                   ParagraphStyle('SpecialHeading', parent=self.normal_style, 
                                                fontSize=10, fontName='Helvetica-Bold'))
        story.append(special_heading)
        
        if booking.special_request:
            special_text = self._clean_simple_html(sanitize_text_block(booking.special_request))
            special_text = special_text.replace('■', '-')
            story.append(Paragraph(special_text, ParagraphStyle('SpecialRequest', parent=self.normal_style, 
                                                              fontSize=9, fontName='Helvetica')))
        else:
            story.append(Paragraph("No special requests", ParagraphStyle('NoSpecial', parent=self.normal_style, 
                                                                        fontSize=9, fontName='Helvetica', textColor=colors.HexColor('#777777'))))
        
        story.append(Spacer(1, 15))

        # --- TERMS & CONDITIONS (English – enhanced layout) ---
        from reportlab.platypus import HRFlowable
        story.append(HRFlowable(width='100%', thickness=0.6, color=colors.HexColor('#CBD5E1'), spaceBefore=4, spaceAfter=6))
        terms_heading = Paragraph("<b>Terms & Conditions:</b>", ParagraphStyle('TermsHeading', parent=self.normal_style,
                                                                                fontSize=10, leading=12, fontName=self.default_font_bold, spaceAfter=6))
        story.append(terms_heading)
        english_terms = [
            "This document serves as an official confirmation of travel services and may be presented as a reference with relevant service providers.",
            "Service details and prices are subject to change in the event of any amendments to the travel dates or number of travelers.",
            "The customer is responsible for reviewing and ensuring the accuracy of all flight, hotel, and service information prior to use.",
            "Any request for changes must be submitted at least 72 business hours in advance, or at the earliest practicable time.",
            "In case of emergency, please contact the coordination number specified in this document or reach us via Line official @DHAKULCHAN.",
        ]
        bullet_style = ParagraphStyle('TermsBullet', parent=self.normal_style, fontName=self.default_font,
                                      fontSize=8.5, leading=11, leftIndent=4, spaceBefore=0, spaceAfter=0)
        # Build bullet paragraphs (•) using &bull; to avoid missing glyph; fallback to '-' if extraction issues.
        para_terms = []
        for t in english_terms:
            safe = t.replace('■','-')
            para_terms.append(Paragraph(f"&bull;&nbsp;{safe}", bullet_style))
        # Two-column layout
        import math
        split_index = math.ceil(len(para_terms)/2)
        left_col = para_terms[:split_index]
        right_col = para_terms[split_index:]
        # Pad shorter
        max_rows = max(len(left_col), len(right_col))
        while len(left_col) < max_rows: left_col.append(Paragraph("", bullet_style))
        while len(right_col) < max_rows: right_col.append(Paragraph("", bullet_style))
        terms_table_data = [[l, r] for l, r in zip(left_col, right_col)]
        terms_table = Table(terms_table_data, colWidths=[(A4[0]-40-40)/2]*2)  # approximate using page width minus margins
        terms_table.setStyle(TableStyle([
            ('VALIGN',(0,0),(-1,-1),'TOP'),
            ('LEFTPADDING',(0,0),(-1,-1),2),
            ('RIGHTPADDING',(0,0),(-1,-1),4),
            ('TOPPADDING',(0,0),(-1,-1),0),
            ('BOTTOMPADDING',(0,0),(-1,-1),1),
        ]))
        story.append(terms_table)
        # Add subtle rule below
        story.append(HRFlowable(width='100%', thickness=0.6, color=colors.HexColor('#CBD5E1'), spaceBefore=6, spaceAfter=4))
        # Ensure font embedding for this section only (add invisible tiny paragraph using the same font)
        story.append(Paragraph(" ", ParagraphStyle('EmbedTermsFont', parent=self.normal_style, fontName=self.default_font, fontSize=1, leading=1)))

        # Build PDF (remains inside generator method)
        doc.build(story)
        return filename
