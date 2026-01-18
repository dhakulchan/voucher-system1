"""
Migration Script: Add air_ticket_cost column to invoices table
Purpose: Track air ticket costs/other expenses for invoices
"""

from models.booking import db
from app import app
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_air_ticket_cost_column():
    """Add air_ticket_cost column to invoices table"""
    
    with app.app_context():
        try:
            # Check if column already exists
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('invoices')]
            
            if 'air_ticket_cost' in columns:
                logger.info("✅ air_ticket_cost column already exists in invoices table")
                return True
            
            # Add air_ticket_cost column
            logger.info("➕ Adding air_ticket_cost column to invoices table...")
            
            with db.engine.connect() as conn:
                conn.execute(text("""
                    ALTER TABLE invoices 
                    ADD COLUMN air_ticket_cost DECIMAL(12,2) DEFAULT 0.00 
                    COMMENT 'Air ticket cost or other expenses'
                """))
                conn.commit()
            
            logger.info("✅ Successfully added air_ticket_cost column to invoices table")
            
            # Verify the column was added
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('invoices')]
            
            if 'air_ticket_cost' in columns:
                logger.info("✅ Verification successful: air_ticket_cost column exists")
                return True
            else:
                logger.error("❌ Verification failed: air_ticket_cost column not found")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error adding air_ticket_cost column: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    print("=" * 60)
    print("Adding air_ticket_cost Column to Invoices Table")
    print("=" * 60)
    
    success = add_air_ticket_cost_column()
    
    if success:
        print("\n✅ Migration completed successfully!")
        print("✅ air_ticket_cost column added to invoices table")
    else:
        print("\n❌ Migration failed!")
        print("Please check the error messages above")
