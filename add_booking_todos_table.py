"""
Create booking_todos table for managing todo items and notes per booking
"""

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS booking_todos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT NOT NULL,
    text TEXT NOT NULL,
    is_completed TINYINT(1) DEFAULT 0,
    priority VARCHAR(20) DEFAULT 'normal',
    category VARCHAR(50),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    completed_at DATETIME,
    created_by INT,
    
    FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
    
    INDEX idx_booking_id (booking_id),
    INDEX idx_is_completed (is_completed),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

if __name__ == '__main__':
    import pymysql
    
    # Database connection details
    connection = pymysql.connect(
        host='localhost',
        user='voucher_user',
        password='voucher_secure_2024',
        database='voucher_enhanced',
        charset='utf8mb4'
    )
    
    try:
        with connection.cursor() as cursor:
            print("Creating booking_todos table...")
            cursor.execute(CREATE_TABLE_SQL)
            connection.commit()
            print("✅ Table booking_todos created successfully!")
            
            # Verify table was created
            cursor.execute("SHOW TABLES LIKE 'booking_todos'")
            result = cursor.fetchone()
            if result:
                print("✅ Verified: booking_todos table exists")
                
                # Show table structure
                cursor.execute("DESCRIBE booking_todos")
                print("\nTable structure:")
                for row in cursor.fetchall():
                    print(f"  {row}")
            else:
                print("❌ Error: Table was not created")
    
    except Exception as e:
        print(f"❌ Error creating table: {e}")
        connection.rollback()
    
    finally:
        connection.close()
