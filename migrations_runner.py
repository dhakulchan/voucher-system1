#!/usr/bin/env python3
"""
Enhanced Migration runner for Dhakul Chan Voucher System
Handles all database migrations for production deployment
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# Set up logging
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/migration.log', 'a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_all_migrations():
    """Run all available migration scripts in order"""
    
    # Migration files in execution order
    migration_files = [
        'add_customer_columns_migration.py',
        'fix_vendors_table_migration.py', 
        'fix_quotes_table_migration.py'
    ]
    
    logger.info("🚀 Starting Dhakul Chan Voucher System Database Migrations...")
    logger.info(f"📅 Migration started at: {datetime.now()}")
    
    success_count = 0
    total_count = len(migration_files)
    
    for migration_file in migration_files:
        if os.path.exists(migration_file):
            logger.info(f"▶️  Running migration: {migration_file}")
            try:
                # Create a clean namespace for each migration
                migration_globals = {
                    '__name__': '__main__',
                    '__file__': migration_file
                }
                
                # Execute migration file
                with open(migration_file, 'r') as f:
                    exec(f.read(), migration_globals)
                
                logger.info(f"✅ Completed successfully: {migration_file}")
                success_count += 1
                
            except Exception as e:
                logger.error(f"❌ Migration failed: {migration_file}")
                logger.error(f"   Error: {str(e)}")
                # Log full traceback for debugging
                import traceback
                logger.error(f"   Traceback: {traceback.format_exc()}")
                
                # Ask if we should continue with remaining migrations
                logger.warning("⚠️  Migration failed. Continuing with remaining migrations...")
                
        else:
            logger.warning(f"⚠️  Migration file not found: {migration_file}")
    
    logger.info(f"📊 Migration Summary: {success_count}/{total_count} completed successfully")
    
    if success_count == total_count:
        logger.info("🎉 All migrations completed successfully!")
        return True
    else:
        logger.warning("⚠️  Some migrations failed. Please check logs and fix issues.")
        return False

def create_initial_admin():
    """Create initial admin user if not exists"""
    try:
        from app import create_app
        from extensions import db
        from models.user import User
        from werkzeug.security import generate_password_hash
        
        app = create_app()
        with app.app_context():
            # Check if admin exists
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                logger.info("👤 Creating initial admin user...")
                admin = User(
                    username='admin',
                    email='admin@dhakulchan.com',
                    password_hash=generate_password_hash('admin123'),
                    role='admin',
                    is_active=True
                )
                db.session.add(admin)
                db.session.commit()
                logger.info("✅ Initial admin user created successfully")
            else:
                logger.info("✅ Admin user already exists")
                
    except Exception as e:
        logger.error(f"❌ Failed to create admin user: {e}")

if __name__ == "__main__":
    # Ensure logs directory exists
    os.makedirs('logs', exist_ok=True)
    
    # Run migrations
    migration_success = run_all_migrations()
    
    # Create admin user
    create_initial_admin()
    
    # Exit with appropriate code
    sys.exit(0 if migration_success else 1)