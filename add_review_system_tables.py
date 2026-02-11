"""
สร้างตารางฐานข้อมูลสำหรับระบบรีวิวและคะแนนสะสม
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import sys
import os

# เพิ่ม path ของโปรเจค
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db

def create_review_system_tables():
    """สร้างตารางทั้งหมดสำหรับระบบรีวิว"""
    
    with app.app_context():
        # ตรวจสอบว่าตารางมีอยู่แล้วหรือไม่
        inspector = db.inspect(db.engine)
        
        # 1. สร้างตาราง campaign_reviews (รีวิวแคมเปญ)
        if 'campaign_reviews' not in inspector.get_table_names():
            with db.engine.connect() as conn:
                conn.execute(db.text("""
                    CREATE TABLE campaign_reviews (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        campaign_id INT NOT NULL,
                        customer_id INT NOT NULL,
                        booking_id INT,
                        rating INT NOT NULL CHECK (rating >= 1 AND rating <= 5),
                        review_text TEXT,
                        is_approved BOOLEAN DEFAULT FALSE,
                        is_featured BOOLEAN DEFAULT FALSE,
                        helpful_count INT DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        FOREIGN KEY (campaign_id) REFERENCES group_buy_campaigns(id) ON DELETE CASCADE,
                        FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
                        FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE SET NULL,
                        UNIQUE KEY unique_customer_review (campaign_id, customer_id, booking_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """))
                conn.commit()
            print("✅ สร้างตาราง campaign_reviews สำเร็จ")
        else:
            print("⚠️  ตาราง campaign_reviews มีอยู่แล้ว")
        
        # 2. สร้างตาราง review_images (รูปภาพรีวิว)
        if 'review_images' not in inspector.get_table_names():
            with db.engine.connect() as conn:
                conn.execute(db.text("""
                    CREATE TABLE review_images (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        review_id INT NOT NULL,
                        image_path VARCHAR(500) NOT NULL,
                        image_url VARCHAR(500),
                        display_order INT DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (review_id) REFERENCES campaign_reviews(id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """))
                conn.commit()
            print("✅ สร้างตาราง review_images สำเร็จ")
        else:
            print("⚠️  ตาราง review_images มีอยู่แล้ว")
        
        # 3. สร้างตาราง customer_points (คะแนนสะสมของลูกค้า)
        if 'customer_points' not in inspector.get_table_names():
            with db.engine.connect() as conn:
                conn.execute(db.text("""
                    CREATE TABLE customer_points (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        customer_id INT NOT NULL,
                        total_points INT DEFAULT 0,
                        available_points INT DEFAULT 0,
                        used_points INT DEFAULT 0,
                        expired_points INT DEFAULT 0,
                        lifetime_points INT DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
                        UNIQUE KEY unique_customer_points (customer_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """))
                conn.commit()
            print("✅ สร้างตาราง customer_points สำเร็จ")
        else:
            print("⚠️  ตาราง customer_points มีอยู่แล้ว")
        
        # 4. สร้างตาราง point_transactions (ประวัติการได้/ใช้คะแนน)
        if 'point_transactions' not in inspector.get_table_names():
            with db.engine.connect() as conn:
                conn.execute(db.text("""
                    CREATE TABLE point_transactions (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        customer_id INT NOT NULL,
                        transaction_type ENUM('earn', 'redeem', 'expire', 'adjustment') NOT NULL,
                        points INT NOT NULL,
                        balance_after INT NOT NULL,
                        source_type VARCHAR(50) COMMENT 'review, booking, referral, admin',
                        source_id INT COMMENT 'ID ของแหล่งที่มา เช่น review_id, booking_id',
                        description VARCHAR(500),
                        expires_at TIMESTAMP NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
                        INDEX idx_customer_date (customer_id, created_at),
                        INDEX idx_transaction_type (transaction_type)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """))
                conn.commit()
            print("✅ สร้างตาราง point_transactions สำเร็จ")
        else:
            print("⚠️  ตาราง point_transactions มีอยู่แล้ว")
        
        # 5. เพิ่มคอลัมน์ในตาราง bookings สำหรับติดตามการรีวิว
        existing_columns = [col['name'] for col in inspector.get_columns('bookings')]
        
        if 'review_requested_at' not in existing_columns:
            with db.engine.connect() as conn:
                conn.execute(db.text("""
                    ALTER TABLE bookings 
                    ADD COLUMN review_requested_at TIMESTAMP NULL COMMENT 'วันที่ส่งอีเมลขอรีวิว'
                """))
                conn.commit()
            print("✅ เพิ่มคอลัมน์ review_requested_at ในตาราง bookings")
        else:
            print("⚠️  คอลัมน์ review_requested_at มีอยู่แล้วในตาราง bookings")
        
        if 'has_reviewed' not in existing_columns:
            with db.engine.connect() as conn:
                conn.execute(db.text("""
                    ALTER TABLE bookings 
                    ADD COLUMN has_reviewed BOOLEAN DEFAULT FALSE COMMENT 'ลูกค้ารีวิวแล้วหรือยัง'
                """))
                conn.commit()
            print("✅ เพิ่มคอลัมน์ has_reviewed ในตาราง bookings")
        else:
            print("⚠️  คอลัมน์ has_reviewed มีอยู่แล้วในตาราง bookings")
        
        print("\n" + "="*70)
        print("✅ สร้างตารางระบบรีวิวและคะแนนสะสมเรียบร้อยแล้ว!")
        print("="*70)
        print("\nตารางที่สร้าง:")
        print("1. campaign_reviews - เก็บรีวิวของแคมเปญ")
        print("2. review_images - เก็บรูปภาพรีวิว")
        print("3. customer_points - เก็บคะแนนสะสมของลูกค้า")
        print("4. point_transactions - เก็บประวัติการได้/ใช้คะแนน")
        print("\nคอลัมน์ที่เพิ่มในตาราง bookings:")
        print("- review_requested_at - วันที่ส่งอีเมลขอรีวิว")
        print("- has_reviewed - สถานะการรีวิว")

if __name__ == '__main__':
    try:
        create_review_system_tables()
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {str(e)}")
        import traceback
        traceback.print_exc()
