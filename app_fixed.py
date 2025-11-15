from flask import Flask, send_from_directory
from config import Config
from dotenv import load_dotenv
import os
import logging
from logging.handlers import RotatingFileHandler
from extensions import db, login_manager

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
    from routes.invoice import invoice_bp
    from routes.customer import customer_bp
    from routes.vendor import vendor_bp
    from routes.sync import sync_bp
    from routes.public import public_bp
    from routes.api_share import api_share_bp
    from routes.user_management import user_mgmt_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/')
    app.register_blueprint(booking_bp, url_prefix='/booking')
    app.register_blueprint(voucher_bp, url_prefix='/voucher')
    app.register_blueprint(queue_bp)
    if supplier_bp:
        app.register_blueprint(supplier_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(language_bp, url_prefix='/language')
    app.register_blueprint(invoice_bp, url_prefix='/invoice')
    app.register_blueprint(customer_bp, url_prefix='/customer')
    app.register_blueprint(vendor_bp, url_prefix='/vendor')
    app.register_blueprint(user_mgmt_bp)
    app.register_blueprint(sync_bp, url_prefix='/sync')
    app.register_blueprint(public_bp, url_prefix='/public')
    app.register_blueprint(api_share_bp)
    
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
    
    return app

# Provide a module-level app instance for shell / scripts (optional)
app = create_app()

@login_manager.user_loader
def load_user(user_id):
    from models.user import User
    return User.query.get(int(user_id))
