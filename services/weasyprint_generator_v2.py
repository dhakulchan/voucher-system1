"""Modern WeasyPrint-based PDF generator with enhanced Thai font support.

This provides beautiful, responsive PDF layouts matching the original design
while properly supporting Thai Unicode characters.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, List, Any, Optional

import weasyprint
from weasyprint import HTML, CSS

from config import Config
from utils.logging_config import get_logger

logger = get_logger(__name__)


class ModernWeasyPrintGenerator:
    """Enhanced PDF generator using WeasyPrint with modern design and Thai font support."""
    
    def __init__(self):
        self.base_url = f"file://{os.path.abspath('.')}"
        logger.info("Modern WeasyPrint generator initialized")
    
    def generate_service_proposal(self, booking_data: Dict[str, Any], products: List[Dict], filename: str = None) -> str:
        """Generate beautiful service proposal PDF using WeasyPrint.
        
        Args:
            booking_data: Booking information dictionary
            products: List of product/service items
            filename: Optional custom filename
            
        Returns:
            str: Path to generated PDF file
        """
        logger.info(f"Generating modern service proposal for booking: {booking_data.get('booking_reference', 'Unknown')}")
        
        # Generate HTML content
        html_content = self._build_html_content(booking_data, products)
        
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            booking_ref = booking_data.get('booking_reference', 'UNK')
            filename = f"service_proposal_{booking_ref}_{timestamp}.pdf"
        
        # Ensure output directory exists
        output_dir = "static/generated"
        os.makedirs(output_dir, exist_ok=True)
        
        # Full output path
        output_path = os.path.join(output_dir, filename)
        
        try:
            # Generate PDF using WeasyPrint
            html_doc = HTML(string=html_content, base_url=self.base_url)
            html_doc.write_pdf(output_path)
            
            logger.info(f"✅ Modern WeasyPrint PDF generated: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"❌ Failed to generate PDF: {str(e)}")
            raise
    
    def generate_service_proposal_png(self, booking_data: Dict[str, Any], products: List[Dict], filename: str = None) -> str:
        """
        Generate Service Proposal as PNG image using WeasyPrint with modern Thai-supported design.
        
        Args:
            booking_data: Booking information dictionary
            products: List of product/service items
            filename: Optional custom filename
            
        Returns:
            str: Path to generated PNG file
        """
        logger.info(f"Generating modern service proposal PNG for booking: {booking_data.get('booking_reference', 'Unknown')}")
        
        # Generate HTML content using the same template as PDF
        from flask import render_template
        try:
            # Render using the same template file
            html_content = render_template('pdf/quote_template_final_fixed.html', 
                                         booking=type('obj', (object,), booking_data)(),
                                         products=products)
        except Exception as e:
            logger.error(f"Template rendering error: {e}")
            # Try with direct booking object if conversion failed
            try:
                html_content = render_template('pdf/quote_template_final_fixed.html', 
                                             booking=booking_data,
                                             products=products)
            except Exception as e2:
                logger.error(f"Direct booking rendering error: {e2}")
                raise Exception(f"Template rendering failed: {e}, {e2}")
        
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            booking_ref = booking_data.get('booking_reference', 'UNK')
            filename = f"service_proposal_{booking_ref}_{timestamp}.png"
        
        # Ensure output directory exists
        output_dir = "static/generated"
        os.makedirs(output_dir, exist_ok=True)
        
        # Full output path
        output_path = os.path.join(output_dir, filename)
        
        try:
            # Generate PDF first using WeasyPrint
            html_doc = HTML(string=html_content, base_url=self.base_url)
            
            # Add CSS for better PNG output
            css_content = """
            @page {
                size: A4;
                margin: 1cm;
            }
            body {
                font-family: 'Sarabun', 'Noto Sans Thai', 'TH Sarabun New', Arial, sans-serif;
            }
            """
            
            pdf_bytes = html_doc.write_pdf(stylesheets=[CSS(string=css_content)])
            
            # Convert PDF to PNG using pdf2image
            try:
                from pdf2image import convert_from_bytes
                from PIL import Image
                
                # Convert PDF to PNG with high DPI for quality
                pages = convert_from_bytes(pdf_bytes, dpi=300, fmt='PNG')
                
                if len(pages) == 1:
                    # Single page
                    pages[0].save(output_path, 'PNG', quality=95, optimize=True)
                else:
                    # Multiple pages - create a single long image
                    total_height = sum(page.height for page in pages)
                    max_width = max(page.width for page in pages)
                    
                    # Create combined image
                    combined_image = Image.new('RGB', (max_width, total_height), 'white')
                    
                    y_offset = 0
                    for page in pages:
                        combined_image.paste(page, (0, y_offset))
                        y_offset += page.height
                    
                    combined_image.save(output_path, 'PNG', quality=95, optimize=True)
                
                logger.info(f"✅ PNG generated successfully: {output_path}")
                return output_path
                
            except ImportError:
                logger.error("pdf2image not available. Install with: pip install pdf2image")
                # Fallback to PDF
                pdf_fallback_path = output_path.replace('.png', '_fallback.pdf')
                with open(pdf_fallback_path, 'wb') as f:
                    f.write(pdf_bytes)
                return pdf_fallback_path
            
        except Exception as e:
            logger.error(f"❌ Failed to generate PNG: {str(e)}")
            raise
    
    def _build_html_content(self, booking_data: Dict[str, Any], products: List[Dict]) -> str:
        """Build complete HTML content with modern styling."""
        
        # Extract booking data
        customer_name = booking_data.get('customer_name', 'N/A')
        customer_email = booking_data.get('customer_email', 'N/A')
        customer_phone = booking_data.get('customer_phone', 'N/A')
        customer_address = booking_data.get('customer_address', '')
        customer_nationality = booking_data.get('customer_nationality', '')
        booking_reference = booking_data.get('booking_reference', 'N/A')
        status = booking_data.get('status', 'N/A')
        adults = booking_data.get('adults', 0)
        children = booking_data.get('children', 0)
        infants = booking_data.get('infants', 0)
        party_name = booking_data.get('party_name', '')
        party_code = booking_data.get('party_code', '')
        description = booking_data.get('description', '')
        pickup_point = booking_data.get('pickup_point', '')
        destination = booking_data.get('destination', '')
        pickup_time = booking_data.get('pickup_time', '')
        vehicle_type = booking_data.get('vehicle_type', '')
        internal_note = booking_data.get('internal_note', '')
        flight_info = booking_data.get('flight_info', '')
        daily_services = booking_data.get('daily_services', '')
        admin_notes = booking_data.get('admin_notes', '')
        manager_memos = booking_data.get('manager_memos', '')
        total_amount = booking_data.get('total_amount', 0.0)
        currency = booking_data.get('currency', 'THB')
        time_limit = booking_data.get('time_limit', '')
        due_date = booking_data.get('due_date', '')
        created_at = booking_data.get('created_at', '')
        updated_at = booking_data.get('updated_at', '')
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Service Proposal - {booking_reference}</title>
            {self._get_modern_css_styles()}
        </head>
        <body>
            <div class="document">
                {self._build_modern_header()}
                
                <div class="main-content">
                    {self._build_modern_booking_summary(booking_reference, status, total_amount, currency)}
                    
                    {self._build_modern_customer_section(customer_name, customer_email, customer_phone, customer_address, customer_nationality)}
                    
                    {self._build_modern_booking_details(booking_reference, adults, children, infants, party_name, party_code, description)}
                    
                    {self._build_basic_itinerary_section(booking_data, products)}
                    {self._build_detailed_itinerary_section(internal_note, daily_services)}
                    
                    {self._build_modern_services_section(pickup_point, destination, pickup_time, vehicle_type, flight_info, daily_services)}
                    
                    {self._build_modern_products_section(products, total_amount, currency)}
                    
                    {self._build_modern_dates_section(time_limit, due_date, created_at, updated_at)}
                    
                    {self._build_modern_notes_section(admin_notes, manager_memos, internal_note)}
                    
                    {self._build_modern_terms_section()}
                </div>
                
                {self._build_modern_footer()}
            </div>
        </body>
        </html>
        """
        
        return html_content
    
    def _get_modern_css_styles(self) -> str:
        """Get modern CSS styles with enhanced Thai font support."""
        # Get absolute paths for fonts
        base_path = os.path.abspath('.')
        thai_regular = f"file://{base_path}/NotoSansThai-Regular.ttf"
        thai_bold = f"file://{base_path}/NotoSansThai-Bold.ttf"
        
        css_content = f"""
        <style>
            @font-face {{
                font-family: 'NotoSansThai';
                src: url('{thai_regular}') format('truetype');
                font-weight: normal;
                font-style: normal;
                unicode-range: U+0E00-0E7F;
            }}
            
            @font-face {{
                font-family: 'NotoSansThai';
                src: url('{thai_bold}') format('truetype');
                font-weight: bold;
                font-style: normal;
                unicode-range: U+0E00-0E7F;
            }}
            
            @font-face {{
                font-family: 'SystemFont';
                src: local('Helvetica Neue'), local('Helvetica'), local('Arial'), local('sans-serif');
                font-weight: normal;
                font-style: normal;
                unicode-range: U+0020-007E, U+00A0-00FF;
            }}
            
            /* Thai Text Specific */
            .thai-text {{
                font-family: 'NotoSansThai', sans-serif !important;
            }}
            
            /* English Text Specific */
            .english-text {{
                font-family: 'SystemFont', 'Helvetica Neue', Helvetica, Arial, sans-serif !important;
            }}
            
            /* Mixed Content */
            .mixed-text {{
                font-family: 'NotoSansThai', 'SystemFont', 'Helvetica Neue', Helvetica, Arial, sans-serif !important;
            }}
            
            @page {{
                size: A4;
                margin: 1.5cm;
            }}
            
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'SystemFont', 'Helvetica Neue', Helvetica, Arial, 'NotoSansThai', sans-serif;
                font-size: 11pt;
                line-height: 1.6;
                color: #2c3e50;
                background: white;
            }}
            
            .document {{
            }}
            
            .document {{
                width: 100%;
                background: white;
                padding: 0;
            }}
            
            /* Modern Header with Gradient */
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                margin-bottom: 30px;
                text-align: center;
                border-radius: 12px;
                box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
            }}
            
            .logo {{
                font-size: 32px;
                font-weight: bold;
                margin-bottom: 10px;
                text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
                letter-spacing: 1px;
            }}
            
            .company-subtitle {{
                font-size: 18px;
                opacity: 0.95;
                margin-bottom: 8px;
                font-weight: 500;
            }}
            
            .generation-date {{
                font-size: 13px;
                opacity: 0.85;
                font-style: italic;
            }}
            
            /* Enhanced Section Styling */
            .section {{
                margin-bottom: 35px;
                page-break-inside: avoid;
            }}
            
            .section-title {{
                font-size: 20px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 20px;
                padding-bottom: 12px;
                border-bottom: 3px solid #3498db;
                position: relative;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            
            .section-title::after {{
                content: '';
                position: absolute;
                bottom: -3px;
                left: 0;
                width: 60px;
                height: 3px;
                background: linear-gradient(135deg, #e74c3c 0%, #f39c12 100%);
            }}
            
            /* Customer Information Section - D.C.T.S Style */
            .customer-info-section {{
                display: block;
                margin: 0 0 15px 0;
                padding: 0;
            }}
            
            .customer-name-section {{
                margin-bottom: 8px;
                line-height: 1.4;
            }}
            
            .customer-label {{
                font-family: 'NotoSansThai', sans-serif;
                font-size: 12px;
                font-weight: 600;
                color: #333;
                display: inline;
            }}
            
            .customer-name {{
                font-size: 12px;
                font-weight: 600;
                color: #333;
                display: inline;
                margin-left: 5px;
            }}
            
            .customer-details {{
                margin-left: 20px;
            }}
            
            .detail-line {{
                margin-bottom: 4px;
                line-height: 1.3;
            }}
            
            .detail-label {{
                font-family: 'NotoSansThai', sans-serif;
                font-size: 11px;
                color: #555;
                display: inline;
            }}
            
            .detail-value {{
                font-size: 11px;
                color: #333;
                display: inline;
                margin-left: 5px;
            }}
            
            /* Booking Summary Styling */
            .booking-summary-card {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 30px;
                border-radius: 15px;
                color: white;
                margin-bottom: 20px;
            }}
            
            .summary-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
            }}
            
            .summary-item {{
                text-align: center;
            }}
            
            .summary-label {{
                font-size: 12px;
                text-transform: uppercase;
                letter-spacing: 1px;
                opacity: 0.8;
                margin-bottom: 8px;
            }}
            
            .summary-value {{
                font-size: 18px;
                font-weight: bold;
                color: white;
            }}
            
            /* Service Subsection Styling */
            .service-subsection {{
                margin-bottom: 25px;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 10px;
                border-left: 4px solid #3182ce;
            }}
            
            /* Basic Itinerary Section - D.C.T.S Style */
            .basic-itinerary-section {{
                display: block;
                margin: 15px 0;
                padding: 0;
            }}
            
            .basic-itinerary-title {{
                font-family: 'NotoSansThai', sans-serif;
                font-size: 12px;
                font-weight: 600;
                color: #333;
                margin-bottom: 8px;
            }}
            
            .basic-itinerary-details {{
                margin-left: 20px;
            }}
            
            .basic-itinerary-row {{
                margin-bottom: 4px;
                line-height: 1.3;
            }}
            
            .basic-itinerary-label {{
                font-family: 'NotoSansThai', sans-serif;
                font-size: 11px;
                color: #555;
                display: inline;
            }}
            
            .basic-itinerary-value {{
                font-size: 11px;
                color: #333;
                display: inline;
                margin-left: 5px;
            }}
            
            /* Itinerary Section Styling */
            .itinerary-card {{
                background: #ffffff;
                padding: 25px;
                border-radius: 12px;
                border: 1px solid #e2e8f0;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            }}
            
            .itinerary-item {{
                display: flex;
                align-items: flex-start;
                margin-bottom: 15px;
                padding: 12px;
                background: #f8fafc;
                border-radius: 8px;
                border-left: 3px solid #4299e1;
            }}
            
            .item-number {{
                color: #2b6cb0;
                font-weight: bold;
                margin-right: 10px;
                min-width: 20px;
                font-size: 14px;
            }}
            
            .item-text {{
                flex: 1;
                line-height: 1.5;
                font-size: 14px;
                color: #2d3748;
            }}
            
            /* Booking Details with Accent */
            .booking-card {{
                background: linear-gradient(135deg, #fff5f5 0%, #fed7d7 20%, #fff5f5 100%);
                padding: 25px;
                border-radius: 12px;
                border-left: 6px solid #e53e3e;
                box-shadow: 0 4px 12px rgba(229, 62, 62, 0.15);
            }}
            
            /* Modern Table Design */
            .products-table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
                background: white;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
            }}
            
            .products-table th {{
                background: linear-gradient(135deg, #4299e1 0%, #3182ce 100%);
                color: white;
                font-weight: 700;
                padding: 18px 15px;
                text-align: left;
                font-size: 13px;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            
            .products-table td {{
                padding: 18px 15px;
                border-bottom: 1px solid #e2e8f0;
                vertical-align: top;
                font-size: 14px;
            }}
            
            .products-table tr:nth-child(even) {{
                background-color: #f8fafc;
            }}
            
            .products-table tr:hover {{
                background-color: #edf2f7;
                transform: translateY(-1px);
                transition: all 0.2s ease;
            }}
            
            /* Enhanced Price Styling */
            .price {{
                font-weight: 700;
                color: #2d3748;
                text-align: right;
                font-size: 15px;
            }}
            
            .total-row {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
                color: white !important;
                font-weight: bold;
            }}
            
            .total-amount {{
                font-size: 20px;
                color: white !important;
                font-weight: bold;
            }}
            
            /* Premium Notes Section */
            .notes-card {{
                background: linear-gradient(135deg, #fef5e7 0%, #fed7aa 20%, #fef5e7 100%);
                padding: 30px;
                border-radius: 15px;
                border: 1px solid #f6ad55;
                margin-top: 30px;
                box-shadow: 0 6px 20px rgba(246, 173, 85, 0.2);
            }}
            
            .note-item {{
                margin-bottom: 20px;
                padding: 15px;
                background: rgba(255, 255, 255, 0.8);
                border-radius: 10px;
                border-left: 5px solid #ed8936;
                box-shadow: 0 3px 8px rgba(0, 0, 0, 0.05);
            }}
            
            .note-label {{
                font-weight: bold;
                color: #c05621;
                margin-bottom: 10px;
                font-size: 14px;
                text-transform: uppercase;
                letter-spacing: 0.6px;
            }}
            
            .note-content {{
                color: #2d3748;
                line-height: 1.7;
                font-size: 14px;
            }}
            
            /* Elegant Terms Section */
            .terms-card {{
                background: linear-gradient(135deg, #f0fff4 0%, #c6f6d5 20%, #f0fff4 100%);
                padding: 30px;
                border-radius: 15px;
                border: 1px solid #68d391;
                margin-top: 35px;
                box-shadow: 0 6px 20px rgba(104, 211, 145, 0.2);
            }}
            
            .terms-title {{
                font-size: 18px;
                font-weight: bold;
                color: #2f855a;
                margin-bottom: 20px;
                text-align: center;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            
            .terms-content {{
                color: #2d3748;
                font-size: 12px;
                line-height: 1.8;
            }}
            
            .terms-section {{
                margin-bottom: 20px;
                padding: 15px;
                background: rgba(255, 255, 255, 0.7);
                border-radius: 8px;
            }}
            
            .terms ol {{
                margin-left: 25px;
                margin-bottom: 15px;
            }}
            
            .terms li {{
                margin-bottom: 10px;
                line-height: 1.6;
            }}
            
            /* Stunning Footer */
            .footer {{
                margin-top: 50px;
                padding: 30px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                text-align: center;
                border-radius: 15px;
                font-size: 15px;
                box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
            }}
            
            .footer-message {{
                font-weight: 700;
                margin-bottom: 10px;
                font-size: 18px;
                text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.3);
            }}
            
            .footer-contact {{
                opacity: 0.9;
                font-size: 14px;
                font-style: italic;
            }}
            
            /* Typography Classes */
            .thai-text {{
                font-family: 'NotoSansThai', Arial, sans-serif;
                font-weight: normal;
            }}
            
            .english-text {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }}
            
            .mixed-text {{
                font-family: 'NotoSansThai', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }}
            
            /* Enhanced Highlight */
            .highlight {{
                background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
                padding: 6px 12px;
                border-radius: 8px;
                border: 1px solid #ffd93d;
                font-weight: 600;
                box-shadow: 0 2px 4px rgba(255, 217, 61, 0.3);
            }}
            
            /* Utility Classes */
            .text-center {{ text-align: center; }}
            .text-right {{ text-align: right; }}
            .text-bold {{ font-weight: bold; }}
            .text-muted {{ color: #6c757d; }}
            
            /* Print Optimizations */
            @media print {{
                body {{
                    -webkit-print-color-adjust: exact;
                    color-adjust: exact;
                }}
                
                .document {{
                    margin: 0;
                    padding: 10mm;
                }}
                
                .section {{
                    page-break-inside: avoid;
                }}
            }}
        </style>
        """
        
        return css_content
    
    def _build_modern_header(self) -> str:
        """Build document header matching D.C.T.S style."""
        return f"""
        <div class="header">
            <div style="display: flex; align-items: flex-start; margin-bottom: 20px;">
                <div style="flex: 0 0 120px; margin-right: 20px;">
                    <div style="width: 100px; height: 80px; background: linear-gradient(135deg, #3498db, #2980b9); border-radius: 10px; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 14px;">
                        D.C.T.S<br><span style="font-size: 10px;">Travel</span>
                    </div>
                </div>
                <div style="flex: 1;">
                    <h1 style="color: #2c3e50; margin: 0; font-size: 18px; font-weight: bold;">บริษัท ดี.ซี.ที.เอส ทราเวล แอนด์ ทัวร์ จำกัด</h1>
                    <p style="color: #34495e; margin: 5px 0; font-size: 14px; line-height: 1.4;">
                        เลขที่ ๑๒๙ อาคาร ร.ส.ยู ทาวเวอร์ ชั้น ๒๗ ถนน รัชดาภิเษก แขวง ดินแดง เขต ดินแดง<br>
                        กรุงเทพมหานคร ๑๐๔๐๐ โทรศัพท์ ๐-๒๖๔๑-๙๗๙๙ โทรสาร ๐-๒๖๔๑-๙๗๙๘<br>
                        อีเมล์ dctstravel@gmail.com<br>
                        ใบอนุญาตการประกอบธุรกิจนำเที่ยว เลขที่ ๑๑/๐๒๗๒๖ วันที่ออกใบอนุญาต
                    </p>
                </div>
            </div>
            <div style="text-align: center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px; border-radius: 10px; margin: 20px 0;">
                <h2 style="margin: 0; font-size: 16px;">ใบเสนอราคา / QUOTATION</h2>
                <p style="margin: 5px 0 0 0; font-size: 12px; opacity: 0.9;">Generated on {datetime.now().strftime("%d %B %Y")}</p>
            </div>
        </div>
        """
    
    def _build_modern_customer_section(self, name: str, email: str, phone: str, address: str = '', nationality: str = '') -> str:
        """Build customer information section matching D.C.T.S style."""
        # Detect if name contains Thai characters
        has_thai = any('\u0e00' <= c <= '\u0e7f' for c in name)
        name_class = "thai-text" if has_thai else "english-text"
        
        return f"""
        <div class="section">
            <div class="customer-info-section">
                <div class="customer-name-section">
                    <span class="customer-label">ชื่อลูกค้า :</span>
                    <span class="customer-name {name_class}">{name}</span>
                </div>
                <div class="customer-details">
                    <div class="detail-line">
                        <span class="detail-label">-อีเมล์ :</span>
                        <span class="detail-value english-text">{email}</span>
                    </div>
                    <div class="detail-line">
                        <span class="detail-label">-เบอร์ติดต่อ :</span>
                        <span class="detail-value english-text">{phone}</span>
                    </div>
                </div>
            </div>
        </div>
        """
    
    def _build_modern_booking_summary(self, reference: str, status: str, total_amount: float, currency: str) -> str:
        """Build modern booking summary section."""
        status_color = {
            'confirmed': '#10b981',
            'pending': '#f59e0b', 
            'cancelled': '#ef4444',
            'completed': '#8b5cf6'
        }.get(status.lower(), '#6b7280')
        
        return f"""
        <div class="section">
            <div class="section-title">Booking Summary</div>
            <div class="booking-summary-card">
                <div class="summary-grid">
                    <div class="summary-item">
                        <div class="summary-label">Booking Reference</div>
                        <div class="summary-value">{reference}</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-label">Status</div>
                        <div class="summary-value" style="color: {status_color}; font-weight: bold;">{status.upper()}</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-label">Total Amount</div>
                        <div class="summary-value" style="color: #10b981; font-weight: bold; font-size: 18px;">{total_amount:,.2f} {currency}</div>
                    </div>
                </div>
            </div>
        </div>
        """
    
    def _build_modern_booking_details(self, reference: str, adults: int, children: int, infants: int, party_name: str = '', party_code: str = '', description: str = '') -> str:
        """Build modern booking details card."""
        
        party_info = ""
        if party_name or party_code:
            party_info = f"""
                    <div class="info-item">
                        <div class="info-label">Party Information</div>
                        <div class="info-value">{party_name} ({party_code})</div>
                    </div>"""
        
        description_info = ""
        if description:
            has_thai = any('\u0e00' <= c <= '\u0e7f' for c in description)
            desc_class = "thai-text" if has_thai else "english-text"
            description_info = f"""
                    <div class="info-item">
                        <div class="info-label">Description</div>
                        <div class="info-value {desc_class}">{description}</div>
                    </div>"""
        
        return f"""
        <div class="section">
            <div class="section-title">Booking Details</div>
            <div class="booking-card">
                <div class="info-grid">
                    <div class="info-item">
                        <div class="info-label">Booking Reference</div>
                        <div class="info-value highlight english-text">{reference}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Guests</div>
                        <div class="info-value mixed-text">
                            Adult {adults}, Child {children}, Infant {infants}<br>
                            <span class="thai-text">(ผู้ใหญ่ {adults} ท่าน เด็ก {children} ท่าน ทารก {infants} ท่าน)</span>
                        </div>
                    </div>
                    {party_info}
                    {description_info}
                </div>
            </div>
        </div>
        """
    
    def _build_basic_itinerary_section(self, booking_data: Dict[str, Any], products: List[Dict]) -> str:
        """Build basic itinerary section matching D.C.T.S style."""
        tour_name = booking_data.get('tour_name', 'Tour Package')
        tour_date = booking_data.get('tour_date', booking_data.get('start_date', 'N/A'))
        pax = booking_data.get('pax', 1)
        adults = booking_data.get('adults', pax)
        children = booking_data.get('children', 0)
        infants = booking_data.get('infants', 0)
        price = booking_data.get('price', 0)
        
        # Detect if tour name contains Thai characters
        has_thai_tour = any('\u0e00' <= c <= '\u0e7f' for c in tour_name)
        tour_class = "thai-text" if has_thai_tour else "english-text"
        
        return f"""
        <div class="section">
            <div class="basic-itinerary-section">
                <div class="basic-itinerary-title">กำหนดการ :</div>
                <div class="basic-itinerary-details">
                    <div class="basic-itinerary-row">
                        <span class="basic-itinerary-label">-โปรแกรมทัวร์ :</span>
                        <span class="basic-itinerary-value {tour_class}">{tour_name}</span>
                    </div>
                    <div class="basic-itinerary-row">
                        <span class="basic-itinerary-label">-วันที่เดินทาง :</span>
                        <span class="basic-itinerary-value english-text">{tour_date}</span>
                    </div>
                    <div class="basic-itinerary-row">
                        <span class="basic-itinerary-label">-จำนวนผู้เดินทาง :</span>
                        <span class="basic-itinerary-value english-text">{pax} ท่าน (ผู้ใหญ่ {adults} ท่าน เด็ก {children} ท่าน ทารก {infants} ท่าน)</span>
                    </div>
                    <div class="basic-itinerary-row">
                        <span class="basic-itinerary-label">-ราคารวม :</span>
                        <span class="basic-itinerary-value english-text">{price:,.2f} บาท</span>
                    </div>
                </div>
            </div>
        </div>
        """

    def _build_detailed_itinerary_section(self, internal_note: str = '', daily_services: str = '') -> str:
        """Build detailed itinerary section matching D.C.T.S style."""
        # สร้าง itinerary แบบรายละเอียดตามภาพ
        itinerary_items = [
            "เวลาเคาะองค์นักในเวลาจราจริงเพื่อไปรับนักเราจะรองเอารายรอง",
            "ราคาและรายละเอียดการให้การเปลี่ยนแปลงไปไดนักโดยตี่เล่งพิการว่วงาล จนกว่าจะได้รับการยืนยัน",
            "กรุณาเปลี่ยนเหง่ครั้งเท่าเดียงราคาเบื้องต้นและข้อกำหนดบุคลากรใหม่ใหม่กับการต้วงรอง",
            "ใบเสนอราคานี้ยังไม่ได้ปิดในใบอนุญาตและเอกสารอื่นๆๆเป็นเหตุขายเป็นงาน",
            "การเปลี่ยนแปลงเงินชำรายดำเนิด ดั่วนิรมรุทดีงูเหหืราายดำเงินอะดอาจระ",
            "คำกำการเปลี่ยนแปลงสินค้าเชื่นต้องมีในรับรองของ่ายราง 72 ชั่วโมง ครอบครัวรึกได้",
            "ในกรณีรองของข่องมูลที่เก่ยวันขิน โรงเรม และบริการทะเวรำใครปลาข้องโฮทัลราชาในิกนังยาย",
            "คำกำการเปลี่ยนแปลงครุดาดาเร็ดฟังยคฟังของขิงองต่อขอ กอ้ 24 ชั่วโมง",
            "ในกรณีลูกขายยืนในบริกติดหั่อดำกาลมพยขะแถววำนกำรีรีแรุงในแรกรรค"
        ]
        
        # ถ้ามี daily_services หรือ internal_note ให้ใช้แทน
        if daily_services or internal_note:
            note_content = daily_services or internal_note
            # แปลง note เป็น list items
            if note_content:
                lines = note_content.split('\n')
                itinerary_items = [line.strip() for line in lines if line.strip()]
        
        items_html = ""
        for i, item in enumerate(itinerary_items, 1):
            has_thai = any('\u0e00' <= c <= '\u0e7f' for c in item)
            item_class = "thai-text" if has_thai else "english-text"
            items_html += f"""
                <div class="itinerary-item">
                    <span class="item-number">{i}.</span>
                    <span class="item-text {item_class}">{item}</span>
                </div>"""
        
        return f"""
        <div class="section">
            <div class="section-title">กำหนด / กติกาการเดินทาง</div>
            <div class="itinerary-card">
                {items_html}
                <div style="text-align: center; margin-top: 30px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                    <p style="margin: 0; color: #2c3e50; font-weight: bold;">บริษัท ดี.ซี.ที.เอส ทราเวล - ขอขอบคุณมา ณ โอกาสนี้</p>
                </div>
            </div>
        </div>
        """
    
    def _build_modern_services_section(self, pickup_point: str = '', destination: str = '', pickup_time: str = '', vehicle_type: str = '', flight_info: str = '', daily_services: str = '') -> str:
        """Build modern services information section."""
        has_service_info = any([pickup_point, destination, pickup_time, vehicle_type, flight_info, daily_services])
        
        if not has_service_info:
            return ""
        
        sections = []
        
        # Transportation Info
        if pickup_point or destination or pickup_time or vehicle_type:
            transport_info = f"""
            <div class="service-subsection">
                <h4 style="color: #3182ce; margin-bottom: 10px;">Transportation Details</h4>
                <div class="info-grid">"""
            
            if pickup_point:
                transport_info += f"""
                    <div class="info-item">
                        <span class="info-label">Pickup Point:</span>
                        <span class="info-value">{pickup_point}</span>
                    </div>"""
            
            if destination:
                transport_info += f"""
                    <div class="info-item">
                        <span class="info-label">Destination:</span>
                        <span class="info-value">{destination}</span>
                    </div>"""
                    
            if pickup_time:
                transport_info += f"""
                    <div class="info-item">
                        <span class="info-label">Pickup Time:</span>
                        <span class="info-value">{pickup_time}</span>
                    </div>"""
                    
            if vehicle_type:
                transport_info += f"""
                    <div class="info-item">
                        <span class="info-label">Vehicle Type:</span>
                        <span class="info-value">{vehicle_type}</span>
                    </div>"""
            
            transport_info += """
                </div>
            </div>"""
            sections.append(transport_info)
        
        # Flight Info
        if flight_info:
            has_thai = any('\u0e00' <= c <= '\u0e7f' for c in flight_info)
            flight_class = "thai-text" if has_thai else "english-text"
            flight_section = f"""
            <div class="service-subsection">
                <h4 style="color: #3182ce; margin-bottom: 10px;">Flight Information</h4>
                <div class="info-value {flight_class}" style="white-space: pre-wrap;">{flight_info}</div>
            </div>"""
            sections.append(flight_section)
        
        # Daily Services
        if daily_services:
            has_thai = any('\u0e00' <= c <= '\u0e7f' for c in daily_services)
            services_class = "thai-text" if has_thai else "english-text"
            services_section = f"""
            <div class="service-subsection">
                <h4 style="color: #3182ce; margin-bottom: 10px;">Daily Services</h4>
                <div class="info-value {services_class}" style="white-space: pre-wrap;">{daily_services}</div>
            </div>"""
            sections.append(services_section)
        
        if not sections:
            return ""
        
        return f"""
        <div class="section">
            <div class="section-title">Service Details</div>
            <div class="customer-card">
                {''.join(sections)}
            </div>
        </div>
        """
    
    def _build_modern_dates_section(self, time_limit: str = '', due_date: str = '', created_at: str = '', updated_at: str = '') -> str:
        """Build modern dates and timeline section."""
        has_dates = any([time_limit, due_date, created_at, updated_at])
        
        if not has_dates:
            return ""
        
        return f"""
        <div class="section">
            <div class="section-title">Important Dates</div>
            <div class="booking-card">
                <div class="info-grid">
                    {f'''<div class="info-item">
                        <div class="info-label">Time Limit</div>
                        <div class="info-value" style="color: #ef4444; font-weight: bold;">{time_limit}</div>
                    </div>''' if time_limit else ''}
                    {f'''<div class="info-item">
                        <div class="info-label">Due Date</div>
                        <div class="info-value">{due_date}</div>
                    </div>''' if due_date else ''}
                    {f'''<div class="info-item">
                        <div class="info-label">Created</div>
                        <div class="info-value">{created_at}</div>
                    </div>''' if created_at else ''}
                    {f'''<div class="info-item">
                        <div class="info-label">Last Updated</div>
                        <div class="info-value">{updated_at}</div>
                    </div>''' if updated_at else ''}
                </div>
            </div>
        </div>
        """
    
    def _build_modern_products_section(self, products: List[Dict], total_amount: float = 0.0, currency: str = 'THB') -> str:
        """Build modern products/services section with enhanced table."""
        if not products:
            return """
            <div class="section">
                <div class="section-title">Services & Products</div>
                <div class="customer-card">
                    <p class="mixed-text text-center" style="padding: 20px; font-size: 16px;">
                        Service details to be confirmed.<br>
                        <span class="thai-text">(รายละเอียดบริการจะแจ้งให้ทราบอีกครั้ง)</span>
                    </p>
                </div>
            </div>
            """
        
        # Calculate total
        total_amount = sum(float(product.get('total_price', 0)) for product in products)
        
        products_html = """
        <div class="section">
            <div class="section-title">Services & Products</div>
            <table class="products-table">
                <thead>
                    <tr>
                        <th>Description</th>
                        <th>Quantity</th>
                        <th>Unit Price</th>
                        <th>Total</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        # Add product rows
        for product in products:
            description = product.get('description', 'N/A')
            quantity = product.get('quantity', 0)
            unit_price = float(product.get('unit_price', 0))
            total_price = float(product.get('total_price', 0))
            
            # Detect Thai in description
            has_thai = any('\u0e00' <= c <= '\u0e7f' for c in description)
            desc_class = "mixed-text" if has_thai else "english-text"
            
            products_html += f"""
                    <tr>
                        <td class="{desc_class}">{description}</td>
                        <td class="text-center">{quantity}</td>
                        <td class="price">฿{unit_price:,.2f}</td>
                        <td class="price">฿{total_price:,.2f}</td>
                    </tr>
            """
        
        # Add total row
        display_total = total_amount if total_amount > 0 else sum(product.get('total_price', 0) for product in products)
        products_html += f"""
                    <tr class="total-row">
                        <td colspan="3" class="text-right text-bold">Total Amount (รวมทั้งหมด)</td>
                        <td class="total-amount">{currency} {display_total:,.2f}</td>
                    </tr>
                </tbody>
            </table>
        </div>
        """
        
        return products_html
    
    def _build_modern_notes_section(self, admin_notes: str, manager_memos: str, internal_note: str) -> str:
        """Build modern notes section with enhanced cards."""
        if not any([admin_notes, manager_memos, internal_note]):
            return ""
        
        notes_html = """
        <div class="section">
            <div class="section-title">Notes & Special Instructions</div>
            <div class="notes-card">
        """
        
        if internal_note:
            notes_html += f"""
                <div class="note-item">
                    <div class="note-label">Internal Note:</div>
                    <div class="note-content mixed-text">{internal_note}</div>
                </div>
            """
        
        if admin_notes:
            notes_html += f"""
                <div class="note-item">
                    <div class="note-label">Admin Notes:</div>
                    <div class="note-content mixed-text">{admin_notes}</div>
                </div>
            """
        
        if manager_memos:
            notes_html += f"""
                <div class="note-item">
                    <div class="note-label">Manager Memos:</div>
                    <div class="note-content mixed-text">{manager_memos}</div>
                </div>
            """
        
        notes_html += """
            </div>
        </div>
        """
        
        return notes_html
    
    def _build_modern_terms_section(self) -> str:
        """Build modern terms and conditions section."""
        return """
        <div class="terms-card">
            <div class="terms-title">Terms & Conditions | ข้อตกลงและเงื่อนไข</div>
            
            <div class="terms-content">
                <div class="terms-section">
                    <strong>English Terms:</strong>
                    <ol>
                        <li>This proposal is valid for 7 days from the date of issue.</li>
                        <li>Payment is required to confirm the booking.</li>
                        <li>Cancellation policy applies as per company terms.</li>
                        <li>All prices are in Thai Baht (THB) unless otherwise specified.</li>
                    </ol>
                </div>
                
                <div class="terms-section thai-text">
                    <strong>เงื่อนไขภาษาไทย:</strong>
                    <ol>
                        <li>ใบเสนอราคานี้มีอายุ 7 วันนับจากวันที่ออกใบเสนอราคา</li>
                        <li>ต้องชำระเงินเพื่อยืนยันการจอง</li>
                        <li>นีติกรรมการยกเลิกตามเงื่อนไขของบริษัท</li>
                        <li>ราคาทั้งหมดเป็นเงินบาทไทย (THB) เว้นแต่จะระบุไว้เป็นอย่างอื่น</li>
                    </ol>
                </div>
            </div>
        </div>
        """
    
    def _build_modern_footer(self) -> str:
        """Build modern footer with gradient styling."""
        return """
        <div class="footer">
            <div class="footer-message">
                Thank you for choosing our services! | ขอขอบคุณที่เลือกใช้บริการของเรา!
            </div>
            <div class="footer-contact">
                For inquiries, please contact us | สำหรับข้อสอบถาม กรุณาติดต่อเรา
            </div>
        </div>
        """
