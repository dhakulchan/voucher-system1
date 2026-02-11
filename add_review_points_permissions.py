#!/usr/bin/env python3
"""
Add Customer Reviews and Points permissions to existing role permissions
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

def add_review_points_permissions():
    """Add Customer Reviews and Points permissions to all roles"""
    
    connection = pymysql.connect(**DB_CONFIG)
    
    try:
        with connection.cursor() as cursor:
            print("=" * 60)
            print("Adding Customer Reviews & Points Permissions")
            print("=" * 60)
            
            # Get all role permissions
            cursor.execute("SELECT * FROM role_permissions")
            roles = cursor.fetchall()
            
            for role in roles:
                role_id = role[0]
                role_name = role[1]
                current_permissions = json.loads(role[2]) if role[2] else {}
                current_sidebar = json.loads(role[3]) if role[3] else []
                
                print(f"\nProcessing role: {role_name} (ID: {role_id})")
                
                # Add customer_reviews permissions based on role
                if role_name in ['Administrator', 'Operation']:
                    # Full access for Admin and Operation
                    current_permissions['customer_reviews'] = {
                        'view': True,
                        'approve': True,
                        'reject': True,
                        'delete': True,
                        'bulk_action': True
                    }
                    current_permissions['customer_points'] = {
                        'view': True,
                        'adjust': True,
                        'view_transactions': True,
                        'export': True
                    }
                    # Add to sidebar menu
                    if 'customer_reviews' not in current_sidebar:
                        current_sidebar.append('customer_reviews')
                    if 'customer_points' not in current_sidebar:
                        current_sidebar.append('customer_points')
                    
                elif role_name == 'Manager':
                    # View only for Manager
                    current_permissions['customer_reviews'] = {
                        'view': True,
                        'approve': False,
                        'reject': False,
                        'delete': False,
                        'bulk_action': False
                    }
                    current_permissions['customer_points'] = {
                        'view': True,
                        'adjust': False,
                        'view_transactions': True,
                        'export': True
                    }
                    # Add to sidebar menu
                    if 'customer_reviews' not in current_sidebar:
                        current_sidebar.append('customer_reviews')
                    if 'customer_points' not in current_sidebar:
                        current_sidebar.append('customer_points')
                    
                else:
                    # No access for other roles (Staff, Counter)
                    current_permissions['customer_reviews'] = {
                        'view': False,
                        'approve': False,
                        'reject': False,
                        'delete': False,
                        'bulk_action': False
                    }
                    current_permissions['customer_points'] = {
                        'view': False,
                        'adjust': False,
                        'view_transactions': False,
                        'export': False
                    }
                
                # Update database
                cursor.execute(
                    "UPDATE role_permissions SET permissions = %s, sidebar_menu = %s WHERE id = %s",
                    (json.dumps(current_permissions), json.dumps(current_sidebar), role_id)
                )
                
                print(f"✅ Updated {role_name}:")
                print(f"   - customer_reviews: {current_permissions.get('customer_reviews', {})}")
                print(f"   - customer_points: {current_permissions.get('customer_points', {})}")
                print(f"   - sidebar_menu: {current_sidebar}")
            
            connection.commit()
            print("\n" + "=" * 60)
            print("✅ All permissions updated successfully!")
            print("=" * 60)
            
    except Exception as e:
        connection.rollback()
        print(f"\n❌ Error: {e}")
        raise
    
    finally:
        connection.close()

if __name__ == '__main__':
    add_review_points_permissions()
