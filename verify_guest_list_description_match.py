#!/usr/bin/env python3
"""
Verification script: Guest List styling matches Description styling
"""

import re

def verify_matching_styles():
    """Verify that Guest List and Description have matching styling"""
    try:
        with open('/Applications/python/voucher-ro_v1.0/templates/public/booking_view.html', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract Description section styling
        description_match = re.search(
            r'<!-- Description -->.*?<div class="card-body">(.*?)</div>\s*</div>\s*{% endif %}',
            content, re.DOTALL
        )
        
        # Extract Guest List section styling  
        guest_list_match = re.search(
            r'<!-- Guest List -->.*?<div class="card-body">(.*?)</div>\s*</div>\s*{% endif %}',
            content, re.DOTALL
        )
        
        if not description_match:
            print("❌ Description section structure not found")
            return False
            
        if not guest_list_match:
            print("❌ Guest List section structure not found")
            return False
            
        description_body = description_match.group(1).strip()
        guest_list_body = guest_list_match.group(1).strip()
        
        print("📋 Description card-body structure:")
        print(f"   Starts with: {description_body[:100]}...")
        
        print("📋 Guest List card-body structure:")
        print(f"   Starts with: {guest_list_body[:100]}...")
        
        # Check for matching card-body (no custom styles)
        desc_card_body_simple = '<div class="card-body">' in content and 'style=' not in description_body.split('>', 1)[0]
        guest_card_body_simple = '<div class="card-body">' in content and 'style=' not in guest_list_body.split('>', 1)[0]
        
        if desc_card_body_simple and guest_card_body_simple:
            print("✅ Both sections use simple card-body (no custom styles)")
        else:
            print("❌ Card-body styles don't match")
            return False
            
        # Check for matching inner div styling
        if 'white-space: pre-line; line-height: 1.6;' in description_body and 'white-space: pre-line; line-height: 1.6;' in guest_list_body:
            print("✅ Both sections use identical inner div styling")
            print("   - white-space: pre-line")
            print("   - line-height: 1.6")
        else:
            print("❌ Inner div styles don't match")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Error during verification: {e}")
        return False

def verify_styling_consistency():
    """Verify styling consistency between sections"""
    try:
        with open('/Applications/python/voucher-ro_v1.0/templates/public/booking_view.html', 'r', encoding='utf-8') as f:
            content = f.read()
        
        checks = []
        
        # Check that Guest List no longer has centering styles
        centering_styles = ['display: flex', 'align-items: center', 'justify-content: center', 'text-align: center']
        has_centering = any(style in content for style in centering_styles)
        
        if not has_centering:
            print("✅ Guest List centering styles removed")
            checks.append(True)
        else:
            print("❌ Guest List still has centering styles")
            checks.append(False)
            
        # Check that Guest List no longer has custom padding/sizing
        custom_sizing = ['max-height: fit-content', 'padding: 1rem', 'min-height: auto']
        has_custom_sizing = any(style in content for style in custom_sizing)
        
        if not has_custom_sizing:
            print("✅ Guest List custom sizing removed")
            checks.append(True)
        else:
            print("❌ Guest List still has custom sizing")
            checks.append(False)
            
        # Check for consistent line-height
        line_height_count = content.count('line-height: 1.6')
        if line_height_count >= 2:  # Both Description and Guest List
            print("✅ Both sections use line-height: 1.6")
            checks.append(True)
        else:
            print(f"❌ line-height: 1.6 found {line_height_count} times (expected 2+)")
            checks.append(False)
            
        return all(checks)
        
    except Exception as e:
        print(f"❌ Error during consistency verification: {e}")
        return False

def verify_template_integrity():
    """Verify template structure integrity"""
    try:
        with open('/Applications/python/voucher-ro_v1.0/templates/public/booking_view.html', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for essential structures
        required_elements = [
            'booking.description',
            'booking.guest_list', 
            '{{ booking.description | html_to_linebreaks }}',
            'html_to_linebreaks',
            'No guest information available',
            'guest.name',
            'guest.age',
            'guest.nationality'
        ]
        
        for element in required_elements:
            if element in content:
                print(f"✅ Found: {element}")
            else:
                print(f"❌ Missing: {element}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error during template integrity check: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Verifying Guest List styling matches Description styling...")
    print("=" * 65)
    
    print("\n1. Matching Styles Verification:")
    matching_ok = verify_matching_styles()
    
    print("\n2. Styling Consistency Verification:")
    consistency_ok = verify_styling_consistency()
    
    print("\n3. Template Integrity Verification:")
    integrity_ok = verify_template_integrity()
    
    print("=" * 65)
    if matching_ok and consistency_ok and integrity_ok:
        print("🎉 All verifications passed!")
        print("✨ Guest List now has identical styling to Description")
        print("✨ Consistent height and display format achieved")
    else:
        print("❌ Some verifications failed. Please check the changes.")
