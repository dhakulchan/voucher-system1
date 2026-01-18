"""
Add auto_cancel_hours and auto_cancel_send_email columns to group_buy_campaigns table
"""
from extensions import db

def add_auto_cancel_fields():
    """Add auto cancel configuration fields"""
    try:
        with db.engine.connect() as conn:
            # Add auto_cancel_enabled column
            try:
                conn.execute(db.text("""
                    ALTER TABLE group_buy_campaigns 
                    ADD COLUMN auto_cancel_enabled BOOLEAN DEFAULT FALSE
                    AFTER partial_payment_value
                """))
                conn.commit()
                print("✅ Added auto_cancel_enabled column")
            except Exception as e:
                if "Duplicate column" not in str(e):
                    raise
                print("⚠️  auto_cancel_enabled column already exists")
            
            # Add auto_cancel_hours column
            try:
                conn.execute(db.text("""
                    ALTER TABLE group_buy_campaigns 
                    ADD COLUMN auto_cancel_hours INT DEFAULT 4
                    AFTER auto_cancel_enabled
                """))
                conn.commit()
                print("✅ Added auto_cancel_hours column")
            except Exception as e:
                if "Duplicate column" not in str(e):
                    raise
                print("⚠️  auto_cancel_hours column already exists")
            
            # Add auto_cancel_send_email column
            try:
                conn.execute(db.text("""
                    ALTER TABLE group_buy_campaigns 
                    ADD COLUMN auto_cancel_send_email BOOLEAN DEFAULT TRUE
                    AFTER auto_cancel_hours
                """))
                conn.commit()
                print("✅ Added auto_cancel_send_email column")
            except Exception as e:
                if "Duplicate column" not in str(e):
                    raise
                print("⚠️  auto_cancel_send_email column already exists")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        raise

if __name__ == '__main__':
    from app import create_app
    app = create_app()
    with app.app_context():
        add_auto_cancel_fields()
        print("✅ Migration completed successfully!")
