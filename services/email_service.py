import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from config import Config
import os
from utils.logging_config import get_logger

logger = get_logger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_server = Config.SMTP_SERVER
        self.smtp_port = Config.SMTP_PORT
        self.username = Config.SMTP_USERNAME
        self.password = Config.SMTP_PASSWORD
        self.company_name = Config.COMPANY_NAME
        self.company_email = Config.COMPANY_EMAIL
        
        # Check if SMTP is properly configured
        self.smtp_configured = bool(self.username and self.password)
        if not self.smtp_configured:
            logger.warning("SMTP credentials not configured. Email sending will be simulated.")
    
    def _send_email(self, msg):
        """Send email with proper error handling"""
        try:
            # If SMTP not configured, simulate sending
            if not self.smtp_configured:
                logger.info("SIMULATED EMAIL SEND:")
                logger.info(f"From: {msg['From']}")
                logger.info(f"To: {msg['To']}")
                logger.info(f"Subject: {msg['Subject']}")
                logger.info("Email would be sent if SMTP credentials were configured.")
                return
            
            # Create secure connection
            context = ssl.create_default_context()
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.username, self.password)
                
                # Send email
                text = msg.as_string()
                server.sendmail(msg['From'], msg['To'], text)
            
            logger.info("Email sent successfully to %s", msg['To'])
            
        except Exception as e:
            logger.error("SMTP Error: %s", e, exc_info=True)
            raise Exception(f"SMTP sending failed: {str(e)}")
    
    def send_voucher_email(self, recipient_email, subject, message, pdf_path, booking):
        """Send tour voucher email with PDF attachment"""
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.company_email
            msg['To'] = recipient_email
            msg['Subject'] = subject
            
            # Email body
            body = f"""
Dear {booking.customer.name},

{message}

Booking Details:
- Reference: {booking.booking_reference}
- Traveling Period: {booking.traveling_period_start} to {booking.traveling_period_end}
- Total PAX: {booking.total_pax}
- Status: {booking.status.title()}

Please find your tour voucher attached to this email.

If you have any questions, please don't hesitate to contact us.

Best regards,
{self.company_name}
Email: {self.company_email}
Phone: {Config.COMPANY_PHONE}
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Attach PDF if exists
            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, 'rb') as file:
                    pdf_attachment = MIMEApplication(file.read(), _subtype='pdf')
                    pdf_attachment.add_header('Content-Disposition', 'attachment', 
                                            filename=f'tour_voucher_{booking.booking_reference}.pdf')
                    msg.attach(pdf_attachment)
            
            # Send email
            self._send_email(msg)
            return True
            
        except Exception as e:
            logger.error("Error sending voucher email: %s", e, exc_info=True)
            raise Exception(f"Email sending failed: {str(e)}")
    
    def send_booking_confirmation(self, booking):
        """Send booking confirmation email"""
        try:
            recipient_email = booking.customer.email
            subject = f"Booking Confirmation - {booking.booking_reference}"
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.company_email
            msg['To'] = recipient_email
            msg['Subject'] = subject
            
            # Email body
            body = f"""
Dear {booking.customer.name},

Thank you for your booking with {self.company_name}!

Your booking has been confirmed with the following details:

Booking Reference: {booking.booking_reference}
Booking Type: {booking.booking_type.title()}
Status: {booking.status.title()}
Total Amount: {booking.currency} {booking.total_amount}
Created Date: {booking.created_at.strftime('%Y-%m-%d %H:%M')}

"""
            
            # Add type-specific details
            if booking.booking_type == 'hotel':
                body += f"""
Hotel Details:
- Hotel Name: {booking.hotel_name}
- Check-in: {booking.arrival_date}
- Check-out: {booking.departure_date}
- Room Type: {booking.room_type}
- Total PAX: {booking.total_pax}
- Special Requests: {booking.special_request or 'None'}
"""
            
            elif booking.booking_type == 'transport':
                body += f"""
Transport Details:
- Vehicle Type: {booking.vehicle_type}
- Pickup Point: {booking.pickup_point}
- Destination: {booking.destination}
- Pickup Time: {booking.pickup_time}
- Total PAX: {booking.total_pax}
"""
            
            elif booking.booking_type == 'tour':
                body += f"""
Tour Details:
- Traveling Period: {booking.traveling_period_start} to {booking.traveling_period_end}
- Total PAX: {booking.total_pax}
- Flight Info: {booking.flight_info or 'N/A'}
"""
                
                # Add guest list
                guests = booking.get_guest_list()
                if guests:
                    body += f"\nGuest List:\n"
                    for i, guest in enumerate(guests, 1):
                        body += f"{i}. {guest}\n"
            
            body += f"""

We will contact you shortly with further details.

If you have any questions, please don't hesitate to contact us.

Best regards,
{self.company_name}
Email: {self.company_email}
Phone: {Config.COMPANY_PHONE}
Address: {Config.COMPANY_ADDRESS}
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            self._send_email(msg)
            return True
            
        except Exception as e:
            logger.error("Error sending booking confirmation: %s", e, exc_info=True)
            raise Exception(f"Email sending failed: {str(e)}")
    
    def send_booking_update(self, booking, update_message):
        """Send booking update email"""
        try:
            recipient_email = booking.customer.email
            subject = f"Booking Update - {booking.booking_reference}"
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.company_email
            msg['To'] = recipient_email
            msg['Subject'] = subject
            
            # Email body
            body = f"""
Dear {booking.customer.name},

We have an update regarding your booking {booking.booking_reference}.

{update_message}

Current Booking Status: {booking.status.title()}

If you have any questions, please don't hesitate to contact us.

Best regards,
{self.company_name}
Email: {self.company_email}
Phone: {Config.COMPANY_PHONE}
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            self._send_email(msg)
            return True
            
        except Exception as e:
            logger.error("Error sending booking update: %s", e, exc_info=True)
            raise Exception(f"Email sending failed: {str(e)}")
    
    def send_admin_notification(self, subject, message, booking=None):
        """Send notification to admin"""
        try:
            admin_emails = [self.company_email]  # Add more admin emails as needed
            
            for admin_email in admin_emails:
                msg = MIMEMultipart()
                msg['From'] = self.company_email
                msg['To'] = admin_email
                msg['Subject'] = f"[ADMIN] {subject}"
                
                body = f"""
Admin Notification: {subject}

{message}
"""
                
                if booking:
                    body += f"""

Booking Details:
- Reference: {booking.booking_reference}
- Customer: {booking.customer.name}
- Type: {booking.booking_type}
- Status: {booking.status}
- Amount: {booking.currency} {booking.total_amount}
- Created: {booking.created_at.strftime('%Y-%m-%d %H:%M')}
"""
                
                body += f"""

Time: {booking.created_at.strftime('%Y-%m-%d %H:%M:%S') if booking else 'N/A'}
System: Dhakul Chan Management System
                """
                
                msg.attach(MIMEText(body, 'plain'))
                self._send_email(msg)
            
            return True
            
        except Exception as e:
            logger.error("Error sending admin notification: %s", e, exc_info=True)
            return False
    
    def _send_email(self, msg):
        """Send email using SMTP"""
        try:
            # Create secure connection
            context = ssl.create_default_context()
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.username, self.password)
                
                # Send email
                text = msg.as_string()
                server.sendmail(msg['From'], msg['To'], text)
            
            logger.info("Email sent successfully to %s", msg['To'])
            
        except Exception as e:
            logger.error("SMTP Error: %s", e, exc_info=True)
            raise Exception(f"SMTP sending failed: {str(e)}")
    
    def test_email_connection(self):
        """Test email server connection"""
        try:
            context = ssl.create_default_context()
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.username, self.password)
            
            return True, "Email connection successful"
            
        except Exception as e:
            return False, f"Email connection failed: {str(e)}"

    def send_booking_pdf(self, recipient_email, pdf_path, booking):
        """Send booking PDF via email"""
        try:
            if not self.smtp_configured:
                logger.info("✅ Booking PDF email simulated successfully")
                logger.info(f"Would send to: {recipient_email}")
                logger.info(f"PDF: {pdf_path}")
                logger.info("⚠️  To send real emails, configure SMTP_USERNAME and SMTP_PASSWORD environment variables")
                return  # Simulate success
                
            subject = f"Booking Confirmation - {booking.booking_reference}"
            
            message = f"""Thank you for your booking with {self.company_name}.
            
Your booking has been confirmed. Please find your booking confirmation attached as a PDF.

If you have any questions, please contact us at {self.company_email}."""
            
            return self.send_voucher_email(recipient_email, subject, message, pdf_path, booking)
            
        except Exception as e:
            logger.error(f"Failed to send booking PDF email: {str(e)}")
            raise Exception(f"Failed to send booking PDF email: {str(e)}")

    def send_quote_pdf(self, recipient_email, pdf_path, booking):
        """Send quote PDF via email"""
        try:
            if not self.smtp_configured:
                logger.info("✅ Quote PDF email simulated successfully")
                logger.info(f"Would send to: {recipient_email}")
                logger.info(f"PDF: {pdf_path}")
                logger.info("⚠️  To send real emails, configure SMTP_USERNAME and SMTP_PASSWORD environment variables")
                return  # Simulate success
            subject = f"Tour Quote - {booking.booking_reference}"
            
            message = f"""Thank you for your interest in our tour services.
            
Please find your detailed quote attached as a PDF. This quote is valid for 30 days from the date of issue.

If you would like to proceed with the booking or have any questions, please contact us at {self.company_email}."""
            
            return self.send_voucher_email(recipient_email, subject, message, pdf_path, booking)
            
        except Exception as e:
            logger.error(f"Failed to send quote PDF email: {str(e)}")
            raise Exception(f"Failed to send quote PDF email: {str(e)}")

    def send_voucher_pdf(self, recipient_email, pdf_path, booking):
        """Send voucher PDF via email (alias for existing send_voucher_email)"""
        try:
            if not self.smtp_configured:
                logger.info("✅ Voucher PDF email simulated successfully")
                logger.info(f"Would send to: {recipient_email}")
                logger.info(f"PDF: {pdf_path}")
                logger.info("⚠️  To send real emails, configure SMTP_USERNAME and SMTP_PASSWORD environment variables")
                return  # Simulate success
                
            subject = f"Tour Voucher - {booking.booking_reference}"
            
            message = f"""Your tour voucher is ready!
            
Please find your tour voucher attached as a PDF. Please bring this voucher with you on your travel date.

Important: This voucher is required for your tour. Please arrive 15 minutes before the scheduled time."""
            
            return self.send_voucher_email(recipient_email, subject, message, pdf_path, booking)
            
        except Exception as e:
            logger.error(f"Failed to send voucher PDF email: {str(e)}")
            raise Exception(f"Failed to send voucher PDF email: {str(e)}")
