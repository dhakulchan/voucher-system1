#!/usr/bin/env python3
"""
Migration script to add voucher_albums table for Voucher Library feature
Stores voucher album images with title and remarks
"""

import pymysql
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_voucher_albums_table():
    """Create voucher_albums table using direct MySQL connection"""
    
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
        
        # Create SQL statement
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS voucher_albums (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            remarks TEXT,
            image_path VARCHAR(500) NOT NULL,
            file_size INT NOT NULL COMMENT 'File size in bytes',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_created_at (created_at),
            INDEX idx_title (title)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
        
        # Execute the SQL
        cursor.execute(create_table_sql)
        connection.commit()
        
        print("✅ Successfully created voucher_albums table")
        
        # Verify table was created
        cursor.execute("SHOW TABLES LIKE 'voucher_albums'")
        result = cursor.fetchone()
        
        if result:
            print("✅ Table verification successful")
            
            # Show table structure
            cursor.execute("DESCRIBE voucher_albums")
            columns = cursor.fetchall()
            print("\n📋 Table structure:")
            for col in columns:
                print(f"  - {col[0]} ({col[1]})")
        else:
            print("❌ Table verification failed - table not found")
        
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
    create_voucher_albums_table()
