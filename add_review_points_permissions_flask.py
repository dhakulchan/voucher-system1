#!/usr/bin/env python3
"""
Add Customer Reviews and Points permissions using Flask app context
"""

import sys
import os
sys.path.insert(0, '/var/www/booking')

from app import create_app
from extensions import db
from models.permission import RolePermission
import json

def add_review_points_permissions():
    """Add Customer Reviews and Points permissions to all roles"""
    
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("Adding Customer Reviews & Points Permissions")
        print("=" * 60)
        
        # Get all role permissions
        roles = RolePermission.query.all()
        
        for role in roles:
            print(f"\nProcessing role: {role.role} (ID: {role.id})")
            
            # Parse current permissions
            current_permissions = role.permissions if isinstance(role.permissions, dict) else {}
            current_sidebar = current_permissions.get('sidebar_menus', [])
            
            # Add customer_reviews permissions based on role
            if role.role in ['Administrator', 'Operation']:
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
                
            elif role.role == 'Manager':
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
            
            # Update role permissions
            current_permissions['sidebar_menus'] = current_sidebar
            role.permissions = current_permissions
            
            print(f"✅ Updated {role.role}:")
            print(f"   - customer_reviews: {current_permissions.get('customer_reviews', {})}")
            print(f"   - customer_points: {current_permissions.get('customer_points', {})}")
            print(f"   - sidebar_menus: {current_sidebar}")
        
        # Commit changes
        db.session.commit()
        
        print("\n" + "=" * 60)
        print("✅ All permissions updated successfully!")
        print("=" * 60)

if __name__ == '__main__':
    add_review_points_permissions()
