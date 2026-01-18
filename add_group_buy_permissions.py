#!/usr/bin/env python3
"""
Add Group Buy permissions to existing role permissions
"""

import pymysql
import json

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'voucher_user',
    'password': 'voucher_secure_2024',
    'database': 'voucher_enhanced',
    'port': 3306,
    'charset': 'utf8mb4'
}

def add_group_buy_permissions():
    """Add Group Buy permissions to all roles"""
    
    connection = pymysql.connect(**DB_CONFIG)
    
    try:
        with connection.cursor() as cursor:
            print("=" * 60)
            print("Adding Group Buy Permissions to Role Permissions")
            print("=" * 60)
            
            # Define Group Buy permissions for each role
            role_permissions = {
                'Administrator': {
                    'group_buy': {
                        'view': True,
                        'create_campaign': True,
                        'edit_campaign': True,
                        'delete_campaign': True,
                        'view_groups': True,
                        'manage_groups': True,
                        'force_success': True,
                        'cancel_group': True,
                        'view_stats': True
                    },
                    'sidebar_menu_add': 'group_buy'
                },
                'Operation': {
                    'group_buy': {
                        'view': True,
                        'create_campaign': True,
                        'edit_campaign': True,
                        'delete_campaign': False,
                        'view_groups': True,
                        'manage_groups': True,
                        'force_success': True,
                        'cancel_group': True,
                        'view_stats': True
                    },
                    'sidebar_menu_add': 'group_buy'
                },
                'Manager': {
                    'group_buy': {
                        'view': True,
                        'create_campaign': False,
                        'edit_campaign': False,
                        'delete_campaign': False,
                        'view_groups': True,
                        'manage_groups': False,
                        'force_success': False,
                        'cancel_group': False,
                        'view_stats': True
                    },
                    'sidebar_menu_add': 'group_buy'
                },
                'Staff': {
                    'group_buy': {
                        'view': False,
                        'create_campaign': False,
                        'edit_campaign': False,
                        'delete_campaign': False,
                        'view_groups': False,
                        'manage_groups': False,
                        'force_success': False,
                        'cancel_group': False,
                        'view_stats': False
                    },
                    'sidebar_menu_add': None
                },
                'Internship': {
                    'group_buy': {
                        'view': False,
                        'create_campaign': False,
                        'edit_campaign': False,
                        'delete_campaign': False,
                        'view_groups': False,
                        'manage_groups': False,
                        'force_success': False,
                        'cancel_group': False,
                        'view_stats': False
                    },
                    'sidebar_menu_add': None
                }
            }
            
            # Update each role
            for role, perms in role_permissions.items():
                print(f"\nUpdating role: {role}...")
                
                # Get current permissions
                cursor.execute("SELECT permissions FROM role_permissions WHERE role = %s", (role,))
                result = cursor.fetchone()
                
                if not result:
                    print(f"  ⚠️  Role {role} not found, skipping...")
                    continue
                
                # Parse current permissions
                current_perms = json.loads(result[0]) if result[0] else {}
                
                # Add Group Buy permissions
                current_perms['group_buy'] = perms['group_buy']
                
                # Add to sidebar_menus if needed
                if perms['sidebar_menu_add']:
                    if 'sidebar_menus' not in current_perms:
                        current_perms['sidebar_menus'] = []
                    if perms['sidebar_menu_add'] not in current_perms['sidebar_menus']:
                        current_perms['sidebar_menus'].append(perms['sidebar_menu_add'])
                
                # Update database
                cursor.execute(
                    "UPDATE role_permissions SET permissions = %s WHERE role = %s",
                    (json.dumps(current_perms), role)
                )
                
                print(f"  ✅ Updated {role} with Group Buy permissions")
                print(f"     - View: {perms['group_buy']['view']}")
                print(f"     - Create Campaign: {perms['group_buy']['create_campaign']}")
                print(f"     - Edit Campaign: {perms['group_buy']['edit_campaign']}")
                print(f"     - Manage Groups: {perms['group_buy']['manage_groups']}")
            
            connection.commit()
            
            print("\n" + "=" * 60)
            print("✅ Group Buy permissions added successfully!")
            print("=" * 60)
            
            # Display summary
            print("\nPermission Summary:")
            print("-" * 60)
            cursor.execute("SELECT role, permissions FROM role_permissions")
            for row in cursor.fetchall():
                role_name = row[0]
                perms = json.loads(row[1])
                if 'group_buy' in perms:
                    print(f"\n{role_name}:")
                    for action, allowed in perms['group_buy'].items():
                        status = "✅" if allowed else "❌"
                        print(f"  {status} {action}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        connection.rollback()
        return False
    finally:
        connection.close()
    
    return True

if __name__ == '__main__':
    success = add_group_buy_permissions()
    exit(0 if success else 1)
