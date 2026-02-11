#!/usr/bin/env python3
"""
เพิ่ม permission 'force_success' ให้กับ Admin/Manager users
เพื่อให้สามารถบังคับให้กลุ่มสำเร็จได้ (manual-success)

รันด้วย: python add_force_success_permission.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from models.user import User
import json


def add_force_success_permission():
    """เพิ่ม permission force_success"""
    app = create_app()
    
    with app.app_context():
        print("=" * 80)
        print("🔧 เพิ่ม Permission: force_success")
        print("=" * 80)
        
        # หา users ที่เป็น admin หรือ manager
        users = User.query.filter(User.role.in_(['admin', 'manager'])).all()
        
        if not users:
            print("❌ ไม่พบ admin/manager users")
            return
        
        updated_count = 0
        
        for user in users:
            print(f"\n👤 User: {user.username} (role: {user.role})")
            
            # ดึง permissions ปัจจุบัน
            current_perms = user.group_buy_permissions or {}
            
            if isinstance(current_perms, str):
                try:
                    current_perms = json.loads(current_perms)
                except:
                    current_perms = {}
            
            print(f"   Current permissions: {current_perms}")
            
            # เช็คว่ามี force_success แล้วหรือยัง
            if current_perms.get('force_success') == True:
                print(f"   ✅ มี force_success อยู่แล้ว")
                continue
            
            # เพิ่ม force_success
            current_perms['force_success'] = True
            user.group_buy_permissions = current_perms
            
            print(f"   ➕ เพิ่ม force_success = True")
            print(f"   New permissions: {user.group_buy_permissions}")
            
            updated_count += 1
        
        # บันทึก
        if updated_count > 0:
            db.session.commit()
            print(f"\n{'='*80}")
            print(f"✅ อัปเดต {updated_count} users สำเร็จ")
            print("=" * 80)
        else:
            print(f"\n{'='*80}")
            print("ℹ️  ไม่มี user ที่ต้องอัปเดต")
            print("=" * 80)


if __name__ == '__main__':
    add_force_success_permission()
