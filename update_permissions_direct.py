#!/usr/bin/env python3
"""
Direct SQL update for role permissions - bypass Flask cache
"""

import sys
import os
sys.path.insert(0, '/var/www/booking')

from sqlalchemy import create_engine, text
import json

# Use SQLAlchemy directly
DATABASE_URL = 'mysql+mysqlconnector://voucher_user:VoucherSecure2026!@localhost:3306/voucher_enhanced?charset=utf8mb4'

def update_permissions_direct():
    """Update permissions directly via SQL"""
    
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            print("=" * 60)
            print("Direct SQL Update - Role Permissions")
            print("=" * 60)
            
            # Get Administrator permissions
            result = conn.execute(text("SELECT id, role, permissions FROM role_permissions WHERE role = 'Administrator'"))
            row = result.fetchone()
            
            if not row:
                print("❌ Administrator role not found")
                return
            
            role_id, role_name, perms_json = row
            print(f"\n✅ Found role: {role_name} (ID: {role_id})")
            
            # Parse current permissions
            current_perms = json.loads(perms_json) if perms_json else {}
            current_sidebar = current_perms.get('sidebar_menus', [])
            
            print(f"📋 Current sidebar_menus count: {len(current_sidebar)}")
            print(f"   Has customer_reviews: {'customer_reviews' in current_sidebar}")
            print(f"   Has customer_points: {'customer_points' in current_sidebar}")
            
            # Add new permissions
            current_perms['customer_reviews'] = {
                'view': True,
                'approve': True,
                'reject': True,
                'delete': True,
                'bulk_action': True
            }
            current_perms['customer_points'] = {
                'view': True,
                'adjust': True,
                'view_transactions': True,
                'export': True
            }
            
            # Add to sidebar if not already there
            if 'customer_reviews' not in current_sidebar:
                current_sidebar.append('customer_reviews')
            if 'customer_points' not in current_sidebar:
                current_sidebar.append('customer_points')
            
            current_perms['sidebar_menus'] = current_sidebar
            
            # Update database
            new_perms_json = json.dumps(current_perms)
            conn.execute(
                text("UPDATE role_permissions SET permissions = :perms WHERE id = :id"),
                {"perms": new_perms_json, "id": role_id}
            )
            conn.commit()
            
            print(f"\n✅ Updated successfully!")
            print(f"📋 New sidebar_menus count: {len(current_sidebar)}")
            print(f"   Added: customer_reviews, customer_points")
            
            # Verify
            result = conn.execute(text("SELECT permissions FROM role_permissions WHERE role = 'Administrator'"))
            row = result.fetchone()
            verify_perms = json.loads(row[0])
            verify_sidebar = verify_perms.get('sidebar_menus', [])
            
            print(f"\n🔍 Verification:")
            print(f"   customer_reviews in sidebar: {'customer_reviews' in verify_sidebar}")
            print(f"   customer_points in sidebar: {'customer_points' in verify_sidebar}")
            print(f"   customer_reviews perms: {verify_perms.get('customer_reviews', {})}")
            print(f"   customer_points perms: {verify_perms.get('customer_points', {})}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    update_permissions_direct()
