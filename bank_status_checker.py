#!/usr/bin/env python3
"""
Simple bank status checker and summary
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from sqlalchemy import text

def check_current_status():
    """Check current bank assignments"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("🏦 CURRENT BANK ASSIGNMENTS STATUS")
            print("=" * 40)
            
            # Check current bookings
            bookings = db.session.execute(text("""
                SELECT id, booking_reference, status, bank_received, total_amount,
                       created_at, traveling_period_start
                FROM bookings 
                ORDER BY id
            """)).fetchall()
            
            print(f"📊 Total bookings: {len(bookings)}")
            print("=" * 40)
            
            bank_counts = {}
            for booking in bookings:
                booking_id, ref, status, bank, amount, created, travel = booking
                bank_name = bank if bank else "No bank assigned"
                
                if bank_name not in bank_counts:
                    bank_counts[bank_name] = 0
                bank_counts[bank_name] += 1
                
                status_emoji = {
                    'quoted': '📋',
                    'paid': '💰', 
                    'vouchered': '🎫',
                    'completed': '✅'
                }.get(status, '❓')
                
                print(f"   {status_emoji} #{booking_id} ({ref})")
                print(f"      💵 Amount: {amount:,.0f} THB")
                print(f"      🏦 Bank: {bank_name}")
                print(f"      📅 Status: {status}")
                print(f"      🗓️ Travel: {travel}")
                print()
            
            print("🏦 BANK DISTRIBUTION SUMMARY")
            print("=" * 30)
            for bank, count in sorted(bank_counts.items()):
                percentage = (count / len(bookings)) * 100
                print(f"   📊 {bank}: {count} bookings ({percentage:.1f}%)")
            
            # Check settings table
            print("\\n⚙️ SYSTEM SETTINGS")
            print("=" * 20)
            
            try:
                settings = db.session.execute(text("""
                    SELECT setting_key, setting_value 
                    FROM app_settings 
                    ORDER BY setting_key
                """)).fetchall()
                
                for setting in settings:
                    key, value = setting
                    if key == 'default_banks':
                        banks = value.split(',')
                        print(f"   🏦 Default Banks ({len(banks)} banks):")
                        for i, bank in enumerate(banks, 1):
                            print(f"      {i}. {bank}")
                    else:
                        print(f"   ⚙️ {key}: {value}")
                        
            except Exception as e:
                print(f"   ⚠️ Settings table not accessible: {e}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

def verify_bank_updates():
    """Verify that bank updates are working"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("\\n🔍 VERIFYING BANK UPDATE SUCCESS")
            print("=" * 35)
            
            # Check for any bookings with old bank names
            old_banks = db.session.execute(text("""
                SELECT id, booking_reference, bank_received
                FROM bookings 
                WHERE bank_received LIKE '%Bank Transfer Received%'
                   OR bank_received IS NULL
                   OR bank_received = ''
                ORDER BY id
            """)).fetchall()
            
            if old_banks:
                print(f"⚠️ Found {len(old_banks)} bookings with generic/missing bank names:")
                for booking in old_banks:
                    print(f"   📋 #{booking[0]} ({booking[1]}): {booking[2] or 'NULL'}")
                print("\\n💡 Run: python update_bank_names.py to fix these")
            else:
                print("✅ All bookings have specific bank assignments!")
            
            # Check for proper Thai bank names
            thai_banks = db.session.execute(text("""
                SELECT DISTINCT bank_received, COUNT(*) as count
                FROM bookings 
                WHERE bank_received IS NOT NULL 
                GROUP BY bank_received
                ORDER BY count DESC
            """)).fetchall()
            
            print("\\n🇹🇭 THAI BANK NAMES IN USE:")
            print("=" * 25)
            for bank, count in thai_banks:
                print(f"   🏦 {bank}: {count} bookings")
            
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_current_status()
    verify_bank_updates()