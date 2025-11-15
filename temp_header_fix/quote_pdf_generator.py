"""
Enhanced PDF Generator for Quotes with social media sharing capabilities
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Frame,
    PageTemplate
)
from reportlab.platypus.doctemplate import BaseDocTemplate
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
import qrcode
import logging

logger = logging.getLogger(__name__)


class QuotePDFGenerator:
    """Enhanced Quote PDF Generator with sharing capabilities"""

    def __init__(self):
        # Adaptive output directory based on environment
        if os.path.exists("/opt/bitnami"):
            # Production environment
            self.output_dir = "/opt/bitnami/apache/htdocs/static/generated/quotes"
            self.static_dir = "/opt/bitnami/apache/htdocs/static"
        else:
            # Local development environment
            self.output_dir = "static/generated/quotes"
            self.static_dir = "static"

        # Ensure directories exist
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(f"{self.output_dir}/png", exist_ok=True)

        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        # Header style
        self.styles.add(
            ParagraphStyle(
                name="CustomHeader",
                parent=self.styles["Heading1"],
                fontSize=24,
                textColor=colors.HexColor("#2E86AB"),
                alignment=TA_CENTER,
                spaceAfter=20,
            )
        )

        # Subheader style
        self.styles.add(
            ParagraphStyle(
                name="CustomSubHeader",
                parent=self.styles["Heading2"],
                fontSize=16,
                textColor=colors.HexColor("#A23B72"),
                alignment=TA_LEFT,
                spaceBefore=15,
                spaceAfter=10,
            )
        )

        # Quote info style
        self.styles.add(
            ParagraphStyle(
                name="QuoteInfo",
                parent=self.styles["Normal"],
                fontSize=10,
                textColor=colors.black,
                alignment=TA_RIGHT,
                rightIndent=20,
            )
        )

        # Terms style
        self.styles.add(
            ParagraphStyle(
                name="Terms",
                parent=self.styles["Normal"],
                fontSize=9,
                textColor=colors.grey,
                leftIndent=10,
                rightIndent=10,
            )
        )

    def generate_quote_pdf(self, quote, booking, customer):
        """
        Generate comprehensive Quote PDF with enhanced layout

        Args:
            quote: Quote model instance
            booking: Booking model instance
            customer: Customer model instance

        Returns:
            tuple: (pdf_path, png_path) - Paths to generated documents
        """
        try:
            # Generate filename
            filename = (
                f"quote_{quote.quote_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            pdf_path = f"{self.output_dir}/{filename}.pdf"

            # Create PDF document with BaseDocTemplate for header/footer
            doc = BaseDocTemplate(
                pdf_path,
                pagesize=A4,
                topMargin=35*mm,     # Space for header
                bottomMargin=20*mm,  # Space for footer
                leftMargin=15*mm,
                rightMargin=15*mm
            )
            
            # Header/footer function
            def header_footer_on_page(canvas, doc):
                """Draw header and footer on each page"""
                canvas.saveState()
                
                # Header - Company Info and Logo (Fixed layout)
                try:
                    # Logo path - adjusted position to align with Reference
                    logo_path = "/opt/bitnami/apache/htdocs/dcts-logo-vou.png" if os.path.exists("/opt/bitnami") else "dcts-logo-vou.png"
                    if os.path.exists(logo_path):
                        from reportlab.lib.utils import ImageReader
                        logo_reader = ImageReader(logo_path)
                        canvas.drawImage(logo_reader, 15*mm, A4[1] - 27*mm, width=32*mm, height=15*mm, mask='auto')
                    
                    # Company info in header - reduced font size to fit on one line
                    canvas.setFont('Helvetica-Bold', 9)  # Reduced from 11 to 9
                    canvas.setFillColor(colors.Color(44/255, 62/255, 80/255))  # #2C3E50
                    canvas.drawString(52*mm, A4[1] - 15*mm, "DHAKUL CHAN TRAVEL SERVICE (THAILAND) CO.,LTD.")
                    
                    canvas.setFont('Helvetica', 8)
                    canvas.setFillColor(colors.Color(127/255, 140/255, 141/255))  # #7F8C8D
                    canvas.drawString(55*mm, A4[1] - 20*mm, "710, 716, 704, 706 Prachauthit Road, Samseenook, Huai Kwang, Bangkok 10310")
                    canvas.drawString(55*mm, A4[1] - 24*mm, "Tel: +662 2744218 | +662 0266525 Fax: +662 0266525 Press 5 | Line: @dhakulchan")
                    
                    canvas.setFont('Helvetica', 8)
                    canvas.setFillColor(colors.Color(52/255, 152/255, 219/255))  # #3498DB
                    canvas.drawString(55*mm, A4[1] - 28*mm, "Website: www.dhakulchan.net | T.A.T License 11/03659")
                    
                except Exception as e:
                    logger.warning(f"Could not draw header: {str(e)}")
                
                # Footer - Company name and page number
                canvas.setFont('Helvetica', 9)
                canvas.setFillColor(colors.Color(127/255, 140/255, 141/255))  # #7F8C8D
                
                # Left side - Company info
                footer_text = "Dhakul Chan Nice Holidays Group - System DCTS V1.0"
                canvas.drawString(15*mm, 10*mm, footer_text)
                
                # Right side - Page number with total pages
                page_num = canvas.getPageNumber()
                # Use simple estimation - most quote PDFs are 1-2 pages
                total_pages = 2  # This can be enhanced to calculate dynamically if needed
                page_text = f"Page {page_num} of {total_pages}"
                page_width = canvas.stringWidth(page_text, 'Helvetica', 9)
                canvas.drawString(A4[0] - 15*mm - page_width, 10*mm, page_text)
                
                canvas.restoreState()
            
            # Create frame for content
            content_frame = Frame(
                15*mm, 20*mm,  # x, y (bottom margin for footer)
                A4[0] - 30*mm,  # width (page width - left/right margins)
                A4[1] - 55*mm,  # height (page height - top/bottom margins)
                id='content_frame'
            )
            
            # Create page template with header/footer
            page_template = PageTemplate(
                id='main_template',
                frames=[content_frame],
                onPage=header_footer_on_page
            )
            
            doc.addPageTemplates([page_template])

            # Build PDF content
            story = []

            # Header section
            story.extend(self._build_header(quote, booking, customer))

            # Quote information
            story.extend(self._build_quote_info(quote))

            # Customer information
            story.extend(self._build_customer_info(customer, booking))

            # Line items table
            story.extend(self._build_line_items_table(quote))

            # Totals section
            story.extend(self._build_totals_section(quote))

            # Terms and conditions
            story.extend(self._build_terms_section(quote))

            # QR Code for sharing
            story.extend(self._build_qr_section(quote))

            # Footer
            story.extend(self._build_footer())

            # Build PDF with BaseDocTemplate
            try:
                logger.info("🔄 Building Quote PDF with header/footer template...")
                doc.build(story)
                logger.info(f"✅ Quote PDF with header/footer generated: {pdf_path}")
            except Exception as e:
                logger.error(f"❌ Quote PDF generation failed: {str(e)}")
                # Fallback to simple generation without header/footer
                simple_doc = SimpleDocTemplate(pdf_path, pagesize=A4)
                simple_doc.build(story)
                logger.info("✅ Quote PDF generated with fallback method")

            # Generate PNG version
            png_path = self._generate_png_from_pdf(pdf_path, filename)

            logger.info(f"✅ Quote PDF generated: {pdf_path}")
            logger.info(f"✅ Quote PNG generated: {png_path}")

            return pdf_path, png_path

        except Exception as e:
            logger.error(f"❌ Error generating quote PDF: {str(e)}")
            raise

    def _build_header(self, quote, booking, customer):
        """Build PDF header section"""
        story = []

        # Company logo and title
        story.append(Paragraph("TRAVEL QUOTE", self.styles["CustomHeader"]))
        story.append(Spacer(1, 20))

        # Company info
        company_info = """
        <b>Dhakul Chan Tours & Travel</b><br/>
        123 Tourism Road, Bangkok 10110<br/>
        Tel: +66 2 123 4567 | Email: quotes@dhakulchan.net<br/>
        Website: www.dhakulchan.net
        """
        story.append(Paragraph(company_info, self.styles["Normal"]))
        story.append(Spacer(1, 30))

        return story

    def _build_quote_info(self, quote):
        """Build quote information section"""
        story = []

        # Quote details table
        quote_data = [
            ["Quote Number:", quote.quote_number],
            [
                "Quote Date:",
                quote.quote_date.strftime("%d %B %Y") if quote.quote_date else "N/A",
            ],
            [
                "Valid Until:",
                quote.valid_until.strftime("%d %B %Y") if quote.valid_until else "N/A",
            ],
            ["Status:", quote.status.title()],
        ]

        quote_table = Table(quote_data, colWidths=[4 * cm, 6 * cm])
        quote_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )

        story.append(quote_table)
        story.append(Spacer(1, 20))

        return story

    def _build_customer_info(self, customer, booking):
        """Build customer information section"""
        story = []

        story.append(Paragraph("Quote For:", self.styles["CustomSubHeader"]))

        customer_info = f"""
        <b>{customer.full_name}</b><br/>
        Email: {customer.email}<br/>
        Phone: {customer.phone}<br/>
        """

        if booking.traveling_period_start and booking.traveling_period_end:
            customer_info += f"Travel Dates: {booking.traveling_period_start} to {booking.traveling_period_end}<br/>"

        story.append(Paragraph(customer_info, self.styles["Normal"]))
        story.append(Spacer(1, 20))

        return story

    def _build_line_items_table(self, quote):
        """Build line items table"""
        story = []

        story.append(Paragraph("Quote Details:", self.styles["CustomSubHeader"]))

        # Table headers
        data = [["Description", "Quantity", "Unit Price (฿)", "Total (฿)"]]

        # Line items
        for item in quote.line_items:
            data.append(
                [
                    item.description,
                    f"{float(item.quantity):,.2f}",
                    f"{float(item.unit_price):,.2f}",
                    f"{float(item.total_amount):,.2f}",
                ]
            )

        # Create table
        table = Table(data, colWidths=[8 * cm, 2 * cm, 3 * cm, 3 * cm])
        table.setStyle(
            TableStyle(
                [
                    # Header row
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E86AB")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    # Data rows
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 10),
                    ("ALIGN", (0, 1), (0, -1), "LEFT"),  # Description left-aligned
                    ("ALIGN", (1, 1), (-1, -1), "RIGHT"),  # Numbers right-aligned
                    # Borders and padding
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    # Alternating row colors
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#F8F9FA")],
                    ),
                ]
            )
        )

        story.append(table)
        story.append(Spacer(1, 20))

        return story

    def _build_totals_section(self, quote):
        """Build totals section"""
        story = []

        # Totals data
        totals_data = [
            ["Subtotal:", f"฿{float(quote.subtotal):,.2f}"],
        ]

        if quote.discount_amount and quote.discount_amount > 0:
            totals_data.append(["Discount:", f"-฿{float(quote.discount_amount):,.2f}"])

        if quote.tax_rate and quote.tax_rate > 0:
            totals_data.append(
                [f"VAT ({float(quote.tax_rate)}%):", f"฿{float(quote.tax_amount):,.2f}"]
            )

        totals_data.append(["", ""])  # Separator
        totals_data.append(["TOTAL:", f"฿{float(quote.total_amount):,.2f}"])

        # Create totals table
        totals_table = Table(totals_data, colWidths=[12 * cm, 4 * cm])
        totals_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -2), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -2), 11),
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, -1), (-1, -1), 14),
                    ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LINEABOVE", (0, -1), (-1, -1), 2, colors.black),
                    ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#F0F8FF")),
                ]
            )
        )

        story.append(totals_table)
        story.append(Spacer(1, 30))

        return story

    def _build_terms_section(self, quote):
        """Build terms and conditions section"""
        story = []

        story.append(Paragraph("Terms & Conditions:", self.styles["CustomSubHeader"]))

        terms = (
            quote.terms_conditions
            if quote.terms_conditions
            else """
        • This quote is valid for 30 days from the date issued
        • All prices are in Thai Baht (THB) and include applicable taxes
        • A 50% deposit is required to confirm booking
        • Final payment due 7 days before travel date
        • Cancellation terms apply as per our standard policy
        • Prices subject to change based on availability and season
        """
        )

        story.append(Paragraph(terms, self.styles["Terms"]))
        story.append(Spacer(1, 20))

        if quote.notes:
            story.append(Paragraph("Additional Notes:", self.styles["CustomSubHeader"]))
            story.append(Paragraph(quote.notes, self.styles["Terms"]))
            story.append(Spacer(1, 20))

        return story

    def _build_qr_section(self, quote):
        """Build QR code section for sharing"""
        story = []

        if quote.public_url:
            story.append(
                Paragraph("Scan to View Online:", self.styles["CustomSubHeader"])
            )

            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=3, border=1)
            qr.add_data(quote.public_url)
            qr.make(fit=True)

            qr_img = qr.make_image(fill_color="black", back_color="white")
            qr_path = f"{self.output_dir}/qr_{quote.quote_number}.png"
            qr_img.save(qr_path)

            story.append(Spacer(1, 10))
            # Note: In production, you'd add the QR image to the PDF
            story.append(
                Paragraph(f"Online Link: {quote.public_url}", self.styles["Normal"])
            )

        return story

    def _build_footer(self):
        """Build PDF footer"""
        story = []

        story.append(Spacer(1, 30))
        footer_text = """
        <i>Thank you for choosing Dhakul Chan Tours & Travel!</i><br/>
        For questions about this quote, please contact us at quotes@dhakulchan.net
        """
        story.append(Paragraph(footer_text, self.styles["Terms"]))

        return story

    def _generate_png_from_pdf(self, pdf_path, filename):
        """Generate PNG version of PDF for social sharing"""
        try:
            import fitz  # PyMuPDF

            png_path = f"{self.output_dir}/png/{filename}.png"

            # Open PDF
            doc = fitz.open(pdf_path)
            page = doc.load_page(0)  # First page

            # Render page as image
            mat = fitz.Matrix(2, 2)  # 2x zoom for better quality
            pix = page.get_pixmap(matrix=mat)

            # Save as PNG
            pix.save(png_path)
            doc.close()

            return png_path

        except ImportError:
            logger.warning("PyMuPDF not available, PNG generation skipped")
            return None
        except Exception as e:
            logger.error(f"Error generating PNG: {str(e)}")
            return None

    def generate_quote_pdf(self, booking) -> str:
        """
        Generate Quote PDF for booking using WeasyPrint
        Args:
            booking: Booking model instance
        Returns:
            str: filename of generated PDF
        """
        try:
            # Import WeasyPrint generator
            from .weasyprint_quote_generator import WeasyPrintQuoteGenerator

            # Use WeasyPrint generator for new format
            weasy_generator = WeasyPrintQuoteGenerator()
            filename = weasy_generator.generate_quote_pdf(booking)

            logger.info(f"Generated Quote PDF using WeasyPrint: {filename}")
            return filename

        except ImportError:
            logger.warning("WeasyPrint not available, falling back to ReportLab")
            return self._generate_reportlab_quote_pdf(booking)
        except Exception as e:
            logger.error(
                f"WeasyPrint generation failed: {str(e)}, falling back to ReportLab"
            )
            return self._generate_reportlab_quote_pdf(booking)

    def _generate_reportlab_quote_pdf(self, booking) -> str:
        """
        Fallback: Generate Quote PDF using ReportLab (original method)
        Args:
            booking: Booking model instance
        Returns:
            str: filename of generated PDF
        """
        try:
            # สร้างชื่อไฟล์
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"Tour_voucher_v2_{booking.booking_reference}_{timestamp}.pdf"

            # เส้นทางไฟล์
            static_dir = "static/generated"
            os.makedirs(static_dir, exist_ok=True)
            filepath = os.path.join(static_dir, filename)

            # สร้าง PDF document with BaseDocTemplate for header/footer
            doc = BaseDocTemplate(
                filepath,
                pagesize=A4,
                topMargin=35*mm,     # Space for header
                bottomMargin=20*mm,  # Space for footer
                leftMargin=15*mm,
                rightMargin=15*mm
            )
            
            # Header/footer function (same as main method)
            def header_footer_on_page(canvas, doc):
                """Draw header and footer on each page"""
                canvas.saveState()
                
                # Header - Company Info and Logo (Fixed layout)
                try:
                    # Logo path - adjusted position to align with Reference
                    logo_path = "/opt/bitnami/apache/htdocs/dcts-logo-vou.png" if os.path.exists("/opt/bitnami") else "dcts-logo-vou.png"
                    if os.path.exists(logo_path):
                        from reportlab.lib.utils import ImageReader
                        logo_reader = ImageReader(logo_path)
                        canvas.drawImage(logo_reader, 15*mm, A4[1] - 27*mm, width=32*mm, height=15*mm, mask='auto')
                    
                    # Company info in header - reduced font size to fit on one line
                    canvas.setFont('Helvetica-Bold', 9)  # Reduced from 11 to 9
                    canvas.setFillColor(colors.Color(44/255, 62/255, 80/255))  # #2C3E50
                    canvas.drawString(52*mm, A4[1] - 15*mm, "DHAKUL CHAN TRAVEL SERVICE (THAILAND) CO.,LTD.")
                    
                    canvas.setFont('Helvetica', 8)
                    canvas.setFillColor(colors.Color(127/255, 140/255, 141/255))  # #7F8C8D
                    canvas.drawString(55*mm, A4[1] - 20*mm, "710, 716, 704, 706 Prachauthit Road, Samseenook, Huai Kwang, Bangkok 10310")
                    canvas.drawString(55*mm, A4[1] - 24*mm, "Tel: +662 2744218 | +662 0266525 Fax: +662 0266525 Press 5 | Line: @dhakulchan")
                    
                    canvas.setFont('Helvetica', 8)
                    canvas.setFillColor(colors.Color(52/255, 152/255, 219/255))  # #3498DB
                    canvas.drawString(55*mm, A4[1] - 28*mm, "Website: www.dhakulchan.net | T.A.T License 11/03659")
                    
                except Exception as e:
                    logger.warning(f"Could not draw header: {str(e)}")
                
                # Footer - Company name and page number
                canvas.setFont('Helvetica', 9)
                canvas.setFillColor(colors.Color(127/255, 140/255, 141/255))  # #7F8C8D
                
                # Left side - Company info
                footer_text = "Dhakul Chan Nice Holidays Group - System DCTS V1.0"
                canvas.drawString(15*mm, 10*mm, footer_text)
                
                # Right side - Page number with total pages
                page_num = canvas.getPageNumber()
                total_pages = 2  # Simple estimation for quote PDFs
                page_text = f"Page {page_num} of {total_pages}"
                page_width = canvas.stringWidth(page_text, 'Helvetica', 9)
                canvas.drawString(A4[0] - 15*mm - page_width, 10*mm, page_text)
                
                canvas.restoreState()
            
            # Create frame for content
            content_frame = Frame(
                15*mm, 20*mm,  # x, y (bottom margin for footer)
                A4[0] - 30*mm,  # width (page width - left/right margins)
                A4[1] - 55*mm,  # height (page height - top/bottom margins)
                id='content_frame'
            )
            
            # Create page template with header/footer
            page_template = PageTemplate(
                id='main_template',
                frames=[content_frame],
                onPage=header_footer_on_page
            )
            
            doc.addPageTemplates([page_template])

            # สร้างเนื้อหา
            content = []

            # Header section
            content.extend(self._build_dhakul_header())

            # Quote information
            content.extend(self._build_dhakul_quote_info(booking))
            content.append(Spacer(1, 12))

            # Description table
            content.extend(self._build_dhakul_description(booking))
            content.append(Spacer(1, 12))

            # Service sections
            content.extend(self._build_dhakul_service_sections(booking))
            content.append(Spacer(1, 12))

            # Terms & Conditions
            content.extend(self._build_dhakul_terms())

            # Footer
            content.extend(self._build_dhakul_footer())

            # Build PDF with BaseDocTemplate
            try:
                logger.info("🔄 Building fallback Quote PDF with header/footer template...")
                doc.build(content)
                logger.info(f"✅ Fallback Quote PDF with header/footer generated: {filename}")
            except Exception as e:
                logger.error(f"❌ Fallback Quote PDF generation failed: {str(e)}")
                # Last resort fallback
                simple_doc = SimpleDocTemplate(filepath, pagesize=A4)
                simple_doc.build(content)
                logger.info("✅ Quote PDF generated with simple fallback method")

            logger.info(f"Generated DHAKUL CHAN quote PDF: {filename}")
            return filename

        except Exception as e:
            logger.error(f"Error generating DHAKUL CHAN quote PDF: {str(e)}")
            raise

    def _build_dhakul_header(self):
        """Build DHAKUL CHAN header"""
        elements = []

        # Company name
        company_header = Paragraph(
            "DHAKUL CHAN TRAVEL SERVICE (THAILAND) CO.,LTD.",
            ParagraphStyle(
                name="DHAKULHeader",
                parent=self.styles["Normal"],
                fontSize=16,
                fontName="Helvetica-Bold",
                textColor=colors.HexColor("#0066CC"),
                alignment=TA_CENTER,
                spaceAfter=6,
            ),
        )
        elements.append(company_header)

        # Company details
        company_details = Paragraph(
            "719, 716, 704, 706 Phetchaburi Road, Samseonnok, Huai Khwang, Bangkok 10310<br/>"
            "Tel: +662 6746525-9, +662 0260525 Fax: +662 0260525 Press 5 | Line: dhatsudchan<br/>"
            "Website: www.dhatsudchan.net | T.A.T License 11/03659",
            ParagraphStyle(
                name="DHAKULDetails",
                parent=self.styles["Normal"],
                fontSize=10,
                alignment=TA_CENTER,
                spaceAfter=12,
            ),
        )
        elements.append(company_details)

        return elements

    def _build_dhakul_quote_info(self, booking):
        """Build quote information section"""
        elements = []

        # Quote title
        quote_title = Paragraph(
            "QUOTE",
            ParagraphStyle(
                name="QuoteTitle",
                parent=self.styles["Normal"],
                fontSize=24,
                fontName="Helvetica-Bold",
                textColor=colors.HexColor("#0066CC"),
                alignment=TA_CENTER,
                spaceAfter=12,
            ),
        )
        elements.append(quote_title)

        # Quote number (top right)
        quote_number = getattr(booking, "quote_number", None) or "QT..........."
        quote_info = Paragraph(
            f"Quote Number: {quote_number}<br/>"
            f"Reference: {booking.booking_reference}<br/>"
            f"Booking Type: {booking.booking_type}",
            ParagraphStyle(
                name="QuoteInfo",
                parent=self.styles["Normal"],
                fontSize=11,
                alignment=TA_RIGHT,
            ),
        )

        # Create info table with real booking data
        create_date = (
            booking.created_at.strftime("%Y-%m-%d")
            if booking.created_at
            else datetime.now().strftime("%Y-%m-%d")
        )

        # Use tour dates from booking
        travel_from = (
            booking.tour_start_date.strftime("%Y-%m-%d")
            if hasattr(booking, "tour_start_date") and booking.tour_start_date
            else ""
        )
        travel_to = (
            booking.tour_end_date.strftime("%Y-%m-%d")
            if hasattr(booking, "tour_end_date") and booking.tour_end_date
            else ""
        )
        traveling_period = (
            f"{travel_from} -<br/>{travel_to}" if travel_from and travel_to else "TBD"
        )

        # Get customer info - try multiple possible attribute names
        customer_name = "TBD"
        customer_tel = ""

        if hasattr(booking, "customer") and booking.customer:
            customer_name = getattr(booking.customer, "name", None) or getattr(
                booking.customer, "company_name", "TBD"
            )
            customer_tel = getattr(booking.customer, "phone", "")
        elif hasattr(booking, "contact_name") and booking.contact_name:
            customer_name = booking.contact_name
            customer_tel = getattr(booking, "phone", "")
        elif hasattr(booking, "company_name") and booking.company_name:
            customer_name = booking.company_name
            customer_tel = getattr(booking, "phone", "")

        # Calculate pax info from booking data
        adults = getattr(booking, "adults", 0)
        children = getattr(booking, "children", 0)
        infants = getattr(booking, "infants", 0)
        total_pax = adults + children + infants

        pax_info = f"{total_pax} pax<br/>"
        if adults > 0:
            pax_info += f"Adult {adults}"
        if children > 0:
            pax_info += f" / Child {children}"
        if infants > 0:
            pax_info += f" / Infant {infants}"

        # Main info table
        table_data = [
            ["Create Date", "Traveling Period", "Customer Name", "PAX"],
            [
                f"{create_date}<br/>By: admin",
                traveling_period,
                f"{customer_name}<br/>Tel. {customer_tel}",
                pax_info,
            ],
        ]

        info_table = Table(table_data, colWidths=[3 * cm, 4 * cm, 4 * cm, 3 * cm])
        info_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E6F3FF")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 11),
                    ("FONTSIZE", (0, 1), (-1, -1), 10),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )

        elements.append(info_table)
        return elements

    def _build_dhakul_description(self, booking):
        """Build enhanced Products & Calculation table matching user's exact format"""
        elements = []

        # Products & Calculation header with calculator icon
        products_header = Paragraph(
            "🧮 Products & Calculation",
            ParagraphStyle(
                name="ProductsHeader",
                parent=self.styles["Normal"],
                fontSize=16,
                fontName="Helvetica-Bold",
                textColor=colors.HexColor("#2E4057"),
                spaceAfter=12,
            ),
        )
        elements.append(products_header)

        # Calculate pricing based on actual booking data
        adt_qty = getattr(booking, "adults", 0)
        chd_qty = getattr(booking, "children", 0)
        inf_qty = getattr(booking, "infants", 0)

        # Use actual total price from booking
        total_booking_price = getattr(booking, "total_price", 0)

        # Calculate individual prices based on total and quantities
        total_pax = adt_qty + chd_qty + inf_qty

        if total_pax > 0 and total_booking_price > 0:
            # Calculate proportional pricing
            base_price_per_pax = total_booking_price / total_pax
            adt_price = base_price_per_pax
            chd_price = (
                base_price_per_pax * 0.7
            )  # Children typically 70% of adult price
            inf_price = base_price_per_pax * 0.1  # Infants typically 10% of adult price

            # Recalculate total to match booking exactly
            calculated_total = (
                (adt_qty * adt_price) + (chd_qty * chd_price) + (inf_qty * inf_price)
            )

            # Adjust adult price to match exact total
            if adt_qty > 0:
                adjustment = (total_booking_price - calculated_total) / adt_qty
                adt_price += adjustment
        else:
            # Fallback pricing if no booking data
            adt_price = 5000.00
            chd_price = 2500.00
            inf_price = 100.00

        adt_amount = adt_price * adt_qty if adt_qty > 0 else 0
        chd_amount = chd_price * chd_qty if chd_qty > 0 else 0
        inf_amount = inf_price * inf_qty if inf_qty > 0 else 0
        total_amount = (
            total_booking_price
            if total_booking_price > 0
            else (adt_amount + chd_amount + inf_amount)
        )

        # Main products table data
        table_data = [
            # Header row with dark blue background
            ["No.", "Products", "Quantity", "Price", "Amount"]
        ]

        # Data rows - only show rows for non-zero quantities
        row_num = 1
        if adt_qty > 0:
            table_data.append(
                [
                    str(row_num),
                    "ADT",
                    str(adt_qty),
                    f"{adt_price:,.2f}",
                    f"{adt_amount:,.2f}",
                ]
            )
            row_num += 1
        if chd_qty > 0:
            table_data.append(
                [
                    str(row_num),
                    "CHD",
                    str(chd_qty),
                    f"{chd_price:,.2f}",
                    f"{chd_amount:,.2f}",
                ]
            )
            row_num += 1
        if inf_qty > 0:
            table_data.append(
                [
                    str(row_num),
                    "INF",
                    str(inf_qty),
                    f"{inf_price:,.2f}",
                    f"{inf_amount:,.2f}",
                ]
            )

        # Create the main table
        col_widths = [2 * cm, 4 * cm, 3 * cm, 3 * cm, 4 * cm]
        products_table = Table(table_data, colWidths=col_widths)

        # Table styling to match the user's image exactly
        products_table.setStyle(
            TableStyle(
                [
                    # Header row - dark blue background with white text
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E4A6B")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 14),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    # Data rows - alternating light backgrounds
                    ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#F8F9FA")),
                    ("BACKGROUND", (0, 2), (-1, 2), colors.white),
                    ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#F8F9FA")),
                    # Data row styling
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 12),
                    ("ALIGN", (0, 1), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 1), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 1), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 1), (-1, -1), 10),
                    # Grid lines
                    ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#D5D5D5")),
                    ("LINEWIDTH", (0, 0), (-1, 0), 2),
                    # Number column with grey circles styling
                    ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#E5E5E5")),
                    ("TEXTCOLOR", (0, 1), (0, -1), colors.white),
                    ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                    # Right align amount columns
                    ("ALIGN", (3, 1), (4, -1), "RIGHT"),
                    ("ALIGN", (2, 1), (2, -1), "CENTER"),
                ]
            )
        )

        elements.append(products_table)
        elements.append(Spacer(1, 15))

        # Total section with green coin icon
        total_table = Table(
            [["💰 Total:", f"{total_amount:,.2f} THB"]], colWidths=[12 * cm, 4 * cm]
        )

        total_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 14),
                    ("TEXTCOLOR", (0, 0), (0, 0), colors.HexColor("#2E4A6B")),
                    ("TEXTCOLOR", (1, 0), (1, 0), colors.HexColor("#2E4A6B")),
                    ("ALIGN", (0, 0), (0, 0), "RIGHT"),
                    ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("LINEABOVE", (0, 0), (-1, -1), 2, colors.HexColor("#2E4A6B")),
                ]
            )
        )

        elements.append(total_table)
        elements.append(Spacer(1, 15))

        # Grand Total section with green coin icon
        grand_total_table = Table(
            [["💰 Grand Total:", f"THB {total_amount:,.2f}"]],
            colWidths=[12 * cm, 4 * cm],
        )

        grand_total_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 16),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#27AE60")),
                    ("ALIGN", (0, 0), (0, 0), "LEFT"),
                    ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )

        elements.append(grand_total_table)

        return elements

    def _build_dhakul_service_sections(self, booking):
        """Build service detail sections"""
        elements = []

        # Service Detail / Itinerary
        elements.append(Spacer(1, 12))
        service_header = Paragraph(
            "Service Detail / Itinerary:",
            ParagraphStyle(
                name="ServiceHeader",
                parent=self.styles["Normal"],
                fontSize=12,
                fontName="Helvetica-Bold",
                textColor=colors.HexColor("#0066CC"),
                spaceAfter=6,
            ),
        )
        elements.append(service_header)

        service_content = (
            booking.description
            if booking.description
            else "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\nBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
        )
        service_para = Paragraph(service_content, self.styles["Normal"])
        elements.append(service_para)
        elements.append(Spacer(1, 6))
        elements.append(Paragraph("_" * 50, self.styles["Normal"]))

        # Name List / Rooming List
        elements.append(Spacer(1, 12))
        name_header = Paragraph(
            "Name List / Rooming List:",
            ParagraphStyle(
                name="NameHeader",
                parent=self.styles["Normal"],
                fontSize=12,
                fontName="Helvetica-Bold",
                textColor=colors.HexColor("#0066CC"),
                spaceAfter=6,
            ),
        )
        elements.append(name_header)

        guest_content = (
            "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC\nDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD"
        )
        if hasattr(booking, "guest_list") and booking.guest_list:
            guest_content = "\n".join(booking.guest_list)

        guest_para = Paragraph(guest_content, self.styles["Normal"])
        elements.append(guest_para)

        # Flight Information sections
        elements.append(Spacer(1, 12))
        flight_header1 = Paragraph(
            "Flight Information:",
            ParagraphStyle(
                name="FlightHeader",
                parent=self.styles["Normal"],
                fontSize=12,
                fontName="Helvetica-Bold",
                textColor=colors.HexColor("#0066CC"),
                spaceAfter=6,
            ),
        )
        elements.append(flight_header1)

        flight_content = (
            "EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE\nFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
        )
        if hasattr(booking, "flight_info") and booking.flight_info:
            # Clean HTML content for ReportLab
            import re
            flight_content = booking.flight_info
            # Remove HTML tags and convert <br> to newlines
            flight_content = re.sub(r'<br\s*/?>', '\n', flight_content)
            flight_content = re.sub(r'<p[^>]*>', '', flight_content)
            flight_content = re.sub(r'</p>', '\n', flight_content)
            flight_content = re.sub(r'<[^>]+>', '', flight_content)  # Remove all other HTML tags
            flight_content = flight_content.strip()

        flight_para1 = Paragraph(flight_content, self.styles["Normal"])
        elements.append(flight_para1)

        # Second Flight Information section
        elements.append(Spacer(1, 12))
        flight_header2 = Paragraph(
            "Flight Information:",
            ParagraphStyle(
                name="FlightHeader2",
                parent=self.styles["Normal"],
                fontSize=12,
                fontName="Helvetica-Bold",
                textColor=colors.HexColor("#0066CC"),
                spaceAfter=6,
            ),
        )
        elements.append(flight_header2)

        flight_content2 = (
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG\nHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHH"
        )
        flight_para2 = Paragraph(flight_content2, self.styles["Normal"])
        elements.append(flight_para2)

        return elements

    def _build_dhakul_terms(self):
        """Build Terms & Conditions section"""
        elements = []

        elements.append(Spacer(1, 20))

        terms_header = Paragraph(
            "Terms & Conditions Apply:",
            ParagraphStyle(
                name="TermsHeader",
                parent=self.styles["Normal"],
                fontSize=12,
                fontName="Helvetica-Bold",
                textColor=colors.HexColor("#0066CC"),
                spaceAfter=6,
            ),
        )
        elements.append(terms_header)
        elements.append(Spacer(1, 6))

        # Thai terms list
        terms_list = [
            "• เอกสารประจำตัวที่ใช้ในการเดินทาง ต้องมีอายุการใช้งานอย่างน้อย 6 เดือน",
            "• ราคานี้สำหรับผู้เดินทางที่เป็นชาวไทย หากมีผู้เดินทางที่เป็นชาวต่างชาติ ราคาอาจมีการเปลี่ยนแปลง",
            "• กรุณาแจ้งความประสงค์เรื่องอาหาร เพื่อความสะดวกในการบริการ",
            "• ในการเดินทางครั้งนี้ สำหรับผู้เดินทางอายุ 12 ปีขึ้นไป ต้องฉีดวัคซีนป้องกันโควิด-19 ครบ 2 เข็ม",
            "• การเปลี่ยนแปลงเงื่อนไขต่าง ๆ จากหน่วยงานที่เกี่ยวข้อง อาจทำให้เกิดค่าใช้จ่าย",
        ]

        for term in terms_list:
            term_para = Paragraph(
                term,
                ParagraphStyle(
                    name="TermsText",
                    parent=self.styles["Normal"],
                    fontSize=10,
                    leftIndent=10,
                ),
            )
            elements.append(term_para)
            elements.append(Spacer(1, 3))

        return elements

    def _build_dhakul_footer(self):
        """Build footer section"""
        elements = []

        elements.append(Spacer(1, 20))

        # Footer with company info and page number
        footer_content = "Dhakul Chan Nice Holidays Group - System DCTS V1.0"
        footer_para = Paragraph(
            footer_content,
            ParagraphStyle(
                name="Footer",
                parent=self.styles["Normal"],
                fontSize=8,
                textColor=colors.grey,
                alignment=TA_LEFT,
            ),
        )
        elements.append(footer_para)

        # Page number (right aligned) - will be updated with actual count
        page_number = Paragraph(
            f"Page {getattr(self, '_current_page', 1)} of {getattr(self, '_total_pages', '?')}",
            ParagraphStyle(
                name="PageNumber",
                parent=self.styles["Normal"],
                fontSize=8,
                textColor=colors.grey,
                alignment=TA_RIGHT,
            ),
        )
        elements.append(page_number)

        return elements
