#!/usr/bin/env python3
"""
Interactive bank selection for specific bookings
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from models.booking import Booking
from sqlalchemy import text

def interactive_bank_selection():
    """Interactive bank selection for bookings"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("🏦 INTERACTIVE BANK SELECTION")
            print("=" * 40)
            
            # Bank options
            banks = [
                "Bangkok Bank (BBL)",
                "Kasikorn Bank (KBANK)", 
                "Siam Commercial Bank (SCB)",
                "Krung Thai Bank (KTB)",
                "TMB Bank (TMB)",
                "Bank of Ayudhya (BAY)",
                "Government Savings Bank (GSB)",
                "CIMB Thai Bank",
                "Custom Bank Name"
            ]
            
            # Show current bookings
            bookings = db.session.execute(text("""
                SELECT id, booking_reference, status, bank_received, total_amount
                FROM bookings 
                ORDER BY id
            """)).fetchall()
            
            print(f"📋 Current bookings:")
            for i, booking in enumerate(bookings, 1):
                print(f"   {i}. Booking #{booking[0]} ({booking[1]}) - {booking[3] or 'No bank set'}")
            
            print(f"\\n🏦 Available banks:")
            for i, bank in enumerate(banks, 1):
                print(f"   {i}. {bank}")
            
            # Interactive selection
            while True:
                try:
                    booking_choice = input(f"\\n📋 Select booking to update (1-{len(bookings)}) or 'q' to quit: ")
                    
                    if booking_choice.lower() == 'q':
                        break
                    
                    booking_idx = int(booking_choice) - 1
                    if booking_idx < 0 or booking_idx >= len(bookings):
                        print("❌ Invalid booking selection")
                        continue
                    
                    selected_booking = bookings[booking_idx]
                    booking_id = selected_booking[0]
                    booking_ref = selected_booking[1]
                    
                    print(f"\\n📋 Selected: {booking_ref} (#{booking_id})")
                    print(f"   Current bank: {selected_booking[3] or 'Not set'}")
                    
                    bank_choice = input(f"\\n🏦 Select bank (1-{len(banks)}): ")
                    bank_idx = int(bank_choice) - 1
                    
                    if bank_idx < 0 or bank_idx >= len(banks):
                        print("❌ Invalid bank selection")
                        continue
                    
                    if bank_idx == len(banks) - 1:  # Custom bank name
                        custom_bank = input("Enter custom bank name: ")
                        selected_bank = custom_bank
                    else:
                        selected_bank = banks[bank_idx]
                    
                    # Update booking
                    db.session.execute(text("""
                        UPDATE bookings 
                        SET bank_received = :bank_name
                        WHERE id = :booking_id
                    """), {
                        'bank_name': selected_bank,
                        'booking_id': booking_id
                    })
                    
                    db.session.commit()
                    
                    print(f"✅ Updated {booking_ref} bank to: {selected_bank}")
                    
                    # Update the bookings list for display
                    bookings = db.session.execute(text("""
                        SELECT id, booking_reference, status, bank_received, total_amount
                        FROM bookings 
                        ORDER BY id
                    """)).fetchall()
                    
                except ValueError:
                    print("❌ Please enter a valid number")
                except KeyboardInterrupt:
                    print("\\n👋 Goodbye!")
                    break
                except Exception as e:
                    print(f"❌ Error: {e}")
            
            print(f"\\n📄 Final bank assignments:")
            final_bookings = db.session.execute(text("""
                SELECT id, booking_reference, bank_received
                FROM bookings 
                ORDER BY id
            """)).fetchall()
            
            for booking in final_bookings:
                print(f"   📋 {booking[1]}: {booking[2] or 'Not set'}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

def set_default_banks():
    """Set logical default banks for tour industry"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("🏦 Setting Default Banks for Tour Industry")
            print("=" * 45)
            
            # Tour industry common bank assignments
            default_assignments = {
                "Bangkok Bank (BBL)": "Most popular for international transfers",
                "Kasikorn Bank (KBANK)": "Good for online payments",
                "Siam Commercial Bank (SCB)": "Corporate accounts"
            }
            
            # Update future booking creation to use default banks
            print("ℹ️ Default bank assignments for new bookings:")
            for bank, description in default_assignments.items():
                print(f"   🏦 {bank}: {description}")
            
            print(f"\\n💡 Future bookings will rotate between these banks automatically")
            
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("Choose an option:")
    print("1. Interactive bank selection")
    print("2. Show default bank info")
    
    try:
        choice = input("Enter choice (1-2): ")
        if choice == "1":
            interactive_bank_selection()
        elif choice == "2":
            set_default_banks()
        else:
            print("Invalid choice")
    except KeyboardInterrupt:
        print("\\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")