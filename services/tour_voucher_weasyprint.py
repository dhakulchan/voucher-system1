"""
Tour Voucher PDF Generator using WeasyPrint
Generates professional PDF and PNG documents for tour vouchers
"""

import os
import io
from datetime import datetime
from weasyprint import HTML, CSS
from utils.logging_config import get_logger


class TourVoucherWeasyPrintGenerator:
    """Tour voucher generator using WeasyPrint for professional PDF output"""
    
    OUTPUT_DIR = "static/vouchers"
    
    def __init__(self):
        """Initialize the generator with output directory and logger"""
        self.logger = get_logger(__name__)
        self.output_dir = self.OUTPUT_DIR
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
    def generate_tour_voucher(self, booking_id) -> str:
        """Generate tour voucher PDF using WeasyPrint and return filename"""
        try:
            # Get booking data from database
            from models import Booking
            booking = Booking.query.filter_by(id=booking_id).first()
            if not booking:
                raise ValueError(f"Booking with ID {booking_id} not found")
                
            self.logger.info(f"Starting WeasyPrint PDF generation for booking {getattr(booking, 'booking_reference', 'UNKNOWN')}")
            
            # Generate HTML content
            html_content = self._generate_html(booking)
            
            # Create filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            booking_ref = getattr(booking, 'booking_reference', 'UNKNOWN')
            filename = f"Tour_voucher_v2_{booking_ref}_{timestamp}.pdf"
            filepath = os.path.join(self.output_dir, filename)
            
            # Generate PDF using WeasyPrint with base_url
            base_url = f"file://{os.getcwd()}/"
            html_doc = HTML(string=html_content, base_url=base_url)
            css_styles = CSS(string=self._get_css_styles())
            
            self.logger.info(f"About to generate PDF with WeasyPrint...")
            html_doc.write_pdf(filepath, stylesheets=[css_styles])
            
            self.logger.info(f"Generated tour voucher PDF using WeasyPrint: {filename}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Failed to generate tour voucher PDF: {e}")
            raise e
            
    def generate_tour_voucher_bytes(self, booking_id) -> bytes:
        """Generate tour voucher PDF using WeasyPrint and return bytes"""
        try:
            # Get booking data from database
            from models import Booking
            booking = Booking.query.filter_by(id=booking_id).first()
            if not booking:
                raise ValueError(f"Booking with ID {booking_id} not found")
                
            self.logger.info(f"Starting WeasyPrint PDF generation (bytes) for booking {getattr(booking, 'booking_reference', 'UNKNOWN')}")
            
            # Generate HTML content
            html_content = self._generate_html(booking)
            
            # Generate PDF using WeasyPrint with base_url
            import os
            base_url = f"file://{os.getcwd()}/"
            html_doc = HTML(string=html_content, base_url=base_url)
            css_styles = CSS(string=self._get_css_styles())
            
            self.logger.info(f"About to generate PDF bytes with WeasyPrint...")
            pdf_bytes = html_doc.write_pdf(stylesheets=[css_styles])
            
            self.logger.info("Generated tour voucher PDF bytes using WeasyPrint")
            return pdf_bytes
            
        except Exception as e:
            self.logger.error(f"Failed to generate tour voucher PDF bytes: {e}")
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            raise e

    def generate_tour_voucher_png(self, booking_id) -> str:
        """Generate tour voucher PNG using WeasyPrint and return filename"""
        try:
            # Get booking data from database
            from models import Booking
            booking = Booking.query.filter_by(id=booking_id).first()
            if not booking:
                raise ValueError(f"Booking with ID {booking_id} not found")
            
            # Generate PDF first
            pdf_bytes = self.generate_tour_voucher_bytes(booking_id)
            
            # Create filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            booking_ref = getattr(booking, 'booking_reference', 'UNKNOWN')
            filename = f"Tour_voucher_v2_{booking_ref}_{timestamp}.png"
            filepath = os.path.join(self.output_dir, filename)
            
            # Convert PDF to PNG using pdf2image
            from pdf2image import convert_from_bytes
            images = convert_from_bytes(pdf_bytes, dpi=150)
            
            if images:
                # Save the first page as PNG (or combine multiple pages if needed)
                images[0].save(filepath, 'PNG')
                self.logger.info(f"Generated tour voucher PNG: {filename}")
                return filepath
            else:
                raise Exception("Failed to convert PDF to PNG - no images generated")
                
        except Exception as e:
            self.logger.error(f"Failed to generate tour voucher PNG: {e}")
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            raise e

    def _generate_html(self, booking):
        """Generate HTML content for the tour voucher using existing template"""
        
        # Use Flask's render_template to load the existing template
        from flask import render_template
        from datetime import datetime
        
        # Prepare template variables
        template_vars = {
            'booking': booking,
            'generation_timestamp': datetime.now().strftime('%Y%m%d%H%M%S'),
            'quote_number': f"TV{booking.id:04d}" if booking.id else 'TV0001',
            'is_tour_voucher': True  # Flag to identify this as tour voucher
        }
        
        # Render the quote template (same as PNG version)
        html_content = render_template('pdf/quote_template_final_fixed.html', **template_vars)
        
        return html_content

    def _get_css_styles(self):
        """Generate CSS styles for the tour voucher"""
        return """
        @page {
            size: A4;
            margin: 2cm 1.5cm 2cm 1.5cm;
        }

        body {
            font-family: Arial, sans-serif;
            font-size: 12px;
            line-height: 1.4;
            color: #333;
            margin: 0;
            padding: 0;
        }

        /* Page 1 Header Styling */
        .page-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #4472C4;
            page-break-inside: avoid;
        }

        /* Inline Header Styling for Pages 2+ */
        .inline-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 20px;
            margin-top: 10px;
            padding-bottom: 15px;
            border-bottom: 2px solid #4472C4;
            page-break-inside: avoid;
        }

        .header-left {
            flex: 0 0 100px;
        }

        .header-logo {
            width: 80px;
            height: auto;
        }

        .logo-placeholder {
            width: 80px;
            height: 60px;
            border: 2px solid #4472C4;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            color: #4472C4;
        }

        .header-center {
            flex: 1;
            text-align: center;
            margin: 0 20px;
        }

        .company-name {
            font-size: 18px;
            font-weight: bold;
            color: #4472C4;
            margin: 0 0 8px 0;
        }

        .company-details {
            font-size: 10px;
            color: #666;
            margin: 2px 0;
        }

        .header-right {
            flex: 0 0 120px;
            text-align: right;
        }

        .quote-box {
            background-color: #4472C4;
            color: white;
            padding: 10px 15px;
            border-radius: 5px;
            font-weight: bold;
            font-size: 12px;
            text-align: center;
        }

        /* Booking Information */
        .booking-info {
            margin-bottom: 25px;
        }

        .booking-row {
            display: flex;
            margin-bottom: 8px;
        }

        .label {
            font-weight: bold;
            width: 150px;
            color: #4472C4;
        }

        .value {
            flex: 1;
        }

        /* Section Headers */
        h3 {
            color: #4472C4;
            font-size: 16px;
            border-bottom: 1px solid #4472C4;
            padding-bottom: 5px;
            margin: 20px 0 15px 0;
        }

        /* Guest Information */
        .guest-details p {
            margin: 8px 0;
        }

        /* Flight Information */
        .flight-details p {
            margin: 8px 0;
        }

        /* Service Table */
        .service-table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }

        .service-table th,
        .service-table td {
            border: 1px solid #ddd;
            padding: 10px;
            text-align: left;
        }

        .service-table th {
            background-color: #f8f9fa;
            font-weight: bold;
            color: #4472C4;
        }

        /* Terms and Conditions */
        .terms-section ul {
            margin: 15px 0;
            padding-left: 20px;
        }

        .terms-section li {
            margin: 8px 0;
        }

        /* Force Page Break */
        .force-page-break {
            page-break-before: always;
        }

        /* Voucher Image */
        .voucher-image {
            margin-top: 20px;
            text-align: center;
        }
        """
