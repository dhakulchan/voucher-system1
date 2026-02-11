"""
Add Group Buy Coupon System Tables
Migration script for coupon management
"""
from extensions import db
from sqlalchemy import text

def upgrade():
    """Add coupon tables"""
    try:
        with db.engine.connect() as conn:
            # Create coupons table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS group_buy_coupons (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    code VARCHAR(50) UNIQUE NOT NULL,
                    description TEXT,
                    discount_type ENUM('fixed', 'percentage') NOT NULL DEFAULT 'fixed',
                    discount_value DECIMAL(10,2) NOT NULL,
                    
                    max_uses INT DEFAULT NULL COMMENT 'NULL = unlimited',
                    used_count INT DEFAULT 0,
                    max_uses_per_user INT DEFAULT 1,
                    
                    min_purchase_amount DECIMAL(10,2) DEFAULT 0.00,
                    campaign_id INT DEFAULT NULL COMMENT 'NULL = all campaigns',
                    
                    start_date DATETIME NOT NULL,
                    end_date DATETIME NOT NULL,
                    
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    created_by INT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    
                    INDEX idx_code (code),
                    INDEX idx_active (is_active),
                    INDEX idx_campaign (campaign_id),
                    FOREIGN KEY (campaign_id) REFERENCES group_buy_campaigns(id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """))
            print("✅ Created group_buy_coupons table")
            
            # Create coupon usage tracking table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS group_buy_coupon_usage (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    coupon_id INT NOT NULL,
                    participant_id INT,
                    payment_id INT,
                    campaign_id INT,
                    discount_amount DECIMAL(10,2) NOT NULL,
                    original_amount DECIMAL(10,2) NOT NULL,
                    final_amount DECIMAL(10,2) NOT NULL,
                    customer_email VARCHAR(255),
                    used_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    
                    INDEX idx_coupon (coupon_id),
                    INDEX idx_participant (participant_id),
                    INDEX idx_email (customer_email),
                    FOREIGN KEY (coupon_id) REFERENCES group_buy_coupons(id) ON DELETE CASCADE,
                    FOREIGN KEY (participant_id) REFERENCES group_buy_participants(id) ON DELETE SET NULL,
                    FOREIGN KEY (campaign_id) REFERENCES group_buy_campaigns(id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """))
            print("✅ Created group_buy_coupon_usage table")
            
            # Add coupon fields to payments table
            conn.execute(text("""
                ALTER TABLE group_buy_payments 
                ADD COLUMN IF NOT EXISTS coupon_id INT DEFAULT NULL,
                ADD COLUMN IF NOT EXISTS coupon_code VARCHAR(50) DEFAULT NULL,
                ADD COLUMN IF NOT EXISTS discount_amount DECIMAL(10,2) DEFAULT 0.00,
                ADD COLUMN IF NOT EXISTS original_amount DECIMAL(10,2) DEFAULT 0.00,
                ADD INDEX IF NOT EXISTS idx_coupon (coupon_id)
            """))
            print("✅ Added coupon fields to group_buy_payments table")
            
            conn.commit()
            print("✅ All tables created successfully!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        db.session.rollback()
        raise

if __name__ == '__main__':
    from run import app
    with app.app_context():
        upgrade()
        print("✅ Migration completed successfully!")
