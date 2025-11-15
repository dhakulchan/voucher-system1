# Quote PDF Integration Module
# Integration functions for the main booking system

import os
import sys
from pathlib import Path
from datetime import datetime
import tempfile
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from jinja2 import Environment, FileSystemLoader, TemplateNotFound
    from weasyprint import HTML, CSS
    from quote_helper_functions import (
        generate_quote_pdf_context, 
        validate_quote_data,
        enhance_product_data,
        calculate_totals
    )
except ImportError as e:
    logger.error(f"Missing required packages: {e}")
    logger.error("Please install: pip install weasyprint jinja2")

class QuotePDFGenerator:
    """Enhanced Quote PDF Generator Class"""
    
    def __init__(self, template_dir=None, output_dir=None):
        """
        Initialize the PDF generator
        
        Args:
            template_dir: Path to template directory
            output_dir: Path to output directory
        """
        self.base_dir = Path(__file__).parent
        self.template_dir = template_dir or (self.base_dir / 'templates' / 'pdf')
        self.output_dir = output_dir or (self.base_dir / 'output')
        
        # Ensure output directory exists
        self.output_dir.mkdir(exist_ok=True)
        
        # Setup Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=True
        )
        
        # Add custom filters
        self.env.filters['safe_date'] = self._safe_date_filter
        self.env.filters['format_phone'] = self._format_phone_filter
        self.env.filters['format_currency'] = self._format_currency_filter
        
    def _safe_date_filter(self, date_value, format_str='%d/%m/%Y'):
        """Jinja2 filter for safe date formatting"""
        try:
            if hasattr(date_value, 'strftime'):
                return date_value.strftime(format_str)
            return str(date_value) if date_value else '-'
        except:
            return '-'
    
    def _format_phone_filter(self, phone):
        """Jinja2 filter for phone formatting"""
        if not phone:
            return ''
        phone_str = str(phone).replace('-', '').replace(' ', '')
        if len(phone_str) == 10 and phone_str.startswith('0'):
            return f"{phone_str[:3]}-{phone_str[3:6]}-{phone_str[6:]}"
        return phone
    
    def _format_currency_filter(self, amount):
        """Jinja2 filter for currency formatting"""
        try:
            return f"{float(amount):,.2f}"
        except:
            return str(amount)
    
    def generate_html(self, template_name='quote_template_final_qt.html', **context_data):
        """
        Generate HTML from template
        
        Args:
            template_name: Name of template file
            **context_data: Context data for template
            
        Returns:
            str: Rendered HTML content
        """
        try:
            template = self.env.get_template(template_name)
            
            # Prepare context
            if 'booking' in context_data or 'customer' in context_data:
                # Use provided data directly
                context = generate_quote_pdf_context(**context_data)
            else:
                # Assume context_data is already prepared
                context = context_data
            
            # Validate data
            booking_data = context.get('booking', {})
            errors = validate_quote_data(booking_data)
            if errors:
                logger.warning(f"Validation warnings: {errors}")
            
            # Render template
            html_content = template.render(**context)
            logger.info("HTML template rendered successfully")
            
            return html_content
            
        except TemplateNotFound:
            logger.error(f"Template not found: {template_name}")
            raise
        except Exception as e:
            logger.error(f"Error rendering template: {e}")
            raise
    
    def generate_pdf(self, html_content, filename=None, return_bytes=False):
        """
        Generate PDF from HTML content
        
        Args:
            html_content: HTML content string
            filename: Output filename (auto-generated if None)
            return_bytes: Return PDF as bytes instead of saving
            
        Returns:
            str or bytes: File path or PDF bytes
        """
        try:
            # Create HTML document
            html_doc = HTML(
                string=html_content,
                base_url=str(self.base_dir)
            )
            
            if return_bytes:
                # Return PDF as bytes
                pdf_bytes = html_doc.write_pdf()
                logger.info("PDF generated as bytes")
                return pdf_bytes
            else:
                # Save to file
                if not filename:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"quote_{timestamp}.pdf"
                
                pdf_path = self.output_dir / filename
                html_doc.write_pdf(str(pdf_path))
                
                logger.info(f"PDF saved to: {pdf_path}")
                return str(pdf_path)
                
        except Exception as e:
            logger.error(f"Error generating PDF: {e}")
            raise
    
    def generate_quote_pdf(self, booking_data, customer_data=None, products_data=None, 
                          filename=None, template_name='quote_template_final_qt.html',
                          return_bytes=False, **extra_context):
        """
        Generate complete quote PDF
        
        Args:
            booking_data: Booking information dict
            customer_data: Customer information dict
            products_data: List of products/services
            filename: Output filename
            template_name: Template to use
            return_bytes: Return as bytes instead of file
            **extra_context: Additional context data
            
        Returns:
            str or bytes: File path or PDF bytes
        """
        try:
            # Prepare context data
            context_data = {
                'booking': booking_data,
                'customer': customer_data,
                'products': enhance_product_data(products_data) if products_data else [],
                **extra_context
            }
            
            # Generate HTML
            html_content = self.generate_html(template_name, **context_data)
            
            # Generate PDF
            result = self.generate_pdf(html_content, filename, return_bytes)
            
            logger.info("Quote PDF generation completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error in quote PDF generation: {e}")
            raise
    
    def preview_html(self, booking_data, customer_data=None, products_data=None,
                    filename=None, template_name='quote_template_final_qt.html',
                    **extra_context):
        """
        Generate HTML preview file
        
        Args:
            booking_data: Booking information dict
            customer_data: Customer information dict  
            products_data: List of products/services
            filename: Output filename
            template_name: Template to use
            **extra_context: Additional context data
            
        Returns:
            str: Path to HTML file
        """
        try:
            # Prepare context data
            context_data = {
                'booking': booking_data,
                'customer': customer_data,
                'products': enhance_product_data(products_data) if products_data else [],
                **extra_context
            }
            
            # Generate HTML
            html_content = self.generate_html(template_name, **context_data)
            
            # Save HTML file
            if not filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"quote_preview_{timestamp}.html"
            
            html_path = self.output_dir / filename
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"HTML preview saved to: {html_path}")
            return str(html_path)
            
        except Exception as e:
            logger.error(f"Error generating HTML preview: {e}")
            raise

# Convenience functions for backward compatibility
def generate_quote_pdf_simple(booking, customer=None, products=None, output_path=None):
    """
    Simple function to generate quote PDF
    
    Args:
        booking: Booking data dict
        customer: Customer data dict  
        products: Products list
        output_path: Output file path
        
    Returns:
        str: Path to generated PDF
    """
    generator = QuotePDFGenerator()
    return generator.generate_quote_pdf(
        booking_data=booking,
        customer_data=customer,
        products_data=products,
        filename=output_path
    )

def generate_quote_html_preview(booking, customer=None, products=None, output_path=None):
    """
    Simple function to generate HTML preview
    
    Args:
        booking: Booking data dict
        customer: Customer data dict
        products: Products list  
        output_path: Output file path
        
    Returns:
        str: Path to generated HTML file
    """
    generator = QuotePDFGenerator()
    return generator.preview_html(
        booking_data=booking,
        customer_data=customer,
        products_data=products,
        filename=output_path
    )

# Integration example for Flask/main application
class QuoteAPIIntegration:
    """Integration class for web applications"""
    
    def __init__(self, app=None):
        self.app = app
        self.generator = QuotePDFGenerator()
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app"""
        self.app = app
        
        # Add template filters to Flask if available
        if hasattr(app, 'template_filter'):
            app.template_filter('safe_date')(self.generator._safe_date_filter)
            app.template_filter('format_phone')(self.generator._format_phone_filter)
            app.template_filter('format_currency')(self.generator._format_currency_filter)
    
    def generate_quote_response(self, booking_id, format='pdf'):
        """
        Generate quote response for web API
        
        Args:
            booking_id: ID of booking
            format: 'pdf' or 'html'
            
        Returns:
            tuple: (content, mimetype, filename)
        """
        try:
            # This would typically fetch from database
            # For now, use sample data
            from quote_helper_functions import generate_quote_pdf_context
            context = generate_quote_pdf_context()
            
            if format.lower() == 'pdf':
                pdf_bytes = self.generator.generate_quote_pdf(
                    booking_data=context['booking'],
                    customer_data=context['customer'],
                    products_data=context['products'],
                    return_bytes=True
                )
                
                filename = f"quote_{booking_id}_{datetime.now().strftime('%Y%m%d')}.pdf"
                return pdf_bytes, 'application/pdf', filename
                
            elif format.lower() == 'html':
                html_content = self.generator.generate_html(**context)
                filename = f"quote_{booking_id}_{datetime.now().strftime('%Y%m%d')}.html"
                return html_content, 'text/html', filename
                
            else:
                raise ValueError(f"Unsupported format: {format}")
                
        except Exception as e:
            logger.error(f"Error generating quote response: {e}")
            raise

# Example usage
if __name__ == "__main__":
    # Test the integration
    print("Testing Quote PDF Integration...")
    
    generator = QuotePDFGenerator()
    
    # Sample data
    sample_booking = {
        'booking_reference': 'BK20250925TEST',
        'party_name': 'Integration Test Package',
        'status': 'confirmed',
        'adults': 2,
        'children': 0,
        'traveling_period_start': datetime.now(),
        'traveling_period_end': datetime.now(),
        'description': 'Test integration booking'
    }
    
    sample_customer = {
        'name': 'Test Customer',
        'phone': '0891234567'
    }
    
    sample_products = [
        {
            'name': 'Test Package',
            'quantity': 2,
            'price': '25000.00',
            'amount': '50000.00'
        }
    ]
    
    # Test HTML preview
    html_path = generator.preview_html(
        booking_data=sample_booking,
        customer_data=sample_customer,
        products_data=sample_products
    )
    print(f"✓ HTML preview: {html_path}")
    
    # Test PDF generation
    pdf_path = generator.generate_quote_pdf(
        booking_data=sample_booking,
        customer_data=sample_customer,
        products_data=sample_products
    )
    print(f"✓ PDF generated: {pdf_path}")
    
    print("Integration test completed!")