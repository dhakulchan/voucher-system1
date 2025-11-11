# Import ultra-aggressive datetime fix FIRST - this MUST come before ANY SQLAlchemy imports
import ultra_aggressive_datetime_fix
ultra_aggressive_datetime_fix.ultra_aggressive_patch()
ultra_aggressive_datetime_fix.apply_engine_level_patch()

from flask import Flask, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config
from dotenv import load_dotenv
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from extensions import db, login_manager
# Import critical datetime fix FIRST to patch SQLAlchemy
import critical_datetime_fix
# Import datetime compatibility fix for MariaDB
import datetime_fix

# Load environment variables
load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    # Initialize file-based logging (writes to instance/app.log)
    try:
        # Ensure instance path exists
        os.makedirs(app.instance_path, exist_ok=True)
        log_path = os.path.join(app.instance_path, 'app.log')
        handler = RotatingFileHandler(log_path, maxBytes=1024 * 1024, backupCount=5)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s %(levelname)s in %(module)s: %(message)s')
        handler.setFormatter(formatter)
        # Attach handler to Flask app logger
        app.logger.addHandler(handler)
        app.logger.setLevel(logging.INFO)
        # Ensure werkzeug (request) logs also go to the same file
        logging.getLogger('werkzeug').addHandler(handler)
        app.logger.info('Logging initialized, writing to %s', log_path)
    except Exception as _log_except:
        # If logging initialization fails, continue without breaking the app
        print('Warning: failed to initialize file logging:', _log_except)
    
    # Enable template auto reload for development
    app.jinja_env.auto_reload = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    
    # Add template global functions
    @app.template_global()
    def timestamp():
        import time
        return int(time.time())
    
    # Add custom filter for HTML to line breaks conversion
    @app.template_filter('html_to_linebreaks')
    def html_to_linebreaks(content):
        """Convert HTML tags to line breaks for display"""
        if not content:
            return ""
        
        import re
        from html import unescape
        
        # First decode HTML entities
        content = unescape(content)
        
        # Replace <p> with paragraph breaks
        content = re.sub(r'<p[^>]*>', '', content, flags=re.IGNORECASE)
        content = re.sub(r'</p>', '\n\n', content, flags=re.IGNORECASE)
        
        # Replace various BR tags with newlines
        content = re.sub(r'<br\s*/?>', '\n', content, flags=re.IGNORECASE)
        content = re.sub(r'<br[^>]*>', '\n', content, flags=re.IGNORECASE)
        
        # Strip any remaining HTML tags
        content = re.sub(r'<[^>]+>', '', content)
        
        # Clean up whitespace
        content = re.sub(r'[ \t]+', ' ', content)  # Multiple spaces to single space
        content = re.sub(r'\n[ \t]+', '\n', content)  # Remove spaces after newlines
        content = re.sub(r'[ \t]+\n', '\n', content)  # Remove spaces before newlines
        content = re.sub(r'\n{3,}', '\n\n', content)  # Max 2 consecutive newlines
        
        return content.strip()

    # Add custom filter for flight info processing
    @app.template_filter('flight_info_to_text')
    def flight_info_to_text(content):
        """Convert HTML flight info to textarea-friendly text"""
        if not content:
            return ''
        
        import re
        
        # Convert HTML line breaks to newlines
        result = content.replace('<br>', '\n')
        result = result.replace('<br/>', '\n')
        result = result.replace('<br />', '\n')
        
        # Convert closing </p> tags to newlines first (for paragraph separation)
        result = result.replace('</p>', '\n')
        
        # Remove opening HTML tags
        result = result.replace('<p>', '')
        result = result.replace('<div>', '')
        result = result.replace('</div>', '')
        
        # Strip any remaining HTML tags
        result = re.sub(r'<[^>]+>', '', result)
        
        # Normalize line breaks
        result = result.replace('\r\n', '\n')
        result = result.replace('\r', '\n')
        
        return result.strip()
    
    # Initialize extensions with app
    db.init_app(app)
    
    # Import models to register event listeners
    try:
        import models_mariadb
        app.logger.info("✅ Models with event listeners imported successfully")
    except ImportError as e:
        app.logger.warning(f"⚠️ Could not import models_mariadb: {e}")
    
    # Configure SQLAlchemy session options
    if hasattr(app.config, 'SQLALCHEMY_SESSION_OPTIONS'):
        from sqlalchemy.orm import sessionmaker
        # Update session maker with custom options
        session_options = app.config.get('SQLALCHEMY_SESSION_OPTIONS', {})
        app.logger.info(f"🔧 Applying SQLAlchemy session options: {session_options}")
    
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    
    # Create upload directory if it doesn't exist
    upload_dir = os.path.join(app.instance_path, 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    
    # Import and register blueprints
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.booking import booking_bp
    from routes.voucher import voucher_bp
    from routes.queue import queue_bp
    try:
        from routes.supplier import supplier_bp
    except Exception:
        supplier_bp = None
    from routes.api import api_bp
    from routes.language import language_bp
    from routes.customer import customer_bp
    from routes.vendor import vendor_bp
    from routes.sync import sync_bp
    from routes.public import public_bp
    from routes.api_share import api_share_bp
    from routes.api_share_enhanced import api_share_enhanced_bp  # Enhanced API share routes
    from routes.api_enhanced import api_enhanced_bp  # NEW Enhanced API routes
    from routes.user_management import user_mgmt_bp
    try:
        from routes.quote import quote_bp
        QUOTE_AVAILABLE = True
    except ImportError:
        QUOTE_AVAILABLE = False
        quote_bp = None
    
    try:
        from routes.paid import paid_bp
        PAID_AVAILABLE = True
    except ImportError:
        PAID_AVAILABLE = False
        paid_bp = None
    
    try:
        from routes.completed import completed_bp
        COMPLETED_AVAILABLE = True
    except ImportError:
        COMPLETED_AVAILABLE = False
        completed_bp = None
    
    try:
        from routes.pre_receipt import pre_receipt_bp
        PRE_RECEIPT_AVAILABLE = True
        print("✅ Pre-receipt blueprint imported successfully")
    except ImportError as e:
        PRE_RECEIPT_AVAILABLE = False
        pre_receipt_bp = None
        print(f"❌ Failed to import pre-receipt blueprint: {e}")
    except Exception as e:
        PRE_RECEIPT_AVAILABLE = False
        pre_receipt_bp = None
        print(f"❌ Error importing pre-receipt blueprint: {e}")
    
    try:
        from routes.invoice import invoice_bp
        INVOICE_AVAILABLE = True
    except ImportError:
        INVOICE_AVAILABLE = False
        invoice_bp = None
        
    # Test blueprint for debugging
    from routes.test import test_bp
    
    # Import special routes for booking #45
    from booking_45_routes import register_booking_45_routes
    from test_45_routes import register_test_45_routes
    from ultra_test_45 import register_ultra_test_routes
    from final_booking_45 import register_final_45_routes
    from debug_booking_45 import register_debug_45_routes
    from minimal_booking_45 import register_minimal_45_routes
    from booking_45_final_fix import register_final_booking_45_routes
    # from booking_46_routes import register_booking_46_routes  # Disabled
    from booking_46_routes import register_booking_46_routes  # Re-enabled
    
    # Import enhanced workflow
    from routes.enhanced_workflow import enhanced_workflow_bp
    
    # Import auto completion routes
    from routes.auto_completion import auto_completion_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/')
    app.register_blueprint(booking_bp, url_prefix='/booking')
    app.register_blueprint(enhanced_workflow_bp, url_prefix='/booking')  # Enhanced workflow
    app.register_blueprint(auto_completion_bp)  # Auto completion routes
    app.register_blueprint(voucher_bp, url_prefix='/voucher')
    app.register_blueprint(queue_bp)
    if supplier_bp:
        app.register_blueprint(supplier_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(api_enhanced_bp)  # NEW Enhanced API routes (has its own url_prefix)
    app.register_blueprint(language_bp, url_prefix='/language')
    app.register_blueprint(customer_bp, url_prefix='/customer')
    app.register_blueprint(vendor_bp, url_prefix='/vendor')
    app.register_blueprint(user_mgmt_bp)
    app.register_blueprint(sync_bp, url_prefix='/sync')
    app.register_blueprint(public_bp)  # Blueprint already has url_prefix='/public' 
    app.register_blueprint(api_share_bp)
    app.register_blueprint(api_share_enhanced_bp)  # Enhanced API share routes
    app.register_blueprint(test_bp)  # Add test blueprint
    register_booking_45_routes(app)  # Register special booking #45 routes
    register_test_45_routes(app)  # Register test routes for booking #45
    register_ultra_test_routes(app)  # Register ultra simple test routes
    register_final_45_routes(app)  # Register final working routes for booking #45
    register_debug_45_routes(app)  # Register debug routes for booking #45
    register_minimal_45_routes(app)  # Register minimal test routes for booking #45
    register_final_booking_45_routes(app)
    register_booking_46_routes(app)  # Register special booking #46 routes - Re-enabled
    if QUOTE_AVAILABLE and quote_bp:
        app.register_blueprint(quote_bp, url_prefix='/quote')
    if PAID_AVAILABLE and paid_bp:
        app.register_blueprint(paid_bp, url_prefix='/paid')
    if COMPLETED_AVAILABLE and completed_bp:
        app.register_blueprint(completed_bp, url_prefix='/completed')
    if PRE_RECEIPT_AVAILABLE and pre_receipt_bp:
        app.register_blueprint(pre_receipt_bp, url_prefix='/pre-receipt')
        print("✅ Pre-receipt blueprint registered successfully")
    else:
        print(f"❌ Pre-receipt blueprint not registered - Available: {PRE_RECEIPT_AVAILABLE}, Blueprint: {pre_receipt_bp}")
    if INVOICE_AVAILABLE and invoice_bp:
        app.register_blueprint(invoice_bp, url_prefix='/invoice')
    
    # Register mark-paid API
    try:
        from routes.mark_paid_api import mark_paid_bp
        app.register_blueprint(mark_paid_bp)
        print("✅ Mark-paid API registered")
    except Exception as e:
        print(f"❌ Failed to register mark-paid API: {e}")
    
    # Add favicon route
    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(app.static_folder, 'favicon.ico', mimetype='image/vnd.microsoft.icon')
    
    # Add global context processor for translations
    @app.context_processor
    def inject_translations():
        from routes.language import t, get_current_language, TRANSLATIONS
        return {
            't': t,
            'current_language': get_current_language(),
            'is_thai': get_current_language() == 'th',
            'translations': TRANSLATIONS.get(get_current_language(), {})
        }
    
    # Add safe formatting filters for templates
    @app.template_filter('safe_format')
    def safe_format_filter(value, format_str="{:,.2f}"):
        """Safely format numbers, returning 0 if value is None"""
        try:
            return format_str.format(value or 0)
        except (ValueError, TypeError):
            return "0.00"
    
    @app.template_filter('safe_currency')
    def safe_currency_filter(value, currency="THB"):
        """Safely format currency values"""
        try:
            formatted = "{:,.2f}".format(value or 0)
            return f"{currency} {formatted}"
        except (ValueError, TypeError):
            return f"{currency} 0.00"
    
    @app.template_filter('thai_currency')
    def thai_currency_filter(value):
        """Format number as Thai currency"""
        try:
            if value is None:
                return "฿0.00"
            
            # Convert to float if it's a string
            if isinstance(value, str):
                value = float(value)
            
            # Format with 2 decimal places and thousands separator
            return "฿{:,.2f}".format(value)
        except (ValueError, TypeError):
            return "฿0.00"
    
    @app.template_filter('thai_date')
    def thai_date_filter(value):
        """Format date as Thai format DD/MM/YYYY"""
        try:
            if value is None:
                return datetime.now().strftime('%d/%m/%Y')
            
            # If it's already a string, return as is
            if isinstance(value, str):
                return value
            
            # If it's a datetime object, format it
            if hasattr(value, 'strftime'):
                return value.strftime('%d/%m/%Y')
            
            return str(value)
        except (ValueError, TypeError):
            return datetime.now().strftime('%d/%m/%Y')
    
    # Add language parameter checking
    @app.before_request
    def check_language_param():
        from flask import request, session
        # Force English only temporarily
        session['language'] = 'en'

    # Log unhandled exceptions from requests (ensures tracebacks go to instance/app.log)
    @app.teardown_request
    def log_request_exception(exc):
        if exc is not None:
            try:
                # Log full stacktrace
                app.logger.exception('Unhandled exception during request: %s', exc)
            except Exception:
                # If logging fails, don't crash the request teardown
                pass

    # Register a global error handler to ensure all exceptions are logged
    from werkzeug.exceptions import HTTPException

    @app.errorhandler(Exception)
    def handle_all_exceptions(e):
        try:
            if isinstance(e, HTTPException):
                app.logger.exception('HTTP exception during request: %s', e)
                return e
            # Non-HTTP exceptions: log full traceback
            app.logger.exception('Unhandled exception (500): %s', e)
        except Exception:
            # if logging itself fails, avoid crashing
            pass
        # Return a generic 500 response
        from flask import Response
        return Response('Internal Server Error', status=500)
    
    # Create database tables
    with app.app_context():
        db.create_all()
        # Ensure legacy / new columns exist (light auto-migration)
        try:
            from sqlalchemy import text, inspect
            engine = db.engine
            insp = inspect(engine)
            cols = [c['name'] for c in insp.get_columns('bookings')]
            ddls = []
            need_map = {
                'vendor_id': 'ALTER TABLE bookings ADD COLUMN vendor_id INTEGER',
                'supplier_id': 'ALTER TABLE bookings ADD COLUMN supplier_id INTEGER',
                'quote_number': 'ALTER TABLE bookings ADD COLUMN quote_number VARCHAR(100)',
                'quote_status': 'ALTER TABLE bookings ADD COLUMN quote_status VARCHAR(50)',
                'invoice_number': 'ALTER TABLE bookings ADD COLUMN invoice_number VARCHAR(100)',
                'voucher_image_path': 'ALTER TABLE bookings ADD COLUMN voucher_image_path VARCHAR(255)'
            }
            for col, ddl in need_map.items():
                if col not in cols:
                    ddls.append(ddl)
            if ddls:
                with engine.begin() as conn:
                    for ddl in ddls:
                        conn.execute(text(ddl))
                app.logger.info('Auto-added columns: %s', ', '.join([d.split()[2] for d in ddls]))
            # Supplier (vendors table) new columns
            vcols = [c['name'] for c in insp.get_columns('vendors')]
            supplier_new_cols = {
                'real_name': 'ALTER TABLE vendors ADD COLUMN real_name VARCHAR(200)',
                'real_tel': 'ALTER TABLE vendors ADD COLUMN real_tel VARCHAR(60)',
                'real_fax': 'ALTER TABLE vendors ADD COLUMN real_fax VARCHAR(60)',
                'real_email': 'ALTER TABLE vendors ADD COLUMN real_email VARCHAR(180)',
                'fax': 'ALTER TABLE vendors ADD COLUMN fax VARCHAR(60)',
                'mobile_phone': 'ALTER TABLE vendors ADD COLUMN mobile_phone VARCHAR(60)',
                'real_group_email': 'ALTER TABLE vendors ADD COLUMN real_group_email VARCHAR(180)',
                'memos': 'ALTER TABLE vendors ADD COLUMN memos TEXT',
                'remarks': 'ALTER TABLE vendors ADD COLUMN remarks TEXT'
            }
            vddls = [ddl for col, ddl in supplier_new_cols.items() if col not in vcols]
            if vddls:
                with engine.begin() as conn:
                    for ddl in vddls:
                        conn.execute(text(ddl))
                app.logger.info('Auto-added supplier columns: %s', ', '.join([d.split()[2] for d in vddls]))
        except Exception as e:
            app.logger.warning(f'Auto-migrate bookings columns failed: {e}')

    # Background PNG cache cleanup thread
    try:
        import threading, time as _time
        from routes.voucher import cleanup_png_cache
        def _png_cleanup_loop():
            while True:
                try:
                    removed = cleanup_png_cache(24)
                    if removed:
                        app.logger.info('PNG cache cleanup removed %s file(s)', removed)
                except Exception:
                    pass
                _time.sleep(3600)  # run hourly
        t = threading.Thread(target=_png_cleanup_loop, daemon=True)
        t.start()
    except Exception:
        pass
    
    # Admin unlock verification endpoint
    @app.route('/api/admin/verify-unlock', methods=['POST'])
    def verify_admin_unlock():
        from flask import request, jsonify
        from models.user import User
        import hashlib
        import datetime
        
        try:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
            reason = data.get('reason')
            section = data.get('section')
            booking_id = data.get('booking_id')
            
            # Log unlock attempt
            app.logger.info(f'Admin unlock attempt - User: {username}, Section: {section}, Booking: {booking_id}')
            
            # Verify admin credentials
            # You can customize these admin credentials as needed
            ADMIN_USERS = {
                'admin': 'admin123',
                'manager': 'manager456',
                'supervisor': 'super789'
            }
            
            if username in ADMIN_USERS and ADMIN_USERS[username] == password:
                # Log successful unlock
                app.logger.info(f'✅ Admin unlock successful - User: {username}, Section: {section}, Booking: {booking_id}, Reason: {reason}')
                
                return jsonify({
                    'success': True,
                    'message': 'Admin verification successful',
                    'admin_user': username,
                    'unlock_time': str(datetime.datetime.now())
                })
            else:
                # Log failed unlock attempt
                app.logger.warning(f'❌ Admin unlock failed - Invalid credentials for user: {username}')
                
                return jsonify({
                    'success': False,
                    'message': 'Invalid admin credentials'
                }), 401
                
        except Exception as e:
            app.logger.error(f'❌ Admin unlock error: {str(e)}')
            return jsonify({
                'success': False,
                'message': 'Server error occurred'
            }), 500
    
    return app

# Provide a module-level app instance for shell / scripts (optional)
app = create_app()

@login_manager.user_loader
def load_user(user_id):
    from models.user import User
    return User.query.get(int(user_id))



if __name__ == '__main__':
    # Run the Flask development server
    app.run(host='0.0.0.0', port=5001, debug=False)
