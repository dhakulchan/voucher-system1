"""
Migration Script: Add calculation fields to invoices table
Purpose: Add Transportation_fee, Advance_expense, Tour_fee, Vat, Withholding_tax, Total_tour_fee
"""

from models.booking import db
from app import app
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_calculation_fields():
    """Add calculation fields to invoices table"""
    
    with app.app_context():
        try:
            # Check if columns already exist
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('invoices')]
            
            new_columns = {
                'transportation_fee': 'Transportation fee (calculated)',
                'advance_expense': 'Advance expense (calculated)',
                'tour_fee': 'Tour fee (calculated)',
                'vat': 'VAT 7% (calculated)',
                'withholding_tax': 'Withholding tax (default 0)',
                'total_tour_fee': 'Total tour fee (calculated)'
            }
            
            with db.engine.connect() as conn:
                for col_name, description in new_columns.items():
                    if col_name in columns:
                        logger.info(f"✅ {col_name} column already exists")
                    else:
                        logger.info(f"➕ Adding {col_name} column...")
                        conn.execute(text(f"""
                            ALTER TABLE invoices 
                            ADD COLUMN {col_name} DECIMAL(12,2) DEFAULT 0.00 
                            COMMENT '{description}'
                        """))
                        conn.commit()
                        logger.info(f"✅ Successfully added {col_name} column")
            
            # Verify all columns were added
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('invoices')]
            
            all_present = all(col in columns for col in new_columns.keys())
            
            if all_present:
                logger.info("✅ All calculation fields verified successfully")
                return True
            else:
                missing = [col for col in new_columns.keys() if col not in columns]
                logger.error(f"❌ Missing columns: {missing}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error adding calculation fields: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    print("=" * 60)
    print("Adding Calculation Fields to Invoices Table")
    print("=" * 60)
    
    success = add_calculation_fields()
    
    if success:
        print("\n✅ Migration completed successfully!")
        print("✅ All 6 calculation fields added to invoices table:")
        print("   - transportation_fee")
        print("   - advance_expense")
        print("   - tour_fee")
        print("   - vat")
        print("   - withholding_tax")
        print("   - total_tour_fee")
    else:
        print("\n❌ Migration failed!")
        print("Please check the error messages above")
