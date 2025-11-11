"""
Working Template Generator - ใช้ template ที่พิสูจน์แล้วว่าทำงาน
"""
import os
import sys
import json
import logging
import subprocess
from datetime import datetime

logger = logging.getLogger(__name__)

class WorkingTemplateGenerator:
    """Quote Generator ที่ใช้ template ที่พิสูจน์แล้วว่าทำงาน"""
    
    def __init__(self):
        # Use temp directory to avoid permission issues, then copy to static
        self.temp_dir = '/tmp'
        self.output_dir = os.path.join('static', 'generated')
        try:
            os.makedirs(self.output_dir, exist_ok=True)
        except PermissionError:
            pass  # Will use temp directory and copy later
    
    def clean_text(self, text):
        """Clean text"""
        if not text:
            return ""
        text = str(text)
        if text.startswith('["') and text.endswith('"]'):
            try:
                import json
                parsed = json.loads(text)
                if isinstance(parsed, list) and len(parsed) > 0:
                    text = parsed[0]
            except:
                pass
        import re
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def format_currency(self, amount):
        """Format currency"""
        if not amount:
            return "0.00"
        try:
            return f"{float(amount):,.2f}"
        except:
            return "0.00"
    
    def generate_working_html(self, booking):
        """Generate HTML using quote_template_final.html with Flask context"""
        try:
            from flask import render_template, has_request_context
            from app import app
            import re
            
            # Check if we're in proper Flask context
            if has_request_context():
                # Try quote_template_final_qt.html first, fallback to simpler template
                try:
                    html_content = render_template('pdf/quote_template_final_qt.html', booking=booking)
                    logger.info(f'✅ Successfully rendered quote_template_final_qt.html for {booking.booking_reference}')
                except Exception as template_error:
                    logger.warning(f'⚠️ quote_template_final_qt.html failed: {template_error}, trying quote_template_final.html')
                    try:
                        html_content = render_template('pdf/quote_template_final.html', booking=booking)
                        logger.info(f'✅ Successfully rendered quote_template_final.html for {booking.booking_reference}')
                    except Exception as template_error:
                        logger.warning(f'⚠️ quote_template_final.html failed: {template_error}, trying quote_template_modern.html')
                    html_content = render_template('pdf/quote_template_modern.html', booking=booking)
                    logger.info(f'✅ Successfully rendered quote_template_modern.html for {booking.booking_reference}')
            else:
                # Create request context for template rendering
                with app.test_request_context():
                    try:
                        html_content = render_template('pdf/quote_template_final_qt.html', booking=booking)
                        logger.info(f'✅ Successfully rendered quote_template_final_qt.html for {booking.booking_reference} (test context)')
                    except Exception as template_error:
                        logger.warning(f'⚠️ quote_template_final_qt.html failed: {template_error}, trying quote_template_final.html')
                        try:
                            html_content = render_template('pdf/quote_template_final.html', booking=booking)
                            logger.info(f'✅ Successfully rendered quote_template_final.html for {booking.booking_reference} (test context)')
                        except Exception as template_error:
                            logger.warning(f'⚠️ quote_template_final.html failed: {template_error}, trying quote_template_modern.html')
                        html_content = render_template('pdf/quote_template_modern.html', booking=booking)
                        logger.info(f'✅ Successfully rendered quote_template_modern.html for {booking.booking_reference} (test context)')
            
            # Clean problematic CSS url() references that cause ProtocolUnknownError
            html_content = re.sub(r"content:\s*url\([^)]+\);?", "", html_content)
            html_content = re.sub(r"background-image:\s*url\([^)]+\);?", "", html_content)
            logger.info(f'✅ Cleaned CSS url() references for PDF generation')
            
            return html_content
        except Exception as e:
            logger.error(f'❌ Error rendering quote_template_final_qt.html: {e}')
            # Fallback to simple template if template fails
            return self.generate_fallback_html(booking)
    
    def generate_fallback_html(self, booking):
        """Fallback simple HTML if template fails"""
        html = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Quote """ + booking.booking_reference + """</title>
<style>
body {
    font-family: Arial, sans-serif;
    margin: 20px;
    line-height: 1.4;
}
h1 {
    color: #2c3e50;
    font-size: 18px;
    text-align: center;
    margin-bottom: 10px;
}
h2 {
    color: #34495e;
    font-size: 16px;
    border-bottom: 2px solid #3498db;
    padding-bottom: 5px;
}
p {
    margin: 8px 0;
    font-size: 12px;
}
</style>
</head>
<body>
<h1>DHAKUL CHAN TRAVEL SERVICE (THAILAND) CO.,LTD.</h1>
<h2>QUOTE</h2>
<p><strong>Reference:</strong> """ + booking.booking_reference + """</p>
<p><strong>Status:</strong> """ + booking.status + """</p>
<p><strong>Total Amount:</strong> """ + self.format_currency(booking.total_amount or 0) + """ THB</p>
</body>
</html>"""
        return html
    
    def generate_direct_pdf(self, booking):
        """Generate PDF directly using ReportLab to avoid wkhtmltopdf issues"""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib import colors
            from reportlab.lib.units import inch
            from datetime import datetime
            
            # Generate filename in temp directory first
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f'quote_{booking.booking_reference}_{timestamp}.pdf'
            temp_filepath = os.path.join(self.temp_dir, filename)
            final_filepath = os.path.join(self.output_dir, filename)
            
            # Create PDF document in temp directory
            doc = SimpleDocTemplate(temp_filepath, pagesize=A4, topMargin=0.75*inch)
            styles = getSampleStyleSheet()
            story = []
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor=colors.darkblue,
                alignment=1,  # Center
                spaceAfter=12
            )
            story.append(Paragraph("DHAKUL CHAN TRAVEL SERVICE (THAILAND) CO.,LTD.", title_style))
            story.append(Spacer(1, 0.2*inch))
            
            # Quote header
            quote_style = ParagraphStyle(
                'QuoteHeader',
                parent=styles['Heading2'],
                fontSize=16,
                textColor=colors.darkred,
                alignment=1,
                spaceAfter=12
            )
            story.append(Paragraph("QUOTE", quote_style))
            story.append(Spacer(1, 0.3*inch))
            
            # Booking details table
            data = [
                ['Booking Reference:', booking.booking_reference or 'N/A'],
                ['Status:', booking.status or 'N/A'],
                ['Customer:', getattr(booking, 'customer_name', 'N/A')],
                ['Total Amount:', f'{self.format_currency(booking.total_amount or 0)} THB'],
                ['Created:', booking.created_at.strftime('%d/%m/%Y %H:%M') if booking.created_at else 'N/A']
            ]
            
            table = Table(data, colWidths=[2*inch, 3*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('BACKGROUND', (1, 0), (1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(table)
            story.append(Spacer(1, 0.5*inch))
            
            # Footer
            footer_style = ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=8,
                textColor=colors.grey,
                alignment=1
            )
            story.append(Paragraph(f"Generated on {datetime.now().strftime('%d/%m/%Y %H:%M')}", footer_style))
            
            # Build PDF
            doc.build(story)
            
            # Copy from temp to final location
            if os.path.exists(temp_filepath):
                try:
                    import shutil
                    shutil.copy2(temp_filepath, final_filepath)
                    os.remove(temp_filepath)  # Clean up temp file
                    
                    file_size = os.path.getsize(final_filepath)
                    logger.info(f'✅ Direct PDF created: {filename} ({file_size} bytes)')
                    return True, filename
                except Exception as copy_error:
                    # If copy fails, return temp file path
                    logger.warning(f'⚠️ Could not copy to final location: {copy_error}')
                    file_size = os.path.getsize(temp_filepath)
                    logger.info(f'✅ PDF in temp location: {filename} ({file_size} bytes)')
                    return True, filename
            else:
                return False, 'PDF file not created'
                
        except Exception as e:
            logger.error(f'❌ Direct PDF generation failed: {e}')
            return False, str(e)
    
    def generate_quote_pdf(self, booking_id):
        """Generate quote PDF for specific booking_id using quote_template_final_qt.html"""
        logger.info(f'🚀 Starting quote PDF generation for booking ID: {booking_id}')
        try:
            from app import app
            from models import Booking
            
            # Ensure we're in application context for database queries
            with app.app_context():
                # Get booking data
                booking = Booking.query.get(booking_id)
                if not booking:
                    error_msg = f'❌ Booking {booking_id} not found'
                    logger.error(error_msg)
                    return False, error_msg
                    
                logger.info(f'✅ Found booking: {booking.booking_reference} (status: {booking.status})')
                
                # Generate HTML content using quote_template_final_qt.html
                with app.test_request_context():
                    html_content = self.generate_working_html(booking)
                logger.info(f'✅ Generated HTML using quote_template_final_qt.html template')
                
                # Generate filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f'quote_{booking.booking_reference}_{timestamp}.pdf'
                filepath = os.path.join(self.output_dir, filename)
                
                # Create temporary HTML file in system temp directory
                import tempfile
                temp_fd, temp_html = tempfile.mkstemp(suffix='.html', prefix='quote_')
                try:
                    with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    logger.info(f'✅ Created temp HTML: {temp_html}')
                except Exception as e:
                    logger.error(f'❌ Failed to create temp HTML: {e}')
                    try:
                        os.close(temp_fd)
                    except:
                        pass
                    return False, f'Temp file creation failed: {str(e)}'
                
                # wkhtmltopdf command - macOS compatible (no xvfb needed)
                abs_temp_html = os.path.abspath(temp_html)
                abs_filepath = os.path.abspath(filepath)
                
                # macOS: Use wkhtmltopdf directly without xvfb
                import platform
                if platform.system() == 'Darwin':  # macOS
                    cmd = [
                        'wkhtmltopdf',
                        '--page-size', 'A4',
                        '--disable-javascript',
                        '--disable-smart-shrinking',
                        '--print-media-type',
                        '--no-background',
                        '--quiet',
                        abs_temp_html, abs_filepath
                    ]
                else:  # Linux
                    cmd = [
                        'xvfb-run', '-a',
                        'wkhtmltopdf',
                        '--page-size', 'A4',
                        '--disable-javascript',
                        '--disable-smart-shrinking',
                        '--print-media-type',
                        '--no-background',
                        '--quiet',
                        abs_temp_html, abs_filepath
                    ]
                
                logger.info(f'�️ Running wkhtmltopdf: {" ".join(cmd)}')
                
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True)
                except Exception as e:
                    logger.error(f'❌ wkhtmltopdf execution failed: {e}')
                    # Clean up temporary HTML file
                    try:
                        os.remove(temp_html)
                    except:
                        pass
                    return False, f'PDF generation failed: {str(e)}'
                
                # Clean up temporary HTML file
                try:
                    os.remove(temp_html)
                except Exception as cleanup_error:
                    logger.warning(f'⚠️ Failed to cleanup temp file: {cleanup_error}')
                
                if result.returncode == 0 and os.path.exists(filepath):
                    file_size = os.path.getsize(filepath)
                    logger.info(f'✅ Quote PDF created using template: {filename} ({file_size} bytes)')
                    
                    return True, filename
                else:
                    logger.error(f'wkhtmltopdf failed with return code {result.returncode}')
                    logger.error(f'Stderr: {result.stderr}')
                    logger.error(f'Stdout: {result.stdout}')
                    
                    # Fallback to ReportLab if wkhtmltopdf fails
                    logger.info('🔄 Falling back to ReportLab direct PDF generation')
                    return self.generate_direct_pdf_from_booking(booking)
            
        except Exception as e:
            logger.error(f'❌ Quote PDF generation error: {e}')
            return False, str(e)

    def generate_direct_pdf_from_booking(self, booking):
        """Generate PDF directly from booking object using ReportLab (no HTML template)"""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            import os
            
            # Create output directory
            os.makedirs(self.output_dir, exist_ok=True)
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            pdf_filename = f'quote_{booking.booking_reference}_{timestamp}.pdf'
            pdf_path = os.path.join(self.output_dir, pdf_filename)
            
            logger.info(f'Generating direct PDF using ReportLab: {pdf_path}')
            
            # Create PDF document
            doc = SimpleDocTemplate(pdf_path, pagesize=letter,
                                  rightMargin=72, leftMargin=72,
                                  topMargin=72, bottomMargin=18)
            
            # Build story
            story = []
            styles = getSampleStyleSheet()
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=30,
                alignment=1  # Center
            )
            story.append(Paragraph("QUOTE", title_style))
            story.append(Spacer(1, 12))
            
            # Booking details
            data = [
                ['Booking Reference:', booking.booking_reference or 'N/A'],
                ['Party Name:', booking.party_name or 'N/A'],
                ['Customer:', getattr(booking.customer, 'name', 'N/A') if booking.customer else 'N/A'],
                ['Total Amount:', f"${booking.total_amount:.2f}" if booking.total_amount else 'N/A'],
                ['Status:', booking.status or 'N/A'],
                ['Type:', booking.booking_type or 'N/A'],
            ]
            
            table = Table(data, colWidths=[2*inch, 4*inch])
            table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(table)
            
            # Build PDF
            doc.build(story)
            
            # Verify file was created
            if os.path.exists(pdf_path):
                file_size = os.path.getsize(pdf_path)
                logger.info(f'✅ Direct PDF generated successfully using ReportLab: {pdf_filename} ({file_size} bytes)')
                return True, pdf_filename
            else:
                logger.error(f'❌ Direct PDF file not found after generation: {pdf_path}')
                return False, 'PDF file not created'
            
        except Exception as e:
            logger.error(f'❌ Error generating direct PDF: {e}')
            return False, str(e)
