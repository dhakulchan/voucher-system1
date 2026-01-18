"""
Cloudflare Turnstile Verification Helper
"""
import os
import requests
import logging

logger = logging.getLogger(__name__)

# อ่านค่าจาก environment หรือใช้ default (development)
TURNSTILE_SECRET_KEY = os.environ.get('TURNSTILE_SECRET_KEY', '0x4AAAAAAAzvKyIGP5BsRam65wZ_nTBD51u')
TURNSTILE_VERIFY_URL = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'

def verify_turnstile_token(token: str, remote_ip: str = None) -> tuple[bool, str]:
    """
    ตรวจสอบ Cloudflare Turnstile token
    
    Args:
        token: cf-turnstile-response token จากฟอร์ม
        remote_ip: IP address ของผู้ใช้ (optional)
    
    Returns:
        (success: bool, message: str)
    """
    if not token:
        return False, 'กรุณายืนยันว่าคุณไม่ใช่บอท'
    
    try:
        payload = {
            'secret': TURNSTILE_SECRET_KEY,
            'response': token
        }
        
        if remote_ip:
            payload['remoteip'] = remote_ip
        
        response = requests.post(
            TURNSTILE_VERIFY_URL,
            data=payload,
            timeout=10
        )
        
        result = response.json()
        
        if result.get('success'):
            logger.info(f"✅ Turnstile verification successful")
            return True, 'ยืนยันตัวตนสำเร็จ'
        else:
            error_codes = result.get('error-codes', [])
            logger.warning(f"⚠️ Turnstile verification failed: {error_codes}")
            return False, 'การยืนยันตัวตนล้มเหลว กรุณาลองใหม่อีกครั้ง'
            
    except requests.exceptions.Timeout:
        logger.error("❌ Turnstile verification timeout")
        return False, 'การยืนยันตัวตนใช้เวลานานเกินไป กรุณาลองใหม่อีกครั้ง'
        
    except Exception as e:
        logger.error(f"❌ Turnstile verification error: {e}")
        return False, 'เกิดข้อผิดพลาดในการยืนยันตัวตน กรุณาลองใหม่อีกครั้ง'


def verify_turnstile_from_request(request_obj) -> tuple[bool, str]:
    """
    ตรวจสอบ Turnstile token จาก Flask request object
    
    Args:
        request_obj: Flask request object
    
    Returns:
        (success: bool, message: str)
    """
    token = request_obj.form.get('cf-turnstile-response')
    remote_ip = request_obj.remote_addr
    
    return verify_turnstile_token(token, remote_ip)
