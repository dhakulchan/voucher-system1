#!/usr/bin/env python3
"""
Create activity_logs table for voucher system
"""

from app import create_app, db
import sqlalchemy as sa

def create_activity_logs_table():
    app = create_app()
    with app.app_context():
        # Create activity_logs table
        sql = '''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            booking_id INT,
            user_id INT,
            action VARCHAR(100) NOT NULL,
            description TEXT,
            old_value TEXT,
            new_value TEXT,
            ip_address VARCHAR(45),
            user_agent TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_booking_id (booking_id),
            INDEX idx_user_id (user_id),
            INDEX idx_action (action),
            INDEX idx_created_at (created_at),
            FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        '''
        
        try:
            db.engine.execute(sa.text(sql))
            print("✅ activity_logs table created successfully")
            
            # Verify table creation
            inspector = sa.inspect(db.engine)
            tables = inspector.get_table_names()
            if "activity_logs" in tables:
                print("✅ activity_logs table confirmed in database")
                
                # Get table structure
                columns = inspector.get_columns("activity_logs")
                print("📊 activity_logs columns:")
                for col in columns:
                    print(f"  - {col['name']}: {col['type']}")
            else:
                print("❌ activity_logs table not found after creation")
                
        except Exception as e:
            print(f"❌ Error creating activity_logs table: {e}")

if __name__ == "__main__":
    create_activity_logs_table()