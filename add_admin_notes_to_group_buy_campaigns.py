"""
Add admin_notes column to group_buy_campaigns table
"""
import pymysql
import os

def add_admin_notes_column():
    """เพิ่ม admin_notes column"""
    connection = pymysql.connect(
        host='localhost',
        user='root',
        password='',
        database='voucher_enhanced',
        charset='utf8mb4'
    )
    
    try:
        with connection.cursor() as cursor:
            # Check if column exists
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = 'voucher_enhanced'
                AND TABLE_NAME = 'group_buy_campaigns' 
                AND COLUMN_NAME = 'admin_notes'
            """)
            
            exists = cursor.fetchone()[0]
            
            if not exists:
                print("Adding admin_notes column to group_buy_campaigns...")
                cursor.execute("""
                    ALTER TABLE group_buy_campaigns 
                    ADD COLUMN admin_notes TEXT AFTER terms_conditions
                """)
                connection.commit()
                print("✅ admin_notes column added successfully")
            else:
                print("⚠️  admin_notes column already exists")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        connection.rollback()
    finally:
        connection.close()

if __name__ == '__main__':
    add_admin_notes_column()
