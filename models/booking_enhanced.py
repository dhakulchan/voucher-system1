"""Enhanced booking model with comprehensive token management and status-based PDF generation."""

import os
import hmac
import hashlib
import base64
import time
from datetime import datetime, timedelta
from flask import current_app
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class BookingEnhanced:
    """Enhanced booking model with comprehensive token management"""
    
    @staticmethod
    def generate_secure_token(booking_id: int, expiry_days: int = 120) -> Optional[str]:
        """Generate secure token with 120-day expiry or departure_date + 120 days"""
        try:
            # Get booking to determine expiry based on departure date
            from models.booking import Booking
            booking = Booking.query.get(booking_id)
            
            if booking and booking.departure_date:
                # Use departure_date + 120 days (convert date to datetime first)
                departure_datetime = datetime.combine(booking.departure_date, datetime.min.time())
                expiry_timestamp = int((departure_datetime + timedelta(days=120)).timestamp())
                logger.info(f"Token expiry set to departure_date + 120 days: {departure_datetime + timedelta(days=120)}")
            else:
                # Fallback to current time + 120 days
                expiry_timestamp = int((datetime.now() + timedelta(days=expiry_days)).timestamp())
                logger.info(f"Token expiry set to current time + {expiry_days} days")
            
            current_timestamp = int(time.time())
            
            # Create token payload: booking_id|current_timestamp|expiry_timestamp
            payload = f"{booking_id}|{current_timestamp}|{expiry_timestamp}"
            
            # Sign with HMAC - Use Flask app's secret key for consistency
            from flask import current_app
            secret_key = current_app.config['SECRET_KEY'].encode('utf-8')
            full_signature = hmac.new(secret_key, payload.encode(), hashlib.sha256).digest()
            signature = full_signature[:26]  # Use first 26 bytes to match Booking.verify_share_token()
            
            # Combine payload and signature with dot separator, then base64 encode
            token_data = payload.encode() + b'.' + signature
            token = base64.urlsafe_b64encode(token_data).decode().rstrip('=')
            
            logger.info(f"Generated secure token for booking {booking_id}, expires: {expiry_timestamp}")
            return token
            
        except Exception as e:
            logger.error(f"Error generating secure token: {e}")
            return None
    
    @staticmethod
    def verify_secure_token(token):
        """Verify secure token and return booking_id if valid"""
        try:
            # Add padding if needed
            token += '=' * (4 - len(token) % 4)
            token_data = base64.urlsafe_b64decode(token)
            
            # Find dot separator to split payload and signature
            if b'.' in token_data:
                payload_bytes, signature = token_data.rsplit(b'.', 1)
            else:
                # Fallback to old format (signature is last 32 bytes)
                payload_bytes = token_data[:-32]
                signature = token_data[-32:]
            
            payload = payload_bytes.decode()
            
            # Verify signature - Use Flask app's secret key for consistency
            from flask import current_app
            secret_key = current_app.config['SECRET_KEY'].encode('utf-8')
            
            # Support both 26-byte (new) and 32-byte (old) signatures
            if len(signature) == 26:
                # New format: use first 26 bytes of SHA256
                expected_signature_full = hmac.new(secret_key, payload_bytes, hashlib.sha256).digest()
                expected_signature = expected_signature_full[:26]
            else:
                # Old format: full SHA256
                expected_signature = hmac.new(secret_key, payload_bytes, hashlib.sha256).digest()
            
            if not hmac.compare_digest(signature, expected_signature):
                logger.warning(f"Token signature verification failed (signature length: {len(signature)})")
                return None
            
            # Parse payload
            parts = payload.split('|')
            if len(parts) != 3:
                logger.warning(f"Invalid token payload format: {len(parts)} parts")
                return None
                
            booking_id = int(parts[0])
            expiry_timestamp = int(parts[2])
            
            # Check if token has expired
            current_time = time.time()
            if current_time > expiry_timestamp:
                logger.warning(f"Token expired: {current_time} > {expiry_timestamp}")
                return None
                
            logger.info(f"Token verified successfully for booking {booking_id}")
            return booking_id
            
        except Exception as e:
            logger.error(f"Error verifying secure token: {e}")
            return None
    
    @staticmethod
    def get_pdf_generator_for_status(status):
        """Return appropriate PDF generator based on booking status"""
        generator_map = {
            'pending': 'classic',      # ClassicPDFGenerator for Service Proposal
            'confirmed': 'classic',    # ClassicPDFGenerator for Service Proposal
            'quoted': 'weasyprint_quote',  # WeasyPrint for Quote
            'paid': 'classic',         # ClassicPDFGenerator for Quote/Provisional Receipt
            'vouchered': 'weasyprint_voucher'  # WeasyPrint for Tour Voucher
        }
        return generator_map.get(status, 'classic')  # Default fallback
    
    @staticmethod
    def get_document_title_for_status(status):
        """Return appropriate document title based on booking status"""
        titles = {
            'pending': 'Service Proposal',
            'confirmed': 'Service Proposal', 
            'quoted': 'Quote',
            'paid': 'Quote / Provisional Receipt',
            'vouchered': 'Tour Voucher'
        }
        return titles.get(status, 'Service Proposal')
    
    @staticmethod
    def get_document_emoji_for_status(status):
        """Return appropriate emoji based on booking status"""
        emojis = {
            'pending': '📋',
            'confirmed': '📋',
            'quoted': '💰',
            'paid': '🧾',
            'vouchered': '🎫'
        }
        return emojis.get(status, '📋')
    
    @staticmethod
    def get_generator_description_for_status(status):
        """Return generator description for UI display"""
        descriptions = {
            'pending': 'ClassicPDFGenerator • Public PDF Route',
            'confirmed': 'ClassicPDFGenerator • Public PDF Route',
            'quoted': 'Jinja2(3.1.4) + WeasyPrint(62.3) • quote_template_final_v2.html',
            'paid': 'ClassicPDFGenerator • Public PDF Route',
            'vouchered': 'Jinja2(3.1.4) + WeasyPrint(62.3) • tour_voucher_template_v2_sample.html'
        }
        return descriptions.get(status, 'ClassicPDFGenerator • Public PDF Route')
    
    @staticmethod
    def generate_share_message(booking_reference, secure_url, pdf_url, png_url, document_title):
        """Generate the standardized Thai message for sharing"""
        message = f"""สวัสดีค่ะ
บริษัท ตระกูลเฉินฯ แจ้งรายละเอียดบริการหรือรายการทัวร์ หมายเลขอ้างอิง {booking_reference}
กรุณาคลิกดูรายละเอียดตามด้านล่างค่ะ

📋 {document_title}: {secure_url}

🖼️ Download PNG: {png_url}

📄 Download PDF: {pdf_url}

ติดต่อสอบถามข้อมูลเพิ่มเติม:
📞 Tel: BKK +662 2744216  📞 Tel: HKG +852 23921155
📧 Email: booking@dhakulchan.com
📱 Line OA: @dhakulchan | @changuru
🏛️ รู้จักตระกูลเฉินฯ: https://www.dhakulchan.net/page/about-dhakulchan"""
        
        return message
    
    @staticmethod
    def get_generator_description(status: str) -> str:
        """Return generator description based on status (alias for compatibility)"""
        return BookingEnhanced.get_generator_description_for_status(status)
    
    @staticmethod
    def get_status_workflow_info(status: str) -> Dict[str, Any]:
        """Get comprehensive workflow information for a status"""
        workflow_info = {
            'draft': {
                'stage': 'Initial',
                'description': 'การจองอยู่ในขั้นตอนการร่างเอกสาร',
                'next_stages': ['pending', 'cancelled'],
                'actions': ['edit', 'submit', 'cancel'],
                'color': '#6c757d',
                'priority': 1
            },
            'pending': {
                'stage': 'Awaiting Confirmation',
                'description': 'รอการยืนยันจากทีมงาน',
                'next_stages': ['confirmed', 'quoted', 'cancelled'],
                'actions': ['confirm', 'quote', 'cancel'],
                'color': '#ffc107',
                'priority': 2
            },
            'confirmed': {
                'stage': 'Confirmed',
                'description': 'การจองได้รับการยืนยันแล้ว',
                'next_stages': ['quoted', 'paid'],
                'actions': ['generate_quote', 'proceed_payment'],
                'color': '#28a745',
                'priority': 3
            },
            'quoted': {
                'stage': 'Quote Generated',
                'description': 'ได้ออกใบเสนอราคาแล้ว',
                'next_stages': ['paid', 'cancelled'],
                'actions': ['process_payment', 'revise_quote'],
                'color': '#17a2b8',
                'priority': 4
            },
            'paid': {
                'stage': 'Payment Received',
                'description': 'ได้รับการชำระเงินแล้ว',
                'next_stages': ['vouchered'],
                'actions': ['generate_voucher'],
                'color': '#007bff',
                'priority': 5
            },
            'vouchered': {
                'stage': 'Tour Voucher Issued',
                'description': 'ออกบัตรนำเที่ยวแล้ว',
                'next_stages': ['completed'],
                'actions': ['complete_tour'],
                'color': '#6f42c1',
                'priority': 6
            },
            'completed': {
                'stage': 'Completed',
                'description': 'การเดินทางเสร็จสิ้นแล้ว',
                'next_stages': [],
                'actions': ['archive'],
                'color': '#20c997',
                'priority': 7
            },
            'cancelled': {
                'stage': 'Cancelled',
                'description': 'การจองถูกยกเลิก',
                'next_stages': [],
                'actions': ['archive'],
                'color': '#dc3545',
                'priority': 0
            }
        }
        
        return workflow_info.get(status, {
            'stage': 'Unknown',
            'description': 'สถานะไม่ทราบ',
            'next_stages': [],
            'actions': [],
            'color': '#6c757d',
            'priority': 0
        })
    
    @staticmethod
    def validate_status_transition(current_status: str, new_status: str) -> bool:
        """Validate if status transition is allowed"""
        workflow_info = BookingEnhanced.get_status_workflow_info(current_status)
        return new_status in workflow_info.get('next_stages', [])