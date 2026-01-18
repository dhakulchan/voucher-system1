#!/usr/bin/env python3
"""
Add product_link column to short_itinerary table
"""

from app import app, db
from sqlalchemy import text, inspect

def add_product_link_column():
    with app.app_context():
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('short_itinerary')]
        
        if 'product_link' in columns:
            print('✅ Column product_link already exists')
            return
        
        print('📋 Adding product_link column...')
        try:
            db.session.execute(text('''
                ALTER TABLE short_itinerary
                ADD COLUMN product_link VARCHAR(500) NULL AFTER tour_code,
                ADD INDEX idx_product_link (product_link)
            '''))
            db.session.commit()
            print('✅ Column product_link added successfully!')
        except Exception as e:
            db.session.rollback()
            print(f'❌ Error: {e}')

if __name__ == '__main__':
    add_product_link_column()
