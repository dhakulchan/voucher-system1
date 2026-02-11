"""
Add price_description field to group_buy_campaigns table
Migration script to add free text field for price description
"""
from extensions import db
from sqlalchemy import text

def upgrade():
    """Add price_description column"""
    try:
        with db.engine.connect() as conn:
            # Add price_description column
            conn.execute(text("""
                ALTER TABLE group_buy_campaigns 
                ADD COLUMN price_description VARCHAR(500) 
                DEFAULT 'ราคาต่อท่าน พัก 3 หรือ 2 ท่าน ต่อห้องตามเงื่อนไข'
            """))
            conn.commit()
            print("✅ Added price_description column to group_buy_campaigns table")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        db.session.rollback()
        raise

if __name__ == '__main__':
    from run import app
    with app.app_context():
        upgrade()
        print("✅ Migration completed successfully!")
