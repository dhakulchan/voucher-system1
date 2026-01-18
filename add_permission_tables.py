#!/usr/bin/env python3
"""
Add permission management tables to the database
- role_permissions: Store default permissions for each role
- user_permissions: Store custom permissions for individual users
"""

import pymysql
from datetime import datetime

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'voucher_user',
    'password': 'voucher_secure_2024',
    'database': 'voucher_enhanced',
    'port': 3306,
    'charset': 'utf8mb4'
}

def create_permission_tables():
    """Create role_permissions and user_permissions tables"""
    
    connection = pymysql.connect(**DB_CONFIG)
    
    try:
        with connection.cursor() as cursor:
            # Create role_permissions table
            print("Creating role_permissions table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS role_permissions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    role VARCHAR(50) NOT NULL UNIQUE,
                    permissions JSON NOT NULL,
                    description TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_role (role)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Create user_permissions table
            print("Creating user_permissions table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_permissions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    permissions JSON NOT NULL,
                    notes TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE KEY unique_user (user_id),
                    INDEX idx_user_id (user_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            connection.commit()
            print("✓ Tables created successfully")
            
            # Insert default role permissions
            print("\nInserting default role permissions...")
            
            default_permissions = [
                {
                    'role': 'Administrator',
                    'permissions': {
                        'sidebar_menus': ['dashboard', 'queue_management', 'bookings', 'customers', 'quotes', 'vouchers', 'suppliers', 'invoices', 'reports', 'task_list', 'user_management', 'system_settings'],
                        'bookings': {'view_all': True, 'view_own': True, 'create': True, 'edit_all': True, 'edit_own': True, 'delete': True},
                        'customers': {'view_all': True, 'view_own': True, 'create': True, 'edit_all': True, 'edit_own': True, 'delete': True},
                        'quotes': {'view': True, 'create': True, 'edit': True, 'delete': True},
                        'vouchers': {'view': True, 'create': True, 'edit': True, 'delete': True},
                        'suppliers': {'view': True, 'create': True, 'edit': True, 'delete': True},
                        'invoices': {'view': True, 'create': True, 'edit': True, 'delete': True},
                        'reports': {'view': True, 'export': True},
                        'users': {'view': True, 'create': True, 'edit': True, 'delete': True, 'manage_roles': True, 'manage_permissions': True},
                        'financial': {'view': True, 'edit': True},
                        'admin_notes': {'view': True, 'edit': True},
                        'system': {'configure': True}
                    },
                    'description': 'Full system access'
                },
                {
                    'role': 'Operation',
                    'permissions': {
                        'sidebar_menus': ['dashboard', 'queue_management', 'bookings', 'customers', 'quotes', 'vouchers', 'suppliers', 'invoices', 'reports', 'task_list'],
                        'bookings': {'view_all': True, 'view_own': True, 'create': True, 'edit_all': True, 'edit_own': True, 'delete': True},
                        'customers': {'view_all': True, 'view_own': True, 'create': True, 'edit_all': True, 'edit_own': True, 'delete': True},
                        'quotes': {'view': True, 'create': True, 'edit': True, 'delete': False},
                        'vouchers': {'view': True, 'create': True, 'edit': True, 'delete': False},
                        'suppliers': {'view': True, 'create': True, 'edit': True, 'delete': False},
                        'invoices': {'view': True, 'create': True, 'edit': True, 'delete': False},
                        'reports': {'view': True, 'export': True},
                        'users': {'view': False, 'create': False, 'edit': False, 'delete': False, 'manage_roles': False, 'manage_permissions': False},
                        'financial': {'view': True, 'edit': False},
                        'admin_notes': {'view': False, 'edit': False},
                        'system': {'configure': False}
                    },
                    'description': 'Operations management access'
                },
                {
                    'role': 'Manager',
                    'permissions': {
                        'sidebar_menus': ['dashboard', 'queue_management', 'bookings', 'customers', 'quotes', 'vouchers', 'reports', 'task_list'],
                        'bookings': {'view_all': True, 'view_own': True, 'create': True, 'edit_all': False, 'edit_own': True, 'delete': False},
                        'customers': {'view_all': True, 'view_own': True, 'create': True, 'edit_all': False, 'edit_own': True, 'delete': False},
                        'quotes': {'view': True, 'create': True, 'edit': True, 'delete': False},
                        'vouchers': {'view': True, 'create': False, 'edit': False, 'delete': False},
                        'suppliers': {'view': False, 'create': False, 'edit': False, 'delete': False},
                        'invoices': {'view': True, 'create': False, 'edit': False, 'delete': False},
                        'reports': {'view': True, 'export': False},
                        'users': {'view': False, 'create': False, 'edit': False, 'delete': False, 'manage_roles': False, 'manage_permissions': False},
                        'financial': {'view': False, 'edit': False},
                        'admin_notes': {'view': False, 'edit': False},
                        'system': {'configure': False}
                    },
                    'description': 'Manager level access'
                },
                {
                    'role': 'Staff',
                    'permissions': {
                        'sidebar_menus': ['dashboard', 'queue_management', 'bookings', 'customers', 'vouchers', 'task_list'],
                        'bookings': {'view_all': True, 'view_own': True, 'create': True, 'edit_all': False, 'edit_own': True, 'delete': False},
                        'customers': {'view_all': True, 'view_own': True, 'create': True, 'edit_all': False, 'edit_own': True, 'delete': False},
                        'quotes': {'view': True, 'create': False, 'edit': False, 'delete': False},
                        'vouchers': {'view': True, 'create': True, 'edit': False, 'delete': False},
                        'suppliers': {'view': False, 'create': False, 'edit': False, 'delete': False},
                        'invoices': {'view': False, 'create': False, 'edit': False, 'delete': False},
                        'reports': {'view': False, 'export': False},
                        'users': {'view': False, 'create': False, 'edit': False, 'delete': False, 'manage_roles': False, 'manage_permissions': False},
                        'financial': {'view': False, 'edit': False},
                        'admin_notes': {'view': False, 'edit': False},
                        'system': {'configure': False}
                    },
                    'description': 'Basic staff access'
                },
                {
                    'role': 'Internship',
                    'permissions': {
                        'sidebar_menus': ['dashboard', 'queue_management', 'bookings', 'customers', 'task_list'],
                        'bookings': {'view_all': False, 'view_own': True, 'create': True, 'edit_all': False, 'edit_own': True, 'delete': False},
                        'customers': {'view_all': False, 'view_own': True, 'create': True, 'edit_all': False, 'edit_own': True, 'delete': False},
                        'quotes': {'view': False, 'create': False, 'edit': False, 'delete': False},
                        'vouchers': {'view': False, 'create': False, 'edit': False, 'delete': False},
                        'suppliers': {'view': False, 'create': False, 'edit': False, 'delete': False},
                        'invoices': {'view': False, 'create': False, 'edit': False, 'delete': False},
                        'reports': {'view': False, 'export': False},
                        'users': {'view': False, 'create': False, 'edit': False, 'delete': False, 'manage_roles': False, 'manage_permissions': False},
                        'financial': {'view': False, 'edit': False},
                        'admin_notes': {'view': False, 'edit': False},
                        'system': {'configure': False}
                    },
                    'description': 'Internship - Own data only'
                },
                {
                    'role': 'Freelance',
                    'permissions': {
                        'sidebar_menus': ['dashboard', 'queue_management', 'bookings', 'customers', 'task_list'],
                        'bookings': {'view_all': False, 'view_own': True, 'create': True, 'edit_all': False, 'edit_own': True, 'delete': False},
                        'customers': {'view_all': False, 'view_own': True, 'create': True, 'edit_all': False, 'edit_own': True, 'delete': False},
                        'quotes': {'view': False, 'create': False, 'edit': False, 'delete': False},
                        'vouchers': {'view': False, 'create': False, 'edit': False, 'delete': False},
                        'suppliers': {'view': False, 'create': False, 'edit': False, 'delete': False},
                        'invoices': {'view': False, 'create': False, 'edit': False, 'delete': False},
                        'reports': {'view': False, 'export': False},
                        'users': {'view': False, 'create': False, 'edit': False, 'delete': False, 'manage_roles': False, 'manage_permissions': False},
                        'financial': {'view': False, 'edit': False},
                        'admin_notes': {'view': False, 'edit': False},
                        'system': {'configure': False}
                    },
                    'description': 'Freelance - Own data only'
                }
            ]
            
            for perm in default_permissions:
                try:
                    import json
                    cursor.execute("""
                        INSERT INTO role_permissions (role, permissions, description)
                        VALUES (%s, %s, %s)
                        ON DUPLICATE KEY UPDATE 
                            permissions = VALUES(permissions),
                            description = VALUES(description)
                    """, (perm['role'], json.dumps(perm['permissions']), perm['description']))
                    print(f"  ✓ {perm['role']} permissions configured")
                except Exception as e:
                    print(f"  ✗ Error with {perm['role']}: {e}")
            
            connection.commit()
            print("\n✓ Default permissions inserted successfully")
            
    except Exception as e:
        print(f"✗ Error: {e}")
        connection.rollback()
        raise
    finally:
        connection.close()

if __name__ == '__main__':
    print("=" * 60)
    print("Creating Permission Management Tables")
    print("=" * 60)
    create_permission_tables()
    print("\n" + "=" * 60)
    print("Migration completed successfully!")
    print("=" * 60)
