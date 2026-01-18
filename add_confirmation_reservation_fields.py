"""
Rename remarks to confirmation and add reservation field to booking_tasks table
"""
import sys
from sqlalchemy import text
from app import app
from extensions import db

def update_booking_tasks_fields():
    """Rename remarks to confirmation and add reservation field"""
    with app.app_context():
        try:
            # Check if remarks column exists
            result = db.session.execute(text("""
                SELECT COUNT(*) as count 
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'booking_tasks' 
                AND COLUMN_NAME = 'remarks'
            """)).fetchone()
            
            if result[0] > 0:
                print("Renaming 'remarks' column to 'confirmation'...")
                db.session.execute(text("""
                    ALTER TABLE booking_tasks 
                    CHANGE COLUMN remarks confirmation TEXT NULL
                """))
                db.session.commit()
                print("✓ Successfully renamed 'remarks' to 'confirmation'")
            else:
                # Check if confirmation already exists
                result = db.session.execute(text("""
                    SELECT COUNT(*) as count 
                    FROM information_schema.COLUMNS 
                    WHERE TABLE_SCHEMA = DATABASE() 
                    AND TABLE_NAME = 'booking_tasks' 
                    AND COLUMN_NAME = 'confirmation'
                """)).fetchone()
                
                if result[0] > 0:
                    print("✓ Column 'confirmation' already exists")
                else:
                    print("Adding 'confirmation' column...")
                    db.session.execute(text("""
                        ALTER TABLE booking_tasks 
                        ADD COLUMN confirmation TEXT NULL 
                        AFTER description
                    """))
                    db.session.commit()
                    print("✓ Successfully added 'confirmation' column")
            
            # Check if reservation column already exists
            result = db.session.execute(text("""
                SELECT COUNT(*) as count 
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'booking_tasks' 
                AND COLUMN_NAME = 'reservation'
            """)).fetchone()
            
            if result[0] > 0:
                print("✓ Column 'reservation' already exists in booking_tasks table")
                return True
            
            # Add reservation column
            print("Adding 'reservation' column to booking_tasks table...")
            db.session.execute(text("""
                ALTER TABLE booking_tasks 
                ADD COLUMN reservation TEXT NULL 
                AFTER confirmation
            """))
            db.session.commit()
            
            print("✓ Successfully added 'reservation' column")
            return True
            
        except Exception as e:
            print(f"✗ Error updating booking_tasks fields: {str(e)}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    print("=" * 60)
    print("Updating Booking Tasks Fields")
    print("=" * 60)
    
    success = update_booking_tasks_fields()
    
    if success:
        print("\n✅ Migration completed successfully!")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)
