"""
Migration: Add Payment System tables for Group Buy
- Payment methods (Stripe, Bank Transfer, QR Code)
- Payment transactions
- Payment fee configurations
"""
from extensions import db
from app import create_app

def create_tables():
    app = create_app()
    with app.app_context():
        try:
            with db.engine.connect() as conn:
                # 1. Add payment configuration columns to campaigns (one by one)
                print("Adding payment configuration columns to group_buy_campaigns...")
                
                columns_to_add = [
                    ("payment_stripe_enabled", "BOOLEAN DEFAULT FALSE"),
                    ("payment_stripe_fee_type", "VARCHAR(20) DEFAULT 'percentage'"),
                    ("payment_stripe_fee_value", "DECIMAL(10,2) DEFAULT 0.00"),
                    ("payment_stripe_fee_label", "VARCHAR(100) DEFAULT 'ค่าธรรมเนียม'"),
                    ("payment_bank_enabled", "BOOLEAN DEFAULT TRUE"),
                    ("payment_qr_enabled", "BOOLEAN DEFAULT FALSE"),
                    ("payment_qr_image", "VARCHAR(500)")
                ]
                
                for col_name, col_def in columns_to_add:
                    try:
                        conn.execute(db.text(f"""
                            ALTER TABLE group_buy_campaigns 
                            ADD COLUMN {col_name} {col_def}
                        """))
                        conn.commit()
                        print(f"  ✓ Added {col_name}")
                    except Exception as e:
                        if "Duplicate column" in str(e):
                            print(f"  - {col_name} already exists")
                        else:
                            print(f"  ✗ Error adding {col_name}: {e}")
                
                # 2. Create bank accounts table
                print("Creating group_buy_bank_accounts table...")
                conn.execute(db.text("""
                    CREATE TABLE IF NOT EXISTS group_buy_bank_accounts (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        bank_name VARCHAR(100) NOT NULL,
                        account_number VARCHAR(50) NOT NULL,
                        account_name VARCHAR(200) NOT NULL,
                        bank_logo VARCHAR(500),
                        is_active BOOLEAN DEFAULT TRUE,
                        display_order INT DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """))
                conn.commit()
                
                # 3. Create payments table
                print("Creating group_buy_payments table...")
                conn.execute(db.text("""
                    CREATE TABLE IF NOT EXISTS group_buy_payments (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        booking_id INT NOT NULL,
                        campaign_id INT NOT NULL,
                        group_id INT,
                        customer_name VARCHAR(200),
                        customer_email VARCHAR(200),
                        customer_phone VARCHAR(50),
                        
                        payment_method VARCHAR(50) NOT NULL COMMENT 'stripe, bank_transfer, qr_code',
                        payment_status VARCHAR(50) DEFAULT 'pending' COMMENT 'pending, paid, refunded, failed',
                        
                        amount DECIMAL(10,2) NOT NULL,
                        fee_amount DECIMAL(10,2) DEFAULT 0.00,
                        total_amount DECIMAL(10,2) NOT NULL,
                        
                        bank_account_id INT,
                        transfer_date DATE,
                        transfer_time TIME,
                        slip_image VARCHAR(500),
                        
                        stripe_payment_intent_id VARCHAR(200),
                        stripe_charge_id VARCHAR(200),
                        
                        admin_verified_by INT,
                        admin_verified_at TIMESTAMP NULL,
                        admin_notes TEXT,
                        
                        refund_amount DECIMAL(10,2),
                        refund_reason TEXT,
                        refunded_at TIMESTAMP NULL,
                        refunded_by INT,
                        
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        
                        INDEX idx_booking (booking_id),
                        INDEX idx_campaign (campaign_id),
                        INDEX idx_status (payment_status),
                        INDEX idx_method (payment_method)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """))
                conn.commit()
                
                print("✅ Successfully created all payment system tables!")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    create_tables()
