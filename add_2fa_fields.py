#!/usr/bin/env python3
"""
Add 2FA fields to users table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

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

def add_2fa_fields():
    """Add 2FA fields to users table"""
    conn = connect_db()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Check if columns exist
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = 'voucher_enhanced' 
            AND TABLE_NAME = 'users' 
            AND COLUMN_NAME IN ('is_2fa_enabled', 'totp_secret', 'backup_codes')
        """)
        existing_columns = [row[0] for row in cursor.fetchall()]
        
        # Add is_2fa_enabled column if not exists
        if 'is_2fa_enabled' not in existing_columns:
            print("➕ Adding is_2fa_enabled column...")
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN is_2fa_enabled BOOLEAN DEFAULT FALSE
            """)
            print("✅ Added is_2fa_enabled column")
        else:
            print("✓ is_2fa_enabled column already exists")
        
        # Add totp_secret column if not exists
        if 'totp_secret' not in existing_columns:
            print("➕ Adding totp_secret column...")
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN totp_secret VARCHAR(32) DEFAULT NULL
            """)
            print("✅ Added totp_secret column")
        else:
            print("✓ totp_secret column already exists")
        
        # Add backup_codes column if not exists (JSON or TEXT)
        if 'backup_codes' not in existing_columns:
            print("➕ Adding backup_codes column...")
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN backup_codes TEXT DEFAULT NULL
            """)
            print("✅ Added backup_codes column")
        else:
            print("✓ backup_codes column already exists")
        
        conn.commit()
        
        print("\n✅ 2FA fields migration completed successfully!")
        print("📋 Added fields:")
        print("   - is_2fa_enabled: BOOLEAN (default: FALSE)")
        print("   - totp_secret: VARCHAR(32) (stores encrypted TOTP secret)")
        print("   - backup_codes: TEXT (stores backup recovery codes)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error adding 2FA fields: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

def main():
    print("=" * 60)
    print("Add 2FA Fields to Users Table")
    print("=" * 60)
    
    if add_2fa_fields():
        print("\n🎉 Migration completed successfully!")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
