#!/usr/bin/env python3
"""
Update sidebar menus in role permissions
Add missing menu items: paid, pre_receipt, completed, voucher_library, 
short_itinerary, flight_templates, group_buy, booking_calendar, 
queue_media_manager, display_token_manager, counter_assignments, 
daily_report, financial_management, permission_management
"""

import sys
import os
from datetime import datetime
import json

# Add app directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import Flask app and database
from app import app
from extensions import db
from models.permission import RolePermission

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
    'landing_page',
    'landing_groups',
    'review_slides',
    'company_images',
    'group_buy',
    'group_buy_campaigns',
    'group_buy_groups',
    'group_buy_bank_accounts',
    'group_buy_coupons',
    'customer_reviews',
    'customer_points',
    'special_codes',
    'campaign_tracking',
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

# Role-specific menu configurations
ROLE_MENUS = {
    'Administrator': COMPLETE_SIDEBAR_MENUS,
    'Operation': [
        'dashboard', 'bookings', 'quotes', 'paid', 'pre_receipt', 'vouchers', 
        'completed', 'voucher_library', 'booking_calendar', 'queue_management',
        'queue_media_manager', 'display_token_manager', 'task_list', 'daily_report',
        'customers', 'suppliers', 'financial_management'
    ],
    'Manager': [
        'dashboard', 'bookings', 'quotes', 'paid', 'pre_receipt', 'vouchers',
        'completed', 'voucher_library', 'booking_calendar', 'queue_management',
        'task_list', 'daily_report', 'customers', 'suppliers'
    ],
    'Staff': [
        'dashboard', 'bookings', 'vouchers', 'completed', 'voucher_library',
        'booking_calendar', 'queue_management', 'task_list', 'customers'
    ],
    'Internship': [
        'dashboard', 'bookings', 'queue_management', 'task_list', 'customers'
    ],
    'Freelance': [
        'dashboard', 'bookings', 'queue_management', 'task_list', 'customers'
    ]
}

def update_role_permissions():
    """Update sidebar_menus in role_permissions table"""
    
    with app.app_context():
        try:
            print("\n" + "=" * 70)
            print("UPDATING SIDEBAR MENUS IN ROLE PERMISSIONS")
            print("=" * 70)
            
            # Get all role permissions
            roles = RolePermission.query.all()
            
            if not roles:
                print("\n⚠️  No role permissions found in database")
                return
            
            print(f"\n📋 Found {len(roles)} roles to update")
            
            updated_count = 0
            for role_perm in roles:
                role_name = role_perm.role
                current_perms = role_perm.permissions if role_perm.permissions else {}
                
                # Get new menu list for this role
                new_menus = ROLE_MENUS.get(role_name, COMPLETE_SIDEBAR_MENUS)
                old_menus = current_perms.get('sidebar_menus', [])
                
                # Update sidebar_menus
                current_perms['sidebar_menus'] = new_menus
                role_perm.permissions = current_perms
                role_perm.updated_at = datetime.now()
                
                print(f"\n✅ {role_name}")
                print(f"   Old menus: {len(old_menus)} items")
                print(f"   New menus: {len(new_menus)} items")
                
                # Show added menus
                added = set(new_menus) - set(old_menus)
                if added:
                    print(f"   ➕ Added: {', '.join(sorted(added))}")
                
                updated_count += 1
            
            # Commit changes
            db.session.commit()
            
            print("\n" + "=" * 70)
            print(f"✅ Successfully updated {updated_count} roles")
            print("=" * 70)
            
            # Display summary
            print("\n📊 COMPLETE SIDEBAR MENU LIST (25 items):")
            print("-" * 70)
            for idx, menu in enumerate(COMPLETE_SIDEBAR_MENUS, 1):
                print(f"  {idx:2d}. {menu}")
            
            print("\n" + "=" * 70)
            print("🎉 UPDATE COMPLETED SUCCESSFULLY!")
            print("=" * 70)
            print("\n📝 Next steps:")
            print("   1. Test the permission management page")
            print("   2. Verify all menu items are visible in the UI")
            print("   3. Check user role assignments")
            print()
            
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    update_role_permissions()
