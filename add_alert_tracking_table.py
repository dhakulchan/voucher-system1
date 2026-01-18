"""
Add alert_tracking table to track email alerts sent per booking per day
"""
import pymysql
from datetime import datetime

def create_alert_tracking_table():
    """Create alert_tracking table"""
    try:
        connection = pymysql.connect(
            host='localhost',
            user='voucher_user',
            password='voucher_secure_2024',
            database='voucher_enhanced',
            charset='utf8mb4'
        )
        
        with connection.cursor() as cursor:
            # Create alert_tracking table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alert_tracking (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    booking_id INT NOT NULL,
                    alert_type VARCHAR(50) NOT NULL COMMENT 'time_limit or due_date',
                    alert_date DATE NOT NULL COMMENT 'Date when alert was sent',
                    sent_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_booking_alert (booking_id, alert_type, alert_date),
                    UNIQUE KEY unique_booking_alert_date (booking_id, alert_type, alert_date),
                    FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                COMMENT='Track email alerts sent to prevent duplicate alerts per day'
            """)
            
            connection.commit()
            print("✅ alert_tracking table created successfully")
            
            # Show table structure
            cursor.execute("DESCRIBE alert_tracking")
            print("\n📋 Table Structure:")
            for row in cursor.fetchall():
                print(f"  {row}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if connection:
            connection.close()

if __name__ == '__main__':
    create_alert_tracking_table()
