"""
เพิ่ม special_booker_codes field ให้ GroupBuyCampaign
เพื่อให้ผู้จองที่มีรหัสพิเศษสามารถจองซ้ำได้
"""
import pymysql
from datetime import datetime

def add_special_booker_codes_field():
    """Add special_booker_codes field to group_buy_campaigns table"""
    
    connection = pymysql.connect(
        host='localhost',
        user='voucher_user',
        password='voucher_secure_2024',
        database='voucher_enhanced',
        charset='utf8mb4'
    )
    
    try:
        with connection.cursor() as cursor:
            # ตรวจสอบว่า column มีอยู่แล้วหรือไม่
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = 'voucher_enhanced'
                    AND TABLE_NAME = 'group_buy_campaigns'
                    AND COLUMN_NAME = 'special_booker_codes'
            """)
            result = cursor.fetchone()
            
            if result[0] == 0:
                print("➕ Adding special_booker_codes field...")
                
                cursor.execute("""
                    ALTER TABLE group_buy_campaigns
                    ADD COLUMN special_booker_codes TEXT 
                    COMMENT 'JSON array of special codes that allow multiple bookings'
                    AFTER admin_notes
                """)
                
                connection.commit()
                print("✅ special_booker_codes field added successfully!")
                print("📝 รหัสพิเศษนี้จะอนุญาตให้ผู้จองสามารถจองซ้ำได้หลายครั้ง")
            else:
                print("ℹ️  special_booker_codes field already exists")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        connection.rollback()
        raise
    finally:
        connection.close()

if __name__ == '__main__':
    print("=" * 60)
    print("🎫 Adding Special Booker Codes to Group Buy Campaigns")
    print("=" * 60)
    add_special_booker_codes_field()
    print("=" * 60)
    print("✅ Migration completed!")
    print("=" * 60)
