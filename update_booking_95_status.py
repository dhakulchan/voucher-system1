#!/usr/bin/env python3
"""
Update booking ID 95 status from 'Completed' to 'Vouchered'
"""
import pymysql
from datetime import datetime

def update_booking_95_status():
    """Update booking 95 status to 'vouchered'"""
    connection = pymysql.connect(
        host='localhost',
        user='voucher_user',
        password='voucher_secure_2024',
        database='voucher_enhanced',
        charset='utf8mb4'
    )
    
    try:
        with connection.cursor() as cursor:
            # Get current status
            cursor.execute("SELECT id, booking_reference, status FROM bookings WHERE id = 95")
            result = cursor.fetchone()
            
            if not result:
                print("❌ Booking ID 95 not found!")
                return False
            
            booking_id, booking_ref, current_status = result
            print(f"📋 Found Booking #{booking_id}: {booking_ref}")
            print(f"   Current status: {current_status}")
            
            if current_status.lower() == 'vouchered':
                print("ℹ️  Status is already 'vouchered'")
                return True
            
            # Update status to 'vouchered'
            old_status = current_status
            new_status = 'vouchered'
            
            cursor.execute("""
                UPDATE bookings 
                SET status = %s, 
                    vouchered_at = NOW(),
                    updated_at = NOW()
                WHERE id = %s
            """, (new_status, booking_id))
            
            connection.commit()
            print(f"✅ Status updated: {old_status} → {new_status}")
            
            # Create activity log entry
            cursor.execute("""
                INSERT INTO activity_logs (booking_id, action, description, created_at) 
                VALUES (%s, %s, %s, %s)
            """, (
                booking_id,
                'status_updated',
                f'Booking status changed from {old_status} to {new_status}',
                datetime.now()
            ))
            
            connection.commit()
            print("✅ Activity log created")
            
            # Verify the update
            cursor.execute("SELECT status, vouchered_at FROM bookings WHERE id = 95")
            result = cursor.fetchone()
            new_status_verify, vouchered_at = result
            
            print(f"\n📝 Verification:")
            print(f"   New status: {new_status_verify}")
            print(f"   Vouchered at: {vouchered_at}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        connection.close()

if __name__ == '__main__':
    import sys
    success = update_booking_95_status()
    sys.exit(0 if success else 1)
