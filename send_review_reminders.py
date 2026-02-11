#!/usr/bin/env python3
"""
Send Review Reminders
ส่งอีเมลเชิญรีวิวให้ลูกค้าหลังจากทัวร์เสร็จ 7 วัน
"""
import os
import sys
from datetime import datetime, timedelta

# เพิ่ม path ของ app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from models.booking import Booking
from models.review import CampaignReview
from flask_mail import Mail, Message
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = create_app()
mail = Mail(app)

def send_review_reminder(booking):
    """ส่งอีเมลเชิญรีวิวไปยังลูกค้า"""
    try:
        # สร้าง URL สำหรับรีวิว
        review_url = f"{app.config.get('SITE_URL', 'https://booking.dhakulchan.net')}/group-buy/campaign/{booking.campaign_id}/review?booking_id={booking.id}"
        
        # สร้าง email
        msg = Message(
            subject=f'เชิญรีวิวทัวร์ของคุณ - รับแต้มสะสม 80 แต้ม!',
            sender=app.config.get('MAIL_DEFAULT_SENDER', 'noreply@dhakulchan.net'),
            recipients=[booking.customer.email] if booking.customer else [booking.guest_email]
        )
        
        # HTML Body
        msg.html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; padding: 15px 30px; background: linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%); color: white; text-decoration: none; border-radius: 8px; margin: 20px 0; font-weight: bold; }}
                .points-box {{ background: #fff3cd; border: 2px solid #ffc107; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 0.9em; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🌟 ขอบคุณที่ใช้บริการกับเรา</h1>
                    <p>เราหวังว่าคุณจะมีความสุขกับทัวร์ที่ผ่านมา</p>
                </div>
                
                <div class="content">
                    <h2>สวัสดีคุณ {booking.customer.name if booking.customer else booking.guest_name} 👋</h2>
                    
                    <p>หลังจากที่คุณได้เดินทางกับเราไปแล้ว <strong>7 วัน</strong></p>
                    <p>เราอยากเชิญคุณมาแบ่งปันประสบการณ์ของคุณ เพื่อช่วยให้ผู้อื่นได้รับข้อมูลที่มีประโยชน์ครับ</p>
                    
                    <div class="points-box">
                        <h3>🎁 รับแต้มสะสมสูงสุด 80 แต้ม!</h3>
                        <p>
                            ✅ รีวิวพื้นฐาน: <strong>50 แต้ม</strong><br>
                            ✅ แนบรูปภาพ: <strong>+20 แต้ม</strong><br>
                            ✅ รีวิวยาว 100+ ตัวอักษร: <strong>+10 แต้ม</strong>
                        </p>
                        <p><strong>100 แต้ม = ส่วนลด 100 บาท</strong> สำหรับการจองครั้งต่อไป</p>
                    </div>
                    
                    <p><strong>ข้อมูลการจอง:</strong></p>
                    <ul>
                        <li>Booking ID: #{booking.booking_reference}</li>
                        <li>แคมเปญ: {booking.campaign.name if hasattr(booking, 'campaign') else 'N/A'}</li>
                        <li>วันเดินทาง: {booking.travel_date.strftime('%d/%m/%Y') if booking.travel_date else 'N/A'}</li>
                    </ul>
                    
                    <div style="text-align: center;">
                        <a href="{review_url}" class="button">
                            ✍️ เขียนรีวิวของคุณ
                        </a>
                    </div>
                    
                    <p style="color: #666; font-size: 0.9em; margin-top: 30px;">
                        * รีวิวของคุณจะช่วยให้ผู้อื่นตัดสินใจเลือกทัวร์ได้ดียิ่งขึ้น<br>
                        * แต้มจะเข้าบัญชีทันทีหลังรีวิวได้รับการอนุมัติ
                    </p>
                </div>
                
                <div class="footer">
                    <p><strong>Dhakul Chan Nice Holidays Group</strong></p>
                    <p>📞 02-274-4216 | 💬 Line: @dhakulchan</p>
                    <p>🌐 <a href="https://www.dhakulchan.net">www.dhakulchan.net</a></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Text Body (สำรองกรณี email client ไม่รองรับ HTML)
        msg.body = f"""
        สวัสดีคุณ {booking.customer.name if booking.customer else booking.guest_name}
        
        ขอบคุณที่ใช้บริการทัวร์กับเรา!
        
        เราอยากเชิญคุณมาเขียนรีวิวเกี่ยวกับทัวร์ที่ผ่านมา
        และรับแต้มสะสมสูงสุด 80 แต้ม!
        
        รีวิวที่: {review_url}
        
        แต้มที่จะได้รับ:
        - รีวิวพื้นฐาน: 50 แต้ม
        - แนบรูปภาพ: +20 แต้ม
        - รีวิวยาว 100+ ตัวอักษร: +10 แต้ม
        
        100 แต้ม = ส่วนลด 100 บาท
        
        ข้อมูลการจอง:
        Booking ID: {booking.booking_reference}
        
        ขอบคุณครับ!
        Dhakul Chan Nice Holidays Group
        """
        
        # ส่ง email
        mail.send(msg)
        
        # อัพเดท booking
        booking.review_requested_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"✅ Sent review reminder to {booking.customer.email if booking.customer else booking.guest_email} (Booking #{booking.booking_reference})")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to send review reminder for Booking #{booking.booking_reference}: {e}")
        return False

def main():
    """Main function - ค้นหา bookings ที่ควรส่ง reminder"""
    with app.app_context():
        logger.info("=" * 60)
        logger.info("Starting Review Reminder Job")
        logger.info("=" * 60)
        
        # คำนวณวันที่ (ทัวร์จบมา 7 วัน)
        target_date = datetime.now() - timedelta(days=7)
        start_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        logger.info(f"Looking for bookings with travel_date between:")
        logger.info(f"  Start: {start_date}")
        logger.info(f"  End: {end_date}")
        
        # ค้นหา bookings ที่:
        # 1. วันเดินทางผ่านมา 7 วัน
        # 2. ยังไม่ได้รีวิว
        # 3. ยังไม่เคยส่ง reminder
        # 4. สถานะ confirmed/completed
        bookings = Booking.query.filter(
            Booking.travel_date >= start_date,
            Booking.travel_date <= end_date,
            Booking.has_reviewed == False,
            Booking.review_requested_at == None,
            Booking.status.in_(['confirmed', 'completed'])
        ).all()
        
        logger.info(f"Found {len(bookings)} bookings to send reminders")
        
        if not bookings:
            logger.info("No bookings found. Exiting.")
            return
        
        # ส่ง reminder
        sent_count = 0
        failed_count = 0
        
        for booking in bookings:
            logger.info(f"\nProcessing Booking #{booking.booking_reference}...")
            
            # ตรวจสอบว่ามี customer email หรือไม่
            email = booking.customer.email if booking.customer else booking.guest_email
            if not email:
                logger.warning(f"  ⚠️  No email found for Booking #{booking.booking_reference}")
                failed_count += 1
                continue
            
            # ตรวจสอบว่ามี campaign_id หรือไม่ (สำหรับ group buy)
            if not hasattr(booking, 'campaign_id') or not booking.campaign_id:
                logger.warning(f"  ⚠️  No campaign_id for Booking #{booking.booking_reference}")
                failed_count += 1
                continue
            
            # ส่ง reminder
            if send_review_reminder(booking):
                sent_count += 1
            else:
                failed_count += 1
        
        # สรุปผล
        logger.info("\n" + "=" * 60)
        logger.info("Review Reminder Job Completed")
        logger.info("=" * 60)
        logger.info(f"Total bookings processed: {len(bookings)}")
        logger.info(f"✅ Successfully sent: {sent_count}")
        logger.info(f"❌ Failed: {failed_count}")
        logger.info("=" * 60)

if __name__ == '__main__':
    main()
