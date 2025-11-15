#!/usr/bin/env python3
"""
Verification script for the latest UI updates
"""
import os

def verify_latest_updates():
    """Verify the latest text and Guest List updates"""
    template_path = "/Applications/python/voucher-ro_v1.0/templates/public/booking_view.html"
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    updates = {
        "1. Updated item #7 text": False,
        "2. Guest List height reduced (50%)": False,
        "3. Guest List scroll added": False,
        "4. Guest List padding optimized": False
    }
    
    # Check 1: Updated text for item 7
    expected_text = "การบริการของเรามีความรับผิดชอบมากกว่าการใช้ 'Self Service' หรือแพลตฟอร์มออนไลน์ทั่วไป ซึ่งไม่อยู่ภายใต้ข้อบังคับตามพระราชบัญญัติธุรกิจนำเที่ยว และมักไม่มีการคุ้มครองประกันการเดินทางหากเป็นแพ็กเกจทัวร์ตามเงื่อนไขบริการ"
    if expected_text in content:
        updates["1. Updated item #7 text"] = True
    
    # Check 2: Guest List height control
    if "max-height: 150px" in content:
        updates["2. Guest List height reduced (50%)"] = True
    
    # Check 3: Scroll functionality
    if "overflow-y: auto" in content:
        updates["3. Guest List scroll added"] = True
    
    # Check 4: Optimized padding
    if "padding: 0.5rem" in content and "line-height: 1.3" in content:
        updates["4. Guest List padding optimized"] = True
    
    print("🔍 Latest Updates Verification:")
    print("=" * 50)
    
    all_passed = True
    for update, status in updates.items():
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {update}")
        if not status:
            all_passed = False
    
    print("=" * 50)
    if all_passed:
        print("🎉 All latest updates implemented successfully!")
    else:
        print("⚠️  Some updates may need attention")
    
    return all_passed

if __name__ == '__main__':
    verify_latest_updates()
