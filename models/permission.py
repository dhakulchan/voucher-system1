"""
Permission models for role-based and user-specific access control
"""
from extensions import db
from utils.datetime_utils import naive_utc_now
import json

class RolePermission(db.Model):
    """Store default permissions for each role"""
    __tablename__ = 'role_permissions'
    
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(50), unique=True, nullable=False, index=True)
    permissions = db.Column(db.JSON, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=naive_utc_now)
    updated_at = db.Column(db.DateTime, default=naive_utc_now, onupdate=naive_utc_now)
    
    def __repr__(self):
        return f'<RolePermission {self.role}>'
    
    def get_permission(self, module, action):
        """
        Check if role has specific permission
        
        Args:
            module: Module name (e.g., 'bookings', 'customers', 'users')
            action: Action name (e.g., 'view', 'create', 'edit', 'delete')
        
        Returns:
            bool: True if permission exists and is True, False otherwise
        """
        if not self.permissions:
            return False
        
        if module not in self.permissions:
            return False
        
        module_perms = self.permissions[module]
        if isinstance(module_perms, dict):
            return module_perms.get(action, False)
        
        return bool(module_perms)
    
    def has_sidebar_menu(self, menu_name):
        """Check if role has access to sidebar menu"""
        if not self.permissions:
            return False
        
        sidebar_menus = self.permissions.get('sidebar_menus', [])
        return menu_name in sidebar_menus
    
    @classmethod
    def get_role_permissions(cls, role):
        """Get permissions for a specific role"""
        return cls.query.filter_by(role=role).first()
    
    @classmethod
    def get_all_roles(cls):
        """Get all configured roles"""
        return cls.query.all()
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'role': self.role,
            'permissions': self.permissions,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class UserPermission(db.Model):
    """Store custom permissions for individual users (overrides role permissions)"""
    __tablename__ = 'user_permissions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False, index=True)
    permissions = db.Column(db.JSON, nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=naive_utc_now)
    updated_at = db.Column(db.DateTime, default=naive_utc_now, onupdate=naive_utc_now)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('custom_permissions', uselist=False, lazy=True))
    
    def __repr__(self):
        return f'<UserPermission user_id={self.user_id}>'
    
    def get_permission(self, module, action):
        """
        Check if user has specific permission
        
        Args:
            module: Module name (e.g., 'bookings', 'customers', 'users')
            action: Action name (e.g., 'view', 'create', 'edit', 'delete')
        
        Returns:
            bool: True if permission exists and is True, False otherwise
        """
        if not self.permissions:
            return False
        
        if module not in self.permissions:
            return False
        
        module_perms = self.permissions[module]
        if isinstance(module_perms, dict):
            return module_perms.get(action, False)
        
        return bool(module_perms)
    
    def has_sidebar_menu(self, menu_name):
        """Check if user has access to sidebar menu"""
        if not self.permissions:
            return False
        
        sidebar_menus = self.permissions.get('sidebar_menus', [])
        return menu_name in sidebar_menus
    
    @classmethod
    def get_user_permissions(cls, user_id):
        """Get custom permissions for a specific user"""
        return cls.query.filter_by(user_id=user_id).first()
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'permissions': self.permissions,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
