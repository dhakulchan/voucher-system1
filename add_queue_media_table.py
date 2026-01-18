"""
Add queue_media table for storing display media
สร้างตารางสำหรับเก็บภาพและวีดีโอที่แสดงในหน้า Queue Display
"""
from app import db, create_app
from models.queue_media import QueueMedia

def add_queue_media_table():
    """Create queue_media table"""
    app = create_app()
    
    with app.app_context():
        try:
            # Create table
            db.create_all()
            print("✅ Successfully created queue_media table!")
            
            # Add sample data
            sample_media = [
                QueueMedia(
                    title='ยินดีต้อนรับสู่ Dhakul Chan Nice Holidays',
                    description='บริษัททัวร์ชั้นนำของไทย',
                    media_type='image',
                    file_path='/static/queue_media/welcome.jpg',
                    duration=10,
                    display_order=1,
                    is_active=True
                ),
                QueueMedia(
                    title='โปรโมชั่นทัวร์ญี่ปุ่น',
                    description='ทัวร์ญี่ปุ่น 5 วัน 3 คืน เริ่มต้น 19,900 บาท',
                    media_type='image',
                    file_path='/static/queue_media/japan_promo.jpg',
                    duration=15,
                    display_order=2,
                    is_active=True
                ),
                QueueMedia(
                    title='แพ็คเกจทัวร์ยุโรป',
                    description='เที่ยวยุโรป 10 ประเทศ',
                    media_type='image',
                    file_path='/static/queue_media/europe_tour.jpg',
                    duration=15,
                    display_order=3,
                    is_active=True
                )
            ]
            
            db.session.add_all(sample_media)
            db.session.commit()
            print("✅ Added sample media entries!")
            
            return True
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    add_queue_media_table()
