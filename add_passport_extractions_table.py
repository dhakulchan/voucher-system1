"""
Add passport_extractions table for temporary MRZ data storage
PDPA compliant: Auto-cleanup after confirmation or 24 hours
"""

from app import db
import pymysql

def upgrade():
    """Create passport_extractions table"""
    try:
        connection = pymysql.connect(
            host='localhost',
            user='voucher_user',
            password='voucher_secure_2024',
            database='voucher_enhanced',
            charset='utf8mb4'
        )
        
        with connection.cursor() as cursor:
            # Create table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS passport_extractions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    booking_id INT NOT NULL,
                    filename_hash VARCHAR(32) NOT NULL,
                    extracted_data JSON NOT NULL,
                    user_id INT NOT NULL,
                    confirmed BOOLEAN DEFAULT FALSE NOT NULL,
                    confirmed_at DATETIME NULL,
                    confirmed_by INT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    
                    INDEX idx_booking_id (booking_id),
                    INDEX idx_confirmed (confirmed),
                    INDEX idx_created_at (created_at),
                    
                    FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (confirmed_by) REFERENCES users(id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)
            
            connection.commit()
            print("✅ passport_extractions table created successfully")
            
    except Exception as e:
        print(f"❌ Error creating passport_extractions table: {e}")
        raise
    finally:
        connection.close()

def downgrade():
    """Drop passport_extractions table"""
    try:
        connection = pymysql.connect(
            host='localhost',
            user='voucher_user',
            password='voucher_secure_2024',
            database='voucher_enhanced',
            charset='utf8mb4'
        )
        
        with connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS passport_extractions;")
            connection.commit()
            print("✅ passport_extractions table dropped successfully")
            
    except Exception as e:
        print(f"❌ Error dropping passport_extractions table: {e}")
        raise
    finally:
        connection.close()

if __name__ == '__main__':
    print("Running passport_extractions table migration...")
    upgrade()
    print("Migration completed!")
