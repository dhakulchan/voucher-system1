"""
เพิ่ม allow_partial_payment field ให้ GroupBuyCampaign
รองรับการอนุญาตให้จ่ายเงินบางส่วนสำหรับการจองกลุ่ม
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db

def add_allow_partial_payment_field():
    """Add allow_partial_payment field to group_buy_campaigns table"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if column already exists
            with db.engine.connect() as conn:
                result = conn.execute(db.text("""
                    SELECT COUNT(*) as count
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                    AND TABLE_NAME = 'group_buy_campaigns'
                    AND COLUMN_NAME = 'allow_partial_payment'
                """))
                exists = result.fetchone()[0] > 0
                
                if exists:
                    print("✓ Column 'allow_partial_payment' already exists")
                    return True
                
                # Add the column
                print("Adding 'allow_partial_payment' column...")
                conn.execute(db.text("""
                    ALTER TABLE group_buy_campaigns
                    ADD COLUMN allow_partial_payment BOOLEAN DEFAULT FALSE
                    AFTER payment_qr_image
                """))
                conn.commit()
                
                print("✓ Successfully added 'allow_partial_payment' column")
                print("\nColumn details:")
                print("- Type: BOOLEAN")
                print("- Default: FALSE")
                print("- Allows NULL: No")
                print("- Purpose: อนุญาตให้จ่ายเงินบางส่วน (มัดจำ)")
                
                return True
                
        except Exception as e:
            print(f"✗ Error: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    print("=" * 60)
    print("Adding allow_partial_payment field to GroupBuyCampaign")
    print("=" * 60)
    
    success = add_allow_partial_payment_field()
    
    if success:
        print("\n" + "=" * 60)
        print("Migration completed successfully!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("Migration failed!")
        print("=" * 60)
        sys.exit(1)
