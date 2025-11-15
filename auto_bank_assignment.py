#!/usr/bin/env python3
"""
Auto bank assignment system for new bookings
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from sqlalchemy import text
import random

def setup_auto_bank_assignment():
    """Setup automatic bank assignment for future bookings"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("🏦 AUTO BANK ASSIGNMENT SETUP")
            print("=" * 35)
            
            # Create or update a settings table for bank rotation
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS app_settings (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    setting_key VARCHAR(100) UNIQUE NOT NULL,
                    setting_value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """))
            
            # Initialize bank rotation settings
            thai_banks = [
                "Bangkok Bank (BBL)",
                "Kasikorn Bank (KBANK)", 
                "Siam Commercial Bank (SCB)",
                "Krung Thai Bank (KTB)",
                "TMB Bank (TMB)",
                "Bank of Ayudhya (BAY)"
            ]
            
            # Set default bank list
            db.session.execute(text("""
                INSERT INTO app_settings (setting_key, setting_value, updated_at)
                VALUES ('default_banks', :banks, CURRENT_TIMESTAMP)
                ON DUPLICATE KEY UPDATE 
                setting_value = VALUES(setting_value),
                updated_at = CURRENT_TIMESTAMP
            """), {'banks': ','.join(thai_banks)})
            
            # Set current bank index for rotation
            db.session.execute(text("""
                INSERT IGNORE INTO app_settings (setting_key, setting_value)
                VALUES ('current_bank_index', '0')
            """))
            
            db.session.commit()
            
            print("✅ Bank assignment system initialized")
            print(f"📋 Available banks: {len(thai_banks)} banks")
            for i, bank in enumerate(thai_banks, 1):
                print(f"   {i}. {bank}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error setting up auto assignment: {e}")
            import traceback
            traceback.print_exc()
            return False

def get_next_bank():
    """Get next bank in rotation"""
    
    app = create_app()
    
    with app.app_context():
        try:
            # Get current settings
            banks_result = db.session.execute(text("""
                SELECT setting_value FROM app_settings WHERE setting_key = 'default_banks'
            """)).fetchone()
            
            index_result = db.session.execute(text("""
                SELECT setting_value FROM app_settings WHERE setting_key = 'current_bank_index'
            """)).fetchone()
            
            if not banks_result or not index_result:
                # Fallback to random assignment
                fallback_banks = ["Bangkok Bank (BBL)", "Kasikorn Bank (KBANK)", "Siam Commercial Bank (SCB)"]
                return random.choice(fallback_banks)
            
            banks = banks_result[0].split(',')
            current_index = int(index_result[0])
            
            # Get current bank
            selected_bank = banks[current_index % len(banks)]
            
            # Update index for next time
            next_index = (current_index + 1) % len(banks)
            db.session.execute(text("""
                UPDATE app_settings 
                SET setting_value = :next_index, updated_at = CURRENT_TIMESTAMP
                WHERE setting_key = 'current_bank_index'
            """), {'next_index': str(next_index)})
            
            db.session.commit()
            
            return selected_bank
            
        except Exception as e:
            print(f"❌ Error getting next bank: {e}")
            # Fallback
            fallback_banks = ["Bangkok Bank (BBL)", "Kasikorn Bank (KBANK)", "Siam Commercial Bank (SCB)"]
            return random.choice(fallback_banks)

def test_bank_rotation():
    """Test the bank rotation system"""
    
    print("🧪 TESTING BANK ROTATION")
    print("=" * 25)
    
    print("Next 10 banks in rotation:")
    for i in range(10):
        bank = get_next_bank()
        print(f"   {i+1}. {bank}")

def apply_auto_assignment_to_existing():
    """Apply automatic bank assignment to existing bookings without banks"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("🔄 APPLYING AUTO ASSIGNMENT TO EXISTING BOOKINGS")
            print("=" * 50)
            
            # Find bookings without bank assignments
            bookings = db.session.execute(text("""
                SELECT id, booking_reference, bank_received
                FROM bookings 
                WHERE bank_received IS NULL OR bank_received = '' OR bank_received = 'Bank Transfer Received'
                ORDER BY id
            """)).fetchall()
            
            if not bookings:
                print("✅ All bookings already have bank assignments")
                return
            
            print(f"📋 Found {len(bookings)} bookings without specific banks:")
            
            updated_count = 0
            for booking in bookings:
                booking_id, booking_ref, current_bank = booking
                
                # Get next bank in rotation
                new_bank = get_next_bank()
                
                # Update booking
                db.session.execute(text("""
                    UPDATE bookings 
                    SET bank_received = :bank_name
                    WHERE id = :booking_id
                """), {
                    'bank_name': new_bank,
                    'booking_id': booking_id
                })
                
                print(f"   ✅ {booking_ref}: {new_bank}")
                updated_count += 1
            
            db.session.commit()
            
            print(f"\\n🎉 Updated {updated_count} bookings with automatic bank assignments")
            
        except Exception as e:
            print(f"❌ Error applying auto assignment: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("🏦 Auto Bank Assignment System")
    print("=" * 35)
    print("1. Setup auto assignment system")
    print("2. Test bank rotation")
    print("3. Apply to existing bookings")
    print("4. Get next bank")
    
    try:
        choice = input("\\nEnter choice (1-4): ")
        
        if choice == "1":
            setup_auto_bank_assignment()
        elif choice == "2":
            test_bank_rotation()
        elif choice == "3":
            apply_auto_assignment_to_existing()
        elif choice == "4":
            next_bank = get_next_bank()
            print(f"🏦 Next bank: {next_bank}")
        else:
            print("❌ Invalid choice")
            
    except KeyboardInterrupt:
        print("\\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")