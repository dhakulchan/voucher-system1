#!/usr/bin/env python3
"""
Database Cleanup - Keep only 20 booking records
"""

import sqlite3
import os
from datetime import datetime

def cleanup_database():
    """Keep only 20 most recent bookings and related data"""
    
    db_path = '/Applications/python/voucher-ro_v1.0/app.db'
    
    if not os.path.exists(db_path):
        print("❌ Database not found!")
        return
    
    # Backup database first
    backup_path = f'/Applications/python/voucher-ro_v1.0/app_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
    os.system(f'cp "{db_path}" "{backup_path}"')
    print(f"💾 Database backed up to: {backup_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get current counts
        cursor.execute("SELECT COUNT(*) FROM bookings")
        total_bookings = cursor.fetchone()[0]
        print(f"📊 Current bookings: {total_bookings}")
        
        # Check voucher_images
        try:
            cursor.execute("SELECT COUNT(*) FROM voucher_images")
            total_voucher_images = cursor.fetchone()[0]
            print(f"📊 Current voucher images: {total_voucher_images}")
        except:
            total_voucher_images = 0
            print("📊 No voucher_images table found")
        
        if total_bookings <= 20:
            print("✅ Already have 20 or fewer bookings. No cleanup needed.")
            conn.close()
            return
        
        # Get top 20 booking IDs to keep (most recent)
        cursor.execute("""
            SELECT id FROM bookings 
            ORDER BY id DESC 
            LIMIT 20
        """)
        keep_booking_ids = [row[0] for row in cursor.fetchall()]
        keep_ids_str = ','.join(map(str, keep_booking_ids))
        
        print(f"🔒 Keeping booking IDs: {keep_ids_str}")
        
        # Delete old voucher_images first (foreign key constraint)
        if total_voucher_images > 0:
            cursor.execute(f"""
                DELETE FROM voucher_images 
                WHERE booking_id NOT IN ({keep_ids_str})
            """)
            deleted_images = cursor.rowcount
            print(f"🗑️  Deleted {deleted_images} voucher images")
        
        # Delete old bookings
        cursor.execute(f"""
            DELETE FROM bookings 
            WHERE id NOT IN ({keep_ids_str})
        """)
        deleted_bookings = cursor.rowcount
        print(f"🗑️  Deleted {deleted_bookings} bookings")
        
        # Commit changes
        conn.commit()
        
        # Verify final counts
        cursor.execute("SELECT COUNT(*) FROM bookings")
        final_bookings = cursor.fetchone()[0]
        
        try:
            cursor.execute("SELECT COUNT(*) FROM voucher_images")
            final_images = cursor.fetchone()[0]
        except:
            final_images = 0
        
        print(f"\n✅ Cleanup completed!")
        print(f"📊 Final counts:")
        print(f"   📋 Bookings: {final_bookings}")
        print(f"   🖼️  Voucher Images: {final_images}")
        
        # VACUUM to reclaim space
        cursor.execute("VACUUM")
        print(f"🧹 Database optimized")
        
        # Show remaining bookings
        cursor.execute("SELECT id, booking_reference, customer_name FROM bookings ORDER BY id DESC")
        remaining = cursor.fetchall()
        print(f"\n📋 Remaining bookings:")
        for booking in remaining:
            print(f"   🆔 {booking[0]}: {booking[1]} - {booking[2]}")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        conn.rollback()
        
    finally:
        conn.close()

if __name__ == "__main__":
    print("🗑️  Starting Database Cleanup...")
    print("🎯 Target: Keep only 20 most recent bookings")
    print("=" * 50)
    cleanup_database()
    print("=" * 50)
    print("✅ Database cleanup completed!")
