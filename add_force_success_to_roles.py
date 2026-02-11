#!/usr/bin/env python3
"""
เพิ่ม permission 'force_success' สำหรับ Group Buy
ให้กับ role Administrator และ Manager

รันด้วย: python add_force_success_to_roles.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from models.permission import RolePermission
import json


def add_force_success_to_roles():
    """เพิ่ม force_success permission ให้ roles"""
    app = create_app()
    
    with app.app_context():
        print("=" * 80)
        print("🔧 เพิ่ม Group Buy Permission: force_success")
        print("=" * 80)
        
        # Roles ที่ต้องการเพิ่ม permission
        target_roles = ['Administrator', 'Manager']
        updated_count = 0
        
        for role_name in target_roles:
            print(f"\n📋 Role: {role_name}")
            
            # หา RolePermission (field ชื่อ 'role' ไม่ใช่ 'role_name')
            role_perm = RolePermission.query.filter_by(role=role_name).first()
            
            if not role_perm:
                print(f"   ⚠️  ไม่พบ RolePermission สำหรับ {role_name}")
                print(f"   ➕ สร้างใหม่...")
                
                # สร้าง RolePermission ใหม่
                role_perm = RolePermission(
                    role=role_name,
                    permissions=json.dumps({
                        'group_buy': {
                            'view_campaigns': True,
                            'create_campaign': True,
                            'edit_campaign': True,
                            'view_groups': True,
                            'force_success': True,
                            'cancel_group': True
                        }
                    })
                )
                db.session.add(role_perm)
                updated_count += 1
                print(f"   ✅ สร้าง RolePermission ใหม่พร้อม force_success")
                continue
            
            # ดึง permissions ปัจจุบัน
            try:
                if isinstance(role_perm.permissions, str):
                    current_perms = json.loads(role_perm.permissions)
                else:
                    current_perms = role_perm.permissions or {}
            except:
                current_perms = {}
            
            # ตรวจสอบ group_buy module
            if 'group_buy' not in current_perms:
                current_perms['group_buy'] = {}
            
            # ตรวจสอบ force_success
            if current_perms['group_buy'].get('force_success') == True:
                print(f"   ✅ มี force_success อยู่แล้ว")
                continue
            
            # เพิ่ม force_success
            current_perms['group_buy']['force_success'] = True
            role_perm.permissions = json.dumps(current_perms)
            
            print(f"   ➕ เพิ่ม force_success = True")
            print(f"   Group Buy permissions: {current_perms.get('group_buy', {})}")
            
            updated_count += 1
        
        # บันทึก
        if updated_count > 0:
            db.session.commit()
            print(f"\n{'='*80}")
            print(f"✅ อัปเดต {updated_count} roles สำเร็จ")
            print("=" * 80)
            
            # แสดงสถานะปัจจุบัน
            print("\n📊 สถานะ Permissions หลังอัปเดต:")
            for role_name in target_roles:
                role_perm = RolePermission.query.filter_by(role=role_name).first()
                if role_perm:
                    perms = json.loads(role_perm.permissions) if isinstance(role_perm.permissions, str) else role_perm.permissions
                    gb_perms = perms.get('group_buy', {})
                    print(f"\n{role_name}:")
                    for key, val in gb_perms.items():
                        print(f"  - {key}: {val}")
        else:
            print(f"\n{'='*80}")
            print("ℹ️  ไม่มี role ที่ต้องอัปเดต")
            print("=" * 80)


if __name__ == '__main__':
    add_force_success_to_roles()
