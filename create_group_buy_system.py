#!/usr/bin/env python3
"""
Create Group Buy System Tables
- group_buy_campaigns: Campaign settings
- group_buy_groups: Customer groups  
- group_buy_participants: Group members
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pymysql
from datetime import datetime

# Database config
LOCAL_DEV_CONFIG = {
    'host': 'localhost',
    'user': 'voucher_user',
    'password': 'voucher_secure_2024',
    'database': 'voucher_enhanced',
    'charset': 'utf8mb4',
    'port': 3306
}

def connect_db():
    """Connect to database"""
    try:
        conn = pymysql.connect(**LOCAL_DEV_CONFIG)
        return conn
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return None

def create_group_buy_tables():
    """Create Group Buy system tables"""
    conn = connect_db()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # 1. Create group_buy_campaigns table
        print("📦 Creating group_buy_campaigns table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS group_buy_campaigns (
                id INT AUTO_INCREMENT PRIMARY KEY,
                
                -- Campaign Info
                name VARCHAR(255) NOT NULL,
                description TEXT,
                product_type VARCHAR(100) NOT NULL COMMENT 'tour, hotel, transport, package',
                
                -- Pricing
                regular_price DECIMAL(12,2) NOT NULL COMMENT 'ราคาปกติ',
                group_price DECIMAL(12,2) NOT NULL COMMENT 'ราคากลุ่ม',
                discount_percentage DECIMAL(5,2) COMMENT 'เปอร์เซ็นต์ส่วนลด',
                
                -- Group Requirements
                min_participants INT NOT NULL DEFAULT 2 COMMENT 'จำนวนคนขั้นต่ำ',
                max_participants INT DEFAULT NULL COMMENT 'จำนวนคนสูงสุด (optional)',
                
                -- Time Limits
                duration_hours INT NOT NULL DEFAULT 48 COMMENT 'เวลาในการรวมกลุ่ม (ชั่วโมง)',
                campaign_start_date DATETIME NOT NULL,
                campaign_end_date DATETIME NOT NULL,
                
                -- Product/Service Details (JSON)
                product_details TEXT COMMENT 'JSON: tour details, hotel info, etc.',
                terms_conditions TEXT,
                
                -- Inventory Management
                total_slots INT DEFAULT NULL COMMENT 'ที่นั่ง/ห้องทั้งหมด',
                available_slots INT DEFAULT NULL COMMENT 'ที่นั่งคงเหลือ',
                
                -- Status
                status VARCHAR(50) NOT NULL DEFAULT 'draft' COMMENT 'draft, active, paused, ended, sold_out',
                is_active BOOLEAN DEFAULT TRUE,
                
                -- Visibility
                is_public BOOLEAN DEFAULT TRUE COMMENT 'แสดงหน้าเว็บ public',
                featured BOOLEAN DEFAULT FALSE COMMENT 'แสดงบน featured section',
                
                -- Images
                banner_image VARCHAR(500),
                gallery_images TEXT COMMENT 'JSON array of image URLs',
                
                -- Meta
                created_by INT COMMENT 'user_id ที่สร้าง',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                
                INDEX idx_status (status),
                INDEX idx_active (is_active),
                INDEX idx_dates (campaign_start_date, campaign_end_date),
                INDEX idx_product_type (product_type)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("✅ group_buy_campaigns table created")
        
        # 2. Create group_buy_groups table
        print("📦 Creating group_buy_groups table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS group_buy_groups (
                id INT AUTO_INCREMENT PRIMARY KEY,
                
                -- Campaign Reference
                campaign_id INT NOT NULL,
                
                -- Group Info
                group_code VARCHAR(50) UNIQUE NOT NULL COMMENT 'รหัสกลุ่มสำหรับแชร์',
                group_name VARCHAR(255) COMMENT 'ชื่อกลุ่ม (optional)',
                
                -- Leader (คนเริ่มกลุ่ม)
                leader_customer_id INT COMMENT 'customer_id',
                leader_name VARCHAR(255) NOT NULL,
                leader_email VARCHAR(255),
                leader_phone VARCHAR(50),
                
                -- Group Status
                status VARCHAR(50) NOT NULL DEFAULT 'pending' COMMENT 'pending, active, success, failed, cancelled',
                current_participants INT DEFAULT 0,
                required_participants INT NOT NULL,
                
                -- Time Management
                expires_at DATETIME NOT NULL COMMENT 'เวลาหมดอายุ',
                completed_at DATETIME COMMENT 'เวลาสำเร็จ',
                cancelled_at DATETIME COMMENT 'เวลายกเลิก',
                
                -- Payment Management
                payment_method VARCHAR(50) DEFAULT 'hold' COMMENT 'hold, immediate',
                total_amount DECIMAL(12,2) DEFAULT 0,
                paid_amount DECIMAL(12,2) DEFAULT 0,
                
                -- Share Link
                share_token VARCHAR(100) UNIQUE NOT NULL COMMENT 'Token สำหรับแชร์',
                share_url TEXT COMMENT 'Full share URL',
                
                -- Booking Integration
                master_booking_id INT COMMENT 'booking_id เมื่อกลุ่มสำเร็จ',
                
                -- Meta
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                
                FOREIGN KEY (campaign_id) REFERENCES group_buy_campaigns(id) ON DELETE CASCADE,
                INDEX idx_campaign (campaign_id),
                INDEX idx_status (status),
                INDEX idx_leader (leader_customer_id),
                INDEX idx_expires (expires_at),
                INDEX idx_group_code (group_code),
                INDEX idx_share_token (share_token)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("✅ group_buy_groups table created")
        
        # 3. Create group_buy_participants table
        print("📦 Creating group_buy_participants table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS group_buy_participants (
                id INT AUTO_INCREMENT PRIMARY KEY,
                
                -- Group Reference
                group_id INT NOT NULL,
                campaign_id INT NOT NULL,
                
                -- Participant Info
                customer_id INT COMMENT 'customer_id ถ้า login',
                participant_name VARCHAR(255) NOT NULL,
                participant_email VARCHAR(255),
                participant_phone VARCHAR(50),
                
                -- Position
                is_leader BOOLEAN DEFAULT FALSE,
                join_order INT COMMENT 'ลำดับที่เข้าร่วม',
                
                -- Participant Details
                pax_count INT DEFAULT 1 COMMENT 'จำนวนคน',
                special_requests TEXT,
                
                -- Payment Status
                payment_status VARCHAR(50) DEFAULT 'pending' COMMENT 'pending, authorized, paid, refunded, failed',
                payment_amount DECIMAL(12,2),
                payment_reference VARCHAR(255),
                payment_date DATETIME,
                
                -- Booking Integration
                booking_id INT COMMENT 'booking_id เมื่อสำเร็จ',
                invoice_id INT COMMENT 'invoice_id',
                
                -- Authorization (สำหรับ hold payment)
                authorization_code VARCHAR(255),
                authorization_expires_at DATETIME,
                
                -- Status
                status VARCHAR(50) DEFAULT 'active' COMMENT 'active, cancelled, removed',
                cancelled_at DATETIME,
                cancel_reason TEXT,
                
                -- Meta
                ip_address VARCHAR(100),
                user_agent TEXT,
                referrer_participant_id INT COMMENT 'ถ้ามีคนชวน',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                
                FOREIGN KEY (group_id) REFERENCES group_buy_groups(id) ON DELETE CASCADE,
                FOREIGN KEY (campaign_id) REFERENCES group_buy_campaigns(id) ON DELETE CASCADE,
                INDEX idx_group (group_id),
                INDEX idx_campaign (campaign_id),
                INDEX idx_customer (customer_id),
                INDEX idx_payment_status (payment_status),
                INDEX idx_status (status)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("✅ group_buy_participants table created")
        
        # 4. Create group_buy_notifications table (สำหรับแจ้งเตือน)
        print("📦 Creating group_buy_notifications table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS group_buy_notifications (
                id INT AUTO_INCREMENT PRIMARY KEY,
                
                group_id INT NOT NULL,
                participant_id INT,
                
                notification_type VARCHAR(50) NOT NULL COMMENT 'new_member, group_full, group_success, group_failed, reminder',
                message TEXT,
                
                sent_at DATETIME,
                read_at DATETIME,
                
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (group_id) REFERENCES group_buy_groups(id) ON DELETE CASCADE,
                INDEX idx_group (group_id),
                INDEX idx_type (notification_type)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("✅ group_buy_notifications table created")
        
        conn.commit()
        
        print("\n✅ Group Buy system tables created successfully!")
        print("📋 Created tables:")
        print("   1. group_buy_campaigns - แคมเปญ Group Buy")
        print("   2. group_buy_groups - กลุ่มที่ลูกค้าสร้าง")
        print("   3. group_buy_participants - สมาชิกในกลุ่ม")
        print("   4. group_buy_notifications - ระบบแจ้งเตือน")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

def main():
    print("=" * 70)
    print("🛍️ GROUP BUY SYSTEM - Database Migration")
    print("=" * 70)
    
    if create_group_buy_tables():
        print("\n🎉 Migration completed successfully!")
        print("\n📖 Next steps:")
        print("   1. Create models in models/group_buy.py")
        print("   2. Create service in services/group_buy_service.py")
        print("   3. Create routes in routes/group_buy.py")
        print("   4. Create public pages in routes/public_group_buy.py")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
