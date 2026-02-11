# LINE Official Account Messaging Service
import requests
import json
import logging
from line_config import LINE_OA_CONFIG, LINE_API_ENDPOINTS

logger = logging.getLogger(__name__)

class LineMessagingService:
    """Service for sending messages via LINE Official Account API"""
    
    def __init__(self):
        self.channel_access_token = LINE_OA_CONFIG['channel_access_token']
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.channel_access_token}'
        }
    
    def send_push_message(self, to_user_id, messages):
        """
        Send push message to specific LINE user
        
        Args:
            to_user_id (str): LINE user ID (obtained from webhook when user messages OA)
            messages (list): List of message objects (text, image, etc.)
            
        Returns:
            dict: Response with success status and details
        """
        try:
            payload = {
                'to': to_user_id,
                'messages': messages
            }
            
            response = requests.post(
                LINE_API_ENDPOINTS['push_message'],
                headers=self.headers,
                data=json.dumps(payload),
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"LINE message sent successfully to {to_user_id}")
                return {
                    'success': True,
                    'message': 'Message sent successfully',
                    'status_code': response.status_code
                }
            else:
                logger.error(f"LINE API error: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'message': f'LINE API error: {response.text}',
                    'status_code': response.status_code
                }
                
        except requests.exceptions.Timeout:
            logger.error("LINE API request timeout")
            return {
                'success': False,
                'message': 'Request timeout',
                'error': 'timeout'
            }
        except Exception as e:
            logger.error(f"Error sending LINE message: {str(e)}")
            return {
                'success': False,
                'message': str(e),
                'error': 'exception'
            }
    
    def send_booking_notification(self, user_id, booking_reference, secure_url, customer_name=""):
        """
        Send booking notification message to LINE user
        
        Args:
            user_id (str): LINE user ID
            booking_reference (str): Booking reference number
            secure_url (str): Secure booking URL
            customer_name (str): Customer name (optional)
            
        Returns:
            dict: Response with success status
        """
        greeting = f"สวัสดีค่ะคุณ {customer_name}\n" if customer_name else "สวัสดีค่ะ\n"
        
        message_text = (
            f"{greeting}"
            f"บริษัท ตระกูลเฉินฯ แจ้งรายละเอียดบริการหรือรายการทัวร์\n"
            f"หมายเลขอ้างอิง {booking_reference}\n\n"
            f"กรุณาคลิกดูรายละเอียดตามด้านล่างค่ะ\n"
            f"🔗 {secure_url}\n\n"
            f"ติดต่อสอบถาม:\n"
            f"📞 Tel: 02-123-4567\n"
            f"📧 Email: booking@dhakulchan.net\n"
            f"💬 Line: @dhakulchan"
        )
        
        messages = [
            {
                'type': 'text',
                'text': message_text
            }
        ]
        
        return self.send_push_message(user_id, messages)
    
    def broadcast_message(self, messages):
        """
        Broadcast message to all OA followers
        
        Args:
            messages (list): List of message objects
            
        Returns:
            dict: Response with success status
        """
        try:
            payload = {
                'messages': messages
            }
            
            response = requests.post(
                LINE_API_ENDPOINTS['broadcast'],
                headers=self.headers,
                data=json.dumps(payload),
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("LINE broadcast sent successfully")
                return {
                    'success': True,
                    'message': 'Broadcast sent successfully',
                    'status_code': response.status_code
                }
            else:
                logger.error(f"LINE broadcast error: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'message': f'LINE API error: {response.text}',
                    'status_code': response.status_code
                }
                
        except Exception as e:
            logger.error(f"Error broadcasting LINE message: {str(e)}")
            return {
                'success': False,
                'message': str(e),
                'error': 'exception'
            }

# Initialize service instance
line_service = LineMessagingService()
