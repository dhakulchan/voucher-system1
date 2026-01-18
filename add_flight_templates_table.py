#!/usr/bin/env python3
"""
Create flight_templates table
"""

from app import app, db
from sqlalchemy import text, inspect

def create_flight_templates_table():
    with app.app_context():
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        if 'flight_templates' in tables:
            print('✅ Table flight_templates already exists')
            return
        
        print('📋 Creating flight_templates table...')
        try:
            db.session.execute(text('''
                CREATE TABLE flight_templates (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    template_name VARCHAR(255) NOT NULL,
                    date VARCHAR(50) NULL,
                    flight_no VARCHAR(50) NULL,
                    from_to VARCHAR(100) NULL,
                    time VARCHAR(50) NULL,
                    note TEXT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_template_name (template_name)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            '''))
            db.session.commit()
            print('✅ Table flight_templates created successfully!')
        except Exception as e:
            db.session.rollback()
            print(f'❌ Error: {e}')

if __name__ == '__main__':
    create_flight_templates_table()
