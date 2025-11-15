#!/usr/bin/env python3
"""Add invoice status fields to booking table using direct SQL"""

from app import create_app, db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_invoice_status_fields():
    """Add invoice status tracking fields to booking table"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if columns already exist
            with db.engine.connect() as conn:
                existing_columns = conn.execute(db.text("PRAGMA table_info(booking)")).fetchall()
                column_names = [col[1] for col in existing_columns]
                
                fields_to_add = [
                    ('invoice_status', 'VARCHAR(50)'),
                    ('invoice_amount', 'DECIMAL(10, 2)'),
                    ('invoice_paid_date', 'DATETIME'),
                    ('last_sync_date', 'DATETIME')
                ]
                
                for field_name, field_type in fields_to_add:
                    if field_name not in column_names:
                        sql = f"ALTER TABLE booking ADD COLUMN {field_name} {field_type}"
                        logger.info(f"Adding column: {sql}")
                        conn.execute(db.text(sql))
                        conn.commit()
                        logger.info(f"✅ Added column: {field_name}")
                    else:
                        logger.info(f"⚠️ Column {field_name} already exists")
            
            logger.info("✅ Migration completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            raise

if __name__ == "__main__":
    add_invoice_status_fields()
