"""
Add payment tracking fields to group buy tables

1. Add payment_timeout to group_buy_payments
2. Add payment_id to group_buy_participants
3. Add payment_status to group_buy_participants
"""

from sqlalchemy import text
from extensions import db

def upgrade():
    """เพิ่ม columns สำหรับ payment tracking"""
    
    conn = db.engine.connect()
    trans = conn.begin()
    
    try:
        # 1. เพิ่ม payment_timeout ใน group_buy_payments
        conn.execute(text("""
            ALTER TABLE group_buy_payments 
            ADD COLUMN payment_timeout DATETIME NULL 
            COMMENT 'เวลาหมดอายุการชำระเงิน (15 นาที หลังสร้าง)'
        """))
        print("✅ Added payment_timeout to group_buy_payments")
        
        # 2. เพิ่ม payment_id ใน group_buy_participants
        conn.execute(text("""
            ALTER TABLE group_buy_participants 
            ADD COLUMN payment_id INT NULL,
            ADD CONSTRAINT fk_participant_payment 
            FOREIGN KEY (payment_id) REFERENCES group_buy_payments(id) 
            ON DELETE SET NULL
        """))
        print("✅ Added payment_id to group_buy_participants")
        
        # 3. เพิ่ม payment_status ใน group_buy_participants
        conn.execute(text("""
            ALTER TABLE group_buy_participants 
            ADD COLUMN payment_status VARCHAR(20) DEFAULT 'pending' 
            COMMENT 'สถานะการชำระเงิน: pending, paid, refunded, failed'
        """))
        print("✅ Added payment_status to group_buy_participants")
        
        # 4. เพิ่ม index เพื่อเพิ่มประสิทธิภาพ
        conn.execute(text("""
            CREATE INDEX idx_participant_payment_status 
            ON group_buy_participants(payment_status)
        """))
        print("✅ Added index on payment_status")
        
        trans.commit()
        print("\n🎉 Migration completed successfully!")
        
    except Exception as e:
        trans.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        conn.close()

def downgrade():
    """ย้อนกลับการเปลี่ยนแปลง"""
    
    conn = db.engine.connect()
    trans = conn.begin()
    
    try:
        # ลบ columns ที่เพิ่มเข้าไป
        conn.execute(text("""
            ALTER TABLE group_buy_participants 
            DROP INDEX idx_participant_payment_status,
            DROP COLUMN payment_status,
            DROP FOREIGN KEY fk_participant_payment,
            DROP COLUMN payment_id
        """))
        
        conn.execute(text("""
            ALTER TABLE group_buy_payments 
            DROP COLUMN payment_timeout
        """))
        
        trans.commit()
        print("✅ Rollback completed")
        
    except Exception as e:
        trans.rollback()
        print(f"❌ Rollback failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    from app import create_app
    app = create_app()
    
    with app.app_context():
        upgrade()
