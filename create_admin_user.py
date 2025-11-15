#!/usr/bin/env python3
"""
Create Admin User for Local Development
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from werkzeug.security import generate_password_hash
import pymysql
from datetime import datetime

# Database config
LOCAL_DEV_CONFIG = {
    'host': 'localhost',
    'user': 'voucher_user',
    'password': 'voucher_secure_2024',
    'database': 'voucher_enhanced',
    'charset': 'utf8mb4',
    'port': 3306
}

def connect_db():
    """Connect to database"""
    try:
        conn = pymysql.connect(**LOCAL_DEV_CONFIG)
        return conn
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return None

def create_admin_user():
    """Create admin user with proper password hash"""
    conn = connect_db()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Delete existing admin user
        cursor.execute("DELETE FROM users WHERE username = 'admin'")
        
        # Create new admin user with Flask-compatible password hash
        username = 'admin'
        email = 'admin@dhakulchan.com'
        password = 'admin123'  # Simple password for development
        password_hash = generate_password_hash(password)
        role = 'admin'
        is_admin = True
        now = datetime.now()
        
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, role, is_admin, created_at, updated_at) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (username, email, password_hash, role, is_admin, now, now))
        
        # Also create a simple user for testing
        cursor.execute("DELETE FROM users WHERE username IN ('user', 'manager')")
        
        # Create user account
        user_password_hash = generate_password_hash('user123')
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, role, is_admin, created_at, updated_at) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, ('user', 'user@dhakulchan.com', user_password_hash, 'user', False, now, now))
        
        # Create manager account
        manager_password_hash = generate_password_hash('manager123')
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, role, is_admin, created_at, updated_at) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, ('manager', 'manager@dhakulchan.com', manager_password_hash, 'manager', False, now, now))
        
        conn.commit()
        
        print("✅ Users created successfully!")
        print("\n📋 Login Credentials:")
        print("   👤 Admin:")
        print(f"      Username: {username}")
        print(f"      Password: {password}")
        print(f"      Email: {email}")
        print("   👤 Manager:")
        print("      Username: manager")
        print("      Password: manager123")
        print("   👤 User:")
        print("      Username: user") 
        print("      Password: user123")
        print(f"\n🌐 Login URL: http://127.0.0.1:5001/auth/login")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

def verify_login():
    """Verify login functionality"""
    conn = connect_db()
    if not conn:
        return False
    
    try:
        from werkzeug.security import check_password_hash
        
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT username, password_hash FROM users WHERE username = 'admin'")
        user = cursor.fetchone()
        
        if user:
            # Test password verification
            if check_password_hash(user['password_hash'], 'admin123'):
                print("✅ Password verification works correctly")
                return True
            else:
                print("❌ Password verification failed")
                return False
        else:
            print("❌ Admin user not found")
            return False
            
    except Exception as e:
        print(f"❌ Verification error: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def main():
    print("🔐 Creating Admin User for Local Development")
    print("=" * 50)
    
    if create_admin_user():
        if verify_login():
            print("\n🎉 Setup completed successfully!")
            print("💡 You can now login to the application")
        else:
            print("\n⚠️  User created but verification failed")
    else:
        print("\n❌ Failed to create admin user")

if __name__ == "__main__":
    main()