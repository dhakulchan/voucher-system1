#!/usr/bin/env python3
"""
Add icon column to landing_page_groups table
"""
from app import create_app
from extensions import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("=" * 80)
    print("Adding icon column to landing_page_groups table...")
    print("=" * 80)
    
    try:
        # Add icon column
        db.session.execute(text("""
            ALTER TABLE landing_page_groups 
            ADD COLUMN icon VARCHAR(10) DEFAULT '✈️' COMMENT 'Emoji icon for group'
            AFTER theme_color
        """))
        
        db.session.commit()
        print("✅ Column 'icon' added successfully!")
        
        # Show current structure
        result = db.session.execute(text("DESC landing_page_groups"))
        print("\n📋 Current table structure:")
        for row in result:
            print(f"  - {row[0]}: {row[1]}")
        
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.session.rollback()
