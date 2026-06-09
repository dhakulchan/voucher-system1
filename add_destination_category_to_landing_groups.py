"""Migration: Add destination_category to landing_page_groups table"""
from app import app
from extensions import db

DESTINATION_CHOICES = [
    ('china', '🇨🇳 จีน / มาเก๊า / ฮ่องกง'),
    ('japan', '🇯🇵 ญี่ปุ่น'),
    ('korea', '🇰🇷 เกาหลี'),
    ('europe', '🌍 ยุโรป'),
    ('asean', '🌏 อาเซียน'),
    ('domestic', '🇹🇭 ไทย'),
    ('other', '✈️ อื่นๆ'),
]

with app.app_context():
    try:
        db.engine.execute("ALTER TABLE landing_page_groups ADD COLUMN destination_category VARCHAR(100) NULL")
        print("✅ Added destination_category column")
    except Exception as e:
        if 'Duplicate column name' in str(e) or 'already exists' in str(e):
            print("ℹ️  Column already exists, skipping")
        else:
            print(f"❌ Error: {e}")
    
    print("\n✅ Migration complete!")
    print("\nDestination choices available:")
    for key, label in DESTINATION_CHOICES:
        print(f"  {key}: {label}")
