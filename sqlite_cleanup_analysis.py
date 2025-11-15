"""
SQLite Cleanup Analysis Report
ศิถึวิเคราะห์การทำความสะอาด SQLite จากระบบหลัง migrate ไป MariaDB
"""

import os
import glob
import re

def analyze_sqlite_usage():
    print("🔍 SQLite Usage Analysis Report")
    print("=" * 60)
    
    # 1. Check SQLite files
    print("\n📁 1. SQLite Files Found:")
    sqlite_files = glob.glob("*.db") + glob.glob("*.db.*")
    for file in sqlite_files:
        size = os.path.getsize(file)
        print(f"   {file:<45} {size:>10,} bytes")
    
    # 2. Check Python files with SQLite imports
    print("\n🐍 2. Python Files with SQLite Imports:")
    python_files = glob.glob("**/*.py", recursive=True)
    sqlite_imports = []
    
    for file in python_files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'import sqlite3' in content or 'from sqlite3' in content:
                    sqlite_imports.append(file)
                    print(f"   {file}")
        except:
            pass
    
    # 3. Check files with direct SQLite connections
    print("\n🔗 3. Files with Direct SQLite Connections:")
    direct_connections = []
    
    for file in python_files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'sqlite3.connect(' in content:
                    direct_connections.append(file)
                    print(f"   {file}")
                    
                    # Find specific line numbers
                    lines = content.split('\n')
                    for i, line in enumerate(lines, 1):
                        if 'sqlite3.connect(' in line:
                            print(f"      Line {i}: {line.strip()}")
        except:
            pass
    
    # 4. Check files referencing app.db
    print("\n💾 4. Files Referencing app.db:")
    app_db_refs = []
    
    for file in python_files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'app.db' in content:
                    app_db_refs.append(file)
                    print(f"   {file}")
                    
                    # Find specific line numbers
                    lines = content.split('\n')
                    for i, line in enumerate(lines, 1):
                        if 'app.db' in line and not line.strip().startswith('#'):
                            print(f"      Line {i}: {line.strip()}")
        except:
            pass
    
    # 5. Summary and recommendations
    print("\n📊 5. Summary:")
    print(f"   SQLite files found: {len(sqlite_files)}")
    print(f"   Python files with sqlite3 imports: {len(sqlite_imports)}")
    print(f"   Files with direct SQLite connections: {len(direct_connections)}")
    print(f"   Files referencing app.db: {len(app_db_refs)}")
    
    total_db_size = sum(os.path.getsize(f) for f in sqlite_files if os.path.exists(f))
    print(f"   Total SQLite files size: {total_db_size:,} bytes ({total_db_size/1024/1024:.2f} MB)")
    
    print("\n💡 6. Recommendations:")
    
    if len(direct_connections) > 0:
        print("   🚨 CRITICAL: Files still using direct SQLite connections!")
        print("      These files will break when SQLite files are removed.")
        print("      Need to update them to use MariaDB or remove them.")
    
    if len(sqlite_files) > 0:
        print("   📁 SQLite files can be moved to backup folder")
        print("      Recommend creating backup before deletion")
    
    if len(sqlite_imports) > 0:
        print("   🐍 Some Python files still import sqlite3")
        print("      Check if these are still needed for MariaDB migration tools")
    
    print("\n🎯 7. Action Plan:")
    
    # Critical files that need updating
    critical_files = [
        'routes/quote.py',
        'services/quote_service.py', 
        'services/weasyprint_quote_generator.py',
        'routes/api.py'
    ]
    
    print("   📋 Phase 1: Update Critical Production Files")
    for file in critical_files:
        if any(file in conn_file for conn_file in direct_connections):
            print(f"      ⚠️  {file} - NEEDS UPDATE")
        else:
            print(f"      ✅ {file} - OK")
    
    print("   📋 Phase 2: Clean Up Test/Debug Files")
    test_files = [f for f in direct_connections if any(keyword in f for keyword in ['test_', 'debug_', 'check_'])]
    for file in test_files:
        print(f"      🧹 {file} - Can be updated or removed")
    
    print("   📋 Phase 3: Archive Migration Files")
    migration_files = [f for f in direct_connections if 'migrat' in f or 'fix_' in f]
    for file in migration_files:
        print(f"      📦 {file} - Move to archive folder")
    
    print("   📋 Phase 4: Remove SQLite Files")
    for file in sqlite_files:
        print(f"      🗑️  {file} - Move to backup then delete")

if __name__ == "__main__":
    analyze_sqlite_usage()