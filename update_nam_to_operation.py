#!/usr/bin/env python3
"""
Update Nam's role to Operation
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models.user import User
from extensions import db

def update_nam_role():
    """Update Nam's role from Staff to Operation"""
    app = create_app()
    
    with app.app_context():
        # Find user 'nam'
        nam_user = User.query.filter_by(username='nam').first()
        
        if not nam_user:
            print("❌ User 'nam' not found!")
            return False
        
        print("\n" + "="*80)
        print("UPDATING NAM'S ROLE TO OPERATION")
        print("="*80)
        
        print(f"\nCurrent Details:")
        print(f"  Username: {nam_user.username}")
        print(f"  Email: {nam_user.email}")
        print(f"  Role: {nam_user.role}")
        print(f"  Is Admin: {nam_user.is_admin}")
        
        # Update role
        old_role = nam_user.role
        nam_user.role = 'Operation'
        
        try:
            db.session.commit()
            print(f"\n✅ Successfully updated role: {old_role} → Operation")
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error updating role: {e}")
            return False
        
        # Verify update
        nam_user = User.query.filter_by(username='nam').first()
        print(f"\nUpdated Details:")
        print(f"  Username: {nam_user.username}")
        print(f"  Email: {nam_user.email}")
        print(f"  Role: {nam_user.role}")
        print(f"  Is Admin: {nam_user.is_admin}")
        
        print("\n" + "="*80)
        print("PERMISSIONS CHECK FOR NAM (Operation Role)")
        print("="*80)
        print(f"  Can see User Management menu: {nam_user.role == 'Administrator'}")
        print(f"  Can access /admin/users/ URL: {nam_user.role == 'Administrator'}")
        print(f"  Can manage quotes: {nam_user.can_manage_quotes()}")
        print(f"  Can view financial data: {nam_user.can_view_financial_data()}")
        print(f"  Can access admin notes: {nam_user.can_access_admin_notes()}")
        print(f"  Can access manager memos: {nam_user.can_access_manager_memos()}")
        print("="*80)
        
        return True

if __name__ == '__main__':
    success = update_nam_role()
    sys.exit(0 if success else 1)
