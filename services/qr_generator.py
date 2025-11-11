import qrcode
import qrcode.image.svg
from io import BytesIO
import os
from config import Config
from functools import lru_cache
from datetime import datetime, timezone
from utils.logging_config import get_logger

logger = get_logger(__name__)

class QRGenerator:
    def __init__(self):
        # Use adaptive path for development vs production
        self.qr_dir = '/opt/bitnami/apache/htdocs/static/qr_codes' if os.path.exists('/opt/bitnami') else 'static/qr_codes'
        try:
            os.makedirs(self.qr_dir, exist_ok=True)
            # Ensure proper permissions for Apache
            os.chmod(self.qr_dir, 0o755)
            logger.info(f"✅ QR directory ready: {self.qr_dir}")
        except Exception as e:
            logger.error(f"❌ Failed to create QR directory: {e}")
            # Fallback to relative path for development
            self.qr_dir = 'static/qr_codes'
            os.makedirs(self.qr_dir, exist_ok=True)
    
    def generate_voucher_qr(self, booking):
        """Generate QR code for voucher"""
        qr_text = (
            f"Tour Voucher\n"
            f"Reference: {booking.booking_reference}\n"
            f"Customer: {booking.customer.name}\n"
            f"Period: {booking.traveling_period_start} to {booking.traveling_period_end}\n"
            f"PAX: {booking.total_pax}\n"
            f"Verify: {Config.COMPANY_NAME}/verify/{booking.booking_reference}"
        )
        return self._generate_qr_code(qr_text, f"voucher_{booking.booking_reference}")
    
    def generate_booking_qr(self, booking):
        """Generate QR code for booking confirmation"""
        qr_text = f"""Booking Confirmation
Reference: {booking.booking_reference}
Type: {booking.booking_type.title()}
Customer: {booking.customer.name}
Status: {booking.status.title()}
Created: {booking.created_at.strftime('%Y-%m-%d')}
Verify: {Config.COMPANY_NAME}/booking/{booking.id}"""
        
        return self._generate_qr_code(qr_text, f"booking_{booking.booking_reference}")
    
    def generate_hotel_ro_qr(self, booking):
        """Generate QR code for hotel reservation order"""
        qr_text = f"""Hotel Reservation Order
Reference: {booking.agency_reference or booking.booking_reference}
Hotel: {booking.hotel_name}
Guest: {booking.customer.name}
Check-in: {booking.arrival_date}
Check-out: {booking.departure_date}
Room: {booking.room_type}
PAX: {booking.total_pax}"""
        
        return self._generate_qr_code(qr_text, f"hotel_ro_{booking.booking_reference}")
    
    def generate_mpv_qr(self, booking):
        """Generate QR code for MPV booking"""
        qr_text = f"""MPV Booking
Reference: {booking.booking_reference}
Vehicle: {booking.vehicle_type}
Pickup: {booking.pickup_point}
Destination: {booking.destination}
Time: {booking.pickup_time}
PAX: {booking.total_pax}
Customer: {booking.customer.name}"""
        
        return self._generate_qr_code(qr_text, f"mpv_{booking.booking_reference}")
    
    def _generate_qr_code(self, data, filename):
        """Generate (and optionally cache) QR code image path.
        If PDF_QR_CACHE_TTL > 0 and existing file newer than TTL, reuse it."""
        try:
            ttl = getattr(Config, 'PDF_QR_CACHE_TTL', 0)
            qr_path = os.path.join(self.qr_dir, f"{filename}.png")
            if ttl > 0 and os.path.exists(qr_path):
                mtime = os.path.getmtime(qr_path)
                age = (datetime.now(timezone.utc) - datetime.fromtimestamp(mtime, timezone.utc)).total_seconds()
                if age < ttl:
                    logger.debug("QR cache hit %s age=%.1fs < ttl=%ss", filename, age, ttl)
                    return qr_path
            # Create QR code instance
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            img.save(qr_path)
            logger.debug("QR generated %s -> %s (cache ttl=%s)", filename, qr_path, ttl)
            return qr_path
        except Exception as e:
            logger.error("QR generation error filename=%s err=%s", filename, e)
            raise Exception(f"QR code generation failed: {str(e)}")
    
    def generate_svg_qr_code(self, data, filename):
        """Generate QR code as SVG"""
        try:
            # Create QR code instance for SVG
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            
            # Add data
            qr.add_data(data)
            qr.make(fit=True)
            
            # Create SVG image
            factory = qrcode.image.svg.SvgPathImage
            img = qr.make_image(image_factory=factory)
            
            # Save SVG
            svg_path = os.path.join(self.qr_dir, f"{filename}.svg")
            img.save(svg_path)
            
            return svg_path
        
        except Exception as e:
            logger.error("QR SVG generation error filename=%s err=%s", filename, e)
            raise Exception(f"SVG QR code generation failed: {str(e)}")
    
    def generate_qr_with_logo(self, data, filename, logo_path=None):
        """Generate QR code with company logo"""
        try:
            from PIL import Image
            
            # Create QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,  # High error correction for logo
                box_size=10,
                border=4,
            )
            
            qr.add_data(data)
            qr.make(fit=True)
            
            # Create QR code image
            qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
            
            # Add logo if provided
            if logo_path and os.path.exists(logo_path):
                logo = Image.open(logo_path)
                
                # Calculate logo size (10% of QR code)
                qr_width, qr_height = qr_img.size
                logo_size = min(qr_width, qr_height) // 10
                
                # Resize logo
                logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
                
                # Create a white background for logo
                logo_bg = Image.new('RGB', (logo_size + 20, logo_size + 20), 'white')
                logo_bg.paste(logo, (10, 10))
                
                # Calculate position (center)
                pos = ((qr_width - logo_size - 20) // 2, (qr_height - logo_size - 20) // 2)
                
                # Paste logo onto QR code
                qr_img.paste(logo_bg, pos)
            
            # Save image
            qr_path = os.path.join(self.qr_dir, f"{filename}_logo.png")
            qr_img.save(qr_path)
            
            return qr_path
        
        except Exception as e:
            logger.error("QR w/logo generation error filename=%s err=%s", filename, e)
            return self._generate_qr_code(data, filename)  # Fallback to simple QR code
