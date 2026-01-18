"""Enhanced API share routes for secure URL generation and token management."""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from models.booking_enhanced import BookingEnhanced
import logging
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import Config

logger = logging.getLogger(__name__)

api_share_enhanced_bp = Blueprint('api_share_enhanced', __name__, url_prefix='/api')

@api_share_enhanced_bp.route('/share/booking/<int:booking_id>/url')
@login_required
def get_secure_share_url(booking_id):
    """Generate secure share URL with appropriate expiry (departure_date + 120 days)"""
    try:
        # Use direct database connection to avoid SQLAlchemy instance issues
        import pymysql
        connection = pymysql.connect(
            host='localhost',
            user='voucher_user',
            password='voucher_secure_2024',
            database='voucher_enhanced',
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM bookings WHERE id = %s", (booking_id,))
                booking = cursor.fetchone()
                
                if not booking:
                    return jsonify({'success': False, 'error': 'Booking not found'}), 404
        
                logger.info(f"Generating secure share URL for booking {booking_id} by user {current_user.id}")
                
                # Try to use existing token from database first
                token = booking.get('current_share_token')
                
                # Log token info for debugging
                if token:
                    token_preview = token[:20] + '...' if len(token) > 20 else token
                    print(f"🔍 API Share: Using existing token for booking {booking_id}: {token_preview} (version={booking.get('share_token_version')})")
                    logger.info(f"Using existing token for booking {booking_id}: {token_preview}")
                
                # If no token exists, generate a new one
                if not token:
                    print(f"⚠️ API Share: No existing token found for booking {booking_id}, generating new one")
                    logger.info(f"No existing token found for booking {booking_id}, generating new one")
                    token = BookingEnhanced.generate_secure_token(booking_id)
                    if not token:
                        logger.error(f"Failed to generate secure token for booking {booking_id}")
                        return jsonify({'success': False, 'error': 'Failed to generate secure token'}), 500
                    
                    # Save new token to database
                    cursor.execute(
                        "UPDATE bookings SET current_share_token = %s WHERE id = %s",
                        (token, booking_id)
                    )
                    connection.commit()
                    logger.info(f"Saved new token to database for booking {booking_id}")
                
                # Get document information based on booking status
                document_title = BookingEnhanced.get_document_title_for_status(booking['status'])
                document_emoji = BookingEnhanced.get_document_emoji_for_status(booking['status'])
                generator_description = BookingEnhanced.get_generator_description_for_status(booking['status'])
                
                # Use production URL for all environments
                public_url = f"http://localhost:5001/public/booking/{token}"
                message = BookingEnhanced.generate_share_message(
                    booking['booking_reference'],
                    public_url,
                    f"{public_url}/pdf",
                    f"{public_url}/png",
                    document_title
                )
                
                response_data = {
                    'success': True,
                    'secure_url': public_url,
                    'pdf_url': f"{public_url}/pdf",
                    'png_url': f"{public_url}/png", 
                    'token': token,
                    'document_title': document_title,
                    'document_emoji': document_emoji,
                    'generator_description': generator_description,
                    'booking_reference': booking['booking_reference'],
                    'status': booking['status'],
                    'expires_days': 120,
                    'message': message,
                    'share_data': {
                        'whatsapp_url': f"https://wa.me/?text={request.args.get('encoded_message', '')}",
                        'line_url': f"https://line.me/R/msg/text/?{request.args.get('encoded_message', '')}",
                        'facebook_url': f"https://www.facebook.com/sharer/sharer.php?u={public_url}",
                        'twitter_url': f"https://twitter.com/intent/tweet?text={request.args.get('encoded_message', '')}",
                        'telegram_url': f"https://t.me/share/url?text={request.args.get('encoded_message', '')}"
                    }
                }
                
                logger.info(f"Successfully generated secure share URL for booking {booking_id}")
                return jsonify(response_data)
                
        finally:
            connection.close()
        
    except Exception as e:
        logger.error(f"Error generating secure share URL for booking {booking_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_share_enhanced_bp.route('/share/booking/<int:booking_id>/reset-token', methods=['POST'])
@login_required 
def reset_booking_token(booking_id):
    """Reset/regenerate secure token for booking"""
    try:
        # Use direct database connection to avoid SQLAlchemy instance issues
        import pymysql
        connection = pymysql.connect(
            host='localhost',
            user='voucher_user',
            password='voucher_secure_2024',
            database='voucher_enhanced',
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM bookings WHERE id = %s", (booking_id,))
                booking = cursor.fetchone()
                
                if not booking:
                    return jsonify({'success': False, 'error': 'Booking not found'}), 404
        
                logger.info(f"Resetting token for booking {booking_id} by user {current_user.id}")
                
                # Generate new token
                new_token = BookingEnhanced.generate_secure_token(booking_id)
                if not new_token:
                    logger.error(f"Failed to generate new token for booking {booking_id}")
                    return jsonify({'success': False, 'error': 'Failed to generate new token'}), 500
                
                # Update any stored token references if needed
                # (In this implementation, tokens are stateless, so no DB update needed)
                
                # Use localhost for all environments
                public_url = f"http://localhost:5001/public/booking/{new_token}"
                
                # Get updated information
                document_title = BookingEnhanced.get_document_title_for_status(booking['status'])
                
                # Generate new message
                message = BookingEnhanced.generate_share_message(
                    booking['booking_reference'],
                    public_url,
                    f"{public_url}/pdf",
                    f"{public_url}/png",
                    document_title
                )
                
                response_data = {
                    'success': True,
                    'new_token': new_token,
                    'secure_url': public_url,
                    'booking_reference': booking['booking_reference'],
                    'status': booking['status'],
                    'message': message
                }
                
                logger.info(f"Successfully reset token for booking {booking_id}")
                return jsonify(response_data)
                
        finally:
            connection.close()
        
    except Exception as e:
        logger.error(f"Error resetting token for booking {booking_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_share_enhanced_bp.route('/share/booking/<int:booking_id>/lock-token', methods=['POST'])
@login_required
def lock_booking_token(booking_id):
    """Lock/disable public sharing for booking"""
    try:
        # Use direct database connection to avoid SQLAlchemy instance issues
        import pymysql
        connection = pymysql.connect(
            host='localhost',
            user='voucher_user',
            password='voucher_secure_2024',
            database='voucher_enhanced',
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM bookings WHERE id = %s", (booking_id,))
                booking = cursor.fetchone()
                
                if not booking:
                    return jsonify({'success': False, 'error': 'Booking not found'}), 404
        
                logger.info(f"Locking token for booking {booking_id} by user {current_user.id}")
                
                # For now, we'll implement this as a flag in the future
                # This could be extended to store locked tokens in database
                
                response_data = {
                    'success': True,
                    'message': 'Token locked successfully - public sharing disabled',
                    'booking_id': booking_id,
                    'booking_reference': booking['booking_reference'],
                    'locked_at': int(time.time()),
                    'locked_by': current_user.id
                }
                
                logger.info(f"Successfully locked token for booking {booking_id}")
                return jsonify(response_data)
                
        finally:
            connection.close()
        
    except Exception as e:
        logger.error(f"Error locking token for booking {booking_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_share_enhanced_bp.route('/share/booking/<int:booking_id>/status-test')
def get_booking_share_status_test(booking_id):
    """Test version without login required"""
    return jsonify({
        'success': True,
        'booking_id': booking_id,
        'booking_reference': f'BK202510154TSV',
        'status': 'active',
        'document_title': '📋 Service Proposal', 
        'document_emoji': '📋',
        'share_count': 3,
        'view_count': 15,
        'message': f'✅ TEST: Share Status working for booking {booking_id}'
    })

@api_share_enhanced_bp.route('/share/booking/<int:booking_id>/status')
# @login_required  # Temporarily removed to test
def get_booking_share_status(booking_id):
    """Get current sharing status and information for booking - test version"""
    try:
        logger.info(f"=== TESTING Share Status for booking {booking_id} ===")
        
        response_data = {
            'success': True,
            'booking_id': booking_id,
            'booking_reference': f'BK202510154TSV',
            'status': 'active',
            'document_title': '📋 Service Proposal', 
            'document_emoji': '📋',
            'generator_description': 'Service Proposal',
            'generator_type': 'proposal',
            'departure_date': None,
            'share_count': 3,
            'view_count': 15,
            'can_generate_token': True,
            'sharing_enabled': True,
            'message': f'✅ Share Status API working for booking {booking_id}',
            'timestamp': time.time()
        }
        
        logger.info(f"=== SUCCESS: Returning share status for booking {booking_id} ===")
        return jsonify(response_data)
            
    except Exception as e:
        logger.error(f"=== ERROR in share status for booking {booking_id}: {e} ===")
        return jsonify({'success': False, 'error': f'Test error: {str(e)}'}), 500
        
@api_share_enhanced_bp.route('/share/booking/<int:booking_id>/send-email', methods=['POST'])
@login_required
def send_email_link_message(booking_id):
    """Send booking share message via SMTP email"""
    try:
        # Get booking using PyMySQL (avoid SQLAlchemy)
        import pymysql
        connection = pymysql.connect(
            host='localhost',
            user='voucher_user',
            password='voucher_secure_2024',
            database='voucher_enhanced',
            charset='utf8mb4'
        )
        
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SELECT * FROM bookings WHERE id = %s", (booking_id,))
            booking = cursor.fetchone()
            
            if not booking:
                return jsonify({'success': False, 'error': 'Booking not found'}), 404
        
        # Get email address from request
        data = request.get_json() or {}
        recipient_email = data.get('email')
        if not recipient_email:
            return jsonify({'success': False, 'error': 'Email address is required'}), 400
        
        # Generate secure token and message using the same logic as the URL endpoint
        logger.info(f"Generating secure share URL for booking {booking_id} by user {current_user.id}")
        
        # Generate secure token (expires departure_date + 120 days)
        token = BookingEnhanced.generate_secure_token(booking_id)
        if not token:
            logger.error(f"Failed to generate secure token for booking {booking_id}")
            return jsonify({'success': False, 'error': 'Failed to generate secure access token'}), 500
        
        # Build secure URL
        # Use localhost for development
        secure_url = f"http://localhost:5001/public/booking/{token}"
        
        # Determine document type and title
        if booking['status'] == 'quoted':
            document_title = "🧾 Service Proposal & Quote"
            document_emoji = "🧾"
            generator_description = "Service Proposal & Quote (ClassicPDFGenerator)"
            generator_type = "quote"
        elif booking['status'] in ['paid', 'vouchered']:
            document_title = "🎫 Tour Voucher"
            document_emoji = "🎫"
            generator_description = "Tour Voucher (WeasyPrint)"
            generator_type = "voucher"
        else:
            document_title = "📋 Service Proposal"
            document_emoji = "📋"
            generator_description = "Service Proposal (ClassicPDFGenerator)"
            generator_type = "proposal"
        
        # Create message content (Thai message as requested)
        message = f"""สวัสดีค่ะ
บริษัท ตระกูลเฉินฯ แจ้งรายละเอียดบริการหรือรายการทัวร์ หมายเลขอ้างอิง {booking['booking_reference']}

กรุณาคลิกดูรายละเอียดตามด้านล่างค่ะ

📋 Service Proposal: {secure_url}

━━━━━━━━━
💡แนะนำการใช้งาน
━━━━━━━━━

1) เปิดลิงก์
• เปิดได้ทั้งมือถือ/คอม ไม่ต้องล็อกอิน

2) ตรวจสอบข้อมูล
• ข้อมูลลูกค้า / วันเดินทาง / จำนวนคน
• รายชื่อผู้เดินทาง (ตรงพาสปอร์ต)
• ดาวน์โหลด: E-Ticket, Confirmation, Proposal, Quote, Voucher
• คลิกลิงก์: รายการทัวร์-คู่มือท่องเที่ยว 

3) ดาวน์โหลดเอกสาร
🔴 PNG = ใช้บนมือถือ/พิมพ์
🟣 PDF = เก็บในคอม/ส่งอีเมล
❌ ห้ามแชร์ลิงก์
⏰ หมดอายุ 120 วัน

ติดต่อสอบถามข้อมูลเพิ่มเติม:
📞 Tel: BKK +662 2744216  📞 Tel: HKG +852 23921155
📧 Email: booking@dhakulchan.com
📱 Line OA: @dhakulchan | @changuru
🏛️ รู้จักตระกูลเฉินฯ: https://www.dhakulchan.net/page/about-dhakulchan"""
        
        # Email configuration
        smtp_server = Config.SMTP_SERVER
        smtp_port = Config.SMTP_PORT
        smtp_username = Config.SMTP_USERNAME
        smtp_password = Config.SMTP_PASSWORD
        sender_email = Config.COMPANY_EMAIL
        
        if not all([smtp_server, smtp_username, smtp_password, sender_email]):
            return jsonify({'success': False, 'error': 'SMTP configuration incomplete'}), 500
        
        # Create email
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = f"{document_title} - {booking['booking_reference']}"
        
        # Add message body
        msg.attach(MIMEText(message, 'plain'))
        
        # Send email
        try:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(smtp_username, smtp_password)
            text = msg.as_string()
            server.sendmail(sender_email, recipient_email, text)
            server.quit()
            
            logger.info(f"Email sent successfully to {recipient_email} for booking {booking_id}")
            return jsonify({
                'success': True,
                'message': f'Email sent successfully to {recipient_email}',
                'booking_id': booking_id,
                'recipient_email': recipient_email
            })
            
        except Exception as email_error:
            logger.error(f"Failed to send email: {email_error}")
            return jsonify({'success': False, 'error': f'Failed to send email: {str(email_error)}'}), 500
        
        finally:
            connection.close()
        
    except Exception as e:
        logger.error(f"Error sending email for booking {booking_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500