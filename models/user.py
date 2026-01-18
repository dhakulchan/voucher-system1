from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from extensions import db
from utils.datetime_utils import naive_utc_now
from werkzeug.security import generate_password_hash, check_password_hash
import pyotp
import json

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='Staff')
    is_admin = db.Column(db.Boolean, default=False)
    assigned_counter = db.Column(db.Integer, nullable=True)  # Counter number assigned to this user
    created_at = db.Column(db.DateTime, default=naive_utc_now)
    updated_at = db.Column(db.DateTime, default=naive_utc_now, onupdate=naive_utc_now)
    
    # 2FA fields
    is_2fa_enabled = db.Column(db.Boolean, default=False)
    totp_secret = db.Column(db.String(32), nullable=True)
    backup_codes = db.Column(db.Text, nullable=True)
    
    def set_password(self, password):
        """Set password hash for user"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if provided password matches user's password"""
        return check_password_hash(self.password_hash, password)
    
    # 2FA Methods
    def generate_totp_secret(self):
        """Generate a new TOTP secret for the user"""
        self.totp_secret = pyotp.random_base32()
        return self.totp_secret
    
    def get_totp_uri(self):
        """Get the provisioning URI for QR code generation"""
        if not self.totp_secret:
            self.generate_totp_secret()
        return pyotp.totp.TOTP(self.totp_secret).provisioning_uri(
            name=self.email,
            issuer_name='Dhakul Chan Tour System'
        )
    
    def verify_totp(self, token):
        """Verify a TOTP token"""
        if not self.totp_secret:
            return False
        totp = pyotp.TOTP(self.totp_secret)
        return totp.verify(token, valid_window=1)  # Allow 1 window tolerance
    
    def generate_backup_codes(self, count=8):
        """Generate backup codes for 2FA recovery"""
        import secrets
        codes = [secrets.token_hex(4).upper() for _ in range(count)]
        self.backup_codes = json.dumps(codes)
        return codes
    
    def verify_backup_code(self, code):
        """Verify and consume a backup code"""
        if not self.backup_codes:
            return False
        
        codes = json.loads(self.backup_codes)
        code_upper = code.upper().replace('-', '').replace(' ', '')
        
        for i, stored_code in enumerate(codes):
            if stored_code.replace('-', '').replace(' ', '') == code_upper:
                # Remove used code
                codes.pop(i)
                self.backup_codes = json.dumps(codes)
                from extensions import db
                db.session.commit()
                return True
        
        return False
    
    def get_remaining_backup_codes(self):
        """Get count of remaining backup codes"""
        if not self.backup_codes:
            return 0
        return len(json.loads(self.backup_codes))
    
    def disable_2fa(self):
        """Disable 2FA for the user"""
        self.is_2fa_enabled = False
        self.totp_secret = None
        self.backup_codes = None

    
    # New Permission System Methods
    def get_permissions(self):
        """
        Get effective permissions for user
        Priority: User-specific permissions > Role permissions
        """
        from models.permission import UserPermission, RolePermission
        
        # Check for user-specific permissions first
        user_perms = UserPermission.get_user_permissions(self.id)
        if user_perms:
            return user_perms.permissions
        
        # Fall back to role permissions
        role_perms = RolePermission.get_role_permissions(self.role)
        if role_perms:
            return role_perms.permissions
        
        # Default: no permissions
        return {}
    
    def has_permission(self, module, action):
        """
        Check if user has specific permission
        
        Args:
            module: Module name (e.g., 'bookings', 'customers', 'users')
            action: Action name (e.g., 'view', 'create', 'edit', 'delete', 'view_all', 'view_own')
        
        Returns:
            bool: True if user has permission
        """
        from models.permission import UserPermission, RolePermission
        
        # Check user-specific permissions first
        user_perms = UserPermission.get_user_permissions(self.id)
        if user_perms:
            return user_perms.get_permission(module, action)
        
        # Fall back to role permissions
        role_perms = RolePermission.get_role_permissions(self.role)
        if role_perms:
            return role_perms.get_permission(module, action)
        
        return False
    
    def has_sidebar_menu(self, menu_name):
        """Check if user has access to sidebar menu"""
        from models.permission import UserPermission, RolePermission
        
        # Check user-specific permissions first
        user_perms = UserPermission.get_user_permissions(self.id)
        if user_perms:
            return user_perms.has_sidebar_menu(menu_name)
        
        # Fall back to role permissions
        role_perms = RolePermission.get_role_permissions(self.role)
        if role_perms:
            return role_perms.has_sidebar_menu(menu_name)
        
        return False
    
    def get_sidebar_menus(self):
        """Get list of sidebar menus user has access to"""
        permissions = self.get_permissions()
        return permissions.get('sidebar_menus', [])
    
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
    
    # Legacy/Backward Compatible Permission Methods
    def can_manage_quotes(self):
        return self.has_permission('quotes', 'edit') or self.role in ['Administrator', 'Operation']
    
    def can_view_financial_data(self):
        return self.has_permission('financial', 'view') or self.role == 'Administrator'
    
    def can_access_admin_notes(self):
        return self.has_permission('admin_notes', 'view') or self.role in ['Administrator', 'Operation']
    
    def is_administrator(self):
        return self.role == 'Administrator'
    
    def is_operation_staff(self):
        return self.role == 'Operation'
    
    def __repr__(self):
        return f'<User {self.username} ({self.role})>'
    
    def has_role(self, *roles):
        """Check if user has any of the specified roles"""
        return self.role in roles
    
    def is_role(self, role):
        """Check if user has specific role"""
        return self.role == role
    
    # Enhanced Permission Methods
    def can_access_admin(self):
        """Check if user can access admin features"""
        return self.has_permission('users', 'view') or self.role in ['Administrator', 'Operation']
    
    def can_manage_users(self):
        """Check if user can manage other users"""
        return self.has_permission('users', 'edit') or self.role == 'Administrator'
    
    def can_create_admin(self):
        """Check if user can create admin accounts"""
        return self.role == 'Administrator'
    
    def can_edit_all_bookings(self):
        """Check if user can edit any booking"""
        return self.has_permission('bookings', 'edit_all') or self.role in ['Administrator', 'Operation']
    
    def can_edit_own_bookings(self):
        """Check if user can edit their own bookings"""
        return self.has_permission('bookings', 'edit_own') or self.role in ['Internship', 'Freelance', 'Administrator', 'Operation', 'Staff']
    
    def can_view_own_data_only(self):
        """Check if user can only view their own data"""
        perms = self.get_permissions()
        bookings = perms.get('bookings', {})
        # If can't view all but can view own, it's own-data-only
        return not bookings.get('view_all', False) and bookings.get('view_own', False)
    
    def can_delete_bookings(self):
        """Check if user can delete bookings"""
        return self.has_permission('bookings', 'delete') or self.role in ['Administrator', 'Operation']
    
    def can_view_financial_data(self):
        """Check if user can view financial information"""
        return self.has_permission('financial', 'view') or self.role in ['Administrator', 'Operation']
    
    def can_manage_quotes(self):
        """Check if user can manage quotes"""
        return self.has_permission('quotes', 'edit') or self.role in ['Administrator', 'Operation']
    
    def can_access_admin_notes(self):
        """Check if user can access admin notes"""
        return self.has_permission('admin_notes', 'view') or self.role == 'Administrator'
    
    def can_access_manager_memos(self):
        """Check if user can access manager memos"""
        return self.role in ['Administrator', 'Operation']
    
    def can_mark_as_paid(self):
        """Check if user can mark bookings as paid - Admin and Manager only"""
        return self.role in ['Administrator', 'Manager']
    
    def can_export_data(self):
        """Check if user can export data"""
        return self.has_permission('reports', 'export') or self.role in ['Administrator', 'Operation']
    
    def can_configure_system(self):
        """Check if user can configure system settings"""
        return self.has_permission('system', 'configure') or self.role == 'Administrator'
    
    def can_manage_permissions(self):
        """Check if user can manage role and user permissions"""
        return self.has_permission('users', 'manage_permissions') or self.role == 'Administrator'
    
    def role_display(self):
        """Get display name for role"""
        role_mapping = {
            'Administrator': 'System Administrator',
            'Operation': 'Operations Manager',
            'Manager': 'Manager',
            'Staff': 'Staff Member',
            'Internship': 'Internship',
            'Freelance': 'Freelance'
        }
        return role_mapping.get(self.role, self.role)
    
    def role_badge_class(self):
        """Get Bootstrap badge class for role"""
        role_classes = {
            'Administrator': 'bg-danger',
            'Operation': 'bg-warning',
            'Manager': 'bg-info',
            'Staff': 'bg-primary',
            'Internship': 'bg-success',
            'Freelance': 'bg-secondary'
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
        return ['Administrator', 'Operation', 'Manager', 'Staff', 'Internship', 'Freelance']
    
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
