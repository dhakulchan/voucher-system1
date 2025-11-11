"""
Enhanced Tour Voucher PDF Generator V2 - Clean Version
Based on the provided sample tour voucher layout with Company2 information
"""

import os
from io import BytesIO
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics import renderPDF

from config import Config
from utils.logging_config import get_logger
from services.qr_generator import QRGenerator


class TourVoucherGeneratorV2:
    """Enhanced Tour Voucher PDF Generator matching sample layout"""
    
    OUTPUT_DIR = "static/generated"
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.output_dir = self._ensure_dir(self.OUTPUT_DIR)
        self.qr = QRGenerator()
        self._register_thai_fonts()
        self._init_styles()
        
    def _ensure_dir(self, path: str) -> str:
        os.makedirs(path, exist_ok=True)
        return path
        
    def _register_thai_fonts(self):
        """Register Thai fonts for mixed language support"""
        try:
            # Try to register Thai fonts with explicit encoding
            font_paths = [
                'NotoSansThai-Regular.ttf',
                'NotoSansThai-Bold.ttf',
                'static/fonts/NotoSansThai-Regular.ttf',
                'static/fonts/NotoSansThai-Bold.ttf',
            ]
            
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        if 'Bold' in font_path:
                            # Register bold font with explicit encoding
                            font = TTFont('NotoSansThai-Bold', font_path)
                            pdfmetrics.registerFont(font)
                            self.logger.info(f"Registered bold Thai font: {font_path}")
                        else:
                            # Register regular font with explicit encoding
                            font = TTFont('NotoSansThai', font_path)
                            pdfmetrics.registerFont(font)
                            self.logger.info(f"Registered Thai font: {font_path}")
                    except Exception as e:
                        self.logger.warning(f"Failed to register font {font_path}: {e}")
                        
            self.has_thai_font = 'NotoSansThai' in pdfmetrics.getRegisteredFontNames()
            if self.has_thai_font:
                self.logger.info("Thai fonts registered successfully")
            else:
                self.logger.warning("Thai fonts not available")
                
        except Exception as e:
            self.logger.error(f"Failed to register Thai fonts: {e}")
            self.has_thai_font = False
            
    def _init_styles(self):
        """Initialize custom styles for tour voucher"""
        styles = getSampleStyleSheet()
        
        # Base font selection
        base_font = 'NotoSansThai' if self.has_thai_font else 'Helvetica'
        bold_font = 'NotoSansThai-Bold' if self.has_thai_font else 'Helvetica-Bold'
        
        # Header styles
        self.style_company_name = ParagraphStyle(
            'CompanyName',
            parent=styles['Normal'],
            fontSize=11,
            leading=13,
            fontName='Helvetica-Bold',
            alignment=TA_LEFT,
            spaceAfter=2
        )
        
        self.style_company_details = ParagraphStyle(
            'CompanyDetails', 
            parent=styles['Normal'],
            fontSize=9,
            leading=11,
            fontName='Helvetica',
            alignment=TA_LEFT,
            spaceAfter=1
        )
        
        # Title style
        self.style_title = ParagraphStyle(
            'Title',
            parent=styles['Normal'],
            fontSize=16,
            leading=20,
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
            spaceAfter=12,
            spaceBefore=12
        )
        
        # Reference info style
        self.style_reference = ParagraphStyle(
            'Reference',
            parent=styles['Normal'],
            fontSize=10,
            leading=12,
            fontName='Helvetica',
            alignment=TA_LEFT,
            spaceAfter=6
        )
        
        # Party/guest style with Thai support
        self.style_party = ParagraphStyle(
            'Party',
            parent=styles['Normal'],
            fontSize=12,
            leading=15,
            fontName=base_font,
            alignment=TA_LEFT,
            spaceAfter=8
        )
        
        # Normal style with Thai support
        self.style_normal = ParagraphStyle(
            'NormalThai',
            parent=styles['Normal'],
            fontSize=10,
            leading=12,
            fontName=base_font,
            alignment=TA_LEFT,
            spaceAfter=6
        )
        
        # Table header style
        self.style_table_header = ParagraphStyle(
            'TableHeader',
            parent=styles['Normal'],
            fontSize=9,
            leading=11,
            fontName=bold_font,
            alignment=TA_CENTER
        )
        
        # Table cell style
        self.style_table_cell = ParagraphStyle(
            'TableCell',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
            fontName=base_font,
            alignment=TA_LEFT
        )
        
    def _build_header(self, story):
        """Build Company2 header information"""
        
        # Company information from Config
        company_name = Config.COMPANY_NAME2
        company_address = Config.COMPANY_ADDRESS2 
        company_phone = Config.COMPANY_PHONE2
        company_mobile = Config.COMPANY_MOBILE2
        company_email = Config.COMPANY_EMAIL2
        company_website = Config.COMPANY_WEBSITE2
        
        # Company name
        story.append(Paragraph(company_name, self.style_company_name))
        
        # Company details
        story.append(Paragraph(company_address, self.style_company_details))
        story.append(Paragraph(f"Tel: {company_phone}", self.style_company_details))
        story.append(Paragraph(f"Email: {company_email} | Web: {company_website}", self.style_company_details))
        
        story.append(Spacer(1, 12))
        
    def _build_title(self, story):
        """Build title section"""
        story.append(Paragraph("TOUR VOUCHER / SERVICE ORDER", self.style_title))
        story.append(Spacer(1, 6))
        
    def _build_reference_info(self, story, booking):
        """Build reference information section"""
        
        # Reference numbers
        ref_no = getattr(booking, 'booking_reference', 'TBD')
        arno = getattr(booking, 'arno', 'TBD')
        quote_no = getattr(booking, 'quote_no', 'TBD')
        
        # Create reference table
        ref_data = [
            [f"Reference No: {ref_no}", f"ARNO: {arno}", f"QTNO: {quote_no}"]
        ]
        
        ref_table = Table(ref_data, colWidths=[6*cm, 4*cm, 4*cm])
        ref_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        
        story.append(ref_table)
        story.append(Spacer(1, 8))
        
    def _build_party_info(self, story, booking):
        """Build party and guest information"""
        
        # Party name
        party_name = getattr(booking, 'party_name', 'TBD')
        customer_name = booking.customer.name if booking.customer else 'TBD'
        
        story.append(Paragraph(f"<b>Party Name:</b> {party_name}", self.style_party))
        story.append(Paragraph(f"<b>Guest Name(s):</b> {customer_name}", self.style_party))
        
        story.append(Spacer(1, 12))
        
    def _build_service_table(self, story, booking):
        """Build 5-column service table with database data"""
        
        # Table headers for 5 columns as requested
        headers = [
            Paragraph("<b>No.</b>", self.style_table_header),
            Paragraph("<b>Arrival</b>", self.style_table_header),
            Paragraph("<b>Departure</b>", self.style_table_header),
            Paragraph("<b>Hotel/Service</b>", self.style_table_header),
            Paragraph("<b>Service By</b>", self.style_table_header),
        ]
        
        # Get voucher rows from database
        voucher_rows = getattr(booking, 'voucher_rows', [])
        if hasattr(booking, 'get_voucher_rows'):
            voucher_rows = booking.get_voucher_rows()
        
        table_data = [headers]
        
        if voucher_rows:
            # Add database data - voucher_rows is list of dictionaries
            for i, row in enumerate(voucher_rows, 1):
                arrival = row.get('arrival', '') or ''
                departure = row.get('departure', '') or ''
                service_by = row.get('service_by', '') or ''
                type_class_pax = row.get('type', '') or row.get('description', '') or ''
                
                # Combine hotel/service info
                hotel_service = service_by
                if type_class_pax and type_class_pax != service_by:
                    hotel_service += f"<br/>{type_class_pax}"
                
                table_data.append([
                    Paragraph(str(i), self.style_table_cell),
                    Paragraph(arrival, self.style_table_cell),
                    Paragraph(departure, self.style_table_cell),
                    Paragraph(hotel_service, self.style_table_cell),
                    Paragraph(service_by, self.style_table_cell),
                ])
        else:
            # Add sample rows if no database data
            for i in range(1, 4):
                table_data.append([
                    Paragraph(str(i), self.style_table_cell),
                    Paragraph("DD/MM/YYYY", self.style_table_cell),
                    Paragraph("DD/MM/YYYY", self.style_table_cell),
                    Paragraph("Hotel/Accommodation/Transfer", self.style_table_cell),
                    Paragraph("Service Provider", self.style_table_cell),
                ])
        
        # Create table with proper column widths
        col_widths = [1*cm, 2.5*cm, 2.5*cm, 6*cm, 4*cm]
        service_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        
        # Apply table styling
        service_table.setStyle(TableStyle([
            # Header styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            
            # Data rows styling
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # No. column center
            ('ALIGN', (1, 1), (-1, -1), 'LEFT'),   # Other columns left
            
            # Grid and padding
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        story.append(service_table)
        story.append(Spacer(1, 15))
        
    def _build_flight_info(self, story, booking):
        """Build flight information section"""
        
        story.append(Paragraph("<b>Flight Information:</b>", self.style_normal))
        
        # Get flight info from database
        flight_info = getattr(booking, 'flight_info', None)
        if flight_info:
            # Clean flight info text
            import re
            clean_flight = re.sub(r'<[^>]+>', '', flight_info)
            lines = clean_flight.split('\\n')
            for line in lines:
                if line.strip():
                    story.append(Paragraph(line.strip(), self.style_normal))
        else:
            # Sample flight information
            story.append(Paragraph("CX700 XXXXXXXXXXX", self.style_normal))
            story.append(Paragraph("CX703 XXXXXXXXXXX", self.style_normal))
        
        story.append(Spacer(1, 12))
        
    def _build_itinerary(self, story, booking):
        """Build service detail/itinerary section"""
        
        story.append(Paragraph("<b>Service Detail / Itinerary:</b>", self.style_normal))
        
        # Get description from booking
        description = getattr(booking, 'description', None)
        if description:
            # Clean HTML tags that cause issues with ReportLab
            import re
            clean_description = description
            # Remove problematic nested tags like <para><p>...</p></para>
            clean_description = re.sub(r'<para><p>(.*?)</p></para>', r'\\1', clean_description, flags=re.DOTALL)
            # Remove HTML tags
            clean_description = re.sub(r'<[^>]+>', '', clean_description)
            # Convert line breaks
            lines = clean_description.split('\\n')
            for line in lines:
                if line.strip():
                    story.append(Paragraph(line.strip(), self.style_normal))
        else:
            # Sample itinerary data
            sample_itinerary = [
                "Day 1: Arrival and hotel check-in",
                "Day 2: City tour and attractions", 
                "Day 3: Free time and shopping",
                "Day 4: Departure"
            ]
            
            for item in sample_itinerary:
                story.append(Paragraph(item, self.style_normal))
                
        story.append(Spacer(1, 12))
        
    def _build_qr_code(self, story, booking):
        """Build QR code section"""
        
        try:
            # Generate QR code for the booking
            qr_url = f"https://voucher.dhakulchan.net/booking/{booking.id}/view"
            
            # Create QR code widget
            qr_code = QrCodeWidget(qr_url)
            qr_code.barWidth = 3*cm
            qr_code.barHeight = 3*cm
            
            # Create drawing
            qr_drawing = Drawing(3*cm, 3*cm)
            qr_drawing.add(qr_code)
            
            # Add QR code to story
            story.append(qr_drawing)
            
        except Exception as e:
            self.logger.error(f"Failed to generate QR code: {e}")
            story.append(Paragraph("QR Code: [Generation Failed]", self.style_normal))
            
        story.append(Spacer(1, 12))
        
    def _build_terms(self, story):
        """Build terms and conditions"""
        
        story.append(Paragraph("<b>Terms & Conditions:</b>", self.style_normal))
        
        terms = [
            "• This voucher is valid for the dates specified above.",
            "• Please present this voucher upon arrival at the service location.",
            "• Changes to bookings must be made at least 24 hours in advance.", 
            "• Service details and prices are subject to change in the event of unforeseen circumstances such as weather, change of travel dates or number of travellers.",
            "• For any inquiries, please contact us immediately."
        ]
        
        for term in terms:
            story.append(Paragraph(term, self.style_normal))
            
        story.append(Spacer(1, 15))
        
    def _build_signatures(self, story):
        """Build signature lines"""
        
        # Signature section
        story.append(Paragraph("Confirmed By (DCTS): _______________________ &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Accepted By: _______________________", self.style_normal))
        story.append(Spacer(1, 8))
        story.append(Paragraph("Date: ___/___/_______ &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Date: ___/___/_______", self.style_normal))
        
    def _build_footer(self, canvas, doc):
        """Build footer with page numbers and system info"""
        canvas.saveState()
        
        # Footer positioning (1.0cm from bottom as requested)
        footer_y = 1.0*cm
        page_width = A4[0]
        
        # Footer text with generation timestamp
        generation_time = datetime.now().strftime('%d/%m/%Y %H:%M')
        footer_text = f"Dhakul Chan Nice Holidays Group - System DCTS V1.0 | Generated: {generation_time}"
        page_text = f"Page {doc.page}"
        
        # Set font
        canvas.setFont('Helvetica', 8)
        
        # Draw footer text (left aligned)
        canvas.drawString(1*cm, footer_y, footer_text)
        
        # Draw page number (right aligned)
        canvas.drawRightString(page_width - 1*cm, footer_y, page_text)
        
        canvas.restoreState()
        
    def generate_tour_voucher_v2(self, booking) -> str:
        """Generate enhanced tour voucher PDF and return filename"""
        
        # Create buffer and document
        buffer = BytesIO()
        
        # Document with 1.0cm margins as requested
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4,
            leftMargin=1.0*cm,
            rightMargin=1.0*cm, 
            topMargin=1.0*cm,
            bottomMargin=2.0*cm  # Extra space for footer
        )
        
        # Build story
        story = []
        
        # Add all sections
        self._build_header(story)
        self._build_title(story)
        self._build_reference_info(story, booking)
        self._build_party_info(story, booking)
        self._build_service_table(story, booking)
        self._build_flight_info(story, booking)
        self._build_itinerary(story, booking)
        # QR code removed as requested
        self._build_terms(story)
        self._build_signatures(story)
        
        # Build PDF with custom footer
        doc.build(story, onFirstPage=self._build_footer, onLaterPages=self._build_footer)
        
        # Save to file with timestamp for uniqueness
        buffer.seek(0)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"Tour_voucher_v2_{getattr(booking, 'booking_reference', 'UNKNOWN')}_{timestamp}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'wb') as f:
            f.write(buffer.getvalue())
            
        self.logger.info(f"Generated enhanced tour voucher: {filename}")
        return filename
        
    def generate_tour_voucher_v2_bytes(self, booking) -> bytes:
        """Generate enhanced tour voucher PDF and return bytes"""
        
        # Create buffer and document
        buffer = BytesIO()
        
        # Document with 1.0cm margins as requested
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4,
            leftMargin=1.0*cm,
            rightMargin=1.0*cm, 
            topMargin=1.0*cm,
            bottomMargin=2.0*cm  # Extra space for footer
        )
        
        # Build story
        story = []
        
        # Add all sections
        self._build_header(story)
        self._build_title(story)
        self._build_reference_info(story, booking)
        self._build_party_info(story, booking)
        self._build_service_table(story, booking)
        self._build_flight_info(story, booking)
        self._build_itinerary(story, booking)
        # QR code removed as requested
        self._build_terms(story)
        self._build_signatures(story)
        
        # Build PDF with custom footer
        doc.build(story, onFirstPage=self._build_footer, onLaterPages=self._build_footer)
        
        # Return bytes
        buffer.seek(0)
        return buffer.getvalue()
