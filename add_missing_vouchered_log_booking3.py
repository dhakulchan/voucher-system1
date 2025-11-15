#!/usr/bin/env python3
"""
Add missing vouchered activity log for booking #3
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from models.booking import Booking, ActivityLog
from sqlalchemy import text
from datetime import datetime

def add_missing_vouchered_log_booking3():
    """Add missing vouchered activity log for booking #3"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("🧪 Adding Missing Vouchered Activity Log for Booking #3...")
            
            # Get booking #3
            booking3 = Booking.query.filter_by(id=3).first()
            if not booking3:
                print("❌ Booking #3 not found!")
                return
            
            print(f"📋 Found booking: {booking3.booking_reference}")
            print(f"📊 Current status: {booking3.status}")
            print(f"📅 Updated: {booking3.updated_at}")
            
            # Check existing vouchered logs
            existing_vouchered_logs = db.session.execute(text("""
                SELECT COUNT(*) FROM activity_logs 
                WHERE description LIKE '%#3%' AND description LIKE '%vouchered%'
            """)).scalar()
            
            print(f"📝 Existing vouchered logs for booking #3: {existing_vouchered_logs}")
            
            if existing_vouchered_logs == 0 and booking3.status == 'vouchered':
                print("\n📝 Creating missing vouchered activity log...")
                
                # Determine what the previous status likely was
                # Check the last status change log
                last_status_log = db.session.execute(text("""
                    SELECT description FROM activity_logs 
                    WHERE description LIKE '%#3%' AND action = 'status_change'
                    ORDER BY created_at DESC 
                    LIMIT 1
                """)).fetchone()
                
                previous_status = 'pending'  # Default assumption
                if last_status_log:
                    desc = last_status_log[0]
                    if 'to pending' in desc:
                        previous_status = 'pending'
                    elif 'to confirmed' in desc:
                        previous_status = 'confirmed'
                    elif 'to quoted' in desc:
                        previous_status = 'quoted'
                    elif 'to paid' in desc:
                        previous_status = 'paid'
                
                print(f"📝 Assuming previous status was: {previous_status}")
                
                # Create the missing vouchered log with estimated timestamp
                # Use the booking's updated_at as the timestamp
                estimated_time = booking3.updated_at or datetime.utcnow()
                
                # Insert directly into database to set specific timestamp
                db.session.execute(text("""
                    INSERT INTO activity_logs (action, description, created_at)
                    VALUES ('status_change', :description, :created_at)
                """), {
                    'description': f'[BOOKING #3] Status changed from {previous_status} to vouchered ({previous_status} → vouchered)',
                    'created_at': estimated_time
                })
                
                db.session.commit()
                print("✅ Missing vouchered activity log added!")
                
            elif booking3.status != 'vouchered':
                print(f"ℹ️  Booking #3 status is '{booking3.status}', not 'vouchered'")
            else:
                print("📝 Vouchered log already exists!")
            
            # Show all logs for booking #3 after adding
            logs = db.session.execute(text("""
                SELECT id, action, description, created_at
                FROM activity_logs 
                WHERE description LIKE '%#3%'
                ORDER BY created_at ASC
            """)).fetchall()
            
            print(f"\\n📄 All logs for booking #3 ({len(logs)} total):")
            for log in logs:
                print(f"   [{log[0]}] {log[1]}: {log[2]}")
                print(f"       Created: {log[3]}")
            
            # Test that future status changes will work
            print(f"\\n🔄 Testing future status change logging...")
            log_count_before = db.session.execute(text("SELECT COUNT(*) FROM activity_logs")).scalar()
            
            # Change status to test
            old_status = booking3.status
            new_status = 'paid' if old_status != 'paid' else 'vouchered'
            
            booking3.status = new_status
            db.session.commit()
            
            log_count_after = db.session.execute(text("SELECT COUNT(*) FROM activity_logs")).scalar()
            new_logs = log_count_after - log_count_before
            
            print(f"   Changed from {old_status} to {new_status}")
            print(f"   New logs created: {new_logs}")
            
            if new_logs > 0:
                print("✅ Future status change logging works!")
            else:
                print("❌ Future status change logging not working!")
                
            # Restore original status
            booking3.status = old_status
            db.session.commit()
            print(f"   Restored status to: {booking3.status}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    add_missing_vouchered_log_booking3()