"""
Enhanced PDF Generator for Invoices with social media sharing capabilities
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
import qrcode
import logging

logger = logging.getLogger(__name__)


class InvoicePDFGenerator:
    """Enhanced Invoice PDF Generator with payment tracking and sharing capabilities"""

    def __init__(self):
        # Adaptive output directory based on environment
        if os.path.exists("/opt/bitnami"):
            # Production environment
            self.output_dir = "/opt/bitnami/apache/htdocs/static/generated/invoices"
            self.static_dir = "/opt/bitnami/apache/htdocs/static"
        else:
            # Local development environment
            self.output_dir = "static/generated/invoices"
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
                fontSize=26,
                textColor=colors.HexColor("#DC3545"),  # Red for invoices
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
                textColor=colors.HexColor("#6F42C1"),
                alignment=TA_LEFT,
                spaceBefore=15,
                spaceAfter=10,
            )
        )

        # Invoice info style
        self.styles.add(
            ParagraphStyle(
                name="InvoiceInfo",
                parent=self.styles["Normal"],
                fontSize=10,
                textColor=colors.black,
                alignment=TA_RIGHT,
                rightIndent=20,
            )
        )

        # Payment status style
        self.styles.add(
            ParagraphStyle(
                name="PaymentStatus",
                parent=self.styles["Normal"],
                fontSize=12,
                textColor=colors.HexColor("#28A745"),  # Green for paid
                alignment=TA_CENTER,
                spaceBefore=10,
                spaceAfter=10,
            )
        )

        # Overdue style
        self.styles.add(
            ParagraphStyle(
                name="OverdueStatus",
                parent=self.styles["Normal"],
                fontSize=12,
                textColor=colors.HexColor("#DC3545"),  # Red for overdue
                alignment=TA_CENTER,
                spaceBefore=10,
                spaceAfter=10,
            )
        )

    def generate_invoice_pdf(self, invoice, booking, customer):
        """
        Generate comprehensive Invoice PDF with payment tracking

        Args:
            invoice: Invoice model instance
            booking: Booking model instance
            customer: Customer model instance

        Returns:
            tuple: (pdf_path, png_path) - Paths to generated documents
        """
        try:
            # Generate filename
            filename = f"invoice_{invoice.invoice_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            pdf_path = f"{self.output_dir}/{filename}.pdf"

            # Create PDF document
            doc = SimpleDocTemplate(
                pdf_path,
                pagesize=A4,
                rightMargin=2 * cm,
                leftMargin=2 * cm,
                topMargin=2 * cm,
                bottomMargin=2 * cm,
            )

            # Build PDF content
            story = []

            # Header section
            story.extend(self._build_header(invoice, booking, customer))

            # Invoice information
            story.extend(self._build_invoice_info(invoice))

            # Payment status banner
            story.extend(self._build_payment_status_banner(invoice))

            # Customer information
            story.extend(self._build_customer_info(customer, booking))

            # Line items table
            story.extend(self._build_line_items_table(invoice))

            # Totals section
            story.extend(self._build_totals_section(invoice))

            # Payment summary
            story.extend(self._build_payment_summary(invoice))

            # Payment instructions
            story.extend(self._build_payment_instructions(invoice))

            # Terms and conditions
            story.extend(self._build_terms_section(invoice))

            # QR Code for sharing
            story.extend(self._build_qr_section(invoice))

            # Footer
            story.extend(self._build_footer())

            # Build PDF
            doc.build(story)

            # Generate PNG version
            png_path = self._generate_png_from_pdf(pdf_path, filename)

            logger.info(f"✅ Invoice PDF generated: {pdf_path}")
            logger.info(f"✅ Invoice PNG generated: {png_path}")

            return pdf_path, png_path

        except Exception as e:
            logger.error(f"❌ Error generating invoice PDF: {str(e)}")
            raise

    def _build_header(self, invoice, booking, customer):
        """Build PDF header section"""
        story = []

        # Company logo and title
        story.append(Paragraph("TAX INVOICE", self.styles["CustomHeader"]))
        story.append(Spacer(1, 20))

        # Company info
        company_info = """
        <b>Dhakul Chan Tours & Travel Co., Ltd.</b><br/>
        Tax ID: 0123456789012<br/>
        123 Tourism Road, Bangkok 10110, Thailand<br/>
        Tel: +66 2 123 4567 | Email: billing@dhakulchan.net<br/>
        Website: www.dhakulchan.net
        """
        story.append(Paragraph(company_info, self.styles["Normal"]))
        story.append(Spacer(1, 30))

        return story

    def _build_invoice_info(self, invoice):
        """Build invoice information section"""
        story = []

        # Invoice details table
        invoice_data = [
            ["Invoice Number:", invoice.invoice_number],
            [
                "Invoice Date:",
                (
                    invoice.invoice_date.strftime("%d %B %Y")
                    if invoice.invoice_date
                    else "N/A"
                ),
            ],
            [
                "Due Date:",
                invoice.due_date.strftime("%d %B %Y") if invoice.due_date else "N/A",
            ],
            ["Payment Terms:", "Net 30 Days"],
        ]

        if invoice.quote_id:
            invoice_data.insert(1, ["Quote Reference:", f"Quote #{invoice.quote_id}"])

        invoice_table = Table(invoice_data, colWidths=[4 * cm, 6 * cm])
        invoice_table.setStyle(
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

        story.append(invoice_table)
        story.append(Spacer(1, 20))

        return story

    def _build_payment_status_banner(self, invoice):
        """Build payment status banner"""
        story = []

        if invoice.payment_status == "paid":
            status_text = "✅ PAID IN FULL"
            if invoice.paid_date:
                status_text += f" - {invoice.paid_date.strftime('%d %B %Y')}"
            story.append(Paragraph(status_text, self.styles["PaymentStatus"]))

        elif invoice.payment_status == "partial":
            paid_amount = float(invoice.paid_amount) if invoice.paid_amount else 0
            balance_due = float(invoice.balance_due) if invoice.balance_due else 0
            status_text = f"⚠️ PARTIALLY PAID - Balance Due: ฿{balance_due:,.2f}"
            story.append(Paragraph(status_text, self.styles["OverdueStatus"]))

        elif invoice.due_date and invoice.due_date < datetime.now().date():
            balance_due = (
                float(invoice.balance_due)
                if invoice.balance_due
                else float(invoice.total_amount)
            )
            status_text = f"🚨 OVERDUE - Amount Due: ฿{balance_due:,.2f}"
            story.append(Paragraph(status_text, self.styles["OverdueStatus"]))

        story.append(Spacer(1, 15))

        return story

    def _build_customer_info(self, customer, booking):
        """Build customer information section"""
        story = []

        story.append(Paragraph("Bill To:", self.styles["CustomSubHeader"]))

        customer_info = f"""
        <b>{customer.full_name}</b><br/>
        Email: {customer.email}<br/>
        Phone: {customer.phone}<br/>
        """

        if booking.traveling_period_start and booking.traveling_period_end:
            customer_info += f"Service Period: {booking.traveling_period_start} to {booking.traveling_period_end}<br/>"

        story.append(Paragraph(customer_info, self.styles["Normal"]))
        story.append(Spacer(1, 20))

        return story

    def _build_line_items_table(self, invoice):
        """Build line items table"""
        story = []

        story.append(Paragraph("Invoice Details:", self.styles["CustomSubHeader"]))

        # Table headers
        data = [["Description", "Quantity", "Unit Price (฿)", "Total (฿)"]]

        # Line items
        for item in invoice.line_items:
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
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DC3545")),
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

    def _build_totals_section(self, invoice):
        """Build totals section"""
        story = []

        # Totals data
        totals_data = [
            ["Subtotal:", f"฿{float(invoice.subtotal):,.2f}"],
        ]

        if invoice.discount_amount and invoice.discount_amount > 0:
            totals_data.append(
                ["Discount:", f"-฿{float(invoice.discount_amount):,.2f}"]
            )

        if invoice.tax_rate and invoice.tax_rate > 0:
            totals_data.append(
                [
                    f"VAT ({float(invoice.tax_rate)}%):",
                    f"฿{float(invoice.tax_amount):,.2f}",
                ]
            )

        totals_data.append(["", ""])  # Separator
        totals_data.append(["TOTAL AMOUNT:", f"฿{float(invoice.total_amount):,.2f}"])

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
                    ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#FFE6E6")),
                ]
            )
        )

        story.append(totals_table)
        story.append(Spacer(1, 20))

        return story

    def _build_payment_summary(self, invoice):
        """Build payment summary section"""
        story = []

        if invoice.payments:
            story.append(Paragraph("Payment History:", self.styles["CustomSubHeader"]))

            # Payment history table
            payment_data = [["Payment Date", "Method", "Amount (฿)", "Reference"]]

            for payment in invoice.payments:
                payment_data.append(
                    [
                        (
                            payment.payment_date.strftime("%d %B %Y")
                            if payment.payment_date
                            else "N/A"
                        ),
                        payment.payment_method or "N/A",
                        f"฿{float(payment.amount):,.2f}",
                        payment.reference or "N/A",
                    ]
                )

            payment_table = Table(
                payment_data, colWidths=[3 * cm, 3 * cm, 3 * cm, 7 * cm]
            )
            payment_table.setStyle(
                TableStyle(
                    [
                        # Header row
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#28A745")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 10),
                        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                        # Data rows
                        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 1), (-1, -1), 9),
                        ("ALIGN", (0, 1), (2, -1), "CENTER"),
                        ("ALIGN", (3, 1), (3, -1), "LEFT"),
                        # Borders and padding
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ]
                )
            )

            story.append(payment_table)

            # Balance summary
            paid_amount = float(invoice.paid_amount) if invoice.paid_amount else 0
            balance_due = float(invoice.balance_due) if invoice.balance_due else 0

            balance_data = [
                ["Total Paid:", f"฿{paid_amount:,.2f}"],
                ["Balance Due:", f"฿{balance_due:,.2f}"],
            ]

            balance_table = Table(balance_data, colWidths=[12 * cm, 4 * cm])
            balance_table.setStyle(
                TableStyle(
                    [
                        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 11),
                        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                        ("LINEABOVE", (0, 0), (-1, -1), 1, colors.black),
                    ]
                )
            )

            story.append(Spacer(1, 10))
            story.append(balance_table)

        story.append(Spacer(1, 20))

        return story

    def _build_payment_instructions(self, invoice):
        """Build payment instructions section"""
        story = []

        if invoice.payment_status != "paid":
            story.append(
                Paragraph("Payment Instructions:", self.styles["CustomSubHeader"])
            )

            payment_info = """
            <b>Bank Transfer:</b><br/>
            Bank: Bangkok Bank<br/>
            Account Name: Dhakul Chan Tours & Travel Co., Ltd.<br/>
            Account Number: 123-456-7890<br/>
            Swift Code: BKKBTHBK<br/><br/>

            <b>Please include:</b><br/>
            • Invoice number in transfer description<br/>
            • Email payment confirmation to billing@dhakulchan.net<br/>
            • Include your booking reference number
            """

            story.append(Paragraph(payment_info, self.styles["Normal"]))
            story.append(Spacer(1, 20))

        return story

    def _build_terms_section(self, invoice):
        """Build terms and conditions section"""
        story = []

        story.append(Paragraph("Terms & Conditions:", self.styles["CustomSubHeader"]))

        terms = (
            invoice.terms_conditions
            if invoice.terms_conditions
            else """
        • Payment is due within 30 days of invoice date
        • Late payment may incur interest charges of 1.5% per month
        • All prices are in Thai Baht (THB) and include VAT as shown
        • Services are subject to our standard terms and conditions
        • Disputes must be raised within 7 days of invoice date
        """
        )

        story.append(Paragraph(terms, self.styles["Terms"]))
        story.append(Spacer(1, 20))

        if invoice.notes:
            story.append(Paragraph("Additional Notes:", self.styles["CustomSubHeader"]))
            story.append(Paragraph(invoice.notes, self.styles["Terms"]))
            story.append(Spacer(1, 20))

        return story

    def _build_qr_section(self, invoice):
        """Build QR code section for sharing"""
        story = []

        if invoice.public_url:
            story.append(
                Paragraph("View Online or Share:", self.styles["CustomSubHeader"])
            )

            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=3, border=1)
            qr.add_data(invoice.public_url)
            qr.make(fit=True)

            qr_img = qr.make_image(fill_color="black", back_color="white")
            qr_path = f"{self.output_dir}/qr_{invoice.invoice_number}.png"
            qr_img.save(qr_path)

            story.append(Spacer(1, 10))
            story.append(
                Paragraph(f"Online Link: {invoice.public_url}", self.styles["Normal"])
            )

        return story

    def _build_footer(self):
        """Build PDF footer"""
        story = []

        story.append(Spacer(1, 30))
        footer_text = """
        <i>Thank you for your business!</i><br/>
        For billing inquiries, please contact us at billing@dhakulchan.net or +66 2 123 4567
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
