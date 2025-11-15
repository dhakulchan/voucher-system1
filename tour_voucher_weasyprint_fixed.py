"""
Tour Voucher PDF Generator using WeasyP            html_doc.write_pdf(filepath, stylesheets=[css_styles])
            
            self.logger.info(f"Generated tour voucher PDF using WeasyPrint: {filename}")
            return filepath  # Return full path instead of just filename
Consistent with booking PDF approach for better Thai font support
"""

import os
import json
from datetime import datetime
from jinja2 import Template
from weasyprint import HTML, CSS
from utils.logging_config import get_logger
from config import Config


class TourVoucherWeasyPrintGenerator:
    """Generate Tour Voucher PDF using WeasyPrint for better Thai font support"""
    
    OUTPUT_DIR = "static/generated"
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.output_dir = self._ensure_dir(self.OUTPUT_DIR)
        
    def _ensure_dir(self, path: str) -> str:
        os.makedirs(path, exist_ok=True)
        return path
        
    def generate_tour_voucher(self, booking) -> str:
        """Generate tour voucher PDF using WeasyPrint and return filename"""
        try:
            self.logger.info(f"🎯 Starting WeasyPrint PDF generation for booking {getattr(booking, 'booking_reference', 'UNKNOWN')}")
            
            # Generate HTML content
            html_content = self._generate_html(booking)
            
            # Create filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"Tour_voucher_v2_{getattr(booking, 'booking_reference', 'UNKNOWN')}_{timestamp}.pdf"
            filepath = os.path.join(self.output_dir, filename)
            
            # Generate PDF using WeasyPrint with base_url
            base_url = f"file://{os.getcwd()}/"
            html_doc = HTML(string=html_content, base_url=base_url)
            css_styles = CSS(string=self._get_css_styles())
            
            self.logger.info(f"🔧 About to generate PDF with WeasyPrint...")
            html_doc.write_pdf(filepath, stylesheets=[css_styles])
            
            self.logger.info(f"✅ Generated tour voucher PDF using WeasyPrint: {filename}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Failed to generate tour voucher PDF: {e}")
            raise e
            
    def generate_tour_voucher_bytes(self, booking) -> bytes:
        """Generate tour voucher PDF and return bytes"""
        try:
            self.logger.info(f"🎯 Starting WeasyPrint PDF bytes generation for booking {getattr(booking, 'booking_reference', 'UNKNOWN')}")
            
            # Generate HTML content
            html_content = self._generate_html(booking)
            
            # Generate PDF using WeasyPrint with base_url
            import os
            base_url = f"file://{os.getcwd()}/"
            html_doc = HTML(string=html_content, base_url=base_url)
            css_styles = CSS(string=self._get_css_styles())
            
            self.logger.info(f"🔧 About to generate PDF bytes with WeasyPrint...")
            pdf_bytes = html_doc.write_pdf(stylesheets=[css_styles])
            
            self.logger.info("✅ Generated tour voucher PDF bytes using WeasyPrint")
            return pdf_bytes
            
        except Exception as e:
            self.logger.error(f"❌ Failed to generate tour voucher PDF bytes: {e}")
            import traceback
            self.logger.error(f"🔧 Full traceback: {traceback.format_exc()}")
            raise e
    
    def generate_tour_voucher_png(self, booking) -> str:
        """Generate tour voucher PNG using WeasyPrint and return filename"""
        try:
            # Generate PDF first
            pdf_bytes = self.generate_tour_voucher_bytes(booking)
            
            # Create filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"Tour_voucher_v2_{getattr(booking, 'booking_reference', 'UNKNOWN')}_{timestamp}.png"
            filepath = os.path.join(self.output_dir, filename)
            
            # Convert PDF to PNG using external tool (requires pdf2image)
            try:
                from pdf2image import convert_from_bytes
                images = convert_from_bytes(pdf_bytes, first_page=1, last_page=1, dpi=200)
                if images:
                    images[0].save(filepath, 'PNG')
                    self.logger.info(f"Generated tour voucher PNG using WeasyPrint + pdf2image: {filename}")
                    return filename
                else:
                    self.logger.error("No images generated from PDF")
                    return None
            except ImportError as e:
                self.logger.error(f"pdf2image not available for PNG conversion: {e}")
                return None
            except Exception as e:
                self.logger.error(f"Error converting PDF to PNG: {e}")
                return None
            
        except Exception as e:
            self.logger.error(f"Failed to generate tour voucher PNG: {e}")
            # Return None if PNG generation fails
            return None
    
    def _generate_html(self, booking) -> str:
        """Generate HTML content for tour voucher"""
        
        # Get guest information from guest_list field
        guest_names = []
        
        # Try to get from guest_list JSON field first
        if hasattr(booking, 'guest_list') and booking.guest_list:
            try:
                guest_list_data = json.loads(booking.guest_list) if isinstance(booking.guest_list, str) else booking.guest_list
                if isinstance(guest_list_data, list):
                    for guest in guest_list_data:
                        if isinstance(guest, dict) and 'name' in guest:
                            guest_names.append(guest['name'])
                        elif isinstance(guest, str):
                            guest_names.append(guest)
            except (json.JSONDecodeError, TypeError) as e:
                self.logger.warning(f"Failed to parse guest_list JSON: {e}")
        
        # Fallback to guests relationship if guest_list is empty
        if not guest_names and hasattr(booking, 'guests') and booking.guests:
            for guest in booking.guests:
                if hasattr(guest, 'name') and guest.name:
                    guest_names.append(guest.name)
        
        # Final fallback to customer if no guests found
        if not guest_names:
            customer = getattr(booking, 'customer', None)
            if customer and hasattr(customer, 'name'):
                guest_names.append(customer.name)
        
        # Format guest names with line breaks for better readability
        if guest_names:
            if len(guest_names) == 1:
                # Single guest - keep simple format
                guest_names_str = guest_names[0]
            else:
                # Multiple guests - format with line breaks and numbering for clarity
                formatted_names = []
                for i, name in enumerate(guest_names, 1):
                    formatted_names.append(f"{i}. {name}")
                guest_names_str = '\n'.join(formatted_names)
        else:
            guest_names_str = 'TBD'
        
        # Get voucher rows data
        voucher_rows = []
        if hasattr(booking, 'get_voucher_rows'):
            voucher_rows = booking.get_voucher_rows()
        
        # Get current timestamp for footer and date formatting
        current_datetime = datetime.now()
        current_time = current_datetime.strftime('%d/%m/%Y %H:%M')
        
        # Get customer name for guest signature
        customer_name = 'Guest'
        if hasattr(booking, 'customer') and booking.customer:
            customer_name = booking.customer.name
        elif hasattr(booking, 'party_name') and booking.party_name:
            customer_name = booking.party_name
        
        # Company2 information
        company_name = Config.COMPANY_NAME2
        company_address = Config.COMPANY_ADDRESS2
        company_phone = Config.COMPANY_PHONE2
        company_mobile = Config.COMPANY_MOBILE2
        company_email = Config.COMPANY_EMAIL2
        company_website = Config.COMPANY_WEBSITE2
        
        # Logo path
        logo_path = os.path.abspath('dcts-logo-vou.png')
        logo_exists = os.path.exists(logo_path)
        
        # Prepare voucher image path (legacy single image)
        voucher_image_full_path = None
        if booking.voucher_image_path:
            # Clean path: remove query parameters and ensure static/ prefix
            clean_path = booking.voucher_image_path.split('?')[0]
            if not clean_path.startswith('static/'):
                clean_path = f"static/{clean_path}"
            
            voucher_image_full_path = os.path.abspath(clean_path)
        
        # Prepare voucher images (multi-image system)
        voucher_images_full_paths = []
        voucher_images = booking.get_voucher_images()
        for img_data in voucher_images:
            clean_path = None
            
            # Try to get path from 'path' key first
            if 'path' in img_data and img_data['path']:
                clean_path = img_data['path'].split('?')[0]
            # If no path, try to extract from URL
            elif 'url' in img_data and img_data['url']:
                url = img_data['url']
                # Extract path from URL like "http://localhost:5001/static/uploads/..."
                if '/static/' in url:
                    clean_path = url.split('/static/', 1)[1]
                    clean_path = 'static/' + clean_path.split('?')[0]  # Remove query params
            
            if clean_path:
                if not clean_path.startswith('static/'):
                    clean_path = f"static/{clean_path}"
                full_path = os.path.abspath(clean_path)
                voucher_images_full_paths.append({
                    'id': img_data.get('id', ''),
                    'full_path': full_path,
                    'url': img_data.get('url', ''),
                    'filename': img_data.get('filename', ''),
                    'path': clean_path,
                    'title': img_data.get('title', '')
                })
                
                # Update booking path for template use (use first image)
                if not hasattr(booking, '_temp_voucher_image_path') or not booking._temp_voucher_image_path:
                    booking._temp_voucher_image_path = clean_path
        
        html_template = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Tour Voucher - {{ booking.booking_reference }}</title>
    <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700&display=swap" rel="stylesheet">
</head>
<body>
    <!-- Page Header for all pages (running header) -->
    <div class="page-header">
        <div class="company-info">
            <h1 class="company-name">{{ company_name }}</h1>
            <p class="company-details">{{ company_address }}</p>
            <p class="company-details">Tel: {{ company_phone }} | Mobile: {{ company_mobile }} | Email: {{ company_email }} | Website: {{ company_website }}</p>
        </div>
        {% if logo_exists %}
        <div class="logo-section">
            <img src="file://{{ logo_path }}" alt="Company Logo" class="company-logo">
        </div>
        {% endif %}
    </div>

    <!-- Title -->
    <div class="title-section">
        <h2 class="voucher-title">TOUR VOUCHER / SERVICE ORDER</h2>
    </div>

    <!-- Reference Information -->
    <div class="reference-section">
        <div class="ref-line-1">
            <span class="ref-left"><strong>Invoice Number:</strong> {{ booking.invoice_number or '0388594' }}</span>
            <span class="ref-right"><strong>Booking Reference:</strong> {{ booking.booking_reference }} | <strong>Total Pax:</strong> {{ booking.total_pax or 'TBD' }}</span>
        </div>
        <div class="ref-line-2">
            <span class="ref-left"><strong>Quote Number:</strong> {{ booking.quote_number or 'TBD' }}</span>
            <span class="ref-right"><strong>Party Name:</strong> {{ booking.party_name or 'TBD' }}</span>
        </div>
        <div class="ref-line-3">
            <span class="ref-left"><strong>Arrival Date:</strong> {{ booking.arrival_date.strftime('%d/%m/%Y') if booking.arrival_date else 'TBD' }}</span>
            <span class="ref-right"><strong>Departure Date:</strong> {{ booking.departure_date.strftime('%d/%m/%Y') if booking.departure_date else 'TBD' }}</span>
        </div>
    </div>

    <!-- Guest Information -->
    <div class="guest-section">
        <p><strong>Guest Name(s):</strong></p>
        <div class="guest-names">{{ guest_names_str }}</div>
    </div>

    <!-- Service Table -->
    <div class="service-section">
        <h3>Hotel / Accommodation | Transfer | Others | Flight Detail</h3>
        <table class="service-table">
            <thead>
                <tr>
                    <th>No.</th>
                    <th>Arrival</th>
                    <th>Departure</th>
                    <th>Service By / Supplier</th>
                    <th>Type/Class/Paxs/Pieces</th>
                </tr>
            </thead>
            <tbody>
                {% if voucher_rows %}
                    {% for row in voucher_rows %}
                    <tr>
                        <td>{{ loop.index }}</td>
                        <td>{{ row.get('arrival', '') }}</td>
                        <td>{{ row.get('departure', '') }}</td>
                        <td>{{ row.get('service_by', '') }}</td>
                        <td>{{ row.get('type', '') }}</td>
                    </tr>
                    {% endfor %}
                {% else %}
                    <tr>
                        <td>1</td>
                        <td>DD/MM/YYYY</td>
                        <td>DD/MM/YYYY</td>
                        <td>Hotel/Accommodation/Transfer</td>
                        <td>Service Provider</td>
                    </tr>
                    <tr>
                        <td>2</td>
                        <td>DD/MM/YYYY</td>
                        <td>DD/MM/YYYY</td>
                        <td>Hotel/Accommodation/Transfer</td>
                        <td>Service Provider</td>
                    </tr>
                    <tr>
                        <td>3</td>
                        <td>DD/MM/YYYY</td>
                        <td>DD/MM/YYYY</td>
                        <td>Hotel/Accommodation/Transfer</td>
                        <td>Service Provider</td>
                    </tr>
                {% endif %}
            </tbody>
        </table>
    </div>

    <!-- Voucher Images (Multi-image support) -->
    {% if voucher_images_full_paths %}
    <div class="voucher-image-section">
        {% for image in voucher_images_full_paths %}
        <div class="voucher-image-item">
            {% if image.title %}
            <h5 class="image-title">{{ image.title }}</h5>
            {% endif %}
            <img src="file://{{ image.full_path }}" alt="Voucher Image {{ loop.index }}" class="voucher-image">
        </div>
        {% endfor %}
    </div>
    {% elif voucher_image_full_path %}
    <div class="voucher-image-section">
        <div class="voucher-image-item">
            <img src="file://{{ voucher_image_full_path }}" alt="Voucher Image" class="voucher-image">
        </div>
    </div>
    {% endif %}

    <!-- Flight Information -->
    {% if booking.flight_info %}
    <div class="flight-section">
        <h3>Flight Information</h3>
        <div class="flight-content">{{ booking.flight_info | replace('\n', '<br>') | safe }}</div>
    </div>
    {% endif %}

    <!-- Service Detail / Itinerary -->
    <div class="service-detail-section">
        <h3>Service Detail / Itinerary</h3>
        {% if booking.description %}
        <div class="service-description">{{ booking.description | replace('\n', '<br>') | safe }}</div>
        {% else %}
        <p>Service details and itinerary will be provided upon confirmation.</p>
        {% endif %}
    </div>

    <!-- Terms and Conditions -->
    <div class="terms-section">
        <h3>Terms and Conditions</h3>
        <ul>
            <li>This voucher is valid only for the dates and services mentioned above.</li>
            <li>Please present this voucher at the time of service.</li>
            <li>Any changes or cancellations must be made 24 hours in advance.</li>
            <li>The company reserves the right to change services due to circumstances beyond our control.</li>
        </ul>
    </div>

    <!-- Signatures -->
    <div class="signature-section">
        <div class="signature-box">
            <p><strong>Authorized Signature</strong></p>
            <div class="signature-line"></div>
            <div class="signature-details">
                <p class="signature-name">William / Tony (Operation Section)</p>
                <p class="signature-date">Date: {{ current_datetime.strftime('%d/%m/%Y') }} (DD/MM/YYYY)</p>
            </div>
        </div>
        <div class="signature-box">
            <p><strong>Guest Acknowledged</strong></p>
            <div class="signature-line"></div>
            <p>Khun. {{ customer_name }}</p>
        </div>
    </div>

</body>
</html>
        '''
        
        template = Template(html_template)
        return template.render(
            booking=booking,
            guest_names_str=guest_names_str,
            voucher_rows=voucher_rows,
            current_time=current_time,
            current_datetime=current_datetime,
            customer_name=customer_name,
            company_name=company_name,
            company_address=company_address,
            company_phone=company_phone,
            company_mobile=company_mobile,
            company_email=company_email,
            company_website=company_website,
            logo_path=logo_path,
            logo_exists=logo_exists,
            voucher_image_full_path=voucher_image_full_path,
            voucher_images_full_paths=voucher_images_full_paths
        )
    
    def _get_css_styles(self) -> str:
        """Get CSS styles for tour voucher"""
        return '''
        @page {
            size: A4;
            margin: 2.5cm 0.8cm 0.8cm 0.8cm;
            @top-center {
                content: element(page-header);
            }
            @bottom-center {
                content: "Dhakul Chan Nice Holidays Group - System DCTS V1.0 | Page " counter(page) " of " counter(pages);
                font-family: 'Sarabun', sans-serif;
                font-size: 10px;
                margin-bottom: 0.8cm;
            }
        }
        
        /* Hide page-header on first page */
        @page :first .page-header {
            display: none;
        }
        
        body {
            font-family: 'Sarabun', sans-serif;
            margin: 0;
            padding: 0;
        }
        
        /* Unified header styles for both main header and running header */
        /* Header styling */
        .header {
            height: 80px; /* Fixed height for all headers */
            margin-bottom: 10px;
            border-bottom: 2px solid #333;
            padding-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            width: 100%;
        }
        
        /* Running header for all pages */
        .page-header {
            position: running(page-header);
            background: white;
            padding: 10px;
            margin: 0;
            box-sizing: border-box;
            width: 100%;
            display: flex;
            align-items: flex-start;
            height: 80px;
            border-bottom: 2px solid #333;
        }
        
        /* Company info section */
        .page-header .company-info {
            flex: 1;
            height: 80px;
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
        }
        
        /* Logo section */
        .page-header .logo-section {
            flex: 0 0 auto;
            margin-left: 20px;
            height: 80px;
            display: flex;
            align-items: flex-start;
        }
        
        /* Company logo */
        .page-header .company-logo {
            width: 92px; /* Fixed width for consistency */
            height: 69px; /* Fixed height for consistency */
            object-fit: contain;
        }
        
        /* Company name */
        .page-header .company-name {
            font-size: 16px; /* Consistent font size */
            font-weight: 700;
            margin: 0 0 8px 0;
            color: #000;
            line-height: 1.2;
        }
        
        /* Company details */
        .page-header .company-details {
            margin: 2px 0;
            font-size: 11px; /* Consistent font size */
            line-height: 1.3;
        }
        
        .company-logo {
            width: 92px; /* Fixed width for consistency */
            height: 69px; /* Fixed height for consistency */
            object-fit: contain;
        }
        
        body {
            font-family: 'Sarabun', sans-serif;
            font-size: 12px;
            line-height: 1.4;
            color: #333;
            margin: 0;
            padding: 0;
        }
        
        .title-section {
            text-align: center;
            margin: 20px 0;
        }
        
        .voucher-title {
            font-size: 20px;
            font-weight: 700;
            margin: 0;
            text-decoration: underline;
        }
        
        .reference-section,
        .guest-section,
        .flight-section,
        .terms-section,
        .service-detail-section {
            margin: 15px 0;
        }
        
        .ref-line-1,
        .ref-line-2,
        .ref-line-3 {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin: 8px 0;
        }
        
        .ref-left {
            flex: 0 0 auto;
        }
        
        .ref-right {
            flex: 0 0 auto;
            text-align: right;
        }
        
        .guest-section p,
        .flight-section p {
            margin: 5px 0;
            white-space: pre-wrap;
            word-wrap: break-word;
            line-height: 1.5;
        }
        
        .guest-section p {
            max-width: 100%;
            overflow-wrap: break-word;
            margin: 5px 0;
        }
        
        .guest-names {
            white-space: pre-line;
            line-height: 1.6;
            margin: 8px 0 8px 20px;
            font-size: 12px;
        }
        
        .flight-content {
            margin: 5px 0;
            line-height: 1.6;
        }
        
        .service-detail-section h3 {
            background-color: #70AD47;
            color: white;
            padding: 8px;
            margin: 0 0 10px 0;
            font-size: 14px;
            font-weight: 600;
        }
        
        .voucher-image-section {
            margin: 10px 0 0 0; /* Reduced top margin, no bottom margin */
            text-align: center;
        }
        
        .voucher-image-item {
            margin: 10px auto; /* Reduced margin between images */
            text-align: center;
            display: block;
        }
        
        .image-title {
            font-size: 14px;
            font-weight: bold;
            color: #333;
            margin-bottom: 8px; /* Reduced margin */
            margin-top: 0;
            text-align: center;
        }
        
        .voucher-image {
            max-width: 90%;
            max-height: 360px;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 5px;
            display: block;
            margin: 0 auto;
        }
        
        .service-description,
        .daily-services {
            margin: 10px 0;
            line-height: 1.6;
        }
        
        .service-section {
            margin: 20px 0;
        }
        
        .service-section h3 {
            background-color: #4472C4;
            color: white;
            padding: 8px;
            margin: 0 0 10px 0;
            font-size: 14px;
            font-weight: 600;
        }
        
        .service-table {
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
        }
        
        .service-table th,
        .service-table td {
            border: 1px solid #333;
            padding: 6px;
            text-align: left;
            vertical-align: top;
        }
        
        .service-table th {
            background-color: #D9D9D9;
            font-weight: 600;
            text-align: center;
            font-size: 11px;
        }
        
        .service-table td {
            font-size: 10px;
        }
        
        .service-table th:nth-child(1),
        .service-table td:nth-child(1) {
            width: 8%;
            text-align: center;
        }
        
        .service-table th:nth-child(2),
        .service-table td:nth-child(2) {
            width: 18%;
        }
        
        .service-table th:nth-child(3),
        .service-table td:nth-child(3) {
            width: 18%;
        }
        
        .service-table th:nth-child(4),
        .service-table td:nth-child(4) {
            width: 36%;
        }
        
        .service-table th:nth-child(5),
        .service-table td:nth-child(5) {
            width: 20%;
        }
        
        .terms-section h3 {
            font-size: 14px;
            font-weight: 600;
            margin: 10px 0 8px 0;
        }
        
        .terms-section ul {
            margin: 5px 0;
            padding-left: 20px;
        }
        
        .terms-section li {
            margin: 3px 0;
            font-size: 11px;
        }
        
        .signature-section {
            display: flex;
            justify-content: space-between;
            margin: 30px 0 20px 0;
        }
        
        .signature-box {
            width: 45%;
            text-align: center;
        }
        
        .signature-line {
            border-bottom: 1px solid #333;
            margin: 30px 0 10px 0;
            height: 1px;
        }
        
        .signature-details {
            margin-top: 0;
        }
        
        .signature-name {
            margin: 0 0 3px 0;
            font-weight: normal;
        }
        
        .signature-date {
            font-size: 11px;
            margin: 0;
            color: #666;
        }
        
        /* Thai text support */
        * {
            font-family: 'Sarabun', sans-serif !important;
        }
        '''
