"""WeasyPrint-based PDF generator with proper Thai font support.

This replaces ReportLab for better Unicode and Thai character rendering.
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


class WeasyPrintGenerator:
    """PDF generator using WeasyPrint for proper Thai font support."""
    
    def __init__(self):
        self.base_url = f"file://{os.path.abspath('.')}"
        logger.info("WeasyPrint generator initialized")
        
    def _build_terms_section(self) -> str:
        """Build modern terms and conditions section."""
        return """
        <div class="terms">
            <div class="terms-title">Terms & Conditions | ข้อตกลงและเงื่อนไข</div>
            
            <div class="terms-content">
                <div style="margin-bottom: 20px;">
                    <strong>English Terms:</strong>
                    <ol>
                        <li>This proposal is valid for 7 days from the date of issue.</li>
                        <li>Payment is required to confirm the booking.</li>
                        <li>Cancellation policy applies as per company terms.</li>
                        <li>All prices are in Thai Baht (THB) unless otherwise specified.</li>
                    </ol>
                </div>
                
                <div class="thai-text">
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
    
    def generate_service_proposal(self, booking_data: Dict[str, Any], products: List[Dict], filename: str = None) -> str:
        """Generate service proposal PDF using WeasyPrint.
        
        Args:
            booking_data: Booking information dictionary
            products: List of product/service items
            filename: Optional custom filename
            
        Returns:
            str: Path to generated PDF file
        """
        logger.info(f"Generating service proposal for booking: {booking_data.get('booking_reference', 'Unknown')}")
        
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
            # Convert HTML to PDF
            html = HTML(string=html_content, base_url=self.base_url)
            html.write_pdf(output_path)
            
            logger.info(f"✅ WeasyPrint PDF generated: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"❌ WeasyPrint PDF generation failed: {e}")
            raise
    
    def _build_html_content(self, booking_data: Dict[str, Any], products: List[Dict]) -> str:
        """Build complete HTML content for the service proposal."""
        
        # Extract customer information
        customer_name = booking_data.get('customer_name', 'N/A')
        customer_email = booking_data.get('customer_email', 'N/A')
        customer_phone = booking_data.get('customer_phone', 'N/A')
        booking_reference = booking_data.get('booking_reference', 'N/A')
        
        # Guest counts
        adults = booking_data.get('adults', 0)
        children = booking_data.get('children', 0)
        infants = booking_data.get('infants', 0)
        
        # Notes and memos
        admin_notes = booking_data.get('admin_notes', '')
        manager_memos = booking_data.get('manager_memos', '')
        internal_note = booking_data.get('internal_note', '')
        
        # Build HTML with proper Thai font support
        html_content = f"""
        <!DOCTYPE html>
        <html lang="th">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Service Proposal - {booking_reference}</title>
            {self._get_css_styles()}
        </head>
        <body>
            <div class="document">
                {self._build_header()}
                
                <div class="main-content">
                    {self._build_customer_section(customer_name, customer_email, customer_phone)}
                    
                    {self._build_booking_details(booking_reference, adults, children, infants)}
                    
                    {self._build_products_section(products)}
                    
                    {self._build_notes_section(admin_notes, manager_memos, internal_note)}
                    
                    {self._build_terms_section()}
                </div>
                
                {self._build_footer()}
            </div>
        </body>
        </html>
        """
        
        return html_content
    
    def _get_css_styles(self) -> str:
        """Get modern CSS styles with Thai font support matching original design."""
        # Get absolute paths for fonts
        base_path = os.path.abspath('.')
        thai_regular = f"file://{base_path}/static/fonts/NotoSansThai-Regular.ttf"
        thai_bold = f"file://{base_path}/static/fonts/NotoSansThai-Bold.ttf"
        
        css_content = f"""
        <style>
            @font-face {{
                font-family: 'NotoSansThai';
                src: url('{thai_regular}') format('truetype');
                font-weight: normal;
                font-style: normal;
            }}
            
            @font-face {{
                font-family: 'NotoSansThai';
                src: url('{thai_bold}') format('truetype');
                font-weight: bold;
                font-style: normal;
            }}
            
            @page {{
                size: A4;
                margin: 2cm;
            }}
            
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'NotoSansThai', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                font-size: 11pt;
                line-height: 1.5;
                color: #2c3e50;
                background: white;
            }}
            
            .document {{
                width: 100%;
                background: white;
                padding: 0;
            }}
            
            /* Modern Header Design */
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 25px;
                margin-bottom: 30px;
                text-align: center;
                border-radius: 8px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }}
            
            .logo {{
                font-size: 28px;
                font-weight: bold;
                margin-bottom: 8px;
                text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.3);
            }}
            
            .company-info {{
                font-size: 16px;
                opacity: 0.95;
                margin-bottom: 5px;
            }}
            
            .generation-date {{
                font-size: 12px;
                opacity: 0.8;
                font-style: italic;
            }}
            
            /* Section Styling */
            .section {{
                margin-bottom: 30px;
                page-break-inside: avoid;
            }}
            
            .section-title {{
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 20px;
                padding-bottom: 10px;
                border-bottom: 3px solid #3498db;
                position: relative;
            }}
            
            .section-title::after {{
                content: '';
                position: absolute;
                bottom: -3px;
                left: 0;
                width: 50px;
                height: 3px;
                background: #e74c3c;
            }}
            
            /* Customer Information Card */
            .customer-info {{
                background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                padding: 25px;
                border-radius: 12px;
                border: 1px solid #dee2e6;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
            }}
            
            .info-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 15px;
            }}
            
            .info-row {{
                margin-bottom: 12px;
            }}
            
            .info-label {{
                font-weight: 600;
                color: #495057;
                display: block;
                margin-bottom: 4px;
                font-size: 12px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            
            .info-value {{
                color: #2c3e50;
                font-size: 14px;
                font-weight: 500;
                padding: 8px 12px;
                background: white;
                border-radius: 6px;
                border: 1px solid #e9ecef;
            }}
            
            /* Booking Details Card */
            .booking-details {{
                background: linear-gradient(135deg, #fff5f5 0%, #fed7d7 20%, #fff5f5 100%);
                padding: 20px;
                border-radius: 10px;
                border-left: 5px solid #e53e3e;
            }}
            
            /* Modern Table Design */
            .products-table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
                background: white;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }}
            
            .products-table th {{
                background: linear-gradient(135deg, #4299e1 0%, #3182ce 100%);
                color: white;
                font-weight: 600;
                padding: 15px 12px;
                text-align: left;
                font-size: 12px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            
            .products-table td {{
                padding: 15px 12px;
                border-bottom: 1px solid #e2e8f0;
                vertical-align: top;
            }}
            
            .products-table tr:nth-child(even) {{
                background-color: #f8fafc;
            }}
            
            .products-table tr:hover {{
                background-color: #edf2f7;
            }}
            
            /* Price Styling */
            .price {{
                font-weight: 600;
                color: #2d3748;
                text-align: right;
            }}
            
            .total-row {{
                background: linear-gradient(135deg, #edf2f7 0%, #e2e8f0 100%) !important;
                font-weight: bold;
            }}
            
            .total-amount {{
                font-size: 18px;
                color: #1a202c;
                font-weight: bold;
            }}
            
            /* Notes Section */
            .notes-section {{
                background: linear-gradient(135deg, #fef5e7 0%, #fed7aa 20%, #fef5e7 100%);
                padding: 25px;
                border-radius: 12px;
                border: 1px solid #f6ad55;
                margin-top: 25px;
            }}
            
            .note-item {{
                margin-bottom: 15px;
                padding: 12px;
                background: rgba(255, 255, 255, 0.7);
                border-radius: 8px;
                border-left: 4px solid #ed8936;
            }}
            
            .note-label {{
                font-weight: bold;
                color: #c05621;
                margin-bottom: 8px;
                font-size: 13px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            
            .note-content {{
                color: #2d3748;
                line-height: 1.6;
            }}
            
            /* Terms and Conditions */
            .terms {{
                background: linear-gradient(135deg, #f0fff4 0%, #c6f6d5 20%, #f0fff4 100%);
                padding: 25px;
                border-radius: 12px;
                border: 1px solid #68d391;
                margin-top: 30px;
                font-size: 11px;
                line-height: 1.6;
            }}
            
            .terms-title {{
                font-size: 16px;
                font-weight: bold;
                color: #2f855a;
                margin-bottom: 15px;
                text-align: center;
            }}
            
            .terms-content {{
                color: #2d3748;
            }}
            
            .terms ol {{
                margin-left: 20px;
                margin-bottom: 15px;
            }}
            
            .terms li {{
                margin-bottom: 8px;
                line-height: 1.5;
            }}
            
            /* Footer */
            .footer {{
                margin-top: 40px;
                padding: 25px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                text-align: center;
                border-radius: 12px;
                font-size: 14px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }}
            
            .footer-message {{
                font-weight: 600;
                margin-bottom: 8px;
                font-size: 16px;
            }}
            
            .footer-contact {{
                opacity: 0.9;
                font-size: 13px;
            }}
            
            /* Enhanced Price Styling */
            .highlight {{
                background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
                padding: 4px 8px;
                border-radius: 6px;
                border: 1px solid #ffd93d;
            }}
            
            .price {{
                font-weight: bold;
                color: #27ae60;
                font-size: 14px;
            }}
            
            /* Typography */
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
            
            /* Utility Classes */
            .text-center {{ text-align: center; }}
            .text-right {{ text-align: right; }}
            .text-bold {{ font-weight: bold; }}
            .text-muted {{ color: #6c757d; }}
            
            /* Responsive adjustments for print */
            @media print {{
                .document {{
                    margin: 0;
                    padding: 15mm;
                }}
                
                .header {{
                    margin-bottom: 20px;
                }}
                
                .section {{
                    page-break-inside: avoid;
                }}
                
                body {{
                    -webkit-print-color-adjust: exact;
                    color-adjust: exact;
                }}
            }}
            }}
        </style>
        """
        
        return css_content
    
    def _build_header(self) -> str:
        """Build document header."""
        return """
        <div class="header">
            <div class="logo">🌟 Dhakul Chan Group Smart System V.202501</div>
            <div class="company-info">
                Service Proposal & Booking Confirmation<br>
                Generated on """ + datetime.now().strftime("%d %B %Y at %H:%M") + """
            </div>
        </div>
        """
    
    def _build_customer_section(self, name: str, email: str, phone: str) -> str:
        """Build customer information section with modern card design."""
        # Detect if name contains Thai characters
        has_thai = any('\u0e00' <= c <= '\u0e7f' for c in name)
        name_class = "thai-text" if has_thai else "english-text"
        
        return f"""
        <div class="section">
            <div class="section-title">Customer Information</div>
            <div class="customer-info">
                <div class="info-grid">
                    <div class="info-row">
                        <div class="info-label">Name:</div>
                        <div class="info-value {name_class}">{name}</div>
                    </div>
                    <div class="info-row">
                        <div class="info-label">Email:</div>
                        <div class="info-value english-text">{email}</div>
                    </div>
                    <div class="info-row">
                        <div class="info-label">Phone:</div>
                        <div class="info-value english-text">{phone}</div>
                    </div>
                </div>
            </div>
        </div>
        """
    
    def _build_booking_details(self, reference: str, adults: int, children: int, infants: int) -> str:
        """Build booking details section with modern card design."""
        return f"""
        <div class="section">
            <div class="section-title">Booking Details</div>
            <div class="booking-details">
                <div class="info-grid">
                    <div class="info-row">
                        <div class="info-label">Reference:</div>
                        <div class="info-value highlight english-text">{reference}</div>
                    </div>
                    <div class="info-row">
                        <div class="info-label">Guests:</div>
                        <div class="info-value mixed-text">
                            Adult {adults}, Child {children}, Infant {infants}<br>
                            <span class="thai-text">(ผู้ใหญ่ {adults} ท่าน เด็ก {children} ท่าน ทารก {infants} ท่าน)</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """
    
    def _build_products_section(self, products: List[Dict]) -> str:
        """Build products/services section."""
        if not products:
            return """
            <div class="section">
                <div class="section-title">Services</div>
                <p class="mixed-text">Service details to be confirmed. (รายละเอียดบริการจะแจ้งให้ทราบอีกครั้ง)</p>
            </div>
            """
        
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
        
        total_amount = 0
        for product in products:
            name = product.get('name', 'N/A')
            quantity = product.get('quantity', 1)
            price = product.get('price', 0)
            subtotal = quantity * price
            total_amount += subtotal
            
            products_html += f"""
                    <tr>
                        <td class="mixed-text">{name}</td>
                        <td>{quantity}</td>
                        <td class="price">฿{price:,.2f}</td>
                        <td class="price">฿{subtotal:,.2f}</td>
                    </tr>
            """
        
        products_html += f"""
                    <tr style="font-weight: bold; background: #f8f9fa;">
                        <td colspan="3">Total Amount (รวมทั้งหมด)</td>
                        <td class="price">฿{total_amount:,.2f}</td>
                    </tr>
                </tbody>
            </table>
        </div>
        """
        
        return products_html
    
    def _build_notes_section(self, admin_notes: str, manager_memos: str, internal_note: str) -> str:
        """Build notes and memos section."""
        if not any([admin_notes, manager_memos, internal_note]):
            return ""
        
        notes_html = """
        <div class="section">
            <div class="section-title">Notes & Special Instructions</div>
            <div class="notes-section">
        """
        
        if internal_note:
            notes_html += f"""
                <div class="note-item">
                    <div class="note-label">Internal Note:</div>
                    <div class="thai-text">{internal_note}</div>
                </div>
            """
        
        if admin_notes:
            notes_html += f"""
                <div class="note-item">
                    <div class="note-label">Admin Notes:</div>
                    <div class="mixed-text">{admin_notes}</div>
                </div>
            """
        
        if manager_memos:
            notes_html += f"""
                <div class="note-item">
                    <div class="note-label">Manager Memos:</div>
                    <div class="mixed-text">{manager_memos}</div>
                </div>
            """
        
        notes_html += """
            </div>
        </div>
        """
        
        return notes_html
    
    def _build_terms_section(self) -> str:
        """Build terms and conditions section."""
        return """
        <div class="terms">
            <strong>Terms & Conditions:</strong><br>
            1. This proposal is valid for 7 days from the date of issue.<br>
            2. Payment is required to confirm the booking.<br>
            3. Cancellation policy applies as per company terms.<br>
            4. All prices are in Thai Baht (THB) unless otherwise specified.<br><br>
            
            <span class="thai-text">
            <strong>ข้อตกลงและเงื่อนไข:</strong><br>
            1. ใบเสนอราคานี้มีอายุ 7 วันนับจากวันที่ออกใบเสนอราคา<br>
            2. ต้องชำระเงินเพื่อยืนยันการจอง<br>
            3. นীติกรรมการยกเลิกตามเงื่อนไขของบริษัท<br>
            4. ราคาทั้งหมดเป็นเงินบาทไทย (THB) เว้นแต่จะระบุไว้เป็นอย่างอื่น
            </span>
        </div>
        """
    
    def _build_footer(self) -> str:
        """Build document footer."""
        return """
        <div class="footer">
            <p>Thank you for choosing our services! | ขอขอบคุณที่เลือกใช้บริการของเรา!</p>
            <p>For inquiries, please contact us | สำหรับข้อสอบถาม กรุณาติดต่อเรา</p>
        </div>
        """
