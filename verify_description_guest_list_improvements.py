#!/usr/bin/env python3
"""
Verification script: Description moved above Guest List + Guest List styling improvements
"""

import re

def verify_section_order():
    """Verify that Description section appears before Guest List section"""
    try:
        with open('/Applications/python/voucher-ro_v1.0/templates/public/booking_view.html', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find positions of Description and Guest List sections
        description_match = re.search(r'<!-- Description -->', content)
        guest_list_match = re.search(r'<!-- Guest List -->', content)
        
        if not description_match:
            print("❌ Description section not found")
            return False
            
        if not guest_list_match:
            print("❌ Guest List section not found")
            return False
            
        description_pos = description_match.start()
        guest_list_pos = guest_list_match.start()
        
        if description_pos < guest_list_pos:
            print("✅ Description section successfully moved above Guest List section")
            print(f"   Description position: {description_pos}")
            print(f"   Guest List position: {guest_list_pos}")
            return True
        else:
            print("❌ Description section is still below Guest List section")
            print(f"   Description position: {description_pos}")
            print(f"   Guest List position: {guest_list_pos}")
            return False
            
    except Exception as e:
        print(f"❌ Error during verification: {e}")
        return False

def verify_guest_list_styling():
    """Verify Guest List styling improvements"""
    try:
        with open('/Applications/python/voucher-ro_v1.0/templates/public/booking_view.html', 'r', encoding='utf-8') as f:
            content = f.read()
        
        checks = []
        
        # Check for flexible height
        if 'max-height: fit-content' in content:
            print("✅ Guest List height set to fit-content")
            checks.append(True)
        else:
            print("❌ Guest List height not set to fit-content")
            checks.append(False)
            
        # Check for centering styles
        if 'display: flex' in content and 'align-items: center' in content and 'justify-content: center' in content:
            print("✅ Guest List container centered with flexbox")
            checks.append(True)
        else:
            print("❌ Guest List container centering missing")
            checks.append(False)
            
        # Check for text centering
        if 'text-align: center' in content:
            print("✅ Guest List text centered")
            checks.append(True)
        else:
            print("❌ Guest List text centering missing")
            checks.append(False)
            
        # Check for improved padding
        if 'padding: 1rem' in content:
            print("✅ Guest List padding improved to 1rem")
            checks.append(True)
        else:
            print("❌ Guest List padding not improved")
            checks.append(False)
            
        # Check for improved line height
        if 'line-height: 1.4' in content:
            print("✅ Guest List line-height improved to 1.4")
            checks.append(True)
        else:
            print("❌ Guest List line-height not improved")
            checks.append(False)
            
        # Check for improved font size
        if 'font-size: 0.95rem' in content:
            print("✅ Guest List font-size improved to 0.95rem")
            checks.append(True)
        else:
            print("❌ Guest List font-size not improved")
            checks.append(False)
            
        return all(checks)
        
    except Exception as e:
        print(f"❌ Error during styling verification: {e}")
        return False

def verify_template_integrity():
    """Verify template structure integrity"""
    try:
        with open('/Applications/python/voucher-ro_v1.0/templates/public/booking_view.html', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for essential structures
        required_elements = [
            '<i class="fas fa-info-circle me-2"></i>',
            '<i class="fas fa-list me-2"></i>',
            'booking.description',
            'booking.guest_list',
            '{{ booking.description | html_to_linebreaks }}',
            'No guest information available'
        ]
        
        for element in required_elements:
            if element in content:
                print(f"✅ Found: {element[:50]}...")
            else:
                print(f"❌ Missing: {element[:50]}...")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error during template integrity check: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Verifying Description and Guest List improvements...")
    print("=" * 60)
    
    print("\n1. Section Order Verification:")
    order_ok = verify_section_order()
    
    print("\n2. Guest List Styling Verification:")
    styling_ok = verify_guest_list_styling()
    
    print("\n3. Template Integrity Verification:")
    integrity_ok = verify_template_integrity()
    
    print("=" * 60)
    if order_ok and styling_ok and integrity_ok:
        print("🎉 All verifications passed!")
        print("✨ Description is now above Guest List")  
        print("✨ Guest List styling improved with centering and proper sizing")
    else:
        print("❌ Some verifications failed. Please check the changes.")
