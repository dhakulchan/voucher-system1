#!/usr/bin/env python3
"""
Group Buy Cron Job
ตรวจสอบและจัดการกลุ่มที่หมดเวลา

ใช้งาน:
1. เพิ่มใน crontab: */5 * * * * /Applications/python/voucher-ro_v1.1/.venv/bin/python /Applications/python/voucher-ro_v1.1/group_buy_cron.py
2. หรือรันด้วยตนเอง: python3 group_buy_cron.py
"""
import sys
import os

# เพิ่ม path ของ app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from services.group_buy_service import GroupBuyService
from utils.datetime_utils import naive_utc_now
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/group_buy_cron.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Main cron job function"""
    logger.info("=" * 60)
    logger.info("Starting Group Buy Cron Job")
    logger.info(f"Timestamp: {naive_utc_now()}")
    
    with app.app_context():
        try:
            service = GroupBuyService()
            
            # ตรวจสอบกลุ่มที่หมดเวลา
            logger.info("Checking for expired groups...")
            expired_count = service.check_expired_groups()
            
            if expired_count > 0:
                logger.info(f"Processed {expired_count} expired groups")
            else:
                logger.info("No expired groups found")
            
            logger.info("Group Buy Cron Job completed successfully")
            
        except Exception as e:
            logger.error(f"Error in Group Buy Cron Job: {e}", exc_info=True)
            return 1
    
    return 0

if __name__ == '__main__':
    exit(main())
