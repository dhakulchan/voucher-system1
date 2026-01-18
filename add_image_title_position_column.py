"""
Migration: Add image_title_position column to group_buy_campaigns table
This allows campaigns to specify where the image title badge should be positioned (left/center/right)
"""
from extensions import db
from app import create_app

def add_column():
    app = create_app()
    with app.app_context():
        try:
            # Add image_title_position column (default: 'left')
            with db.engine.connect() as conn:
                conn.execute(db.text("""
                    ALTER TABLE group_buy_campaigns 
                    ADD COLUMN image_title_position VARCHAR(20) DEFAULT 'left'
                    COMMENT 'Position of image title badge: left, center, or right'
                """))
                conn.commit()
            print("✅ Successfully added image_title_position column")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            print("Column may already exist or there's another issue")

if __name__ == '__main__':
    add_column()
