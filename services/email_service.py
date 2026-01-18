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
                if msg.get('Cc'):
                    logger.info(f"Cc: {msg['Cc']}")
                logger.info(f"Subject: {msg['Subject']}")
                logger.info("Email would be sent if SMTP credentials were configured.")
                return
            
            # Create secure connection
            context = ssl.create_default_context()
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.username, self.password)
                
                # Send email - handle CC recipients
                recipients = [msg['To']]
                if msg.get('Cc'):
                    cc_recipients = msg['Cc'].split(',')
                    recipients.extend([r.strip() for r in cc_recipients])
                
                text = msg.as_string()
                server.sendmail(msg['From'], recipients, text)
            
            logger.info("Email sent successfully to %s", msg['To'])
            if msg.get('Cc'):
                logger.info("CC: %s", msg['Cc'])
            
        except Exception as e:
            logger.error("SMTP Error: %s", e, exc_info=True)
            raise Exception(f"SMTP sending failed: {str(e)}")
    
    def send_email(self, to_email, subject, body, cc_email=None, attachments=None):
        """Generic email sending with HTML support and optional CC"""
        try:
            # Create message
            msg = MIMEMultipart()
            # Set From with display name format
            msg['From'] = f"DonotReply <{self.company_email}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            
            if cc_email:
                msg['Cc'] = cc_email
            
            # Attach HTML body
            msg.attach(MIMEText(body, 'html'))
            
            # Attach files if provided
            if attachments:
                for attachment_path in attachments:
                    if os.path.exists(attachment_path):
                        with open(attachment_path, 'rb') as f:
                            attachment = MIMEApplication(f.read())
                            attachment.add_header('Content-Disposition', 'attachment', 
                                                filename=os.path.basename(attachment_path))
                            msg.attach(attachment)
            
            # Send email
            self._send_email(msg)
            return True
            
        except Exception as e:
            logger.error("Error sending email: %s", e, exc_info=True)
            raise Exception(f"Email sending failed: {str(e)}")
    
    def send_voucher_email(self, recipient_email, subject, message, pdf_path, booking):
        """Send tour voucher email with PDF attachment"""
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = f"DonotReply <{self.company_email}>"
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
            msg['From'] = f"DonotReply <{self.company_email}>"
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
            msg['From'] = f"DonotReply <{self.company_email}>"
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
                msg['From'] = f"DonotReply <{self.company_email}>"
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

    def send_time_limit_alert(self, booking):
        """Send Time Limit alert to internal team - ถึงกำหนดวันดำเนินการแล้ว"""
        try:
            recipient_email = "support@dhakulchan.com"
            subject = f"⚠️ TIME LIMIT ALERT - {booking.booking_reference}"
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = f"DonotReply <{self.company_email}>"
            msg['To'] = recipient_email
            msg['Subject'] = subject
            
            # Get creator info
            from models.user import User
            creator = User.query.get(booking.created_by) if booking.created_by else None
            creator_name = creator.username if creator else 'Unknown'
            creator_role = creator.role if creator else 'N/A'
            
            # Email body
            body = f"""
⚠️ TIME LIMIT ALERT ⚠️

ถึงกำหนดวันดำเนินการแล้ว (Time limit approaching - operation date)

BOOKING DETAILS:
================
Booking Reference: {booking.booking_reference}
Customer Name: {booking.customer.name if booking.customer else 'N/A'}
Customer Email: {booking.customer.email if booking.customer else 'N/A'}
Customer Phone: {booking.customer.phone if booking.customer else 'N/A'}

Booking Type: {booking.booking_type or 'N/A'}
Status: {booking.status.upper()}
Total Amount: {booking.currency or 'THB'} {float(booking.total_amount or 0):,.2f}

TIME INFORMATION:
=================
Time Limit: {booking.time_limit.strftime('%Y-%m-%d %H:%M') if booking.time_limit else 'N/A'} ⚠️ APPROACHING!
Due Date: {booking.due_date.strftime('%Y-%m-%d') if booking.due_date else 'N/A'}
Created Date: {booking.created_at.strftime('%Y-%m-%d %H:%M') if booking.created_at else 'N/A'}

TRAVEL DETAILS:
===============
Traveling From: {booking.traveling_period_start.strftime('%Y-%m-%d') if booking.traveling_period_start else (booking.arrival_date.strftime('%Y-%m-%d') if booking.arrival_date else 'N/A')}
Traveling To: {booking.traveling_period_end.strftime('%Y-%m-%d') if booking.traveling_period_end else (booking.departure_date.strftime('%Y-%m-%d') if booking.departure_date else 'N/A')}
Total Passengers: {booking.total_pax or 0} (Adults: {booking.adults or 0}, Children: {booking.children or 0}, Infants: {booking.infants or 0})

Created By: {creator_name} ({creator_role})

ACTION REQUIRED:
================
เตือนให้เตรียมเอกสาร/วอชเชอร์/ดำเนินการจัดทัวร์ - Please take immediate action:
1. Verify all booking arrangements are confirmed
2. Check payment status (should be completed by now)
3. Prepare vouchers and documents
4. Contact customer for final confirmation
5. Update operation status

View Booking: http://localhost:5001/booking/view/{booking.id}
Edit Booking: http://localhost:5001/booking/edit/{booking.id}

--
This is an automated alert from {self.company_name} Booking System
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            if not self.smtp_configured:
                logger.warning("SIMULATED TIME LIMIT ALERT EMAIL:")
                logger.warning(f"To: {recipient_email}")
                logger.warning(f"Subject: {subject}")
                logger.warning(f"Booking: {booking.booking_reference}")
                return True
            
            self._send_email(msg)
            logger.info(f"Time Limit alert sent for booking {booking.booking_reference}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending time limit alert: {e}", exc_info=True)
            return False

    def send_due_date_alert(self, booking):
        """Send Due Date alert to internal team - ครบ/เลยเวลายืนยัน/ชำระเงินแล้ว"""
        try:
            recipient_email = "support@dhakulchan.com"
            subject = f"⚠️ DUE DATE ALERT - {booking.booking_reference}"
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = f"DonotReply <{self.company_email}>"
            msg['To'] = recipient_email
            msg['Subject'] = subject
            
            # Get creator info
            from models.user import User
            creator = User.query.get(booking.created_by) if booking.created_by else None
            creator_name = creator.username if creator else 'Unknown'
            creator_role = creator.role if creator else 'N/A'
            
            # Email body
            body = f"""
⚠️ DUE DATE ALERT ⚠️

ครบ/เลยเวลายืนยัน/ชำระเงินแล้ว (Payment due date has been reached)

BOOKING DETAILS:
================
Booking Reference: {booking.booking_reference}
Customer Name: {booking.customer.name if booking.customer else 'N/A'}
Customer Email: {booking.customer.email if booking.customer else 'N/A'}
Customer Phone: {booking.customer.phone if booking.customer else 'N/A'}

Booking Type: {booking.booking_type or 'N/A'}
Status: {booking.status.upper()}
Total Amount: {booking.currency or 'THB'} {float(booking.total_amount or 0):,.2f}

TIME INFORMATION:
=================
Due Date: {booking.due_date.strftime('%Y-%m-%d') if booking.due_date else 'N/A'} ⚠️ REACHED!
Time Limit: {booking.time_limit.strftime('%Y-%m-%d %H:%M') if booking.time_limit else 'N/A'}
Created Date: {booking.created_at.strftime('%Y-%m-%d %H:%M') if booking.created_at else 'N/A'}

TRAVEL DETAILS:
===============
Traveling From: {booking.traveling_period_start.strftime('%Y-%m-%d') if booking.traveling_period_start else (booking.arrival_date.strftime('%Y-%m-%d') if booking.arrival_date else 'N/A')}
Traveling To: {booking.traveling_period_end.strftime('%Y-%m-%d') if booking.traveling_period_end else (booking.departure_date.strftime('%Y-%m-%d') if booking.departure_date else 'N/A')}
Total Passengers: {booking.total_pax or 0} (Adults: {booking.adults or 0}, Children: {booking.children or 0}, Infants: {booking.infants or 0})

Created By: {creator_name} ({creator_role})

ACTION REQUIRED:
================
ลูกค้ายังไม่ชำระเงิน และครบ/เลยเวลาแล้ว - Please follow up immediately:
1. Confirm payment status
2. Update booking status if payment received
3. Consider extending due date if needed
4. Cancel booking if no response

View Booking: http://localhost:5001/booking/view/{booking.id}
Edit Booking: http://localhost:5001/booking/edit/{booking.id}

--
This is an automated alert from {self.company_name} Booking System
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            if not self.smtp_configured:
                logger.warning("SIMULATED DUE DATE ALERT EMAIL:")
                logger.warning(f"To: {recipient_email}")
                logger.warning(f"Subject: {subject}")
                logger.warning(f"Booking: {booking.booking_reference}")
                return True
            
            self._send_email(msg)
            logger.info(f"Due Date alert sent for booking {booking.booking_reference}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending due date alert: {e}", exc_info=True)
            return False

