#!/usr/bin/env python3
"""Add Group Buy permissions to all users - Simple Version"""
from app import app, db
from models.user import User
import json

with app.app_context():
    users = User.query.all()
    
    for user in users:
        print(f"\nUser: {user.username} ({user.role})")
        
        # Parse permissions
        try:
            perms = json.loads(user.permissions) if user.permissions else {}
        except:
            perms = {}
        
        # Add group_buy
        if 'group_buy' not in perms:
            perms['group_buy'] = {}
        
        perms['group_buy']['view'] = True
        
        if user.role in ['Administrator', 'Manager', 'Operation']:
            perms['group_buy'].update({
                'create_campaign': True,
                'edit_campaign': True,
                'view_groups': True,
                'manage_groups': True,
                'view_stats': True
            })
        
        # Add to sidebar
        if 'sidebar_menus' not in perms:
            perms['sidebar_menus'] = []
        
        if 'group_buy' not in perms['sidebar_menus']:
            perms['sidebar_menus'].append('group_buy')
        
        user.permissions = json.dumps(perms, ensure_ascii=False)
        print("  ✅ Updated")
    
    db.session.commit()
    print("\n🎉 Done!")
