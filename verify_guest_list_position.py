#!/usr/bin/env python3
"""
Verification script: Guest List moved above Description section
"""

import re

def verify_guest_list_position():
    """Verify that Guest List section appears before Description section"""
    try:
        with open('/Applications/python/voucher-ro_v1.0/templates/public/booking_view.html', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find positions of Guest List and Description sections
        guest_list_match = re.search(r'<!-- Guest List -->', content)
        description_match = re.search(r'<!-- Description -->', content)
        
        if not guest_list_match:
            print("❌ Guest List section not found")
            return False
            
        if not description_match:
            print("❌ Description section not found")
            return False
            
        guest_list_pos = guest_list_match.start()
        description_pos = description_match.start()
        
        if guest_list_pos < description_pos:
            print("✅ Guest List section successfully moved above Description section")
            print(f"   Guest List position: {guest_list_pos}")
            print(f"   Description position: {description_pos}")
            return True
        else:
            print("❌ Guest List section is still below Description section")
            print(f"   Guest List position: {guest_list_pos}")
            print(f"   Description position: {description_pos}")
            return False
            
    except Exception as e:
        print(f"❌ Error during verification: {e}")
        return False

def verify_template_structure():
    """Verify template structure after the change"""
    try:
        with open('/Applications/python/voucher-ro_v1.0/templates/public/booking_view.html', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for Guest List section structure
        guest_list_header = '<i class="fas fa-list me-2"></i>\n                            Guest List'
        if guest_list_header in content:
            print("✅ Guest List header structure intact")
        else:
            print("❌ Guest List header structure missing")
            return False
            
        # Check for Description section structure  
        description_header = '<i class="fas fa-info-circle me-2"></i>\n                            Description'
        if description_header in content:
            print("✅ Description header structure intact")
        else:
            print("❌ Description header structure missing")
            return False
            
        # Check for optimized Guest List styling
        guest_list_style = 'max-height: 150px; overflow-y: auto'
        if guest_list_style in content:
            print("✅ Guest List optimized styling preserved")
        else:
            print("❌ Guest List optimized styling missing")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Error during template structure verification: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Verifying Guest List position change...")
    print("=" * 50)
    
    position_ok = verify_guest_list_position()
    structure_ok = verify_template_structure()
    
    print("=" * 50)
    if position_ok and structure_ok:
        print("🎉 All verifications passed! Guest List now appears above Description section.")
    else:
        print("❌ Verification failed. Please check the changes.")
