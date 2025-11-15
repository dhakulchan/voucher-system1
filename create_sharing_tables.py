"""
Create voucher sharing tables migration
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from models.voucher_sharing import VoucherFile, VoucherLink

def create_sharing_tables():
    """Create voucher sharing tables"""
    app = create_app()
    
    with app.app_context():
        try:
            # Create tables
            db.create_all()
            print("✅ Created voucher sharing tables successfully!")
            
            # Verify tables exist
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'voucher_files' in tables:
                print("✅ voucher_files table created")
            if 'voucher_links' in tables:
                print("✅ voucher_links table created")
                
            return True
            
        except Exception as e:
            print(f"❌ Error creating tables: {e}")
            return False

if __name__ == "__main__":
    create_sharing_tables()