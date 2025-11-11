from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from extensions import db
from utils.datetime_utils import naive_utc_now
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='Staff')
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=naive_utc_now)
    updated_at = db.Column(db.DateTime, default=naive_utc_now, onupdate=naive_utc_now)
    
    def set_password(self, password):
        """Set password hash for user"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if provided password matches user's password"""
        return check_password_hash(self.password_hash, password)
    
    @classmethod
    def create_user(cls, username, email, password, is_admin=False, role=None):
        """Create a new user"""
        if role is None:
            role = 'Administrator' if is_admin else 'Staff'
            
        user = cls(
            username=username,
            email=email,
            role=role,
            is_admin=is_admin
        )
        user.set_password(password)
        return user
    
    # Role-based Permission Methods
    def can_manage_quotes(self):
        return self.role in ['Administrator', 'Operation']
    
    def can_view_financial_data(self):
        return self.role == 'Administrator'
    
    def can_access_admin_notes(self):
        return self.role in ['Administrator', 'Operation']
    
    def is_administrator(self):
        return self.role == 'Administrator'
    
    def is_operation_staff(self):
        return self.role == 'Operation'
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def __repr__(self):
        return f'<User {self.username} ({self.role})>'
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def has_role(self, *roles):
        """Check if user has any of the specified roles"""
        return self.role in roles
    
    def is_role(self, role):
        """Check if user has specific role"""
        return self.role == role
    
    # Enhanced Permission Methods
    def can_access_admin(self):
        """Check if user can access admin features"""
        return self.role in ['Administrator', 'Operation']
    
    def can_manage_users(self):
        """Check if user can manage other users"""
        return self.role == 'Administrator'
    
    def can_create_admin(self):
        """Check if user can create admin accounts"""
        return self.role == 'Administrator'
    
    def can_edit_all_bookings(self):
        """Check if user can edit any booking"""
        return self.role in ['Administrator', 'Operation']
    
    def can_delete_bookings(self):
        """Check if user can delete bookings"""
        return self.role in ['Administrator', 'Operation']
    
    def can_view_financial_data(self):
        """Check if user can view financial information"""
        return self.role in ['Administrator', 'Operation']
    
    def can_manage_quotes(self):
        """Check if user can manage quotes"""
        return self.role in ['Administrator', 'Operation']
    
    def can_access_admin_notes(self):
        """Check if user can access admin notes"""
        return self.role == 'Administrator'
    
    def can_access_manager_memos(self):
        """Check if user can access manager memos"""
        return self.role in ['Administrator', 'Operation']
    
    def can_export_data(self):
        """Check if user can export data"""
        return self.role in ['Administrator', 'Operation']
    
    def can_configure_system(self):
        """Check if user can configure system settings"""
        return self.role == 'Administrator'
    
    def role_display(self):
        """Get display name for role"""
        role_mapping = {
            'Administrator': 'System Administrator',
            'Operation': 'Operations Manager', 
            'Staff': 'Staff Member'
        }
        return role_mapping.get(self.role, self.role)
    
    def role_badge_class(self):
        """Get Bootstrap badge class for role"""
        role_classes = {
            'Administrator': 'bg-danger',
            'Operation': 'bg-warning',
            'Staff': 'bg-primary'
        }
        return role_classes.get(self.role, 'bg-secondary')
    
    def get_permissions_summary(self):
        """Get summary of user permissions"""
        permissions = []
        
        if self.can_access_admin():
            permissions.append('Admin Access')
        if self.can_manage_users():
            permissions.append('User Management')
        if self.can_edit_all_bookings():
            permissions.append('Edit All Bookings')
        if self.can_delete_bookings():
            permissions.append('Delete Bookings')
        if self.can_view_financial_data():
            permissions.append('View Financial Data')
        if self.can_manage_quotes():
            permissions.append('Manage Quotes')
        if self.can_access_admin_notes():
            permissions.append('Admin Notes')
        if self.can_access_manager_memos():
            permissions.append('Manager Memos')
        if self.can_export_data():
            permissions.append('Export Data')
        if self.can_configure_system():
            permissions.append('System Configuration')
            
        return permissions
    
    @classmethod
    def get_available_roles(cls):
        """Get list of available user roles"""
        return ['Administrator', 'Operation', 'Staff']
    
    @classmethod
    def create_user(cls, username, email, password, role='Staff', **kwargs):
        """Create a new user"""
        user = cls(
            username=username,
            email=email,
            role=role,
            **kwargs
        )
        user.set_password(password)
        return user
    
    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = naive_utc_now()
    
    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'role_display': self.role_display(),
            'full_name': self.full_name,
            'phone': self.phone,
            'department': self.department,
            'is_active': self.is_active,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'permissions': self.get_permissions_summary()
        }
