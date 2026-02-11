#!/usr/bin/env python3
"""
สร้าง Booking สำหรับกลุ่ม Group Buy ด้วยตนเอง
ใช้เมื่อ:
1. กลุ่มครบแล้วแต่ booking ไม่ถูกสร้างอัตโนมัติ
2. Admin ต้องการสร้าง booking ก่อนกลุ่มครบ
3. ต้องการสร้าง booking ใหม่หลังจากมีปัญหา

รันด้วย: python manual_create_bookings.py <group_code>
เช่น: python manual_create_bookings.py GB-ABC123
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db
from models.group_buy import GroupBuyGroup
from services.group_buy_service import GroupBuyService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def manual_create_bookings(group_code, force=False):
    """
    สร้าง booking สำหรับกลุ่มด้วยตนเอง
    
    Args:
        group_code: รหัสกลุ่ม เช่น GB-ABC123
        force: True = สร้างแม้กลุ่มยังไม่ครบคน (default: False)
    """
    app = create_app()
    
    with app.app_context():
        print("=" * 80)
        print("🔧 สร้าง Booking ด้วยตนเอง")
        print("=" * 80)
        
        # หากลุ่ม
        group = GroupBuyGroup.query.filter_by(group_code=group_code).first()
        
        if not group:
            print(f"❌ ไม่พบกลุ่ม: {group_code}")
            return False
        
        print(f"\n📦 กลุ่ม: {group.group_code}")
        print(f"   Campaign: {group.campaign.name}")
        print(f"   สถานะ: {group.status}")
        print(f"   ผู้เข้าร่วม: {group.current_participants}/{group.required_participants} คน")
        print(f"   Master Booking: {group.master_booking_id or 'ยังไม่มี'}")
        
        # ตรวจสอบเงื่อนไข
        if not force and not group.is_full:
            print(f"\n⚠️  กลุ่มยังไม่ครบคน!")
            print(f"   ขาดอีก {group.required_participants - group.current_participants} คน")
            print(f"   ถ้าต้องการสร้างแบบบังคับ ให้เพิ่ม argument: --force")
            return False
        
        if group.status == 'cancelled':
            print("\n❌ กลุ่มนี้ถูกยกเลิกแล้ว ไม่สามารถสร้าง booking ได้")
            return False
        
        if group.status == 'failed':
            print("\n❌ กลุ่มนี้ล้มเหลวแล้ว (หมดเวลา) ไม่สามารถสร้าง booking ได้")
            return False
        
        # ยืนยัน
        if group.master_booking_id:
            print(f"\n⚠️  กลุ่มนี้มี Master Booking แล้ว (#{group.master_booking_id})")
            confirm = input("   ต้องการสร้างใหม่หรือไม่? (yes/no): ")
            if confirm.lower() != 'yes':
                print("❌ ยกเลิกการสร้าง")
                return False
        
        print("\n🚀 เริ่มสร้าง Booking...")
        
        try:
            # สร้าง booking ผ่าน service
            service = GroupBuyService()
            service._handle_group_success(group)
            
            db.session.commit()
            
            print("\n" + "=" * 80)
            print("✅ สร้าง Booking สำเร็จ!")
            print("=" * 80)
            
            # แสดงผลลัพธ์
            db.session.refresh(group)
            print(f"\n📋 ผลลัพธ์:")
            print(f"   Master Booking ID: {group.master_booking_id}")
            print(f"   สถานะกลุ่ม: {group.status}")
            
            participants = group.participants.all()
            print(f"\n   👥 Participant Bookings:")
            for p in participants:
                if p.booking_id:
                    print(f"   ✅ {p.participant_name}: Booking #{p.booking_id}")
                else:
                    print(f"   ❌ {p.participant_name}: ไม่มี booking")
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating bookings: {e}", exc_info=True)
            print(f"\n❌ เกิดข้อผิดพลาด: {e}")
            db.session.rollback()
            return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python manual_create_bookings.py <group_code> [--force]")
        print("Example: python manual_create_bookings.py GB-ABC123")
        print("\nOptions:")
        print("  --force    สร้าง booking แม้กลุ่มยังไม่ครบคน")
        sys.exit(1)
    
    group_code = sys.argv[1]
    force = '--force' in sys.argv
    
    success = manual_create_bookings(group_code, force=force)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
