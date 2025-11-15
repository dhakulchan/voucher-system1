#!/usr/bin/env python3
"""
Create activity log for existing booking #3
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from models.booking import Booking, ActivityLog
from sqlalchemy import text
from utils.datetime_utils import naive_utc_now

def create_activity_log_for_booking3():
    """Create activity log for existing booking #3"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("🧪 Creating Activity Log for Existing Booking #3...")
            
            # Get booking #3
            booking3 = Booking.query.filter_by(id=3).first()
            if not booking3:
                print("❌ Booking #3 not found!")
                return
            
            print(f"📋 Found booking: {booking3.booking_reference}")
            print(f"📊 Current status: {booking3.status}")
            print(f"📅 Created: {booking3.created_at}")
            
            # Check current logs for booking #3
            existing_logs = db.session.execute(text("""
                SELECT COUNT(*) FROM activity_logs 
                WHERE description LIKE :search
            """), {'search': f'%#3%'}).scalar()
            
            print(f"📝 Existing logs for booking #3: {existing_logs}")
            
            if existing_logs == 0:
                print("\n📝 Creating initial activity log for booking #3...")
                
                # Create a "booking_created" log for the existing booking
                ActivityLog.log_activity(
                    'booking', 3, 'booking_created',
                    f'New booking created: {booking3.booking_reference} (status: {booking3.status})'
                )
                
                print("✅ Initial booking creation log added!")
                
                # If status is not draft, also add status change log
                if booking3.status != 'draft':
                    print(f"📝 Adding status progression log (draft → {booking3.status})...")
                    ActivityLog.log_activity(
                        'booking', 3, 'status_change',
                        f'Status changed from draft to {booking3.status}',
                        'draft', booking3.status
                    )
                    print("✅ Status progression log added!")
                
            else:
                print("📝 Booking #3 already has activity logs!")
            
            # Show all logs for booking #3
            logs = db.session.execute(text("""
                SELECT id, action, description, created_at
                FROM activity_logs 
                WHERE description LIKE :search
                ORDER BY created_at ASC
            """), {'search': f'%#3%'}).fetchall()
            
            print(f"\\n📄 All logs for booking #3 ({len(logs)} total):")
            for log in logs:
                print(f"   [{log[0]}] {log[1]}: {log[2]}")
                print(f"       Created: {log[3]}")
            
            # Test a new status change on booking #3
            print(f"\\n🔄 Testing new status change on booking #3...")
            log_count_before = db.session.execute(text("SELECT COUNT(*) FROM activity_logs")).scalar()
            
            old_status = booking3.status
            new_status = 'pending' if old_status != 'pending' else 'confirmed'
            
            booking3.status = new_status
            db.session.commit()
            
            log_count_after = db.session.execute(text("SELECT COUNT(*) FROM activity_logs")).scalar()
            new_logs = log_count_after - log_count_before
            
            print(f"   Changed from {old_status} to {new_status}")
            print(f"   New logs created: {new_logs}")
            
            if new_logs > 0:
                print("✅ Status change logging works for booking #3!")
            else:
                print("❌ Status change logging not working!")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    create_activity_log_for_booking3()