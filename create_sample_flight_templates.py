#!/usr/bin/env python3
"""
Create sample flight templates
"""

from app import app, db
from models.flight_template import FlightTemplate

def create_sample_templates():
    with app.app_context():
        # Check if templates already exist
        existing = FlightTemplate.query.filter_by(template_name='BKK-HKG Round Trip').first()
        if existing:
            print('✅ Sample templates already exist')
            return
        
        print('📋 Creating sample flight templates...')
        
        try:
            # Template 1: Outbound flight
            template1 = FlightTemplate(
                template_name='BKK-HKG Outbound',
                date='20Dec25',
                flight_no='TG600',
                from_to='BKKHKG',
                time='08:00-12:00 +1hrs',
                note='เที่ยวบินและเวลาอาจมีการเปลี่ยนแปลงโดยขึ้นอยู่กับสายการบินที่ให้บริการเป็นหลัก'
            )
            db.session.add(template1)
            
            # Template 2: Return flight
            template2 = FlightTemplate(
                template_name='HKG-BKK Return',
                date='22Dec25',
                flight_no='TG607',
                from_to='HKGBKK',
                time='18:30-20:30 -1hrs',
                note='เที่ยวบินและเวลาอาจมีการเปลี่ยนแปลงโดยขึ้นอยู่กับสายการบินที่ให้บริการเป็นหลัก'
            )
            db.session.add(template2)
            
            # Template 3: Round trip combined
            template3 = FlightTemplate(
                template_name='BKK-HKG Round Trip',
                date='20Dec25-22Dec25',
                flight_no='TG600/TG607',
                from_to='BKKHKG/HKGBKK',
                time='08:00-12:00/18:30-20:30',
                note='เที่ยวบินและเวลาอาจมีการเปลี่ยนแปลงโดยขึ้นอยู่กับสายการบินที่ให้บริการเป็นหลัก'
            )
            db.session.add(template3)
            
            db.session.commit()
            print('✅ Sample flight templates created successfully!')
            print('   - BKK-HKG Outbound')
            print('   - HKG-BKK Return')
            print('   - BKK-HKG Round Trip')
            
        except Exception as e:
            db.session.rollback()
            print(f'❌ Error: {e}')

if __name__ == '__main__':
    create_sample_templates()
