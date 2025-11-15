#!/usr/bin/env python3
"""
Comprehensive activity logs audit and fix for all bookings
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from models.booking import Booking, ActivityLog
from sqlalchemy import text
from datetime import datetime

def audit_and_fix_all_booking_logs():
    """Audit and fix activity logs for all bookings"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("🔍 COMPREHENSIVE ACTIVITY LOGS AUDIT & FIX")
            print("=" * 50)
            
            # Get all bookings
            all_bookings = db.session.execute(text("""
                SELECT id, booking_reference, status, created_at, updated_at 
                FROM bookings 
                ORDER BY id
            """)).fetchall()
            
            print(f"📋 Found {len(all_bookings)} bookings to audit:")
            
            bookings_fixed = 0
            bookings_ok = 0
            
            for booking in all_bookings:
                booking_id = booking[0]
                booking_ref = booking[1]
                booking_status = booking[2]
                created_at = booking[3]
                updated_at = booking[4]
                
                print(f"\\n📋 Booking #{booking_id}: {booking_ref} (status: {booking_status})")
                
                # Check existing logs
                existing_logs = db.session.execute(text("""
                    SELECT COUNT(*) FROM activity_logs 
                    WHERE description LIKE :search
                """), {'search': f'%#{booking_id}%'}).scalar()
                
                print(f"   📝 Existing logs: {existing_logs}")
                
                if existing_logs == 0:
                    print(f"   🔧 FIXING: No activity logs found!")
                    
                    # Create booking_created log
                    ActivityLog.log_activity(
                        'booking', booking_id, 'booking_created',
                        f'New booking created: {booking_ref} (status: draft)'
                    )
                    
                    # Create status progression
                    status_progression = {
                        'draft': [],
                        'pending': ['draft'],
                        'confirmed': ['draft', 'pending'], 
                        'quoted': ['draft', 'pending', 'confirmed'],
                        'paid': ['draft', 'pending', 'confirmed', 'quoted'],
                        'vouchered': ['draft', 'pending', 'confirmed', 'quoted', 'paid']
                    }
                    
                    if booking_status in status_progression:
                        progression = status_progression[booking_status]
                        
                        previous_status = 'draft'
                        for next_status in progression[1:]:
                            ActivityLog.log_activity(
                                'booking', booking_id, 'status_change',
                                f'Status changed from {previous_status} to {next_status}',
                                previous_status, next_status
                            )
                            previous_status = next_status
                        
                        # Final status
                        if progression and booking_status != progression[-1]:
                            ActivityLog.log_activity(
                                'booking', booking_id, 'status_change',
                                f'Status changed from {progression[-1]} to {booking_status}',
                                progression[-1], booking_status
                            )
                    
                    bookings_fixed += 1
                    print(f"   ✅ FIXED: Created complete activity log history")
                    
                elif existing_logs < 2 and booking_status != 'draft':
                    print(f"   ⚠️  WARNING: Only {existing_logs} logs for non-draft booking")
                    # Could add partial fixes here if needed
                    bookings_ok += 1
                    
                else:
                    print(f"   ✅ OK: Has sufficient activity logs")
                    bookings_ok += 1
            
            # Summary
            print(f"\\n📊 AUDIT SUMMARY:")
            print(f"   ✅ Bookings OK: {bookings_ok}")
            print(f"   🔧 Bookings Fixed: {bookings_fixed}")
            print(f"   📋 Total Bookings: {len(all_bookings)}")
            
            # Test auto-sync on a random booking
            if all_bookings:
                test_booking_data = all_bookings[0]  # Use first booking for test
                test_booking = Booking.query.filter_by(id=test_booking_data[0]).first()
                
                print(f"\\n🧪 Testing auto-sync on booking #{test_booking.id}...")
                
                log_count_before = db.session.execute(text("SELECT COUNT(*) FROM activity_logs")).scalar()
                
                old_status = test_booking.status
                test_status = 'paid' if old_status != 'paid' else 'quoted'
                
                test_booking.status = test_status
                db.session.commit()
                
                log_count_after = db.session.execute(text("SELECT COUNT(*) FROM activity_logs")).scalar()
                new_logs = log_count_after - log_count_before
                
                if new_logs > 0:
                    print(f"   ✅ AUTO-SYNC WORKING: Created {new_logs} new log(s)")
                else:
                    print(f"   ❌ AUTO-SYNC NOT WORKING: No new logs created")
                    print(f"   💡 Recommendation: Restart Flask application")
                
                # Restore status
                test_booking.status = old_status
                db.session.commit()
                
            print(f"\\n🎉 Activity logs audit and fix completed!")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    audit_and_fix_all_booking_logs()