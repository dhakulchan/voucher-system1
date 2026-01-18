#!/usr/bin/env python3
"""
Migration script to add tour_code column to short_itinerary table
"""

from app import app, db
from sqlalchemy import text, inspect

def add_tour_code_column():
    """Add tour_code column to short_itinerary table"""
    
    with app.app_context():
        inspector = inspect(db.engine)
        
        # Check if table exists
        if 'short_itinerary' not in inspector.get_table_names():
            print("❌ Table 'short_itinerary' does not exist")
            return
        
        # Check if column already exists
        columns = [col['name'] for col in inspector.get_columns('short_itinerary')]
        
        if 'tour_code' in columns:
            print("✅ Column 'tour_code' already exists")
            return
        
        print("📋 Adding 'tour_code' column to 'short_itinerary' table...")
        
        # Add column
        db.session.execute(text("""
            ALTER TABLE short_itinerary
            ADD COLUMN tour_code VARCHAR(100) NULL AFTER program_name,
            ADD INDEX idx_tour_code (tour_code)
        """))
        
        db.session.commit()
        print("✅ Column 'tour_code' added successfully!")
        
        # Verify column structure
        columns = inspector.get_columns('short_itinerary')
        tour_code_col = next((col for col in columns if col['name'] == 'tour_code'), None)
        
        if tour_code_col:
            print(f"\n✅ Verified: tour_code column added")
            print(f"   Type: {tour_code_col['type']}")
            print(f"   Nullable: {tour_code_col['nullable']}")
        
        print("\n✅ Migration completed successfully!")

if __name__ == '__main__':
    try:
        add_tour_code_column()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
