"""
Add paid_at column to group_buy_payments table
"""
from extensions import db
from datetime import datetime

def add_paid_at_column():
    """Add paid_at column to group_buy_payments"""
    try:
        # Add paid_at column
        with db.engine.connect() as conn:
            conn.execute(db.text("""
                ALTER TABLE group_buy_payments 
                ADD COLUMN paid_at DATETIME DEFAULT NULL
                AFTER admin_notes
            """))
            conn.commit()
            print("✅ Added paid_at column to group_buy_payments")
            
            # Update existing paid records with created_at or admin_verified_at
            conn.execute(db.text("""
                UPDATE group_buy_payments 
                SET paid_at = COALESCE(admin_verified_at, created_at)
                WHERE payment_status = 'paid'
            """))
            conn.commit()
            print("✅ Updated existing paid records with paid_at timestamps")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        raise

if __name__ == '__main__':
    from app import create_app
    app = create_app()
    with app.app_context():
        add_paid_at_column()
        print("✅ Migration completed successfully!")
