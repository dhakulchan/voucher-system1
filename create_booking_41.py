#!/usr/bin/env python3
"""
Create Missing Booking 41 for Testing
สร้าง booking 41 ที่หายไปเพื่อทดสอบ
"""

from app import create_app, db
from models.booking import Booking
from models.customer import Customer
from datetime import datetime, date

def create_booking_41():
    """สร้าง booking 41 เพื่อแก้ปัญหา"""
    app = create_app()
    
    with app.app_context():
        # ตรวจสอบว่า booking 41 มีอยู่แล้วหรือไม่
        existing = Booking.query.get(41)
        if existing:
            print("✅ Booking 41 มีอยู่แล้ว")
            return True
        
        # ตรวจสอบ customer
        customer = Customer.query.first()
        if not customer:
            # สร้าง customer ใหม่
            customer = Customer(
                name="Test Customer",
                email="test@example.com",
                phone="0123456789"
            )
            db.session.add(customer)
            db.session.commit()
            print("✅ สร้าง customer ใหม่")
        
        # สร้าง booking 41
        booking = Booking(
            id=41,  # กำหนด ID เป็น 41
            customer_id=customer.id,
            booking_reference="BK20250930TEST41",
            booking_type="tour",
            status="confirmed",
            party_name="Test Party 41",
            total_pax=2,
            adults=2,
            children=0,
            infants=0,
            arrival_date=date(2025, 10, 15),
            departure_date=date(2025, 10, 20),
            traveling_period_start=date(2025, 10, 15),
            traveling_period_end=date(2025, 10, 20),
            time_limit=datetime(2025, 10, 10, 23, 59),
            total_amount=15000.00,
            description="Test booking for fixing edit issue",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        try:
            db.session.add(booking)
            db.session.commit()
            print("🎉 สร้าง booking 41 สำเร็จ!")
            
            # ตรวจสอบ
            test_booking = Booking.query.get(41)
            if test_booking:
                print(f"✅ ยืนยัน: booking 41 - {test_booking.party_name}")
                return True
            else:
                print("❌ ไม่สามารถยืนยันการสร้าง booking ได้")
                return False
                
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาด: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    print("🚀 กำลังสร้าง booking 41...")
    success = create_booking_41()
    
    if success:
        print("\n🎯 เสร็จสิ้น! ตอนนี้ลอง http://localhost:5001/booking/edit/41")
    else:
        print("\n❌ การสร้าง booking ล้มเหลว")