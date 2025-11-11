#!/usr/bin/env python3
"""
Simple Quote PDF Generator - Fixed version using ReportLab
"""
import os
import logging
from datetime import datetime
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

logger = logging.getLogger(__name__)

class SimpleQuotePDFGenerator:
    """Simple Quote PDF Generator using ReportLab"""
    
    def __init__(self):
        self.setup_fonts()
        
    def setup_fonts(self):
        """Setup fonts for Thai text support"""
        try:
            # Try to register Thai fonts if available
            font_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'fonts')
            if os.path.exists(os.path.join(font_path, 'THSarabunNew.ttf')):
                pdfmetrics.registerFont(TTFont('THSarabunNew', os.path.join(font_path, 'THSarabunNew.ttf')))
                self.thai_font = 'THSarabunNew'
            else:
                self.thai_font = 'Helvetica'
        except:
            self.thai_font = 'Helvetica'
            
    def generate_quote_pdf(self, booking):
        """Generate Quote PDF for a booking using ReportLab"""
        try:
            logger.info(f'Generating simple Quote PDF for booking {booking.booking_reference}')
            
            # Prepare data
            template_data = self._prepare_simple_template_data(booking)
            
            # Generate filename
            current_time = datetime.now()
            date_stamp = current_time.strftime('%Y%m%d')
            time_stamp = current_time.strftime('%H%M%S')
            filename = f'Quote_{booking.booking_reference}_{date_stamp}_{time_stamp}.pdf'
            
            # Ensure output directory exists
            output_dir = os.path.join('static', 'generated')
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, filename)
            
            # Create PDF document
            doc = SimpleDocTemplate(output_path, pagesize=A4)
            
            # Build story
            story = []
            styles = getSampleStyleSheet()
            
            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=30,
                alignment=1,  # Center
                textColor=colors.black
            )
            
            header_style = ParagraphStyle(
                'CustomHeader',
                parent=styles['Heading2'],
                fontSize=14,
                spaceAfter=12,
                textColor=colors.black
            )
            
            # Add content
            story.append(Paragraph(template_data['company_name'], title_style))
            story.append(Paragraph(f"{template_data['company_address']}<br/>{template_data['company_phone']} | {template_data['company_email']}", styles['Normal']))
            story.append(Spacer(1, 20))
            
            story.append(Paragraph("QUOTATION", title_style))
            story.append(Spacer(1, 20))
            
            # Quote details table
            quote_data = [
                ['Quote Number:', template_data['quote_number']],
                ['Date:', template_data['quote_date']],
                ['Customer:', template_data['customer_name']],
                ['Phone:', template_data['customer_phone']],
                ['Booking Reference:', template_data['booking_reference']],
            ]
            
            quote_table = Table(quote_data, colWidths=[2*inch, 4*inch])
            quote_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ]))
            
            story.append(quote_table)
            story.append(Spacer(1, 30))
            
            # Service details
            story.append(Paragraph("Service Details", header_style))
            
            service_data = [
                ['Party Name:', template_data['party_name']],
                ['Description:', template_data['description']],
                ['Total Amount:', f"฿{template_data['total_amount']}"],
            ]
            
            service_table = Table(service_data, colWidths=[2*inch, 4*inch])
            service_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
                ('BOX', (0, 0), (-1, -1), 1, colors.black),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
            ]))
            
            story.append(service_table)
            story.append(Spacer(1, 50))
            
            # Footer
            story.append(Paragraph(f"Generated on {template_data['generation_date']} at {template_data['generation_time']}", styles['Normal']))
            story.append(Paragraph("This quotation is valid for 30 days from the date of issue.", styles['Normal']))
            
            # Build PDF
            doc.build(story)
            
            logger.info(f'Generated simple Quote PDF: {filename}')
            return filename
            
        except Exception as e:
            logger.error(f'Error generating simple Quote PDF: {str(e)}')
            raise
    
    def _prepare_simple_template_data(self, booking):
        """Prepare simple template data"""
        
        # Generate quote number - use new starting pattern
        quote_number = booking.quote_number or f'QT{2509000 + booking.id:07d}'
        
        # Update booking if needed
        if not booking.quote_number and booking.status == 'quoted':
            try:
                booking.quote_number = quote_number
                from extensions import db
                db.session.commit()
                logger.info(f'Updated booking {booking.id} with quote number: {quote_number}')
            except Exception as e:
                logger.warning(f'Could not update booking quote number: {e}')
        
        # Basic booking info
        customer_name = booking.customer.name if booking.customer else 'Customer'
        customer_phone = booking.customer.phone if booking.customer and booking.customer.phone else '+66123456789'
        
        # Format total amount
        total_amount = float(booking.total_amount) if booking.total_amount else 0
        total_formatted = f'{total_amount:,.2f}'
        
        # Current date
        current_date = datetime.now().strftime('%d/%m/%Y')
        
        template_data = {
            'booking': booking,
            'quote_number': quote_number,
            'customer_name': customer_name,
            'customer_phone': customer_phone,
            'booking_reference': booking.booking_reference,
            'party_name': booking.party_name or customer_name,
            'description': booking.description or 'Tour Package',
            'total_amount': total_formatted,
            'quote_date': current_date,
            'generation_date': current_date,
            'generation_time': datetime.now().strftime('%H:%M:%S'),
            'company_name': os.getenv('COMPANY_NAME_EN', 'DHAKUL CHAN TRAVEL SERVICE'),
            'company_address': os.getenv('COMPANY_ADDRESS_EN', 'Bangkok, Thailand'),
            'company_phone': os.getenv('COMPANY_PHONE', '+66 2 274 4216'),
            'company_email': os.getenv('COMPANY_EMAIL', 'info@dhakulchan.net'),
            'company_website': os.getenv('COMPANY_WEBSITE', 'www.dhakulchan.net'),
        }
        
        return template_data
    


if __name__ == "__main__":
    # Test the generator
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    
    from app import create_app
    from models.booking import Booking
    
    app = create_app()
    with app.app_context():
        booking = Booking.query.get(20)
        if booking:
            generator = SimpleQuotePDFGenerator()
            pdf_file = generator.generate_quote_pdf(booking)
            print(f"Generated: {pdf_file}")
        else:
            print("Booking 20 not found")