"""
Public Share Service - Enhanced social media sharing capabilities
Handles public URLs, sharing tokens, and social media integration
"""
import os
import uuid
import logging
from datetime import datetime, timedelta
from urllib.parse import urljoin
from flask import url_for, current_app
import qrcode
from PIL import Image, ImageDraw, ImageFont
import secrets

logger = logging.getLogger(__name__)

class PublicShareService:
    """Service for managing public sharing of documents (Bookings, Quotes, Invoices)"""
    
    def __init__(self):
        # Adaptive base URL based on environment
        if os.path.exists("/opt/bitnami"):
            self.base_url = "https://booking.dhakulchan.net"
            self.static_dir = "/opt/bitnami/apache/htdocs/static"
        else:
            self.base_url = "http://127.0.0.1:5002"
            self.static_dir = "/Applications/python/voucher-ro_v1.0/static"
        
        self.share_dir = f"{self.static_dir}/shared"
        os.makedirs(self.share_dir, exist_ok=True)
        os.makedirs(f"{self.share_dir}/qr", exist_ok=True)
        os.makedirs(f"{self.share_dir}/social", exist_ok=True)
    
    def generate_share_token(self, document_type, document_id, expires_days=90):
        """
        Generate secure sharing token for document
        
        Args:
            document_type: 'booking', 'quote', 'invoice'
            document_id: Document ID
            expires_days: Token expiry in days (default 90)
            
        Returns:
            str: Secure sharing token
        """
        # Generate secure random token
        token = secrets.token_urlsafe(32)
        
        # In production, you'd store this in database with expiry
        # For now, we'll embed document info in token (not secure for production)
        timestamp = datetime.now().strftime('%Y%m%d')
        
        return f"{token}_{document_type}_{document_id}_{timestamp}"
    
    def create_public_url(self, document_type, document_id, share_token):
        """
        Create public sharing URL
        
        Args:
            document_type: 'booking', 'quote', 'invoice'
            document_id: Document ID
            share_token: Sharing token
            
        Returns:
            str: Public sharing URL
        """
        if document_type == 'booking':
            path = f"/public/booking/{share_token}"
        elif document_type == 'quote':
            path = f"/public/quote/{share_token}"
        elif document_type == 'invoice':
            path = f"/public/invoice/{share_token}"
        else:
            raise ValueError(f"Unsupported document type: {document_type}")
        
        return urljoin(self.base_url, path)
    
    def generate_qr_code(self, url, filename_prefix):
        """
        Generate QR code for sharing URL
        
        Args:
            url: URL to encode
            filename_prefix: Prefix for QR code filename
            
        Returns:
            str: Path to generated QR code image
        """
        try:
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=4,
            )
            
            qr.add_data(url)
            qr.make(fit=True)
            
            # Create QR code image
            qr_image = qr.make_image(fill_color="black", back_color="white")
            
            # Save QR code
            qr_filename = f"qr_{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            qr_path = f"{self.share_dir}/qr/{qr_filename}"
            qr_image.save(qr_path)
            
            logger.info(f"✅ QR code generated: {qr_path}")
            return qr_path
            
        except Exception as e:
            logger.error(f"❌ Error generating QR code: {str(e)}")
            return None
    
    def create_social_media_image(self, document_type, document_data, document_number):
        """
        Create optimized social media sharing image
        
        Args:
            document_type: 'booking', 'quote', 'invoice'
            document_data: Document data dictionary
            document_number: Document reference number
            
        Returns:
            str: Path to social media image
        """
        try:
            # Create social media image (1200x630 for Facebook/Twitter)
            img_width, img_height = 1200, 630
            
            # Create image with gradient background
            img = Image.new('RGB', (img_width, img_height), color='white')
            draw = ImageDraw.Draw(img)
            
            # Create gradient background
            self._create_gradient_background(draw, img_width, img_height, document_type)
            
            # Add company branding
            self._add_company_branding(draw, img_width, img_height)
            
            # Add document information
            self._add_document_info(draw, img_width, img_height, document_type, document_data, document_number)
            
            # Add social media elements
            self._add_social_elements(draw, img_width, img_height, document_type)
            
            # Save social media image
            social_filename = f"social_{document_type}_{document_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            social_path = f"{self.share_dir}/social/{social_filename}"
            img.save(social_path, quality=95)
            
            logger.info(f"✅ Social media image generated: {social_path}")
            return social_path
            
        except Exception as e:
            logger.error(f"❌ Error generating social media image: {str(e)}")
            return None
    
    def _create_gradient_background(self, draw, width, height, document_type):
        """Create gradient background based on document type"""
        # Color schemes for different document types
        color_schemes = {
            'booking': ((23, 162, 184), (13, 202, 240)),    # Blue gradient
            'quote': ((46, 134, 171), (162, 59, 114)),      # Blue to purple
            'invoice': ((220, 53, 69), (253, 126, 20))      # Red to orange
        }
        
        start_color, end_color = color_schemes.get(document_type, ((108, 117, 125), (173, 181, 189)))
        
        # Create vertical gradient
        for y in range(height):
            ratio = y / height
            r = int(start_color[0] * (1 - ratio) + end_color[0] * ratio)
            g = int(start_color[1] * (1 - ratio) + end_color[1] * ratio)
            b = int(start_color[2] * (1 - ratio) + end_color[2] * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))
    
    def _add_company_branding(self, draw, width, height):
        """Add company branding to social image"""
        try:
            # Company name
            company_font = ImageFont.truetype("Arial", 48)
            company_text = "Dhakul Chan Tours & Travel"
            
            # Get text size
            bbox = draw.textbbox((0, 0), company_text, font=company_font)
            text_width = bbox[2] - bbox[0]
            text_x = (width - text_width) // 2
            
            # Add company name with shadow
            draw.text((text_x + 2, 52), company_text, fill=(0, 0, 0, 128), font=company_font)  # Shadow
            draw.text((text_x, 50), company_text, fill=(255, 255, 255), font=company_font)     # Main text
            
        except Exception:
            # Fallback without custom font
            company_text = "Dhakul Chan Tours & Travel"
            bbox = draw.textbbox((0, 0), company_text)
            text_width = bbox[2] - bbox[0]
            text_x = (width - text_width) // 2
            draw.text((text_x, 50), company_text, fill=(255, 255, 255))
    
    def _add_document_info(self, draw, width, height, document_type, document_data, document_number):
        """Add document information to social image"""
        try:
            # Document title
            title_font = ImageFont.truetype("Arial", 36)
            title_map = {
                'booking': 'BOOKING CONFIRMATION',
                'quote': 'TRAVEL QUOTE',
                'invoice': 'INVOICE'
            }
            title_text = title_map.get(document_type, 'DOCUMENT')
            
            bbox = draw.textbbox((0, 0), title_text, font=title_font)
            text_width = bbox[2] - bbox[0]
            text_x = (width - text_width) // 2
            
            draw.text((text_x + 2, 152), title_text, fill=(0, 0, 0, 128), font=title_font)  # Shadow
            draw.text((text_x, 150), title_text, fill=(255, 255, 255), font=title_font)     # Main text
            
            # Document number
            number_font = ImageFont.truetype("Arial", 32)
            number_text = f"#{document_number}"
            
            bbox = draw.textbbox((0, 0), number_text, font=number_font)
            text_width = bbox[2] - bbox[0]
            text_x = (width - text_width) // 2
            
            draw.text((text_x + 2, 202), number_text, fill=(0, 0, 0, 128), font=number_font)  # Shadow
            draw.text((text_x, 200), number_text, fill=(255, 255, 255), font=number_font)     # Main text
            
            # Additional info based on document type
            info_font = ImageFont.truetype("Arial", 24)
            
            if document_type == 'booking' and 'customer_name' in document_data:
                info_text = f"Customer: {document_data['customer_name']}"
            elif document_type == 'quote' and 'total_amount' in document_data:
                info_text = f"Total: ฿{document_data['total_amount']:,.2f}"
            elif document_type == 'invoice' and 'total_amount' in document_data:
                info_text = f"Amount: ฿{document_data['total_amount']:,.2f}"
            else:
                info_text = "View Details Online"
            
            bbox = draw.textbbox((0, 0), info_text, font=info_font)
            text_width = bbox[2] - bbox[0]
            text_x = (width - text_width) // 2
            
            draw.text((text_x + 1, 261), info_text, fill=(0, 0, 0, 128), font=info_font)  # Shadow
            draw.text((text_x, 260), info_text, fill=(255, 255, 255), font=info_font)     # Main text
            
        except Exception:
            # Fallback without custom fonts
            title_text = f"{document_type.upper()} #{document_number}"
            bbox = draw.textbbox((0, 0), title_text)
            text_width = bbox[2] - bbox[0]
            text_x = (width - text_width) // 2
            draw.text((text_x, 200), title_text, fill=(255, 255, 255))
    
    def _add_social_elements(self, draw, width, height, document_type):
        """Add social media elements"""
        try:
            # Call-to-action
            cta_font = ImageFont.truetype("Arial", 28)
            cta_text = "📱 Scan QR Code or Click Link to View"
            
            bbox = draw.textbbox((0, 0), cta_text, font=cta_font)
            text_width = bbox[2] - bbox[0]
            text_x = (width - text_width) // 2
            
            draw.text((text_x + 2, 402), cta_text, fill=(0, 0, 0, 128), font=cta_font)  # Shadow
            draw.text((text_x, 400), cta_text, fill=(255, 255, 255), font=cta_font)     # Main text
            
            # Website
            website_font = ImageFont.truetype("Arial", 20)
            website_text = "www.dhakulchan.net"
            
            bbox = draw.textbbox((0, 0), website_text, font=website_font)
            text_width = bbox[2] - bbox[0]
            text_x = (width - text_width) // 2
            
            draw.text((text_x + 1, 451), website_text, fill=(0, 0, 0, 128), font=website_font)  # Shadow
            draw.text((text_x, 450), website_text, fill=(255, 255, 255), font=website_font)     # Main text
            
        except Exception:
            # Fallback without custom fonts
            cta_text = "View Online - www.dhakulchan.net"
            bbox = draw.textbbox((0, 0), cta_text)
            text_width = bbox[2] - bbox[0]
            text_x = (width - text_width) // 2
            draw.text((text_x, 400), cta_text, fill=(255, 255, 255))
    
    def create_shareable_content(self, document_type, document_instance, document_data):
        """
        Create complete shareable content package
        
        Args:
            document_type: 'booking', 'quote', 'invoice'
            document_instance: Database model instance
            document_data: Document data for social image
            
        Returns:
            dict: Complete sharing package
        """
        try:
            # Get document number
            if document_type == 'booking':
                document_number = document_instance.booking_reference
            elif document_type == 'quote':
                document_number = document_instance.quote_number
            elif document_type == 'invoice':
                document_number = document_instance.invoice_number
            else:
                document_number = str(document_instance.id)
            
            # Generate sharing token
            share_token = self.generate_share_token(document_type, document_instance.id)
            
            # Create public URL
            public_url = self.create_public_url(document_type, document_instance.id, share_token)
            
            # Generate QR code
            qr_path = self.generate_qr_code(public_url, f"{document_type}_{document_number}")
            
            # Create social media image
            social_image_path = self.create_social_media_image(
                document_type, 
                document_data, 
                document_number
            )
            
            # Update database model with sharing info
            document_instance.share_token = share_token
            document_instance.public_url = public_url
            
            from extensions import db
            db.session.commit()
            
            sharing_package = {
                'share_token': share_token,
                'public_url': public_url,
                'qr_code_path': qr_path,
                'social_image_path': social_image_path,
                'social_media_urls': self.generate_social_media_urls(public_url, document_type, document_number),
                'sharing_text': self.generate_sharing_text(document_type, document_number)
            }
            
            logger.info(f"✅ Complete sharing package created for {document_type} #{document_number}")
            return sharing_package
            
        except Exception as e:
            logger.error(f"❌ Error creating shareable content: {str(e)}")
            raise
    
    def generate_social_media_urls(self, public_url, document_type, document_number):
        """Generate social media sharing URLs"""
        import urllib.parse
        
        # Sharing text
        text_map = {
            'booking': f"Check out my travel booking #{document_number}",
            'quote': f"View my travel quote #{document_number}",
            'invoice': f"My travel invoice #{document_number}"
        }
        
        share_text = text_map.get(document_type, f"Check out this document #{document_number}")
        encoded_text = urllib.parse.quote(share_text)
        encoded_url = urllib.parse.quote(public_url)
        
        return {
            'facebook': f"https://www.facebook.com/sharer/sharer.php?u={encoded_url}",
            'twitter': f"https://twitter.com/intent/tweet?text={encoded_text}&url={encoded_url}",
            'whatsapp': f"https://api.whatsapp.com/send?text={encoded_text}%20{encoded_url}",
            'line': f"https://social-plugins.line.me/lineit/share?url={encoded_url}&text={encoded_text}",
            'telegram': f"https://t.me/share/url?url={encoded_url}&text={encoded_text}",
            'email': f"mailto:?subject={encoded_text}&body={encoded_url}"
        }
    
    def generate_sharing_text(self, document_type, document_number):
        """Generate sharing text templates"""
        text_templates = {
            'booking': {
                'short': f"My travel booking #{document_number} is confirmed! 🎫✈️",
                'medium': f"Just confirmed my travel booking #{document_number} with Dhakul Chan Tours! 🎫✈️ #Travel #Booking",
                'long': f"Excited to share that my travel booking #{document_number} is confirmed with Dhakul Chan Tours & Travel! Can't wait for this amazing journey! 🎫✈️🌟 #Travel #Adventure #DhakulChan"
            },
            'quote': {
                'short': f"Got my travel quote #{document_number}! 💰✈️",
                'medium': f"Received my personalized travel quote #{document_number} from Dhakul Chan Tours! 💰✈️ #TravelQuote",
                'long': f"Just received an amazing travel quote #{document_number} from Dhakul Chan Tours & Travel! Planning my next adventure has never been easier! 💰✈️🌍 #TravelPlanning #Quote #DhakulChan"
            },
            'invoice': {
                'short': f"Travel invoice #{document_number} ready for payment! 💳✈️",
                'medium': f"Payment time for my travel booking! Invoice #{document_number} 💳✈️ #Travel #Payment",
                'long': f"One step closer to my dream vacation! Payment ready for travel invoice #{document_number} with Dhakul Chan Tours! 💳✈️🎯 #TravelPayment #AlmostThere #DhakulChan"
            }
        }
        
        return text_templates.get(document_type, {
            'short': f"Document #{document_number}",
            'medium': f"Check out document #{document_number}",
            'long': f"View my document #{document_number} from Dhakul Chan Tours & Travel!"
        })
    
    def cleanup_expired_shares(self, days_old=90):
        """Clean up expired sharing files"""
        try:
            import os
            import time
            
            current_time = time.time()
            cutoff_time = current_time - (days_old * 24 * 60 * 60)
            
            # Clean up QR codes
            qr_dir = f"{self.share_dir}/qr"
            if os.path.exists(qr_dir):
                for filename in os.listdir(qr_dir):
                    file_path = os.path.join(qr_dir, filename)
                    if os.path.isfile(file_path):
                        if os.path.getmtime(file_path) < cutoff_time:
                            os.remove(file_path)
                            logger.info(f"🗑️ Cleaned up old QR code: {filename}")
            
            # Clean up social images
            social_dir = f"{self.share_dir}/social"
            if os.path.exists(social_dir):
                for filename in os.listdir(social_dir):
                    file_path = os.path.join(social_dir, filename)
                    if os.path.isfile(file_path):
                        if os.path.getmtime(file_path) < cutoff_time:
                            os.remove(file_path)
                            logger.info(f"🗑️ Cleaned up old social image: {filename}")
            
            logger.info(f"✅ Cleanup completed for files older than {days_old} days")
            
        except Exception as e:
            logger.error(f"❌ Error during cleanup: {str(e)}")
