#!/usr/bin/env python3
"""
Migration script to add operation_status column to bookings table
"""
import pymysql
import sys

def add_operation_status_column():
    """Add operation_status column to bookings table"""
    connection = pymysql.connect(
        host='localhost',
        user='voucher_user',
        password='voucher_secure_2024',
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
                AND TABLE_NAME = 'bookings' 
                AND COLUMN_NAME = 'operation_status'
            """)
            
            if cursor.fetchone()[0] > 0:
                print("✅ Column 'operation_status' already exists")
                return True
            
            # Add column
            print("Adding operation_status column...")
            cursor.execute("""
                ALTER TABLE bookings 
                ADD COLUMN operation_status VARCHAR(50) 
                DEFAULT 'No' 
                COMMENT 'Operations team status: No/Yes/Cancel'
            """)
            
            # Add index for performance
            print("Creating index...")
            cursor.execute("""
                CREATE INDEX idx_operation_status 
                ON bookings(operation_status)
            """)
            
            connection.commit()
            print("✅ Successfully added operation_status column with index")
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        connection.rollback()
        return False
    finally:
        connection.close()

if __name__ == '__main__':
    success = add_operation_status_column()
    sys.exit(0 if success else 1)
