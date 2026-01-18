#!/usr/bin/env python3
"""
Migration script to add short_itinerary table
"""

from app import app, db
from sqlalchemy import text, inspect
from datetime import datetime

def add_short_itinerary_table():
    """Add short_itinerary table for itinerary templates"""
    
    with app.app_context():
        inspector = inspect(db.engine)
        
        # Check if table already exists
        if 'short_itinerary' in inspector.get_table_names():
            print("✅ Table 'short_itinerary' already exists")
            return
        
        print("📋 Creating 'short_itinerary' table...")
        
        # Create table
        db.session.execute(text("""
            CREATE TABLE short_itinerary (
                id INT AUTO_INCREMENT PRIMARY KEY,
                program_name VARCHAR(255) NOT NULL,
                description TEXT,
                adult_twin_sharing DECIMAL(10,2) DEFAULT 0.00,
                adult_single DECIMAL(10,2) DEFAULT 0.00,
                child_extra_bed DECIMAL(10,2) DEFAULT 0.00,
                child_no_bed DECIMAL(10,2) DEFAULT 0.00,
                infant DECIMAL(10,2) DEFAULT 0.00,
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_program_name (program_name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """))
        
        db.session.commit()
        print("✅ Table 'short_itinerary' created successfully!")
        
        # Verify table structure
        columns = inspector.get_columns('short_itinerary')
        print(f"\n📊 Table structure ({len(columns)} columns):")
        for col in columns:
            print(f"   - {col['name']}: {col['type']}")
        
        print("\n✅ Migration completed successfully!")

if __name__ == '__main__':
    try:
        add_short_itinerary_table()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
