#!/usr/bin/env python3
"""
Add voucher_album_ids column to bookings table
Date: 2025-11-30
"""

import pymysql
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def add_voucher_album_ids_column():
    """Add voucher_album_ids column to bookings table"""
    
    # Database connection details
    db_config = {
        'host': 'localhost',
        'user': 'voucher_user',
        'password': 'voucher_secure_2024',
        'database': 'voucher_db',
        'charset': 'utf8mb4'
    }
    
    try:
        # Connect to database
        connection = pymysql.connect(**db_config)
        print("✅ Connected to database successfully")
        
        cursor = connection.cursor()
        
        # Check if column already exists
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'bookings' 
            AND COLUMN_NAME = 'voucher_album_ids'
        """)
        
        if cursor.fetchone():
            print("ℹ️  Column 'voucher_album_ids' already exists")
        else:
            # Add column
            cursor.execute("""
                ALTER TABLE bookings 
                ADD COLUMN voucher_album_ids TEXT 
                COMMENT 'JSON string of selected voucher album IDs from library'
                AFTER voucher_images
            """)
            connection.commit()
            print("✅ Successfully added voucher_album_ids column")
        
        # Verify column was added
        cursor.execute("DESCRIBE bookings")
        columns = cursor.fetchall()
        
        voucher_cols = [col for col in columns if 'voucher' in col[0].lower()]
        print("\n📋 Voucher-related columns in bookings table:")
        for col in voucher_cols:
            print(f"  - {col[0]} ({col[1]})")
        
        cursor.close()
        connection.close()
        print("\n✅ Migration completed successfully!")
        
    except pymysql.Error as e:
        print(f"❌ Database error: {e}")
        raise
    except Exception as e:
        print(f"❌ Error: {e}")
        raise

if __name__ == '__main__':
    add_voucher_album_ids_column()
