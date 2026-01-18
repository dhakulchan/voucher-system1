"""
เพิ่ม partial payment configuration fields
รองรับการตั้งค่าจำนวนเงินมัดจำแบบต่างๆ
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db

def add_partial_payment_config_fields():
    """Add partial payment configuration fields"""
    app = create_app()
    
    with app.app_context():
        try:
            with db.engine.connect() as conn:
                # Check existing columns
                result = conn.execute(db.text("""
                    SELECT COLUMN_NAME
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                    AND TABLE_NAME = 'group_buy_campaigns'
                    AND COLUMN_NAME IN ('partial_payment_type', 'partial_payment_value')
                """))
                existing = [row[0] for row in result.fetchall()]
                
                if 'partial_payment_type' in existing and 'partial_payment_value' in existing:
                    print("✓ Columns already exist")
                    return True
                
                print("Adding partial payment configuration fields...")
                
                # Add partial_payment_type
                if 'partial_payment_type' not in existing:
                    print("  - Adding partial_payment_type...")
                    conn.execute(db.text("""
                        ALTER TABLE group_buy_campaigns
                        ADD COLUMN partial_payment_type VARCHAR(20) DEFAULT 'percentage'
                        AFTER allow_partial_payment
                    """))
                    print("  ✓ partial_payment_type added")
                
                # Add partial_payment_value
                if 'partial_payment_value' not in existing:
                    print("  - Adding partial_payment_value...")
                    conn.execute(db.text("""
                        ALTER TABLE group_buy_campaigns
                        ADD COLUMN partial_payment_value DECIMAL(10, 2) DEFAULT 30.00
                        AFTER partial_payment_type
                    """))
                    print("  ✓ partial_payment_value added")
                
                conn.commit()
                
                print("\n✓ Successfully added partial payment configuration fields")
                print("\nField details:")
                print("- partial_payment_type: VARCHAR(20)")
                print("  Options: 'fixed' (คงที่/คน), 'percentage' (%), 'full' (เต็มจำนวน)")
                print("- partial_payment_value: DECIMAL(10,2)")
                print("  Value: จำนวนเงิน (fixed) หรือ % (percentage)")
                
                return True
                
        except Exception as e:
            print(f"✗ Error: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    print("=" * 60)
    print("Adding Partial Payment Configuration Fields")
    print("=" * 60)
    
    success = add_partial_payment_config_fields()
    
    if success:
        print("\n" + "=" * 60)
        print("Migration completed successfully!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("Migration failed!")
        print("=" * 60)
        sys.exit(1)
