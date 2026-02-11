"""
Create queue_sequences table for atomic queue number generation
"""
from app import app, db
from sqlalchemy import text

def create_queue_sequence_table():
    """Create the queue_sequences helper table"""
    with app.app_context():
        # Create the table
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS queue_sequences (
                date_prefix VARCHAR(4) PRIMARY KEY COMMENT 'YYMM format like 2601',
                next_number INT NOT NULL DEFAULT 1 COMMENT 'Next number to use',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_prefix (date_prefix)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            COMMENT='Atomic counter for queue number generation'
        """))
        db.session.commit()
        print("✅ queue_sequences table created successfully")

if __name__ == '__main__':
    create_queue_sequence_table()
