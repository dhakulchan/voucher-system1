#!/usr/bin/env python3
"""
Cleanup expired voucher files - should be run as a cron job
This script removes expired files and marks them as inactive in the database
"""

import os
import sys
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models.voucher_sharing import VoucherFile
from extensions import db

def cleanup_expired_files():
    """Clean up expired voucher files"""
    app = create_app()
    
    with app.app_context():
        try:
            print(f"Starting cleanup at {datetime.now()}")
            
            # Find expired files
            expired_files = VoucherFile.query.filter(
                VoucherFile.expires_at < datetime.utcnow(),
                VoucherFile.is_active == True
            ).all()
            
            print(f"Found {len(expired_files)} expired files")
            
            deleted_count = 0
            error_count = 0
            
            for file in expired_files:
                try:
                    print(f"Processing file: {file.original_filename} (ID: {file.id})")
                    
                    # Delete physical file
                    if os.path.exists(file.file_path):
                        os.remove(file.file_path)
                        print(f"  - Deleted physical file: {file.file_path}")
                    else:
                        print(f"  - Physical file not found: {file.file_path}")
                    
                    # Mark as inactive
                    file.is_active = False
                    deleted_count += 1
                    
                except Exception as e:
                    print(f"  - Error processing file {file.id}: {e}")
                    error_count += 1
            
            # Commit changes
            db.session.commit()
            
            print(f"Cleanup completed:")
            print(f"  - Files processed: {deleted_count}")
            print(f"  - Errors: {error_count}")
            print(f"  - Total expired files marked inactive: {deleted_count}")
            
            # Also clean up empty directories
            upload_dir = os.path.join('static', 'uploads', 'voucher_files')
            if os.path.exists(upload_dir):
                try:
                    # Remove empty directories
                    for root, dirs, files in os.walk(upload_dir, topdown=False):
                        for dir_name in dirs:
                            dir_path = os.path.join(root, dir_name)
                            try:
                                os.rmdir(dir_path)  # Only removes if empty
                                print(f"Removed empty directory: {dir_path}")
                            except OSError:
                                pass  # Directory not empty, that's fine
                except Exception as e:
                    print(f"Error cleaning up directories: {e}")
            
            return True
            
        except Exception as e:
            print(f"Error during cleanup: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    success = cleanup_expired_files()
    sys.exit(0 if success else 1)