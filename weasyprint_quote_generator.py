#!/usr/bin/env python3
"""
WeasyPrint Quote Generator for Voucher System
Generates professional quotes using WeasyPrint with HTML templates
"""

import os
import sys
from datetime import datetime, timedelta
from flask import current_app
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

class WeasyPrintQuoteGenerator:
    def __init__(self):
        self.font_config = FontConfiguration()
        self.ensure_directories()
    
    def ensure_directories(self):
        """Ensure required directories exist"""
        dirs = [
            'static/generated',
            'static/generated/quotes',
            'templates/pdf'
        ]
        
        for dir_path in dirs:
            os.makedirs(dir_path, exist_ok=True)
    
    def generate_quote_pdf(self, booking):
        """Generate quote PDF using WeasyPrint with HTML template"""
        try:
            # Generate HTML content
            html_content = self._generate_quote_html(booking)
            
            # Create WeasyPrint HTML object
            html_doc = HTML(string=html_content, base_url='.')
            
            # Generate PDF
            filename = f"quote_{booking.booking_reference}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            pdf_path = os.path.join('static/generated/quotes', filename)
            
            # Custom CSS for quote styling
            css_content = self._get_quote_css()
            css = CSS(string=css_content, font_config=self.font_config)
            
            # Generate PDF with custom styling
            html_doc.write_pdf(pdf_path, stylesheets=[css], font_config=self.font_config)
            
            if hasattr(current_app, 'logger'):
                current_app.logger.info(f"✅ Quote PDF generated: {pdf_path}")
            else:
                print(f"✅ Quote PDF generated: {pdf_path}")
            return filename
            
        except Exception as e:
            if hasattr(current_app, 'logger'):
                current_app.logger.error(f"❌ Error generating quote PDF: {str(e)}")
            else:
                print(f"❌ Error generating quote PDF: {str(e)}")
            raise
    
    def _generate_quote_html(self, booking):
        """Generate HTML content for quote"""
        # Calculate totals
        total_amount = 0
        services = []
        
        # Process booking products/services
        if hasattr(booking, 'products') and booking.products:
            for product in booking.products:
                if hasattr(product, 'name'):
                    name = product.name
                    price = getattr(product, 'price', 0) or 0
                    description = getattr(product, 'description', '') or ''
                elif isinstance(product, dict):
                    name = product.get('name', '')
                    price = product.get('price', 0)
                    description = product.get('description', '')
                else:
                    name = str(product)
                    price = 0
                    description = ''
                
                services.append({
                    'name': name,
                    'description': description,
                    'price': price,
                    'quantity': 1
                })
                total_amount += price
        
        # If no products, create a generic service entry
        if not services:
            services.append({
                'name': 'Tour Package',
                'description': 'Complete tour package as discussed',
                'price': 0,
                'quantity': 1
            })
        
        # Get customer info
        customer_name = booking.customer.full_name if booking.customer else 'N/A'
        customer_email = booking.customer.email if booking.customer else ''
        customer_phone = booking.customer.phone if booking.customer else ''
        
        # Generate travel dates
        travel_dates = 'TBD'
        if hasattr(booking, 'traveling_period_start') and booking.traveling_period_start:
            start_date = booking.traveling_period_start.strftime('%d/%m/%Y')
            if hasattr(booking, 'traveling_period_end') and booking.traveling_period_end:
                end_date = booking.traveling_period_end.strftime('%d/%m/%Y')
                travel_dates = f"{start_date} - {end_date}"
            else:
                travel_dates = start_date
        
        # Generate HTML template
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Quote - {booking.booking_reference}</title>
        </head>
        <body>
            <div class="quote-container">
                <!-- Header -->
                <div class="header">
                    <div class="logo-section">
                        <h1>DHAKUL CHAN TRAVEL SERVICE</h1>
                        <p class="company-tagline">Your Trusted Travel Partner</p>
                        <p class="company-details">
                            710, 716, 704, 706 Prachautid Road, Samsennok, Huai Kwang, Bangkok 10310<br>
                            Tel: +662 2744216 | Email: support@dhakulchan.com<br>
                            TAT License: 11/03589
                        </p>
                    </div>
                    <div class="quote-info">
                        <h2>QUOTATION</h2>
                        <p><strong>Quote No:</strong> {booking.booking_reference}</p>
                        <p><strong>Date:</strong> {datetime.now().strftime('%d/%m/%Y')}</p>
                        <p><strong>Valid Until:</strong> {(datetime.now() + timedelta(days=30)).strftime('%d/%m/%Y')}</p>
                    </div>
                </div>
                
                <!-- Customer Information -->
                <div class="customer-section">
                    <h3>Customer Information</h3>
                    <div class="customer-details">
                        <p><strong>Name:</strong> {customer_name}</p>
                        <p><strong>Email:</strong> {customer_email}</p>
                        <p><strong>Phone:</strong> {customer_phone}</p>
                        <p><strong>Travel Dates:</strong> {travel_dates}</p>
                        <p><strong>Passengers:</strong> {booking.adults or 0} Adults, {booking.children or 0} Children, {booking.infants or 0} Infants</p>
                    </div>
                </div>
                
                <!-- Services Table -->
                <div class="services-section">
                    <h3>Proposed Services</h3>
                    <table class="services-table">
                        <thead>
                            <tr>
                                <th>Service</th>
                                <th>Description</th>
                                <th>Quantity</th>
                                <th>Price (THB)</th>
                            </tr>
                        </thead>
                        <tbody>
        """
        
        # Add services to HTML
        for service in services:
            html_content += f"""
                            <tr>
                                <td>{service['name']}</td>
                                <td>{service['description']}</td>
                                <td>{service['quantity']}</td>
                                <td class="price">{service['price']:,.2f}</td>
                            </tr>
            """
        
        # Add total and footer
        html_content += f"""
                        </tbody>
                        <tfoot>
                            <tr class="total-row">
                                <td colspan="3"><strong>Total Amount</strong></td>
                                <td class="price"><strong>{total_amount:,.2f} THB</strong></td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
                
                <!-- Terms and Conditions -->
                <div class="terms-section">
                    <h3>Terms & Conditions</h3>
                    <ul>
                        <li>This quotation is valid for 30 days from the date of issue</li>
                        <li>Prices are subject to change without prior notice</li>
                        <li>50% deposit required to confirm booking</li>
                        <li>Full payment required 7 days before travel date</li>
                        <li>Cancellation charges may apply as per our policy</li>
                        <li>All prices are in Thai Baht (THB)</li>
                        <li>Government taxes and service charges are included unless otherwise stated</li>
                    </ul>
                </div>
                
                <!-- Contact Information -->
                <div class="contact-section">
                    <h3>Contact Information</h3>
                    <div class="contact-details">
                        <p><strong>DHAKUL CHAN TRAVEL SERVICE (THAILAND) CO.,LTD.</strong></p>
                        <p>Address: 710, 716, 704, 706 Prachautid Road, Samsennok, Huai Kwang, Bangkok 10310</p>
                        <p>Phone: +662 2744216</p>
                        <p>Email: support@dhakulchan.com</p>
                        <p>Website: www.dhakulchan.net</p>
                        <p>TAT License: 11/03589</p>
                    </div>
                </div>
                
                <!-- Footer -->
                <div class="footer">
                    <p>Thank you for choosing DHAKUL CHAN TRAVEL SERVICE</p>
                    <p class="generated-note">Generated on {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_content
    
    def _get_quote_css(self):
        """Get CSS styling for quote PDF"""
        return """
        @page {
            size: A4;
            margin: 2cm;
        }
        
        body {
            font-family: 'Arial', sans-serif;
            font-size: 11pt;
            line-height: 1.4;
            color: #333;
        }
        
        .quote-container {
            max-width: 100%;
        }
        
        /* Header Styles */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #2c5aa0;
        }
        
        .logo-section h1 {
            color: #2c5aa0;
            font-size: 20pt;
            font-weight: bold;
            margin: 0;
            text-transform: uppercase;
        }
        
        .company-tagline {
            color: #666;
            font-style: italic;
            margin: 5px 0;
            font-size: 10pt;
        }
        
        .company-details {
            color: #666;
            font-size: 8pt;
            margin: 10px 0 0 0;
            line-height: 1.3;
        }
        
        .quote-info {
            text-align: right;
        }
        
        .quote-info h2 {
            color: #2c5aa0;
            font-size: 18pt;
            margin: 0 0 10px 0;
        }
        
        .quote-info p {
            margin: 5px 0;
            font-size: 10pt;
        }
        
        /* Section Styles */
        .customer-section,
        .services-section,
        .terms-section,
        .contact-section {
            margin-bottom: 25px;
        }
        
        .customer-section h3,
        .services-section h3,
        .terms-section h3,
        .contact-section h3 {
            color: #2c5aa0;
            font-size: 14pt;
            margin-bottom: 10px;
            border-bottom: 1px solid #ddd;
            padding-bottom: 5px;
        }
        
        .customer-details p {
            margin: 8px 0;
            font-size: 10pt;
        }
        
        /* Table Styles */
        .services-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
            font-size: 10pt;
        }
        
        .services-table th,
        .services-table td {
            border: 1px solid #ddd;
            padding: 10px;
            text-align: left;
        }
        
        .services-table th {
            background-color: #2c5aa0;
            color: white;
            font-weight: bold;
        }
        
        .services-table tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        
        .price {
            text-align: right;
        }
        
        .total-row {
            background-color: #e8f4fd !important;
        }
        
        .total-row td {
            border-top: 2px solid #2c5aa0;
            font-weight: bold;
        }
        
        /* Terms Styles */
        .terms-section ul {
            margin: 10px 0;
            padding-left: 20px;
        }
        
        .terms-section li {
            margin: 5px 0;
            font-size: 9pt;
        }
        
        /* Contact Styles */
        .contact-details p {
            margin: 5px 0;
            font-size: 9pt;
        }
        
        /* Footer Styles */
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            text-align: center;
            color: #666;
        }
        
        .generated-note {
            font-size: 8pt;
            color: #999;
            margin-top: 10px;
        }
        
        /* Print Styles */
        @media print {
            .quote-container {
                page-break-inside: avoid;
            }
            
            .services-table {
                page-break-inside: auto;
            }
            
            .services-table tr {
                page-break-inside: avoid;
                page-break-after: auto;
            }
        }
        """
    
    def generate_quote_bytes(self, booking):
        """Generate quote PDF and return as bytes"""
        try:
            html_content = self._generate_quote_html(booking)
            html_doc = HTML(string=html_content, base_url='.')
            css_content = self._get_quote_css()
            css = CSS(string=css_content, font_config=self.font_config)
            
            pdf_bytes = html_doc.write_pdf(stylesheets=[css], font_config=self.font_config)
            return pdf_bytes
            
        except Exception as e:
            if hasattr(current_app, 'logger'):
                current_app.logger.error(f"❌ Error generating quote PDF bytes: {str(e)}")
            else:
                print(f"❌ Error generating quote PDF bytes: {str(e)}")
            return None

# For testing purposes
if __name__ == "__main__":
    print("WeasyPrint Quote Generator")
    print("This module should be imported and used within the Flask application")