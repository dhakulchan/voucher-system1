#!/usr/bin/env python3
"""
Verification script to check if all requested changes are implemented
"""
import os
import sys

def verify_template_changes():
    """Verify all changes in the booking template"""
    template_path = "/Applications/python/voucher-ro_v1.0/templates/public/booking_view.html"
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    changes = {
        "1. Guest list line breaks": False,
        "2. Party name/code display": False,
        "3. ทำไมต้องเลือก ตระกูลเฉินฯ": False,
        "4. Logo implementation": False,
        "5. Email booking@dhakulchan.com": False
    }
    
    # Check 1: Guest list line breaks fix
    if "replace('<br>', '\\n')" in content and "replace('</p>', '\\n')" in content:
        changes["1. Guest list line breaks"] = True
    
    # Check 2: Party name/code display  
    if "Party Name/Code:" in content and "booking.party_name" in content:
        changes["2. Party name/code display"] = True
    
    # Check 3: Updated text
    if "ทำไมต้องเลือก ตระกูลเฉินฯ" in content:
        changes["3. ทำไมต้องเลือก ตระกูลเฉินฯ"] = True
    
    # Check 4: Logo implementation
    if "dcts-logo-vou.png" in content and "Logo Section" in content:
        changes["4. Logo implementation"] = True
    
    # Check 5: Email change
    booking_email_count = content.count("booking@dhakulchan.com")
    support_email_count = content.count("support@dhakulchan.com")
    if booking_email_count >= 3 and support_email_count == 0:
        changes["5. Email booking@dhakulchan.com"] = True
    
    print("🔍 Verification Results:")
    print("=" * 50)
    
    all_passed = True
    for change, status in changes.items():
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {change}")
        if not status:
            all_passed = False
    
    print("=" * 50)
    if all_passed:
        print("🎉 All changes implemented successfully!")
    else:
        print("⚠️  Some changes may need attention")
    
    return all_passed

if __name__ == '__main__':
    verify_template_changes()
