# Set timezone to Asia/Bangkok FIRST
import os
os.environ.setdefault('TZ', 'Asia/Bangkok')
try:
    import time
    time.tzset()
except AttributeError:
    pass  # Windows doesn't support time.tzset()

# Apply ReportLab MD5 fix FIRST for Python 3.8 compatibility
from reportlab_fix import patch_reportlab_md5
patch_reportlab_md5()

# Apply ultra-aggressive datetime fix FIRST - CRITICAL for SQLAlchemy TIME handling
import ultra_aggressive_datetime_fix
ultra_aggressive_datetime_fix.ultra_aggressive_patch()
ultra_aggressive_datetime_fix.apply_engine_level_patch()
print("🚀 Ultra-aggressive datetime fix applied in run.py")

from app import create_app, db
from models.user import User
from models.customer import Customer
from models.booking import Booking
import os

app = create_app()

@app.cli.command()
def init_db():
    """Initialize the database"""
    db.create_all()
    print("Database initialized!")

@app.cli.command()
def create_admin():
    """Create admin user"""
    admin = User.create_user(
        username='admin',
        email='support@dhakulchan.com',
        password='admin123',
        is_admin=True
    )
    
    db.session.add(admin)
    db.session.commit()
    print("Admin user created! Username: admin, Password: admin123")

if __name__ == '__main__':
    with app.app_context():
        try:
            db.create_all()
            
            # Create admin user if not exists
            try:
                existing_admin = User.query.filter_by(username='admin').first()
                if not existing_admin:
                    admin = User.create_user(
                        username='admin',
                        email='support@dhakulchan.com',
                        password='admin123',
                        is_admin=True
                    )
                    db.session.add(admin)
                    db.session.commit()
                    print("Admin user created! Username: admin, Password: admin123")
                else:
                    print("Admin user already exists")
            except Exception as e:
                print(f"Error checking/creating admin user: {e}")
                # Create tables and admin user anyway
                db.create_all()
                admin = User.create_user(
                    username='admin',
                    email='support@dhakulchan.com',
                    password='admin123',
                    is_admin=True
                )
                db.session.add(admin)
                db.session.commit()
                print("Admin user created after fixing schema! Username: admin, Password: admin123")
        except Exception as e:
            print(f"Database initialization error: {e}")
    
    # Allow overriding host/port via environment variables
    port = int(os.environ.get('PORT', 5001))
    host = os.environ.get('HOST', '0.0.0.0')
    debug_mode = os.environ.get('DEBUG', 'false').lower() == 'true'
    app.run(debug=debug_mode, host=host, port=port)
