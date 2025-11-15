#!/usr/bin/env python3
"""
Local Development Data Migration Script
Migrates data from Production MariaDB to Local Development MariaDB
"""

import pymysql
import sys
import json
from datetime import datetime, date
import re

# Database configurations
PRODUCTION_CONFIG = {
    'host': '54.255.136.172',
    'user': 'voucher_user',
    'password': 'VoucherSecure123!',
    'database': 'voucher_db',
    'charset': 'utf8mb4',
    'port': 3306
}

LOCAL_DEV_CONFIG = {
    'host': 'localhost',
    'user': 'voucher_user',
    'password': 'voucher_secure_2024',
    'database': 'voucher_enhanced',
    'charset': 'utf8mb4',
    'port': 3306
}

def connect_production():
    """Connect to Production MariaDB"""
    try:
        conn = pymysql.connect(**PRODUCTION_CONFIG)
        print("✅ Connected to Production database")
        return conn
    except Exception as e:
        print(f"❌ Error connecting to Production: {e}")
        return None

def connect_local():
    """Connect to Local Development MariaDB"""
    try:
        conn = pymysql.connect(**LOCAL_DEV_CONFIG)
        print("✅ Connected to Local Development database")
        return conn
    except Exception as e:
        print(f"❌ Error connecting to Local Dev: {e}")
        return None

def create_tables_if_not_exist(local_conn):
    """Create necessary tables in local database"""
    cursor = local_conn.cursor()
    
    # Create tables based on models_mariadb.py structure
    tables = [
        """
        CREATE TABLE IF NOT EXISTS customers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            first_name VARCHAR(100),
            last_name VARCHAR(100),
            email VARCHAR(255) UNIQUE,
            phone VARCHAR(20),
            address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """,
        
        """
        CREATE TABLE IF NOT EXISTS bookings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            customer_id INT,
            booking_reference VARCHAR(100) UNIQUE,
            quote_id INT,
            quote_number VARCHAR(100),
            quote_status VARCHAR(50),
            invoice_number VARCHAR(100),
            invoice_status VARCHAR(20),
            is_paid BOOLEAN DEFAULT FALSE,
            booking_type VARCHAR(50) NOT NULL,
            status VARCHAR(50) DEFAULT 'draft',
            arrival_date DATE,
            departure_date DATE,
            traveling_period_start DATE,
            traveling_period_end DATE,
            adults INT DEFAULT 0,
            children INT DEFAULT 0,
            infants INT DEFAULT 0,
            total_pax INT DEFAULT 0,
            guest_list TEXT,
            party_name VARCHAR(255),
            party_code VARCHAR(100),
            description TEXT,
            admin_notes TEXT,
            manager_memos TEXT,
            pickup_point VARCHAR(255),
            destination VARCHAR(255),
            pickup_time TIME,
            vehicle_type VARCHAR(100),
            flight_info TEXT,
            daily_services TEXT,
            products TEXT,
            total_amount DECIMAL(10,2) DEFAULT 0.00,
            currency VARCHAR(10) DEFAULT 'THB',
            time_limit DATETIME,
            due_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """,
        
        """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(80) UNIQUE NOT NULL,
            email VARCHAR(120) UNIQUE NOT NULL,
            password_hash VARCHAR(255),
            role VARCHAR(20) DEFAULT 'user',
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """,
        
        """
        CREATE TABLE IF NOT EXISTS quotes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            customer_id INT,
            quote_number VARCHAR(100) UNIQUE,
            status VARCHAR(50) DEFAULT 'draft',
            total_amount DECIMAL(10,2) DEFAULT 0.00,
            currency VARCHAR(10) DEFAULT 'THB',
            valid_until DATE,
            description TEXT,
            terms_conditions TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """,
        
        """
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            action VARCHAR(100),
            description TEXT,
            ip_address VARCHAR(45),
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
    ]
    
    for table_sql in tables:
        try:
            cursor.execute(table_sql)
            print(f"✅ Table created/verified")
        except Exception as e:
            print(f"⚠️  Table creation warning: {e}")
    
    local_conn.commit()
    cursor.close()

def migrate_data_table(production_conn, local_conn, table_name, limit=None):
    """Migrate data from production to local for a specific table"""
    prod_cursor = production_conn.cursor(pymysql.cursors.DictCursor)
    local_cursor = local_conn.cursor()
    
    try:
        # Get data from production
        if limit:
            prod_cursor.execute(f"SELECT * FROM {table_name} ORDER BY id DESC LIMIT {limit}")
        else:
            prod_cursor.execute(f"SELECT * FROM {table_name}")
        
        rows = prod_cursor.fetchall()
        
        if not rows:
            print(f"⚠️  No data found in production {table_name}")
            return 0
        
        # Clear existing data in local
        local_cursor.execute(f"DELETE FROM {table_name}")
        local_cursor.execute(f"ALTER TABLE {table_name} AUTO_INCREMENT = 1")
        
        # Insert data into local
        for row in rows:
            columns = list(row.keys())
            placeholders = ', '.join(['%s'] * len(columns))
            sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
            
            values = []
            for value in row.values():
                if isinstance(value, (datetime, date)):
                    values.append(value)
                elif value is None:
                    values.append(None)
                else:
                    values.append(value)
            
            local_cursor.execute(sql, values)
        
        local_conn.commit()
        count = len(rows)
        print(f"✅ Migrated {count} records to {table_name}")
        return count
        
    except Exception as e:
        print(f"❌ Error migrating {table_name}: {e}")
        local_conn.rollback()
        return 0
    finally:
        prod_cursor.close()
        local_cursor.close()

def main():
    """Main migration function"""
    print("🚀 Starting Local Development Data Migration")
    print("=" * 60)
    
    # Connect to databases
    prod_conn = connect_production()
    if not prod_conn:
        print("❌ Cannot connect to production database")
        return False
    
    local_conn = connect_local()
    if not local_conn:
        print("❌ Cannot connect to local development database")
        return False
    
    try:
        # Create tables
        print("\n📋 Creating/Verifying tables...")
        create_tables_if_not_exist(local_conn)
        
        # Migrate data (limit to recent records for development)
        print("\n📊 Migrating data...")
        
        tables_to_migrate = [
            ('customers', 50),      # Last 50 customers
            ('users', None),        # All users
            ('quotes', 100),        # Last 100 quotes
            ('bookings', 100),      # Last 100 bookings
        ]
        
        total_migrated = 0
        for table_name, limit in tables_to_migrate:
            count = migrate_data_table(prod_conn, local_conn, table_name, limit)
            total_migrated += count
        
        # Add some activity logs for testing
        print("\n📝 Adding test activity logs...")
        local_cursor = local_conn.cursor()
        local_cursor.execute("""
            INSERT INTO activity_logs (user_id, action, description, created_at) VALUES
            (1, 'login', 'ระบบ development login ทดสอบ', NOW()),
            (1, 'view_booking', 'ดูข้อมูล booking สำหรับทดสอบ', NOW()),
            (1, 'create_quote', 'สร้าง quote ใหม่', NOW())
        """)
        local_conn.commit()
        local_cursor.close()
        
        print("\n" + "=" * 60)
        print(f"✅ Migration completed successfully!")
        print(f"📊 Total records migrated: {total_migrated}")
        print(f"🔧 Activity logs: 3 test records added")
        print(f"🌐 Access via Adminer: http://localhost:8080/adminer.php")
        print(f"📝 Database: voucher_enhanced")
        print(f"👤 Username: voucher_user")
        print(f"🔑 Password: voucher_secure_2024")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False
    
    finally:
        prod_conn.close()
        local_conn.close()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)