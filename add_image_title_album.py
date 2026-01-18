#!/usr/bin/env python3
"""
Add image_title and album_images columns to group_buy_campaigns table
"""
import pymysql
import sys

def main():
    try:
        # Connect to database
        conn = pymysql.connect(
            host='localhost',
            user='root',
            password='',
            database='voucher_enhanced',
            charset='utf8mb4'
        )
        cursor = conn.cursor()
        
        print("Adding image_title column...")
        try:
            cursor.execute("""
                ALTER TABLE group_buy_campaigns 
                ADD COLUMN image_title VARCHAR(255) DEFAULT NULL
                AFTER product_image
            """)
            print("✅ Added image_title column")
        except pymysql.err.OperationalError as e:
            if "Duplicate column name" in str(e):
                print("ℹ️  image_title column already exists")
            else:
                raise
        
        print("\nAdding album_images column...")
        try:
            cursor.execute("""
                ALTER TABLE group_buy_campaigns 
                ADD COLUMN album_images TEXT DEFAULT NULL
                AFTER image_title
            """)
            print("✅ Added album_images column")
        except pymysql.err.OperationalError as e:
            if "Duplicate column name" in str(e):
                print("ℹ️  album_images column already exists")
            else:
                raise
        
        conn.commit()
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    main()
