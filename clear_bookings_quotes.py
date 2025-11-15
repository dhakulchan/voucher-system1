#!/usr/bin/env python3
"""
Safe deletion of all bookings and quotes data with proper foreign key handling
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from sqlalchemy import text

def clear_bookings_and_quotes():
    """Safely delete all bookings and quotes data"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("🚨 WARNING: This will delete ALL bookings and quotes data!")
            print("📋 Tables that will be cleared:")
            print("   - bookings")
            print("   - quotes")
            print("   - Related foreign key references")
            
            # Get counts before deletion
            booking_count = db.session.execute(text("SELECT COUNT(*) FROM bookings")).scalar()
            quote_count = db.session.execute(text("SELECT COUNT(*) FROM quotes")).scalar()
            
            print(f"\n📊 Current data:")
            print(f"   - Bookings: {booking_count}")
            print(f"   - Quotes: {quote_count}")
            
            confirm = input("\n⚠️  Are you sure you want to proceed? (type 'DELETE ALL' to confirm): ")
            
            if confirm != 'DELETE ALL':
                print("❌ Operation cancelled.")
                return False
            
            print("\n🔧 Starting deletion process...")
            
            # Disable foreign key checks
            print("1️⃣ Disabling foreign key constraints...")
            db.session.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            
            # Delete activity logs that reference users
            print("2️⃣ Clearing activity logs...")
            db.session.execute(text("DELETE FROM activity_logs"))
            
            # Delete quote related data
            print("3️⃣ Clearing quote line items...")
            db.session.execute(text("DELETE FROM quote_line_items"))
            
            # Delete invoice related data
            print("4️⃣ Clearing invoice data...")
            db.session.execute(text("DELETE FROM invoice_payments"))
            db.session.execute(text("DELETE FROM invoice_line_items"))
            db.session.execute(text("DELETE FROM invoices"))
            
            # Delete voucher images
            print("5️⃣ Clearing voucher images...")
            db.session.execute(text("DELETE FROM voucher_images"))
            
            # Delete queue sessions/tickets
            print("6️⃣ Clearing queue data...")
            db.session.execute(text("DELETE FROM queue_tickets"))
            db.session.execute(text("DELETE FROM queue_sessions"))
            
            # Delete quotes
            print("7️⃣ Clearing quotes...")
            db.session.execute(text("DELETE FROM quotes"))
            
            # Delete bookings
            print("8️⃣ Clearing bookings...")
            db.session.execute(text("DELETE FROM bookings"))
            
            # Reset auto increment
            print("9️⃣ Resetting auto increment counters...")
            db.session.execute(text("ALTER TABLE bookings AUTO_INCREMENT = 1"))
            db.session.execute(text("ALTER TABLE quotes AUTO_INCREMENT = 1"))
            db.session.execute(text("ALTER TABLE activity_logs AUTO_INCREMENT = 1"))
            
            # Re-enable foreign key checks
            print("🔟 Re-enabling foreign key constraints...")
            db.session.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
            
            # Commit all changes
            db.session.commit()
            
            print("\n✅ Data deletion completed successfully!")
            print("📊 All bookings and quotes have been removed")
            print("🔄 Auto-increment counters have been reset")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Error during deletion: {e}")
            db.session.rollback()
            
            # Make sure to re-enable foreign keys even on error
            try:
                db.session.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
                db.session.commit()
            except:
                pass
                
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = clear_bookings_and_quotes()
    if success:
        print("\n🎉 Database cleanup completed!")
        print("💡 You can now create fresh bookings and quotes")
    else:
        print("\n❌ Database cleanup failed!")
        sys.exit(1)