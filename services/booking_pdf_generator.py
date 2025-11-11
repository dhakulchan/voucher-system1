"""
Enhanced Booking PDF Generator with comprehensive booking information and social sharing
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
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime
import qrcode
import logging

logger = logging.getLogger(__name__)


class BookingPDFGenerator:
    """Enhanced Booking PDF Generator with workflow status and sharing capabilities"""

    def __init__(self):
        # Adaptive output directory based on environment
        if os.path.exists("/opt/bitnami"):
            # Production environment
            self.output_dir = "/opt/bitnami/apache/htdocs/static/generated/bookings"
            self.static_dir = "/opt/bitnami/apache/htdocs/static"
        else:
            # Local development environment
            self.output_dir = "static/generated/bookings"
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
                textColor=colors.HexColor("#17A2B8"),  # Info blue for bookings
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
                textColor=colors.HexColor("#20C997"),  # Teal
                alignment=TA_LEFT,
                spaceBefore=15,
                spaceAfter=10,
            )
        )

        # Status style
        self.styles.add(
            ParagraphStyle(
                name="StatusStyle",
                parent=self.styles["Normal"],
                fontSize=14,
                textColor=colors.HexColor("#FD7E14"),  # Orange
                alignment=TA_CENTER,
                spaceBefore=10,
                spaceAfter=10,
            )
        )

        # Workflow style
        self.styles.add(
            ParagraphStyle(
                name="WorkflowStyle",
                parent=self.styles["Normal"],
                fontSize=10,
                textColor=colors.HexColor("#6C757D"),  # Gray
                alignment=TA_LEFT,
                leftIndent=20,
                rightIndent=20,
            )
        )

    def generate_booking_pdf(self, booking, customer, vendor=None):
        """
        Generate comprehensive Booking PDF with workflow tracking

        Args:
            booking: Booking model instance
            customer: Customer model instance
            vendor: Vendor model instance (optional)

        Returns:
            tuple: (pdf_path, png_path) - Paths to generated documents
        """
        try:
            # Generate filename
            filename = f"booking_{booking.booking_reference}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
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
            story.extend(self._build_header(booking, customer))

            # Booking status and workflow
            story.extend(self._build_status_section(booking))

            # Booking information
            story.extend(self._build_booking_info(booking))

            # Customer information
            story.extend(self._build_customer_info(customer))

            # Travel details
            story.extend(self._build_travel_details(booking))

            # Pricing information
            story.extend(self._build_pricing_section(booking))

            # Vendor information
            if vendor:
                story.extend(self._build_vendor_info(vendor))

            # Workflow progress
            story.extend(self._build_workflow_progress(booking))

            # Additional services
            story.extend(self._build_additional_services(booking))

            # QR Code for sharing
            story.extend(self._build_qr_section(booking))

            # Footer
            story.extend(self._build_footer())

            # Build PDF
            doc.build(story)

            # Generate PNG version
            png_path = self._generate_png_from_pdf(pdf_path, filename)

            logger.info(f"✅ Booking PDF generated: {pdf_path}")
            logger.info(f"✅ Booking PNG generated: {png_path}")

            return pdf_path, png_path

        except Exception as e:
            logger.error(f"❌ Error generating booking PDF: {str(e)}")
            raise

    def _build_header(self, booking, customer):
        """Build PDF header section"""
        story = []

        # Company logo and title
        story.append(Paragraph("BOOKING CONFIRMATION", self.styles["CustomHeader"]))
        story.append(Spacer(1, 20))

        # Company info
        company_info = """
        <b>Dhakul Chan Tours & Travel</b><br/>
        Your Premium Travel Experience<br/>
        123 Tourism Road, Bangkok 10110<br/>
        Tel: +66 2 123 4567 | Email: bookings@dhakulchan.net<br/>
        Website: www.dhakulchan.net
        """
        story.append(Paragraph(company_info, self.styles["Normal"]))
        story.append(Spacer(1, 30))

        return story

    def _build_status_section(self, booking):
        """Build booking status section"""
        story = []

        # Status banner
        status_text = f"Status: {booking.status.upper().replace('_', ' ')}"
        story.append(Paragraph(status_text, self.styles["StatusStyle"]))

        # Workflow indicators
        workflow_status = self._get_workflow_status(booking)
        story.append(Paragraph(workflow_status, self.styles["WorkflowStyle"]))
        story.append(Spacer(1, 20))

        return story

    def _build_booking_info(self, booking):
        """Build booking information section"""
        story = []

        story.append(Paragraph("Booking Information:", self.styles["CustomSubHeader"]))

        # Booking details table
        booking_data = [
            ["Booking Reference:", booking.booking_reference],
            [
                "Booking Type:",
                booking.booking_type.title() if booking.booking_type else "N/A",
            ],
            [
                "Booking Date:",
                (
                    booking.created_at.strftime("%d %B %Y")
                    if booking.created_at
                    else "N/A"
                ),
            ],
            ["Status:", booking.status.title().replace("_", " ")],
        ]

        if booking.confirmed_at:
            booking_data.append(
                ["Confirmed Date:", booking.confirmed_at.strftime("%d %B %Y")]
            )

        booking_table = Table(booking_data, colWidths=[5 * cm, 7 * cm])
        booking_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.gray),
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F8F9FA")),
                ]
            )
        )

        story.append(booking_table)
        story.append(Spacer(1, 20))

        return story

    def _build_customer_info(self, customer):
        """Build customer information section"""
        story = []

        story.append(Paragraph("Customer Information:", self.styles["CustomSubHeader"]))

        customer_info = f"""
        <b>Name:</b> {customer.full_name}<br/>
        <b>Email:</b> {customer.email}<br/>
        <b>Phone:</b> {customer.phone}<br/>
        """

        if hasattr(customer, "address") and customer.address:
            customer_info += f"<b>Address:</b> {customer.address}<br/>"

        if hasattr(customer, "nationality") and customer.nationality:
            customer_info += f"<b>Nationality:</b> {customer.nationality}<br/>"

        story.append(Paragraph(customer_info, self.styles["Normal"]))
        story.append(Spacer(1, 20))

        return story

    def _build_travel_details(self, booking):
        """Build travel details section"""
        story = []

        story.append(Paragraph("Travel Details:", self.styles["CustomSubHeader"]))

        # Travel information table
        travel_data = []

        if booking.arrival_date:
            travel_data.append(
                ["Arrival Date:", booking.arrival_date.strftime("%d %B %Y")]
            )

        if booking.departure_date:
            travel_data.append(
                ["Departure Date:", booking.departure_date.strftime("%d %B %Y")]
            )

        if booking.traveling_period_start:
            travel_data.append(
                ["Travel Start:", booking.traveling_period_start.strftime("%d %B %Y")]
            )

        if booking.traveling_period_end:
            travel_data.append(
                ["Travel End:", booking.traveling_period_end.strftime("%d %B %Y")]
            )

        if hasattr(booking, "adults") and booking.adults:
            travel_data.append(["Adults:", str(booking.adults)])

        if hasattr(booking, "children") and booking.children:
            travel_data.append(["Children:", str(booking.children)])

        if hasattr(booking, "infants") and booking.infants:
            travel_data.append(["Infants:", str(booking.infants)])

        if travel_data:
            travel_table = Table(travel_data, colWidths=[5 * cm, 7 * cm])
            travel_table.setStyle(
                TableStyle(
                    [
                        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 0), (-1, -1), 10),
                        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.gray),
                        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F8F9FA")),
                    ]
                )
            )

            story.append(travel_table)

        story.append(Spacer(1, 20))

        return story

    def _build_pricing_section(self, booking):
        """Build pricing information section"""
        story = []

        story.append(Paragraph("Pricing Information:", self.styles["CustomSubHeader"]))

        # Pricing table
        pricing_data = []

        if hasattr(booking, "total_price") and booking.total_price:
            pricing_data.append(["Total Price:", f"฿{float(booking.total_price):,.2f}"])

        if hasattr(booking, "deposit_amount") and booking.deposit_amount:
            pricing_data.append(
                ["Deposit Required:", f"฿{float(booking.deposit_amount):,.2f}"]
            )

        if hasattr(booking, "balance_due") and booking.balance_due:
            pricing_data.append(["Balance Due:", f"฿{float(booking.balance_due):,.2f}"])

        # Payment status from Invoice Ninja integration
        if booking.is_paid:
            pricing_data.append(["Payment Status:", "✅ PAID"])
            if booking.invoice_paid_date:
                pricing_data.append(
                    ["Payment Date:", booking.invoice_paid_date.strftime("%d %B %Y")]
                )
        else:
            pricing_data.append(["Payment Status:", "⏳ PENDING"])

        if pricing_data:
            pricing_table = Table(pricing_data, colWidths=[5 * cm, 7 * cm])
            pricing_table.setStyle(
                TableStyle(
                    [
                        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 0), (-1, -1), 10),
                        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.gray),
                        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F8F9FA")),
                    ]
                )
            )

            story.append(pricing_table)

        story.append(Spacer(1, 20))

        return story

    def _build_vendor_info(self, vendor):
        """Build vendor information section"""
        story = []

        story.append(Paragraph("Service Provider:", self.styles["CustomSubHeader"]))

        vendor_info = f"""
        <b>Company:</b> {vendor.company_name}<br/>
        <b>Contact:</b> {vendor.contact_person}<br/>
        <b>Email:</b> {vendor.email}<br/>
        <b>Phone:</b> {vendor.phone}<br/>
        """

        story.append(Paragraph(vendor_info, self.styles["Normal"]))
        story.append(Spacer(1, 20))

        return story

    def _build_workflow_progress(self, booking):
        """Build workflow progress section"""
        story = []

        story.append(Paragraph("Booking Progress:", self.styles["CustomSubHeader"]))

        # Workflow steps with timestamps
        workflow_steps = [
            ("Draft", booking.created_at, booking.status == "draft"),
            (
                "Confirmed",
                booking.confirmed_at,
                booking.status
                in ["confirmed", "quoted", "invoiced", "paid", "vouchered"],
            ),
            (
                "Quoted",
                booking.quoted_at,
                booking.status in ["quoted", "invoiced", "paid", "vouchered"],
            ),
            (
                "Invoiced",
                booking.invoiced_at,
                booking.status in ["invoiced", "paid", "vouchered"],
            ),
            ("Paid", booking.paid_at, booking.status in ["paid", "vouchered"]),
            ("Vouchered", booking.vouchered_at, booking.status == "vouchered"),
        ]

        # Create progress table
        progress_data = [["Step", "Status", "Date"]]

        for step_name, step_date, is_completed in workflow_steps:
            status_icon = "✅" if is_completed else "⏳"
            date_str = step_date.strftime("%d %B %Y") if step_date else "Pending"
            progress_data.append([step_name, status_icon, date_str])

        progress_table = Table(progress_data, colWidths=[4 * cm, 2 * cm, 6 * cm])
        progress_table.setStyle(
            TableStyle(
                [
                    # Header row
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17A2B8")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 11),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    # Data rows
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 10),
                    ("ALIGN", (0, 1), (0, -1), "LEFT"),
                    ("ALIGN", (1, 1), (1, -1), "CENTER"),
                    ("ALIGN", (2, 1), (2, -1), "CENTER"),
                    # Borders and padding
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )

        story.append(progress_table)
        story.append(Spacer(1, 20))

        return story

    def _build_additional_services(self, booking):
        """Build additional services section"""
        story = []

        story.append(
            Paragraph("Additional Information:", self.styles["CustomSubHeader"])
        )

        info_text = """
        <b>Services Included:</b><br/>
        • Professional tour guide<br/>
        • Transportation as specified<br/>
        • Accommodation as booked<br/>
        • Travel insurance coverage<br/>
        • 24/7 customer support<br/><br/>

        <b>Important Notes:</b><br/>
        • Please carry valid identification during travel<br/>
        • Arrive at pickup points 15 minutes early<br/>
        • Contact us immediately for any changes<br/>
        • Emergency contact: +66 2 123 4567
        """

        story.append(Paragraph(info_text, self.styles["Normal"]))
        story.append(Spacer(1, 20))

        return story

    def _build_qr_section(self, booking):
        """Build QR code section for sharing"""
        story = []

        if hasattr(booking, "public_url") and booking.public_url:
            story.append(
                Paragraph("View Online or Share:", self.styles["CustomSubHeader"])
            )

            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=3, border=1)
            qr.add_data(booking.public_url)
            qr.make(fit=True)

            qr_img = qr.make_image(fill_color="black", back_color="white")
            qr_path = f"{self.output_dir}/qr_{booking.booking_reference}.png"
            qr_img.save(qr_path)

            story.append(Spacer(1, 10))
            story.append(
                Paragraph(f"Online Link: {booking.public_url}", self.styles["Normal"])
            )

        return story

    def _build_footer(self):
        """Build PDF footer"""
        story = []

        story.append(Spacer(1, 30))
        footer_text = """
        <i>Thank you for choosing Dhakul Chan Tours & Travel!</i><br/>
        We look forward to providing you with an exceptional travel experience.<br/>
        For support: support@dhakulchan.net | Emergency: +66 2 123 4567
        """
        story.append(
            Paragraph(
                footer_text,
                (
                    self.styles["Terms"]
                    if "Terms" in self.styles
                    else self.styles["Normal"]
                ),
            )
        )

        return story

    def _get_workflow_status(self, booking):
        """Get workflow status description"""
        status_map = {
            "draft": "📝 Booking created, awaiting confirmation",
            "confirmed": "✅ Booking confirmed, quote preparation in progress",
            "quoted": "📋 Quote sent, awaiting customer approval",
            "invoiced": "💰 Invoice generated, payment pending",
            "paid": "💳 Payment received, voucher preparation in progress",
            "vouchered": "🎫 Voucher issued, booking complete",
            "cancelled": "❌ Booking cancelled",
        }

        return status_map.get(booking.status, f"Status: {booking.status}")

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
