#!/usr/bin/env python3
"""
Add Group Buy sub menus to role permissions
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from extensions import db
from models.permission import RolePermission
from datetime import datetime

# Group Buy sub menus to add
NEW_MENUS = ['group_buy_campaigns', 'group_buy_groups', 'group_buy_bank_accounts']

def update_permissions():
    """Add Group Buy sub menus to all roles that have group_buy"""
    
    with app.app_context():
        try:
            print("\n" + "=" * 70)
            print("ADDING GROUP BUY SUB MENUS")
            print("=" * 70)
            
            roles = RolePermission.query.all()
            updated = 0
            
            for role_perm in roles:
                current_menus = role_perm.permissions.get('sidebar_menus', [])
                
                # Check if role has group_buy menu
                if 'group_buy' in current_menus:
                    # Add sub menus after group_buy if not already present
                    modified = False
                    for new_menu in NEW_MENUS:
                        if new_menu not in current_menus:
                            # Find index of group_buy
                            idx = current_menus.index('group_buy')
                            # Insert after group_buy
                            current_menus.insert(idx + 1, new_menu)
                            modified = True
                            print(f"   + Added '{new_menu}' to {role_perm.role}")
                    
                    if modified:
                        role_perm.permissions['sidebar_menus'] = current_menus
                        role_perm.updated_at = datetime.now()
                        updated += 1
                        print(f"✅ {role_perm.role}: {len(current_menus)} menus")
                else:
                    print(f"⏭️  {role_perm.role}: No group_buy menu, skipped")
            
            if updated > 0:
                db.session.commit()
                print("\n" + "=" * 70)
                print(f"✅ Updated {updated} roles")
                print("=" * 70)
            else:
                print("\n⚠️  No updates needed")
            
            print("\n📋 New Group Buy sub menus:")
            for menu in NEW_MENUS:
                print(f"   • {menu}")
            
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    update_permissions()
