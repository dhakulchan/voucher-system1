#!/usr/bin/env python3
"""
Group Buy Auto Refund Cron Job
รันทุก 10 นาที เพื่อ:
1. ยกเลิก payments ที่หมดเวลา
2. คืนเงินอัตโนมัติสำหรับกลุ่มที่ล้มเหลว

ติดตั้ง crontab:
*/10 * * * * cd /Applications/python/voucher-ro_v1.1 && .venv/bin/python auto_refund_cron.py >> logs/auto_refund.log 2>&1
"""

import sys
import os
from datetime import datetime

# เพิ่ม path ของ project
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from services.group_buy_refund_service import process_expired_payments, auto_refund_failed_groups
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main cron job function"""
    try:
        logger.info("="*60)
        logger.info("🚀 Starting Auto Refund Cron Job")
        logger.info(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*60)
        
        app = create_app()
        
        with app.app_context():
            # 1. ยกเลิก payments ที่หมดเวลา
            logger.info("\n📋 Step 1: Processing expired payments...")
            result1 = process_expired_payments()
            
            if result1.get('success'):
                cancelled = result1.get('cancelled_count', 0)
                logger.info(f"✅ Cancelled {cancelled} expired payments")
            else:
                logger.error(f"❌ Failed: {result1.get('error')}")
            
            # 2. คืนเงินอัตโนมัติสำหรับกลุ่มที่ล้มเหลว
            logger.info("\n💰 Step 2: Processing auto refunds...")
            result2 = auto_refund_failed_groups()
            
            if result2.get('success'):
                groups = result2.get('groups_processed', 0)
                amount = result2.get('total_refunded', 0)
                logger.info(f"✅ Processed {groups} groups, refunded ฿{amount:,.2f}")
            else:
                logger.error(f"❌ Failed: {result2.get('error')}")
            
            logger.info("\n" + "="*60)
            logger.info("✅ Auto Refund Cron Job Completed")
            logger.info("="*60 + "\n")
            
            return 0
            
    except Exception as e:
        logger.error(f"❌ Cron job failed with exception: {e}", exc_info=True)
        return 1

if __name__ == '__main__':
    sys.exit(main())
