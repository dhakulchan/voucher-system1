#!/usr/bin/env python3
"""
Update user-specific permissions for admin user
"""

import sys, os
sys.path.insert(0, '/var/www/booking')

from sqlalchemy import create_engine, text
import json

DATABASE_URL = 'mysql+mysqlconnector://voucher_user:VoucherSecure2026!@localhost:3306/voucher_enhanced?charset=utf8mb4'

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    print("=" * 60)
    print("Update User-Specific Permissions")
    print("=" * 60)
    
    # Get admin user ID
    result = conn.execute(text("SELECT id, username, role FROM users WHERE username = 'admin'"))
    user = result.fetchone()
    
    if not user:
        print("❌ Admin user not found")
        exit(1)
    
    user_id, username, role = user
    print(f"\n✅ Found user: {username} (ID: {user_id}, Role: {role})")
    
    # Check for user_permissions
    result = conn.execute(text("SELECT id, permissions FROM user_permissions WHERE user_id = :uid"), {"uid": user_id})
    user_perm = result.fetchone()
    
    if user_perm:
        perm_id, perms_json = user_perm
        print(f"✅ User has custom permissions (ID: {perm_id})")
        
        # Parse and update
        perms = json.loads(perms_json) if perms_json else {}
        sidebar = perms.get('sidebar_menus', [])
        
        print(f"\n📋 Current sidebar menus: {len(sidebar)}")
        print(f"   - Has customer_reviews: {'customer_reviews' in sidebar}")
        print(f"   - Has customer_points: {'customer_points' in sidebar}")
        
        # Add if missing
        if 'customer_reviews' not in sidebar:
            sidebar.append('customer_reviews')
            print(f"   ➕ Added customer_reviews")
        
        if 'customer_points' not in sidebar:
            sidebar.append('customer_points')
            print(f"   ➕ Added customer_points")
        
        # Add permissions
        perms['customer_reviews'] = {
            'view': True,
            'approve': True,
            'reject': True,
            'delete': True,
            'bulk_action': True
        }
        perms['customer_points'] = {
            'view': True,
            'adjust': True,
            'view_transactions': True,
            'export': True
        }
        perms['sidebar_menus'] = sidebar
        
        # Update
        new_perms_json = json.dumps(perms)
        conn.execute(
            text("UPDATE user_permissions SET permissions = :perms WHERE id = :id"),
            {"perms": new_perms_json, "id": perm_id}
        )
        conn.commit()
        
        print(f"\n✅ Updated user permissions!")
        print(f"📋 New sidebar menus count: {len(sidebar)}")
        
    else:
        print(f"✅ No custom user permissions found")
        print(f"   (Will use role permissions - which are already correct)")

print("\n" + "=" * 60)
print("🔄 Logout and login again to see changes!")
print("=" * 60)
