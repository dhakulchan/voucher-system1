"""
Create booking_tasks table for managing tasks with sub-tasks per booking
Replaces booking_todos with enhanced task management features
"""

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS booking_tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT NOT NULL,
    parent_task_id INT NULL,
    
    -- Task details
    title VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Task management
    assigned_to INT,
    status VARCHAR(50) DEFAULT 'pending',
    priority VARCHAR(20) DEFAULT 'normal',
    category VARCHAR(50),
    
    -- Deadline and completion
    deadline DATE,
    is_completed TINYINT(1) DEFAULT 0,
    completed_at DATETIME,
    
    -- Timestamps
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by INT,
    
    -- Foreign keys
    FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_task_id) REFERENCES booking_tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL,
    
    -- Indexes
    INDEX idx_booking_id (booking_id),
    INDEX idx_parent_task_id (parent_task_id),
    INDEX idx_status (status),
    INDEX idx_is_completed (is_completed),
    INDEX idx_deadline (deadline),
    INDEX idx_assigned_to (assigned_to),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

MIGRATE_DATA_SQL = """
INSERT INTO booking_tasks (
    booking_id, 
    title, 
    is_completed, 
    priority, 
    category, 
    created_at, 
    updated_at, 
    completed_at, 
    created_by,
    status
)
SELECT 
    booking_id,
    text as title,
    is_completed,
    priority,
    category,
    created_at,
    updated_at,
    completed_at,
    created_by,
    CASE 
        WHEN is_completed = 1 THEN 'completed'
        ELSE 'pending'
    END as status
FROM booking_todos
WHERE NOT EXISTS (
    SELECT 1 FROM booking_tasks WHERE booking_tasks.booking_id = booking_todos.booking_id
);
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
            print("Creating booking_tasks table...")
            cursor.execute(CREATE_TABLE_SQL)
            connection.commit()
            print("✅ Table booking_tasks created successfully!")
            
            # Verify table was created
            cursor.execute("SHOW TABLES LIKE 'booking_tasks'")
            result = cursor.fetchone()
            if result:
                print("✅ Verified: booking_tasks table exists")
                
                # Show table structure
                cursor.execute("DESCRIBE booking_tasks")
                print("\nTable structure:")
                for row in cursor.fetchall():
                    print(f"  {row}")
                
                # Check if booking_todos exists and has data
                cursor.execute("SHOW TABLES LIKE 'booking_todos'")
                if cursor.fetchone():
                    cursor.execute("SELECT COUNT(*) FROM booking_todos")
                    todo_count = cursor.fetchone()[0]
                    
                    if todo_count > 0:
                        print(f"\n📦 Found {todo_count} todos to migrate...")
                        print("Migrating data from booking_todos to booking_tasks...")
                        cursor.execute(MIGRATE_DATA_SQL)
                        connection.commit()
                        
                        cursor.execute("SELECT COUNT(*) FROM booking_tasks")
                        task_count = cursor.fetchone()[0]
                        print(f"✅ Migrated {task_count} tasks successfully!")
                    else:
                        print("\n📭 No todos to migrate (booking_todos is empty)")
                else:
                    print("\n📭 booking_todos table not found, no migration needed")
                    
            else:
                print("❌ Error: Table was not created")
    
    except Exception as e:
        print(f"❌ Error creating table: {e}")
        connection.rollback()
    
    finally:
        connection.close()
