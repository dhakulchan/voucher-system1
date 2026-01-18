"""
Add remarks column to booking_tasks table
"""
import sys
from sqlalchemy import text
from app import app
from extensions import db

def add_remarks_column():
    """Add remarks column to booking_tasks table"""
    with app.app_context():
        try:
            # Check if column already exists
            result = db.session.execute(text("""
                SELECT COUNT(*) as count 
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'booking_tasks' 
                AND COLUMN_NAME = 'remarks'
            """)).fetchone()
            
            if result[0] > 0:
                print("✓ Column 'remarks' already exists in booking_tasks table")
                return True
            
            # Add remarks column
            print("Adding 'remarks' column to booking_tasks table...")
            db.session.execute(text("""
                ALTER TABLE booking_tasks 
                ADD COLUMN remarks TEXT NULL 
                AFTER description
            """))
            db.session.commit()
            
            print("✓ Successfully added 'remarks' column")
            return True
            
        except Exception as e:
            print(f"✗ Error adding remarks column: {str(e)}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    print("=" * 60)
    print("Adding Remarks Column to Booking Tasks")
    print("=" * 60)
    
    success = add_remarks_column()
    
    if success:
        print("\n✅ Migration completed successfully!")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)
