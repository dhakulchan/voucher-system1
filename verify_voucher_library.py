#!/usr/bin/env python3
"""
Verification script for Voucher Library feature
Checks if table exists and folder is ready
"""

import pymysql
import os

def verify_setup():
    """Verify Voucher Library setup"""
    
    print("🔍 Voucher Library Setup Verification\n")
    print("=" * 50)
    
    # 1. Check database table
    print("\n1️⃣ Checking database table...")
    try:
        connection = pymysql.connect(
            host='localhost',
            user='voucher_user',
            password='voucher_secure_2024',
            database='voucher_db',
            charset='utf8mb4'
        )
        cursor = connection.cursor()
        
        # Check if table exists
        cursor.execute("SHOW TABLES LIKE 'voucher_albums'")
        result = cursor.fetchone()
        
        if result:
            print("   ✅ Table 'voucher_albums' exists")
            
            # Check table structure
            cursor.execute("DESCRIBE voucher_albums")
            columns = cursor.fetchall()
            print("\n   📋 Table structure:")
            for col in columns:
                print(f"      - {col[0]} ({col[1]})")
            
            # Check record count
            cursor.execute("SELECT COUNT(*) FROM voucher_albums")
            count = cursor.fetchone()[0]
            print(f"\n   📊 Current records: {count}")
        else:
            print("   ❌ Table 'voucher_albums' does NOT exist")
            print("   ⚠️  Run: mysql -u root -p voucher_db < create_voucher_albums_table.sql")
        
        cursor.close()
        connection.close()
        
    except pymysql.Error as e:
        print(f"   ❌ Database connection failed: {e}")
        print("   ℹ️  This is expected if running locally without database access")
    
    # 2. Check upload folder
    print("\n2️⃣ Checking upload folder...")
    upload_folder = 'static/uploads/voucher_albums'
    
    if os.path.exists(upload_folder):
        print(f"   ✅ Folder exists: {upload_folder}")
        
        # Check permissions
        if os.access(upload_folder, os.W_OK):
            print("   ✅ Folder is writable")
        else:
            print("   ⚠️  Folder is NOT writable")
            print("   💡 Run: chmod 755 static/uploads/voucher_albums")
        
        # Count files
        files = [f for f in os.listdir(upload_folder) if os.path.isfile(os.path.join(upload_folder, f))]
        print(f"   📁 Files in folder: {len(files)}")
    else:
        print(f"   ⚠️  Folder does NOT exist: {upload_folder}")
        print("   ℹ️  It will be created automatically on first upload")
    
    # 3. Check required files
    print("\n3️⃣ Checking required files...")
    required_files = [
        'models/voucher_album.py',
        'routes/voucher_library.py',
        'templates/voucher_library/list.html'
    ]
    
    all_exist = True
    for file in required_files:
        if os.path.exists(file):
            print(f"   ✅ {file}")
        else:
            print(f"   ❌ {file} - MISSING!")
            all_exist = False
    
    # 4. Check app.py registration
    print("\n4️⃣ Checking app.py registration...")
    try:
        with open('app.py', 'r') as f:
            content = f.read()
            
        if 'from routes.voucher_library import voucher_library_bp' in content:
            print("   ✅ Blueprint imported")
        else:
            print("   ❌ Blueprint NOT imported")
        
        if "app.register_blueprint(voucher_library_bp, url_prefix='/voucher-library')" in content:
            print("   ✅ Blueprint registered")
        else:
            print("   ❌ Blueprint NOT registered")
            
    except FileNotFoundError:
        print("   ❌ app.py not found")
    
    # 5. Check base.html menu
    print("\n5️⃣ Checking sidebar menu...")
    try:
        with open('templates/base.html', 'r') as f:
            content = f.read()
        
        if 'voucher_library.list_albums' in content:
            print("   ✅ Voucher Library menu item added")
        else:
            print("   ❌ Menu item NOT added to sidebar")
            
    except FileNotFoundError:
        print("   ❌ templates/base.html not found")
    
    # Summary
    print("\n" + "=" * 50)
    print("\n📝 Summary:")
    print("   - If database table check failed, run the SQL migration")
    print("   - If all files exist, the feature is ready to use")
    print("   - Restart the application after database setup")
    print("\n✨ Access at: http://localhost:5000/voucher-library/list")
    print("=" * 50 + "\n")

if __name__ == '__main__':
    verify_setup()
