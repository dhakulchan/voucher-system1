"""
Unified PDF Generator Service for MariaDB System
Enhanced WeasyPrint generator supporting both Quote and Voucher PDFs with social sharing
"""

import os
import sys
import logging
from datetime import datetime, date
from pathlib import Path
import json
import qrcode
from io import BytesIO
import base64

# WeasyPrint imports
try:
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration
except ImportError as e:
    print(f"WeasyPrint import error: {e}")
    HTML = CSS = FontConfiguration = None

# Flask imports
from flask import current_app, render_template, url_for
from jinja2 import Template

# Database imports
from models_mariadb import db, Quote, Voucher, DocumentGeneration, ActivityLog

class UnifiedPDFGenerator:
    """Unified PDF generator for quotes and vouchers"""
    
    def __init__(self, app=None):
        self.app = app
        self.logger = None
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app"""
        self.app = app
        self.setup_logging()
        self.setup_directories()
        
        # Font configuration for Thai support
        self.font_config = FontConfiguration() if FontConfiguration else None
        
        # Base URL for assets
        self.base_url = app.config.get('WEASYPRINT_BASE_URL', 'http://localhost:5000')
        
        # Template directories
        self.template_dir = app.config.get('PDF_TEMPLATE_FOLDER', 'templates/pdf')
        self.pdf_output_dir = app.config.get('PDF_OUTPUT_FOLDER', 'static/generated_pdfs')
        self.png_output_dir = app.config.get('PNG_OUTPUT_FOLDER', 'static/generated_pngs')
    
    def setup_logging(self):
        """Setup logging"""
        self.logger = logging.getLogger('pdf_generator')
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def setup_directories(self):
        """Ensure output directories exist"""
        directories = [self.pdf_output_dir, self.png_output_dir]
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def generate_qr_code(self, data, size=(200, 200)):
        """Generate QR code for voucher verification"""
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            img = img.resize(size)
            
            # Convert to base64 for template
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            img_data = buffer.getvalue()
            buffer.close()
            
            return base64.b64encode(img_data).decode()
        except Exception as e:
            self.logger.error(f"QR code generation error: {e}")
            return None
    
    def get_quote_data(self, quote_id):
        """Get comprehensive quote data for PDF generation"""
        try:
            quote = Quote.query.options(
                db.joinedload(Quote.booking).joinedload('customer'),
                db.joinedload(Quote.booking).joinedload('products')
            ).get(quote_id)
            
            if not quote:
                raise ValueError(f"Quote {quote_id} not found")
            
            booking = quote.booking
            customer = booking.customer
            
            # Prepare comprehensive data
            data = {
                'quote': {
                    'id': quote.id,
                    'quote_number': quote.quote_number,
                    'status': quote.status,
                    'generated_at': quote.generated_at,
                    'valid_until': quote.valid_until,
                    'subtotal': float(quote.subtotal) if quote.subtotal else 0,
                    'tax_amount': float(quote.tax_amount) if quote.tax_amount else 0,
                    'discount_amount': float(quote.discount_amount) if quote.discount_amount else 0,
                    'total_amount': float(quote.total_amount) if quote.total_amount else 0,
                    'notes': quote.notes,
                    'terms_conditions': quote.terms_conditions
                },
                'booking': {
                    'id': booking.id,
                    'booking_number': booking.booking_number,
                    'booking_date': booking.booking_date,
                    'return_date': booking.return_date,
                    'adults': booking.adults,
                    'children': booking.children,
                    'infants': booking.infants,
                    'total_guests': booking.total_guests,
                    'departure_flight': booking.departure_flight,
                    'arrival_flight': booking.arrival_flight,
                    'departure_time': booking.departure_time,
                    'arrival_time': booking.arrival_time,
                    'guest_list': booking.guest_list,
                    'special_requirements': booking.special_requirements,
                    'notes': booking.notes
                },
                'customer': {
                    'id': customer.id,
                    'full_name': customer.full_name,
                    'first_name': customer.first_name,
                    'last_name': customer.last_name,
                    'email': customer.email,
                    'phone': customer.phone,
                    'address': customer.address,
                    'city': customer.city,
                    'country': customer.country
                },
                'products': [product.to_dict() for product in booking.products],
                'company': {
                    'name': 'Dhakulchan Travel',
                    'address': '710 Prachautid road, Samsen Nok, Huai Khwang, Bangkok 10320',
                    'phone': '+662 274 4216',
                    'email': 'thailand@dhakulchan.com',
                    'website': 'www.dhakulchan.com'
                },
                'meta': {
                    'generated_at': datetime.now(),
                    'base_url': self.base_url,
                    'template_used': quote.template_used
                }
            }
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error getting quote data for {quote_id}: {e}")
            raise
    
    def get_voucher_data(self, voucher_id):
        """Get comprehensive voucher data for PDF generation"""
        try:
            voucher = Voucher.query.options(
                db.joinedload(Voucher.quote).joinedload('booking').joinedload('customer'),
                db.joinedload(Voucher.booking).joinedload('products')
            ).get(voucher_id)
            
            if not voucher:
                raise ValueError(f"Voucher {voucher_id} not found")
            
            quote = voucher.quote
            booking = voucher.booking
            customer = booking.customer
            
            # Generate QR code for voucher verification
            qr_data = {
                'voucher_number': voucher.voucher_number,
                'issue_date': voucher.issue_date.isoformat(),
                'verify_url': f"{self.base_url}/verify/voucher/{voucher.voucher_number}"
            }
            qr_code_base64 = self.generate_qr_code(json.dumps(qr_data))
            
            # Prepare comprehensive data
            data = {
                'voucher': {
                    'id': voucher.id,
                    'voucher_number': voucher.voucher_number,
                    'status': voucher.status,
                    'issue_date': voucher.issue_date,
                    'expiry_date': voucher.expiry_date,
                    'service_date': voucher.service_date,
                    'service_time': voucher.service_time,
                    'pickup_location': voucher.pickup_location,
                    'dropoff_location': voucher.dropoff_location,
                    'notes': voucher.notes,
                    'special_instructions': voucher.special_instructions,
                    'qr_code': qr_code_base64,
                    'is_valid': voucher.is_valid()
                },
                'quote': {
                    'quote_number': quote.quote_number,
                    'total_amount': float(quote.total_amount) if quote.total_amount else 0
                },
                'booking': {
                    'id': booking.id,
                    'booking_number': booking.booking_number,
                    'booking_date': booking.booking_date,
                    'adults': booking.adults,
                    'children': booking.children,
                    'infants': booking.infants,
                    'total_guests': booking.total_guests,
                    'departure_flight': booking.departure_flight,
                    'arrival_flight': booking.arrival_flight,
                    'guest_list': booking.guest_list
                },
                'customer': {
                    'full_name': customer.full_name,
                    'email': customer.email,
                    'phone': customer.phone,
                    'address': customer.address
                },
                'products': [product.to_dict() for product in booking.products],
                'company': {
                    'name': 'Dhakulchan Travel',
                    'address': '710 Prachautid road, Samsen Nok, Huai Khwang, Bangkok 10320',
                    'phone': '+662 274 4216',
                    'email': 'thailand@dhakulchan.com',
                    'website': 'www.dhakulchan.com'
                },
                'meta': {
                    'generated_at': datetime.now(),
                    'base_url': self.base_url,
                    'template_used': voucher.template_used
                }
            }
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error getting voucher data for {voucher_id}: {e}")
            raise
    
    def render_template(self, template_name, data):
        """Render HTML template with data"""
        try:
            template_path = os.path.join(self.template_dir, template_name)
            
            if not os.path.exists(template_path):
                raise FileNotFoundError(f"Template not found: {template_path}")
            
            # Read template content
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            # Render with Jinja2
            template = Template(template_content)
            html_content = template.render(**data)
            
            return html_content
            
        except Exception as e:
            self.logger.error(f"Template rendering error: {e}")
            raise
    
    def generate_pdf(self, html_content, output_path):
        """Generate PDF from HTML content"""
        try:
            if not HTML:
                raise ImportError("WeasyPrint not available")
            
            start_time = datetime.now()
            
            # Create HTML object with base URL
            html_doc = HTML(string=html_content, base_url=self.base_url)
            
            # Generate PDF
            html_doc.write_pdf(
                output_path,
                font_config=self.font_config,
                optimize_images=True
            )
            
            generation_time = (datetime.now() - start_time).total_seconds() * 1000
            file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
            
            self.logger.info(f"PDF generated: {output_path} ({file_size} bytes, {generation_time:.0f}ms)")
            
            return {
                'success': True,
                'file_path': output_path,
                'file_size': file_size,
                'generation_time_ms': int(generation_time)
            }
            
        except Exception as e:
            self.logger.error(f"PDF generation error: {e}")
            return {
                'success': False,
                'error': str(e),
                'generation_time_ms': 0
            }
    
    def generate_quote_pdf(self, quote_id, template_name=None):
        """Generate Quote PDF"""
        try:
            self.logger.info(f"Generating Quote PDF for ID: {quote_id}")
            
            # Get quote data
            data = self.get_quote_data(quote_id)
            quote = Quote.query.get(quote_id)
            
            # Use specified template or default
            template_name = template_name or quote.template_used or 'quote_template_final_qt.html'
            
            # Render HTML
            html_content = self.render_template(template_name, data)
            
            # Generate output filename
            quote_number = data['quote']['quote_number']
            output_filename = f"quote_{quote_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            output_path = os.path.join(self.pdf_output_dir, output_filename)
            
            # Generate PDF
            result = self.generate_pdf(html_content, output_path)
            
            # Log generation
            DocumentGeneration.query.filter_by(
                entity_type='quote',
                entity_id=quote_id,
                document_type='quote_pdf'
            ).delete()
            
            log_entry = DocumentGeneration(
                document_type='quote_pdf',
                entity_type='quote',
                entity_id=quote_id,
                template_used=template_name,
                generation_status='success' if result['success'] else 'error',
                file_path=output_path if result['success'] else None,
                file_size=result.get('file_size'),
                generation_time_ms=result.get('generation_time_ms'),
                error_message=result.get('error')
            )
            db.session.add(log_entry)
            
            # Update quote with PDF path
            if result['success']:
                quote.pdf_path = output_path
                ActivityLog.log_activity('quote', quote_id, 'pdf_generated', 
                                       f'Quote PDF generated: {output_filename}')
            
            db.session.commit()
            
            return result
            
        except Exception as e:
            self.logger.error(f"Quote PDF generation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def generate_voucher_pdf(self, voucher_id, template_name=None):
        """Generate Voucher PDF"""
        try:
            self.logger.info(f"Generating Voucher PDF for ID: {voucher_id}")
            
            # Get voucher data
            data = self.get_voucher_data(voucher_id)
            voucher = Voucher.query.get(voucher_id)
            
            # Use specified template or default
            template_name = template_name or voucher.template_used or 'voucher_template_final.html'
            
            # Render HTML
            html_content = self.render_template(template_name, data)
            
            # Generate output filename
            voucher_number = data['voucher']['voucher_number']
            output_filename = f"voucher_{voucher_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            output_path = os.path.join(self.pdf_output_dir, output_filename)
            
            # Generate PDF
            result = self.generate_pdf(html_content, output_path)
            
            # Log generation
            DocumentGeneration.query.filter_by(
                entity_type='voucher',
                entity_id=voucher_id,
                document_type='voucher_pdf'
            ).delete()
            
            log_entry = DocumentGeneration(
                document_type='voucher_pdf',
                entity_type='voucher',
                entity_id=voucher_id,
                template_used=template_name,
                generation_status='success' if result['success'] else 'error',
                file_path=output_path if result['success'] else None,
                file_size=result.get('file_size'),
                generation_time_ms=result.get('generation_time_ms'),
                error_message=result.get('error')
            )
            db.session.add(log_entry)
            
            # Update voucher with PDF path
            if result['success']:
                voucher.pdf_path = output_path
                ActivityLog.log_activity('voucher', voucher_id, 'pdf_generated',
                                       f'Voucher PDF generated: {output_filename}')
            
            db.session.commit()
            
            return result
            
        except Exception as e:
            self.logger.error(f"Voucher PDF generation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def generate_png_from_pdf(self, pdf_path, png_path):
        """Convert PDF to PNG using external tools"""
        try:
            import subprocess
            
            # Use ImageMagick or similar tool to convert PDF to PNG
            cmd = [
                'convert',
                '-density', '300',
                '-quality', '100',
                f'{pdf_path}[0]',  # First page only
                png_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                file_size = os.path.getsize(png_path) if os.path.exists(png_path) else 0
                self.logger.info(f"PNG generated: {png_path} ({file_size} bytes)")
                return {'success': True, 'file_path': png_path, 'file_size': file_size}
            else:
                self.logger.error(f"PNG conversion failed: {result.stderr}")
                return {'success': False, 'error': result.stderr}
                
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'PNG conversion timeout'}
        except FileNotFoundError:
            return {'success': False, 'error': 'ImageMagick not found'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def generate_quote_png(self, quote_id):
        """Generate Quote PNG"""
        try:
            quote = Quote.query.get(quote_id)
            if not quote or not quote.pdf_path or not os.path.exists(quote.pdf_path):
                # Generate PDF first
                pdf_result = self.generate_quote_pdf(quote_id)
                if not pdf_result['success']:
                    return pdf_result
                quote = Quote.query.get(quote_id)  # Refresh
            
            # Generate PNG filename
            quote_number = quote.quote_number
            png_filename = f"quote_{quote_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            png_path = os.path.join(self.png_output_dir, png_filename)
            
            # Convert PDF to PNG
            result = self.generate_png_from_pdf(quote.pdf_path, png_path)
            
            # Update quote with PNG path
            if result['success']:
                quote.png_path = png_path
                ActivityLog.log_activity('quote', quote_id, 'png_generated',
                                       f'Quote PNG generated: {png_filename}')
                db.session.commit()
            
            return result
            
        except Exception as e:
            self.logger.error(f"Quote PNG generation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def generate_voucher_png(self, voucher_id):
        """Generate Voucher PNG"""
        try:
            voucher = Voucher.query.get(voucher_id)
            if not voucher or not voucher.pdf_path or not os.path.exists(voucher.pdf_path):
                # Generate PDF first
                pdf_result = self.generate_voucher_pdf(voucher_id)
                if not pdf_result['success']:
                    return pdf_result
                voucher = Voucher.query.get(voucher_id)  # Refresh
            
            # Generate PNG filename
            voucher_number = voucher.voucher_number
            png_filename = f"voucher_{voucher_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            png_path = os.path.join(self.png_output_dir, png_filename)
            
            # Convert PDF to PNG
            result = self.generate_png_from_pdf(voucher.pdf_path, png_path)
            
            # Update voucher with PNG path
            if result['success']:
                voucher.png_path = png_path
                ActivityLog.log_activity('voucher', voucher_id, 'png_generated',
                                       f'Voucher PNG generated: {png_filename}')
                db.session.commit()
            
            return result
            
        except Exception as e:
            self.logger.error(f"Voucher PNG generation failed: {e}")
            return {'success': False, 'error': str(e)}

# Create global instance
pdf_generator = UnifiedPDFGenerator()