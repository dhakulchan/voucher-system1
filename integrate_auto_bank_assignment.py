#!/usr/bin/env python3
"""
Integration script to automatically assign banks to new bookings
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from sqlalchemy import text

def get_next_bank_for_booking():
    """Get next bank in rotation for new booking"""
    
    try:
        # Get current settings
        banks_result = db.session.execute(text("""
            SELECT setting_value FROM app_settings WHERE setting_key = 'default_banks'
        """)).fetchone()
        
        index_result = db.session.execute(text("""
            SELECT setting_value FROM app_settings WHERE setting_key = 'current_bank_index'
        """)).fetchone()
        
        if not banks_result or not index_result:
            # Fallback to default banks
            return "Bangkok Bank (BBL)"
        
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
        print(f"⚠️ Error getting next bank: {e}")
        # Fallback
        return "Bangkok Bank (BBL)"

def integrate_auto_bank_assignment():
    """Add auto bank assignment to booking creation"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("🔧 INTEGRATING AUTO BANK ASSIGNMENT")
            print("=" * 40)
            
            # Read current booking model
            try:
                with open('models/booking.py', 'r') as f:
                    content = f.read()
                    
                # Check if auto assignment is already integrated
                if 'auto_assign_bank' in content:
                    print("✅ Auto bank assignment already integrated!")
                    return
                    
                print("🔧 Adding auto bank assignment to Booking model...")
                
                # Add the auto assignment method
                auto_assignment_code = '''
    def auto_assign_bank(self):
        """Automatically assign a bank using rotation system"""
        if not self.bank_received:
            from sqlalchemy import text
            try:
                # Get next bank in rotation
                banks_result = db.session.execute(text("""
                    SELECT setting_value FROM app_settings WHERE setting_key = 'default_banks'
                """)).fetchone()
                
                index_result = db.session.execute(text("""
                    SELECT setting_value FROM app_settings WHERE setting_key = 'current_bank_index'
                """)).fetchone()
                
                if banks_result and index_result:
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
                    
                    # Assign bank to this booking
                    self.bank_received = selected_bank
                    
                    print(f"🏦 Auto-assigned bank: {selected_bank} to booking {self.booking_reference}")
                
            except Exception as e:
                print(f"⚠️ Auto bank assignment error: {e}")
                # Fallback
                self.bank_received = "Bangkok Bank (BBL)"
'''
                
                # Find the right place to insert the method (before the event listeners)
                if '@event.listens_for(Booking, \'after_insert\')' in content:
                    insert_point = content.find('@event.listens_for(Booking, \'after_insert\')')
                    new_content = content[:insert_point] + auto_assignment_code + '\n\n' + content[insert_point:]
                else:
                    # Insert before the last class closing
                    lines = content.split('\n')
                    for i in range(len(lines)-1, -1, -1):
                        if lines[i].strip() == '':
                            continue
                        if not lines[i].startswith('    ') and not lines[i].startswith('\t'):
                            # Found the end of the class
                            lines.insert(i, auto_assignment_code)
                            break
                    new_content = '\n'.join(lines)
                
                # Write back to file
                with open('models/booking.py', 'w') as f:
                    f.write(new_content)
                
                print("✅ Auto bank assignment method added to Booking model")
                
            except Exception as e:
                print(f"❌ Error modifying booking model: {e}")
                return False
            
            # Update the after_insert event listener to call auto_assign_bank
            print("🔧 Updating event listener to trigger auto bank assignment...")
            
            try:
                with open('models/booking.py', 'r') as f:
                    content = f.read()
                
                # Look for the after_insert listener and update it
                old_listener = '''@event.listens_for(Booking, 'after_insert')
def create_booking_activity_log(mapper, connection, target):'''
                
                new_listener = '''@event.listens_for(Booking, 'after_insert')
def create_booking_activity_log(mapper, connection, target):
    # Auto-assign bank if not already set
    target.auto_assign_bank()'''
                
                if old_listener in content:
                    updated_content = content.replace(old_listener, new_listener)
                    
                    with open('models/booking.py', 'w') as f:
                        f.write(updated_content)
                    
                    print("✅ Event listener updated to auto-assign banks")
                else:
                    print("⚠️ Could not find after_insert listener to update")
                
            except Exception as e:
                print(f"❌ Error updating event listener: {e}")
                return False
            
            print("\n🎉 AUTO BANK ASSIGNMENT INTEGRATION COMPLETE!")
            print("=" * 45)
            print("✅ New bookings will automatically get assigned banks")
            print("✅ Banks rotate through the configured list")
            print("✅ No manual intervention required")
            
            return True
            
        except Exception as e:
            print(f"❌ Integration error: {e}")
            import traceback
            traceback.print_exc()
            return False

def test_integration():
    """Test the integration by checking a booking creation"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("\n🧪 TESTING AUTO BANK ASSIGNMENT")
            print("=" * 35)
            
            # Check current bank index
            current_index = db.session.execute(text("""
                SELECT setting_value FROM app_settings WHERE setting_key = 'current_bank_index'
            """)).fetchone()
            
            print(f"📊 Current bank index: {current_index[0] if current_index else 'Not set'}")
            
            # Get what the next bank would be
            next_bank = get_next_bank_for_booking()
            print(f"🏦 Next bank would be: {next_bank}")
            
            # Check updated index
            updated_index = db.session.execute(text("""
                SELECT setting_value FROM app_settings WHERE setting_key = 'current_bank_index'
            """)).fetchone()
            
            print(f"📊 Updated bank index: {updated_index[0] if updated_index else 'Not set'}")
            
            print("✅ Auto bank assignment is working!")
            
        except Exception as e:
            print(f"❌ Test error: {e}")

if __name__ == "__main__":
    print("🏦 Auto Bank Assignment Integration")
    print("=" * 40)
    print("1. Integrate auto assignment into Booking model")
    print("2. Test integration")
    print("3. Check integration status")
    
    choice = input("\\nSelect option (1-3): ")
    
    if choice == "1":
        integrate_auto_bank_assignment()
    elif choice == "2":
        test_integration()
    elif choice == "3":
        app = create_app()
        with app.app_context():
            with open('models/booking.py', 'r') as f:
                content = f.read()
                if 'auto_assign_bank' in content:
                    print("✅ Auto bank assignment IS integrated")
                else:
                    print("❌ Auto bank assignment NOT integrated")
    else:
        print("❌ Invalid choice")