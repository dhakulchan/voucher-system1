#!/usr/bin/env python3
"""
Verification script to check all the latest UI improvements
"""
import os
import sys

def verify_ui_improvements():
    """Verify all UI improvements in the booking template"""
    template_path = "/Applications/python/voucher-ro_v1.0/templates/public/booking_view.html"
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    improvements = {
        "1. Logo moved to right side": False,
        "2. N/A text removed": False,
        "3. Guest List height adjusted": False,
        "4. Guest List numbering fixed": False,
        "5. Text: ความน่าเชื่อถือและการรับรองจากหน่วยงานต่างฯ": False,
        "6. Text: ทีมงานมืออาชีพ บริการทันใจ": False,
        "7. Text: ทีมงานมีประสบการณ์ยาวนานกว่า 35 ปี": False,
        "8. Added item 7 about service responsibility": False,
        "9. Reduced font sizes and modern styling": False
    }
    
    # Check 1: Logo moved to right column
    if 'col-md-4 text-md-end' in content and 'dcts-logo-vou.png' in content and 'mb-2' in content:
        improvements["1. Logo moved to right side"] = True
    
    # Check 2: N/A removal (conditional booking_date)
    if '{% if booking.booking_date %}' in content and 'else %}' not in content.split('{% if booking.booking_date %}')[1].split('{% endif %}')[0]:
        improvements["2. N/A text removed"] = True
    
    # Check 3: Guest List height adjustment
    if 'min-height: auto' in content and 'padding: 1rem' in content:
        improvements["3. Guest List height adjusted"] = True
    
    # Check 4: Guest List numbering (removed loop.index)
    if 'loop.index' not in content.split('Guest List')[1].split('</div>')[0]:
        improvements["4. Guest List numbering fixed"] = True
    
    # Check 5-7: Updated texts
    if "ความน่าเชื่อถือและการรับรองจากหน่วยงานต่างฯ" in content:
        improvements["5. Text: ความน่าเชื่อถือและการรับรองจากหน่วยงานต่างฯ"] = True
    
    if "ทีมงานมืออาชีพ บริการทันใจ" in content:
        improvements["6. Text: ทีมงานมืออาชีพ บริการทันใจ"] = True
    
    if "ทีมงานมีประสบการณ์ยาวนานกว่า 35 ปี" in content:
        improvements["7. Text: ทีมงานมีประสบการณ์ยาวนานกว่า 35 ปี"] = True
    
    # Check 8: New item 7
    if "Self Service" in content and "Platform online" in content and "พ.ร.บ. ท่องเที่ยว" in content:
        improvements["8. Added item 7 about service responsibility"] = True
    
    # Check 9: Font size reductions
    if "font-size: 0.9rem" in content and "width: 28px; height: 28px" in content:
        improvements["9. Reduced font sizes and modern styling"] = True
    
    print("🔍 UI Improvements Verification:")
    print("=" * 60)
    
    all_passed = True
    for improvement, status in improvements.items():
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {improvement}")
        if not status:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("🎉 All UI improvements implemented successfully!")
    else:
        print("⚠️  Some improvements may need attention")
    
    return all_passed

if __name__ == '__main__':
    verify_ui_improvements()
