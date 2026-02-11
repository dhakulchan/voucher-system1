#!/usr/bin/env python3
"""
Initialize or update role permissions in production database
Creates role_permissions and updates with complete sidebar menus (25 items)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from extensions import db
from models.permission import RolePermission
from datetime import datetime
import json

# Complete sidebar menus list (25 items)
COMPLETE_SIDEBAR_MENUS = [
    'dashboard',
    'bookings',
    'quotes',
    'paid',
    'pre_receipt',
    'vouchers',
    'completed',
    'voucher_library',
    'short_itinerary',
    'flight_templates',
    'group_buy',
    'booking_calendar',
    'queue_management',
    'queue_media_manager',
    'display_token_manager',
    'counter_assignments',
    'task_list',
    'daily_report',
    'customers',
    'suppliers',
    'financial_management',
    'user_management',
    'permission_management',
    'system_settings'
]

# Default permissions for each role
DEFAULT_PERMISSIONS = {
    'Administrator': {
        'sidebar_menus': COMPLETE_SIDEBAR_MENUS,
        'bookings': {'view_all': True, 'view_own': True, 'create': True, 'edit_all': True, 'edit_own': True, 'delete': True},
        'customers': {'view_all': True, 'view_own': True, 'create': True, 'edit_all': True, 'edit_own': True, 'delete': True},
        'quotes': {'view': True, 'create': True, 'edit': True, 'delete': True},
        'vouchers': {'view': True, 'create': True, 'edit': True, 'delete': True},
        'suppliers': {'view': True, 'create': True, 'edit': True, 'delete': True},
        'invoices': {'view': True, 'create': True, 'edit': True, 'delete': True},
        'reports': {'view': True, 'export': True},
        'group_buy': {'view': True, 'create': True, 'edit': True, 'delete': True, 'manage': True},
        'users': {'view': True, 'create': True, 'edit': True, 'delete': True, 'manage_roles': True, 'manage_permissions': True},
        'financial': {'view': True, 'edit': True},
        'admin_notes': {'view': True, 'edit': True},
        'system': {'configure': True},
        'description': 'Full system access'
    },
    'Operation': {
        'sidebar_menus': [
            'dashboard', 'bookings', 'quotes', 'paid', 'pre_receipt', 'vouchers', 
            'completed', 'voucher_library', 'booking_calendar', 'queue_management',
            'queue_media_manager', 'display_token_manager', 'task_list', 'daily_report',
            'customers', 'suppliers', 'financial_management'
        ],
        'bookings': {'view_all': True, 'view_own': True, 'create': True, 'edit_all': True, 'edit_own': True, 'delete': True},
        'customers': {'view_all': True, 'view_own': True, 'create': True, 'edit_all': True, 'edit_own': True, 'delete': True},
        'quotes': {'view': True, 'create': True, 'edit': True, 'delete': False},
        'vouchers': {'view': True, 'create': True, 'edit': True, 'delete': False},
        'suppliers': {'view': True, 'create': True, 'edit': True, 'delete': False},
        'invoices': {'view': True, 'create': True, 'edit': True, 'delete': False},
        'reports': {'view': True, 'export': True},
        'group_buy': {'view': False, 'create': False, 'edit': False, 'delete': False, 'manage': False},
        'users': {'view': False, 'create': False, 'edit': False, 'delete': False, 'manage_roles': False, 'manage_permissions': False},
        'financial': {'view': True, 'edit': False},
        'admin_notes': {'view': False, 'edit': False},
        'system': {'configure': False},
        'description': 'Operations management access'
    },
    'Manager': {
        'sidebar_menus': [
            'dashboard', 'bookings', 'quotes', 'paid', 'pre_receipt', 'vouchers',
            'completed', 'voucher_library', 'booking_calendar', 'queue_management',
            'task_list', 'daily_report', 'customers', 'suppliers'
        ],
        'bookings': {'view_all': True, 'view_own': True, 'create': True, 'edit_all': True, 'edit_own': True, 'delete': False},
        'customers': {'view_all': True, 'view_own': True, 'create': True, 'edit_all': True, 'edit_own': True, 'delete': False},
        'quotes': {'view': True, 'create': True, 'edit': True, 'delete': False},
        'vouchers': {'view': True, 'create': True, 'edit': True, 'delete': False},
        'suppliers': {'view': True, 'create': False, 'edit': False, 'delete': False},
        'invoices': {'view': True, 'create': False, 'edit': False, 'delete': False},
        'reports': {'view': True, 'export': False},
        'group_buy': {'view': False, 'create': False, 'edit': False, 'delete': False, 'manage': False},
        'users': {'view': False, 'create': False, 'edit': False, 'delete': False, 'manage_roles': False, 'manage_permissions': False},
        'financial': {'view': False, 'edit': False},
        'admin_notes': {'view': False, 'edit': False},
        'system': {'configure': False},
        'description': 'Manager level access'
    },
    'Staff': {
        'sidebar_menus': [
            'dashboard', 'bookings', 'vouchers', 'completed', 'voucher_library',
            'booking_calendar', 'queue_management', 'task_list', 'customers'
        ],
        'bookings': {'view_all': True, 'view_own': True, 'create': True, 'edit_all': False, 'edit_own': True, 'delete': False},
        'customers': {'view_all': True, 'view_own': True, 'create': True, 'edit_all': False, 'edit_own': True, 'delete': False},
        'quotes': {'view': False, 'create': False, 'edit': False, 'delete': False},
        'vouchers': {'view': True, 'create': False, 'edit': False, 'delete': False},
        'suppliers': {'view': False, 'create': False, 'edit': False, 'delete': False},
        'invoices': {'view': False, 'create': False, 'edit': False, 'delete': False},
        'reports': {'view': False, 'export': False},
        'group_buy': {'view': False, 'create': False, 'edit': False, 'delete': False, 'manage': False},
        'users': {'view': False, 'create': False, 'edit': False, 'delete': False, 'manage_roles': False, 'manage_permissions': False},
        'financial': {'view': False, 'edit': False},
        'admin_notes': {'view': False, 'edit': False},
        'system': {'configure': False},
        'description': 'Staff level access'
    },
    'Internship': {
        'sidebar_menus': [
            'dashboard', 'bookings', 'queue_management', 'task_list', 'customers'
        ],
        'bookings': {'view_all': False, 'view_own': True, 'create': True, 'edit_all': False, 'edit_own': True, 'delete': False},
        'customers': {'view_all': False, 'view_own': True, 'create': True, 'edit_all': False, 'edit_own': True, 'delete': False},
        'quotes': {'view': False, 'create': False, 'edit': False, 'delete': False},
        'vouchers': {'view': False, 'create': False, 'edit': False, 'delete': False},
        'suppliers': {'view': False, 'create': False, 'edit': False, 'delete': False},
        'invoices': {'view': False, 'create': False, 'edit': False, 'delete': False},
        'reports': {'view': False, 'export': False},
        'group_buy': {'view': False, 'create': False, 'edit': False, 'delete': False, 'manage': False},
        'users': {'view': False, 'create': False, 'edit': False, 'delete': False, 'manage_roles': False, 'manage_permissions': False},
        'financial': {'view': False, 'edit': False},
        'admin_notes': {'view': False, 'edit': False},
        'system': {'configure': False},
        'description': 'Internship - Own data only'
    },
    'Freelance': {
        'sidebar_menus': [
            'dashboard', 'bookings', 'queue_management', 'task_list', 'customers'
        ],
        'bookings': {'view_all': False, 'view_own': True, 'create': True, 'edit_all': False, 'edit_own': True, 'delete': False},
        'customers': {'view_all': False, 'view_own': True, 'create': True, 'edit_all': False, 'edit_own': True, 'delete': False},
        'quotes': {'view': False, 'create': False, 'edit': False, 'delete': False},
        'vouchers': {'view': False, 'create': False, 'edit': False, 'delete': False},
        'suppliers': {'view': False, 'create': False, 'edit': False, 'delete': False},
        'invoices': {'view': False, 'create': False, 'edit': False, 'delete': False},
        'reports': {'view': False, 'export': False},
        'group_buy': {'view': False, 'create': False, 'edit': False, 'delete': False, 'manage': False},
        'users': {'view': False, 'create': False, 'edit': False, 'delete': False, 'manage_roles': False, 'manage_permissions': False},
        'financial': {'view': False, 'edit': False},
        'admin_notes': {'view': False, 'edit': False},
        'system': {'configure': False},
        'description': 'Freelance - Own data only'
    }
}

def init_role_permissions():
    """Initialize or update role permissions"""
    
    with app.app_context():
        try:
            print("\n" + "=" * 70)
            print("INITIALIZING ROLE PERMISSIONS")
            print("=" * 70)
            
            # Check if role_permissions table exists
            inspector = db.inspect(db.engine)
            if 'role_permissions' not in inspector.get_table_names():
                print("\n📦 Creating role_permissions table...")
                db.create_all()
                print("✅ Table created")
            
            updated = 0
            created = 0
            
            for role_name, permissions in DEFAULT_PERMISSIONS.items():
                role_perm = RolePermission.query.filter_by(role=role_name).first()
                
                if role_perm:
                    # Update existing
                    old_menu_count = len(role_perm.permissions.get('sidebar_menus', []))
                    role_perm.permissions = permissions
                    role_perm.description = permissions.get('description', '')
                    role_perm.updated_at = datetime.now()
                    updated += 1
                    print(f"\n✅ Updated {role_name}")
                    print(f"   Menus: {old_menu_count} → {len(permissions['sidebar_menus'])}")
                else:
                    # Create new
                    role_perm = RolePermission(
                        role=role_name,
                        permissions=permissions,
                        description=permissions.get('description', '')
                    )
                    db.session.add(role_perm)
                    created += 1
                    print(f"\n✅ Created {role_name}")
                    print(f"   Menus: {len(permissions['sidebar_menus'])}")
            
            db.session.commit()
            
            print("\n" + "=" * 70)
            print(f"✅ Completed: {created} created, {updated} updated")
            print("=" * 70)
            
            # Display summary
            print("\n📊 COMPLETE SIDEBAR MENU LIST (25 items):")
            print("-" * 70)
            for idx, menu in enumerate(COMPLETE_SIDEBAR_MENUS, 1):
                print(f"  {idx:2d}. {menu}")
            
            print("\n" + "=" * 70)
            print("🎉 ROLE PERMISSIONS INITIALIZED!")
            print("=" * 70)
            print("\n📝 Next steps:")
            print("   1. Restart the application")
            print("   2. Test permission management at /admin/permissions")
            print("   3. Verify all menu items appear in UI")
            print()
            
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            raise

if __name__ == '__main__':
    init_role_permissions()
