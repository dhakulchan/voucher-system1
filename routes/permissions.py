"""
Routes for managing user roles and permissions
Administrator can configure role-level permissions and user-specific permissions
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from functools import wraps
from extensions import db
from models.user import User
from models.permission import RolePermission, UserPermission
import json

permissions_bp = Blueprint('permissions', __name__, url_prefix='/admin/permissions')

def admin_required(f):
    """Decorator to require administrator access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.can_manage_permissions():
            flash('คุณไม่มีสิทธิ์เข้าถึงหน้านี้', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function

@permissions_bp.route('/')
@login_required
@admin_required
def index():
    """Permission management dashboard"""
    roles = RolePermission.get_all_roles()
    users = User.query.order_by(User.username).all()
    
    return render_template('admin/permissions/index.html',
                         roles=roles,
                         users=users)

@permissions_bp.route('/role/<string:role>')
@login_required
@admin_required
def view_role(role):
    """View and edit role permissions"""
    role_perms = RolePermission.get_role_permissions(role)
    
    if not role_perms:
        flash(f'ไม่พบสิทธิ์สำหรับ Role: {role}', 'warning')
        return redirect(url_for('permissions.index'))
    
    # Get list of users with this role
    users_with_role = User.query.filter_by(role=role).all()
    
    return render_template('admin/permissions/role_edit.html',
                         role=role,
                         role_perms=role_perms,
                         users_with_role=users_with_role)

@permissions_bp.route('/role/<string:role>/update', methods=['POST'])
@login_required
@admin_required
def update_role(role):
    """Update role permissions"""
    try:
        role_perms = RolePermission.get_role_permissions(role)
        
        if not role_perms:
            return jsonify({'success': False, 'message': 'Role not found'}), 404
        
        # Get permissions from form
        permissions_json = request.form.get('permissions')
        if permissions_json:
            permissions = json.loads(permissions_json)
        else:
            # Build permissions from individual form fields
            permissions = {
                'sidebar_menus': request.form.getlist('sidebar_menus[]'),
                'bookings': {
                    'view_all': request.form.get('bookings_view_all') == 'true',
                    'view_own': request.form.get('bookings_view_own') == 'true',
                    'create': request.form.get('bookings_create') == 'true',
                    'edit_all': request.form.get('bookings_edit_all') == 'true',
                    'edit_own': request.form.get('bookings_edit_own') == 'true',
                    'delete': request.form.get('bookings_delete') == 'true',
                },
                'customers': {
                    'view_all': request.form.get('customers_view_all') == 'true',
                    'view_own': request.form.get('customers_view_own') == 'true',
                    'create': request.form.get('customers_create') == 'true',
                    'edit_all': request.form.get('customers_edit_all') == 'true',
                    'edit_own': request.form.get('customers_edit_own') == 'true',
                    'delete': request.form.get('customers_delete') == 'true',
                },
                'quotes': {
                    'view': request.form.get('quotes_view') == 'true',
                    'create': request.form.get('quotes_create') == 'true',
                    'edit': request.form.get('quotes_edit') == 'true',
                    'delete': request.form.get('quotes_delete') == 'true',
                },
                'vouchers': {
                    'view': request.form.get('vouchers_view') == 'true',
                    'create': request.form.get('vouchers_create') == 'true',
                    'edit': request.form.get('vouchers_edit') == 'true',
                    'delete': request.form.get('vouchers_delete') == 'true',
                },
                'suppliers': {
                    'view': request.form.get('suppliers_view') == 'true',
                    'create': request.form.get('suppliers_create') == 'true',
                    'edit': request.form.get('suppliers_edit') == 'true',
                    'delete': request.form.get('suppliers_delete') == 'true',
                },
                'invoices': {
                    'view': request.form.get('invoices_view') == 'true',
                    'create': request.form.get('invoices_create') == 'true',
                    'edit': request.form.get('invoices_edit') == 'true',
                    'delete': request.form.get('invoices_delete') == 'true',
                },
                'reports': {
                    'view': request.form.get('reports_view') == 'true',
                    'export': request.form.get('reports_export') == 'true',
                },
                'users': {
                    'view': request.form.get('users_view') == 'true',
                    'create': request.form.get('users_create') == 'true',
                    'edit': request.form.get('users_edit') == 'true',
                    'delete': request.form.get('users_delete') == 'true',
                    'manage_roles': request.form.get('users_manage_roles') == 'true',
                    'manage_permissions': request.form.get('users_manage_permissions') == 'true',
                },
                'financial': {
                    'view': request.form.get('financial_view') == 'true',
                    'edit': request.form.get('financial_edit') == 'true',
                },
                'admin_notes': {
                    'view': request.form.get('admin_notes_view') == 'true',
                    'edit': request.form.get('admin_notes_edit') == 'true',
                },
                'system': {
                    'configure': request.form.get('system_configure') == 'true',
                }
            }
        
        role_perms.permissions = permissions
        role_perms.description = request.form.get('description', role_perms.description)
        
        db.session.commit()
        
        flash(f'อัปเดตสิทธิ์สำหรับ Role: {role} สำเร็จ', 'success')
        return jsonify({'success': True, 'message': 'Role permissions updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@permissions_bp.route('/user/<int:user_id>')
@login_required
@admin_required
def view_user(user_id):
    """View and edit user-specific permissions"""
    user = User.query.get_or_404(user_id)
    user_perms = UserPermission.get_user_permissions(user_id)
    role_perms = RolePermission.get_role_permissions(user.role)
    
    # Get current effective permissions
    if user_perms:
        current_perms = user_perms.permissions
    else:
        current_perms = role_perms.permissions if role_perms else {}
    
    return render_template('admin/permissions/user_edit.html',
                         user=user,
                         user_perms=user_perms,
                         role_perms=role_perms,
                         current_perms=current_perms)

@permissions_bp.route('/user/<int:user_id>/update', methods=['POST'])
@login_required
@admin_required
def update_user(user_id):
    """Update user-specific permissions"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Get permissions from form
        permissions_json = request.form.get('permissions')
        if permissions_json:
            permissions = json.loads(permissions_json)
        else:
            # Build permissions from individual form fields
            permissions = {
                'sidebar_menus': request.form.getlist('sidebar_menus[]'),
                'bookings': {
                    'view_all': request.form.get('bookings_view_all') == 'true',
                    'view_own': request.form.get('bookings_view_own') == 'true',
                    'create': request.form.get('bookings_create') == 'true',
                    'edit_all': request.form.get('bookings_edit_all') == 'true',
                    'edit_own': request.form.get('bookings_edit_own') == 'true',
                    'delete': request.form.get('bookings_delete') == 'true',
                },
                'customers': {
                    'view_all': request.form.get('customers_view_all') == 'true',
                    'view_own': request.form.get('customers_view_own') == 'true',
                    'create': request.form.get('customers_create') == 'true',
                    'edit_all': request.form.get('customers_edit_all') == 'true',
                    'edit_own': request.form.get('customers_edit_own') == 'true',
                    'delete': request.form.get('customers_delete') == 'true',
                },
                'quotes': {
                    'view': request.form.get('quotes_view') == 'true',
                    'create': request.form.get('quotes_create') == 'true',
                    'edit': request.form.get('quotes_edit') == 'true',
                    'delete': request.form.get('quotes_delete') == 'true',
                },
                'vouchers': {
                    'view': request.form.get('vouchers_view') == 'true',
                    'create': request.form.get('vouchers_create') == 'true',
                    'edit': request.form.get('vouchers_edit') == 'true',
                    'delete': request.form.get('vouchers_delete') == 'true',
                },
                'suppliers': {
                    'view': request.form.get('suppliers_view') == 'true',
                    'create': request.form.get('suppliers_create') == 'true',
                    'edit': request.form.get('suppliers_edit') == 'true',
                    'delete': request.form.get('suppliers_delete') == 'true',
                },
                'invoices': {
                    'view': request.form.get('invoices_view') == 'true',
                    'create': request.form.get('invoices_create') == 'true',
                    'edit': request.form.get('invoices_edit') == 'true',
                    'delete': request.form.get('invoices_delete') == 'true',
                },
                'reports': {
                    'view': request.form.get('reports_view') == 'true',
                    'export': request.form.get('reports_export') == 'true',
                },
                'users': {
                    'view': request.form.get('users_view') == 'true',
                    'create': request.form.get('users_create') == 'true',
                    'edit': request.form.get('users_edit') == 'true',
                    'delete': request.form.get('users_delete') == 'true',
                    'manage_roles': request.form.get('users_manage_roles') == 'true',
                    'manage_permissions': request.form.get('users_manage_permissions') == 'true',
                },
                'financial': {
                    'view': request.form.get('financial_view') == 'true',
                    'edit': request.form.get('financial_edit') == 'true',
                },
                'admin_notes': {
                    'view': request.form.get('admin_notes_view') == 'true',
                    'edit': request.form.get('admin_notes_edit') == 'true',
                },
                'system': {
                    'configure': request.form.get('system_configure') == 'true',
                }
            }
        
        # Check if user already has custom permissions
        user_perms = UserPermission.get_user_permissions(user_id)
        
        if user_perms:
            user_perms.permissions = permissions
            user_perms.notes = request.form.get('notes', user_perms.notes)
        else:
            user_perms = UserPermission(
                user_id=user_id,
                permissions=permissions,
                notes=request.form.get('notes', '')
            )
            db.session.add(user_perms)
        
        db.session.commit()
        
        flash(f'อัปเดตสิทธิ์สำหรับผู้ใช้: {user.username} สำเร็จ', 'success')
        return jsonify({'success': True, 'message': 'User permissions updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@permissions_bp.route('/user/<int:user_id>/reset', methods=['POST'])
@login_required
@admin_required
def reset_user_permissions(user_id):
    """Reset user permissions to role defaults"""
    try:
        user_perms = UserPermission.get_user_permissions(user_id)
        
        if user_perms:
            db.session.delete(user_perms)
            db.session.commit()
            flash('รีเซ็ตสิทธิ์ผู้ใช้เป็นค่าเริ่มต้นของ Role สำเร็จ', 'success')
        else:
            flash('ผู้ใช้นี้ไม่มีสิทธิ์แบบกำหนดเอง', 'info')
        
        return jsonify({'success': True, 'message': 'User permissions reset to role defaults'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@permissions_bp.route('/api/role/<string:role>')
@login_required
@admin_required
def api_get_role(role):
    """API endpoint to get role permissions as JSON"""
    role_perms = RolePermission.get_role_permissions(role)
    
    if not role_perms:
        return jsonify({'success': False, 'message': 'Role not found'}), 404
    
    return jsonify({
        'success': True,
        'data': role_perms.to_dict()
    })

@permissions_bp.route('/api/user/<int:user_id>')
@login_required
@admin_required
def api_get_user(user_id):
    """API endpoint to get user permissions as JSON"""
    user = User.query.get_or_404(user_id)
    user_perms = UserPermission.get_user_permissions(user_id)
    role_perms = RolePermission.get_role_permissions(user.role)
    
    return jsonify({
        'success': True,
        'data': {
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role
            },
            'custom_permissions': user_perms.to_dict() if user_perms else None,
            'role_permissions': role_perms.to_dict() if role_perms else None,
            'effective_permissions': user.get_permissions()
        }
    })
