"""Tour Voucher PDF generator with image header support.

Uses Tour-voucher-header250822-up.png image header for Tour Voucher PDFs.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import List

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from config import Config
from services.pdf_common import build_header, append_terms
from utils.pdf_sanitize import sanitize_text_block
from utils.logging_config import get_logger


class TourVoucherPDFGenerator:
    OUTPUT_DIR = 'static/generated'

    def __init__(self):
        self.logger = get_logger(__name__)
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)
        self.output_dir = self.OUTPUT_DIR
        self._init_styles()

    def _init_styles(self):
        """Initialize paragraph styles for Tour Voucher PDF."""
        styles = getSampleStyleSheet()
        
        # Normal text style
        self.style_normal = ParagraphStyle(
            'TourVoucherNormal',
            parent=styles['Normal'],
            fontSize=11,
            leading=13,
            spaceAfter=6,
            fontName='Helvetica'
        )
        
        # Section header style
        self.style_section = ParagraphStyle(
            'TourVoucherSection',
            parent=styles['Heading2'],
            fontSize=13,
            leading=15,
            spaceBefore=12,
            spaceAfter=8,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#1a365d')
        )
        
        # Small gray text for details
        self.style_small_gray = ParagraphStyle(
            'TourVoucherSmallGray',
            parent=styles['Normal'],
            fontSize=9,
            leading=11,
            textColor=colors.HexColor('#666666'),
            fontName='Helvetica'
        )

    def generate_tour_voucher_pdf(self, booking) -> str:
        """Generate Tour Voucher PDF with image header.
        
        Args:
            booking: Booking model instance
            
        Returns:
            str: Path to generated PDF file
        """
        timestamp = datetime.now(timezone.utc)
        # Use microseconds for unique filename
        microseconds = int(timestamp.microsecond)
        filename = f"tour_voucher_{booking.booking_reference}_{timestamp.strftime('%Y%m%d_%H%M%S')}_{microseconds}.pdf"
        file_path = os.path.join(self.output_dir, filename)
        
        # Create PDF document
        doc = SimpleDocTemplate(file_path, pagesize=A4, 
                               leftMargin=28, rightMargin=28,
                               topMargin=28, bottomMargin=28)
        
        story = []
        avail_width = A4[0] - 56  # Total margins
        
        # Build header with image (voucher type)
        header, _ = build_header(self, avail_width, 'voucher')
        story.append(header)
        story.append(Spacer(1, 20))
        
        # Voucher title
        story.append(Paragraph('<b>TOUR VOUCHER</b>', 
                             ParagraphStyle('VoucherTitle', 
                                          parent=self.style_section,
                                          fontSize=16, 
                                          alignment=TA_CENTER,
                                          textColor=colors.HexColor('#1a365d'))))
        story.append(Spacer(1, 15))
        
        # Booking details
        story.append(Paragraph(f'<b>Voucher Reference:</b> {booking.booking_reference}', 
                             self.style_normal))
        story.append(Paragraph(f'<b>Party Name:</b> {booking.party_name or "N/A"}', 
                             self.style_normal))
        story.append(Paragraph(f'<b>Booking Type:</b> {booking.booking_type.title()}', 
                             self.style_normal))
        story.append(Paragraph(f'<b>Status:</b> {booking.status.title()}', 
                             self.style_normal))
        
        # Travel information
        if booking.arrival_date or booking.departure_date:
            story.append(Spacer(1, 10))
            story.append(Paragraph('<b>Travel Information</b>', self.style_section))
            
            if booking.arrival_date:
                story.append(Paragraph(f'<b>Arrival Date:</b> {booking.arrival_date.strftime("%d %B %Y")}', 
                                     self.style_normal))
            if booking.departure_date:
                story.append(Paragraph(f'<b>Departure Date:</b> {booking.departure_date.strftime("%d %B %Y")}', 
                                     self.style_normal))
        
        # Guest information
        if booking.total_pax > 0:
            story.append(Spacer(1, 10))
            story.append(Paragraph('<b>Guest Information</b>', self.style_section))
            story.append(Paragraph(f'<b>Total PAX:</b> {booking.total_pax}', self.style_normal))
            
            if booking.adults:
                story.append(Paragraph(f'<b>Adults:</b> {booking.adults}', self.style_normal))
            if booking.children:
                story.append(Paragraph(f'<b>Children:</b> {booking.children}', self.style_normal))
            if booking.infants:
                story.append(Paragraph(f'<b>Infants:</b> {booking.infants}', self.style_normal))
        
        # Additional information
        if booking.description:
            story.append(Spacer(1, 10))
            story.append(Paragraph('<b>Description</b>', self.style_section))
            story.append(Paragraph(sanitize_text_block(booking.description), self.style_normal))
        
        # Hotel specific information
        if booking.hotel_name:
            story.append(Spacer(1, 10))
            story.append(Paragraph('<b>Hotel Information</b>', self.style_section))
            story.append(Paragraph(f'<b>Hotel:</b> {booking.hotel_name}', self.style_normal))
            if booking.room_type:
                story.append(Paragraph(f'<b>Room Type:</b> {booking.room_type}', self.style_normal))
        
        # Transport specific information
        if booking.pickup_point or booking.destination:
            story.append(Spacer(1, 10))
            story.append(Paragraph('<b>Transport Information</b>', self.style_section))
            if booking.pickup_point:
                story.append(Paragraph(f'<b>Pickup Point:</b> {booking.pickup_point}', self.style_normal))
            if booking.destination:
                story.append(Paragraph(f'<b>Destination:</b> {booking.destination}', self.style_normal))
        
        # Footer
        story.append(Spacer(1, 20))
        story.append(Paragraph('Thank you for choosing our services!', 
                             ParagraphStyle('Footer', 
                                          parent=self.style_normal,
                                          alignment=TA_CENTER,
                                          textColor=colors.HexColor('#666666'))))
        
        # Build PDF
        doc.build(story)
        self.logger.info(f"Tour Voucher PDF generated: {filename}")
        
        return file_path


__all__ = ['TourVoucherPDFGenerator']
