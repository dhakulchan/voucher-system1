# Set timezone to Asia/Bangkok FIRST
import os
os.environ.setdefault('TZ', 'Asia/Bangkok')
try:
    import time
    time.tzset()
except AttributeError:
    pass  # Windows doesn't support time.tzset()

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
from extensions import db, login_manager, mail
# Import critical datetime fix FIRST to patch SQLAlchemy
import critical_datetime_fix
# Import datetime compatibility fix for MariaDB
import datetime_fix
# Import timezone helper for Thailand timezone
from utils.timezone_helper import now_thailand, format_thai_datetime

# Load environment variables
load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Set max upload size to 1GB (1024 MB)
    app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024
    
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
    
    # Add Thailand timezone functions to templates
    @app.template_global()
    def now_th():
        """Get current datetime in Thailand timezone"""
        return now_thailand()
    
    @app.template_filter('thai_datetime')
    def thai_datetime_filter(dt, format_str='%d/%m/%Y %H:%M'):
        """Format datetime in Thailand timezone"""
        return format_thai_datetime(dt, format_str)
    
    # Add custom filter for HTML to line breaks conversion
    @app.template_filter('html_to_linebreaks')
    def html_to_linebreaks(content):
        """Convert HTML tags to line breaks for display"""
        if not content:
            return ""
        
        import re
        from html import unescape
        from markupsafe import Markup
        
        # First decode HTML entities
        content = unescape(content)
        
        # Replace pattern "คลิกดูเพิ่ม {URL}" with clickable link BEFORE stripping HTML
        content = re.sub(
            r'คลิกดูเพิ่ม\s+(https?://[^\s<]+)',
            r'<a href="\1" target="_blank">คลิกดูเพิ่ม</a>',
            content
        )
        
        # Replace <p> with paragraph breaks
        content = re.sub(r'<p[^>]*>', '', content, flags=re.IGNORECASE)
        content = re.sub(r'</p>', '\n\n', content, flags=re.IGNORECASE)
        
        # Replace various BR tags with newlines
        content = re.sub(r'<br\s*/?>', '\n', content, flags=re.IGNORECASE)
        content = re.sub(r'<br[^>]*>', '\n', content, flags=re.IGNORECASE)
        
        # Strip HTML tags EXCEPT for anchor tags
        content = re.sub(r'<(?!/?a\b)[^>]+>', '', content, flags=re.IGNORECASE)
        
        # Clean up whitespace
        content = re.sub(r'[ \t]+', ' ', content)  # Multiple spaces to single space
        content = re.sub(r'\n[ \t]+', '\n', content)  # Remove spaces after newlines
        content = re.sub(r'[ \t]+\n', '\n', content)  # Remove spaces before newlines
        content = re.sub(r'\n{3,}', '\n\n', content)  # Max 2 consecutive newlines
        
        return Markup(content.strip())

    # Add custom filter for newlines to br tags
    @app.template_filter('nl2br')
    def nl2br_filter(text):
        """Convert newlines to HTML br tags"""
        if not text:
            return ""
        from markupsafe import Markup
        import re
        # Replace pattern "คลิกดูเพิ่ม {URL}" with clickable link
        text = str(text)
        text = re.sub(
            r'คลิกดูเพิ่ม\s+(https?://[^\s<]+)',
            r'<a href="\1" target="_blank">คลิกดูเพิ่ม</a>',
            text
        )
        # Replace \r\n, \r, and \n with <br>
        result = text.replace('\r\n', '<br>').replace('\r', '<br>').replace('\n', '<br>')
        return Markup(result)

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
    
    @app.template_filter('service_detail_to_text')
    def service_detail_to_text(content):
        """Convert service detail content to display-friendly text with proper line breaks"""
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
        
        # Convert literal \n strings to actual newlines (for database stored as escaped)
        result = result.replace('\\n', '\n')
        result = result.replace('\\r\\n', '\n')
        result = result.replace('\\r', '\n')
        
        # Normalize line breaks
        result = result.replace('\r\n', '\n')
        result = result.replace('\r', '\n')
        
        return result.strip()
    
    # Initialize extensions with app
    db.init_app(app)
    
    # Initialize Flask-Mail
    mail.init_app(app)
    
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
    from routes.two_factor import two_factor_bp
    from routes.dashboard import dashboard_bp
    from routes.booking import booking_bp
    from routes.voucher import voucher_bp
    from routes.voucher_library import voucher_library_bp
    from routes.queue_routes import queue_bp
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
    from routes.passport_upload import passport_upload_bp  # Passport MRZ OCR system
    from routes.passport_nfc import passport_nfc_bp  # Passport NFC reading via mobile app
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
    
    # Short Itinerary Admin
    try:
        from routes.short_itinerary_admin import short_itinerary_admin
        SHORT_ITINERARY_AVAILABLE = True
    except ImportError as e:
        SHORT_ITINERARY_AVAILABLE = False
        short_itinerary_admin = None
        print(f"❌ Failed to import short_itinerary_admin: {e}")
    
    # Flight Template Admin
    try:
        from routes.flight_template_admin import flight_template_admin
        FLIGHT_TEMPLATE_AVAILABLE = True
    except ImportError as e:
        FLIGHT_TEMPLATE_AVAILABLE = False
        flight_template_admin = None
        print(f"❌ Failed to import flight_template_admin: {e}")
        
    # Test blueprint for debugging
    from routes.test import test_bp
    
    # Import special routes for booking #45
    from booking_45_routes import register_booking_45_routes
    # from test_45_routes import register_test_45_routes  # Module not found
    from ultra_test_45 import register_ultra_test_routes
    from final_booking_45 import register_final_45_routes
    from debug_booking_45 import register_debug_45_routes
    from minimal_booking_45 import register_minimal_45_routes
    from booking_45_final_fix import register_final_booking_45_routes
    # from booking_46_routes import register_booking_46_routes  # Disabled
    from booking_46_routes import register_booking_46_routes  # Re-enabled
    
    # Import enhanced workflow
    from routes.enhanced_workflow import enhanced_workflow_bp
    
    # Import debug user route
    from routes.debug_user import debug_user_bp
    
    # Import permissions management routes
    from routes.permissions import permissions_bp
    
    # Import auto completion routes
    # from routes.auto_completion import auto_completion_bp  # Module not found
    
    # Import booking calendar routes
    from routes.booking_calendar import calendar_bp
    
    # Import account report routes
    try:
        from routes.account_report import account_report
        ACCOUNT_REPORT_AVAILABLE = True
    except ImportError as e:
        ACCOUNT_REPORT_AVAILABLE = False
        account_report = None
        print(f"❌ Failed to import account_report: {e}")
    
    # Import Group Buy routes
    try:
        from routes.group_buy_admin import bp as group_buy_admin_bp
        from routes.group_buy_public import bp as group_buy_public_bp
        GROUP_BUY_AVAILABLE = True
        print("✅ Group Buy blueprints imported successfully")
    except ImportError as e:
        GROUP_BUY_AVAILABLE = False
        group_buy_admin_bp = None
        group_buy_public_bp = None
        print(f"❌ Failed to import Group Buy blueprints: {e}")
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(two_factor_bp, url_prefix='/auth/2fa')
    app.register_blueprint(dashboard_bp, url_prefix='/')
    app.register_blueprint(booking_bp, url_prefix='/booking')
    app.register_blueprint(calendar_bp)  # Calendar and daily report
    app.register_blueprint(enhanced_workflow_bp, url_prefix='/booking')  # Enhanced workflow
    app.register_blueprint(debug_user_bp)  # Debug user info
    app.register_blueprint(permissions_bp)  # Permission management routes
    # app.register_blueprint(auto_completion_bp)  # Auto completion routes - Module not found
    app.register_blueprint(voucher_bp, url_prefix='/voucher')
    app.register_blueprint(voucher_library_bp, url_prefix='/voucher-library')
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
    app.register_blueprint(passport_upload_bp)  # Passport MRZ OCR routes
    app.register_blueprint(passport_nfc_bp)  # Passport NFC routes (QR Code + Mobile App)
    app.register_blueprint(test_bp)  # Add test blueprint
    register_booking_45_routes(app)  # Register special booking #45 routes
    # register_test_45_routes(app)  # Module not found
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
    
    # Short Itinerary Admin
    if SHORT_ITINERARY_AVAILABLE and short_itinerary_admin:
        app.register_blueprint(short_itinerary_admin)  # Already has url_prefix='/admin/short-itinerary'
        print("✅ Short Itinerary Admin registered")
    
    # Flight Template Admin
    if FLIGHT_TEMPLATE_AVAILABLE and flight_template_admin:
        app.register_blueprint(flight_template_admin)  # Already has url_prefix='/admin/flight-template'
        print("✅ Flight Template Admin registered")
    
    # Account Report
    if ACCOUNT_REPORT_AVAILABLE and account_report:
        app.register_blueprint(account_report)  # Already has url_prefix='/account-report'
        print("✅ Account Report registered")
    
    # Group Buy
    if GROUP_BUY_AVAILABLE:
        if group_buy_admin_bp:
            app.register_blueprint(group_buy_admin_bp)  # Already has url_prefix='/backoffice/group-buy'
            print("✅ Group Buy Admin registered")
        if group_buy_public_bp:
            app.register_blueprint(group_buy_public_bp)  # Already has url_prefix='/group-buy'
            print("✅ Group Buy Public registered")
        
        # Register Group Buy Payment routes
        try:
            from routes.group_buy_payment_admin import bp as group_buy_payment_admin_bp
            app.register_blueprint(group_buy_payment_admin_bp)
            print("✅ Group Buy Payment Admin registered")
        except Exception as e:
            print(f"❌ Failed to register Group Buy Payment Admin: {e}")
        
        try:
            from routes.group_buy_payment_public import bp as group_buy_payment_public_bp
            app.register_blueprint(group_buy_payment_public_bp)
            print("✅ Group Buy Payment Public registered")
        except Exception as e:
            print(f"❌ Failed to register Group Buy Payment Public: {e}")
    
    # Register mark-paid API
    try:
        from routes.mark_paid_api import mark_paid_bp
        app.register_blueprint(mark_paid_bp)
        print("✅ Mark-paid API registered")
    except Exception as e:
        print(f"❌ Failed to register mark-paid API: {e}")
    
    # Add Quote PDF generation route
    @app.route('/booking/<booking_ref>/quote_pdf')
    def generate_quote_pdf(booking_ref):
        """Generate Quote PDF using WeasyPrint"""
        from flask import Response
        from weasyprint_quote_generator import WeasyPrintQuoteGenerator
        import os
        import sqlite3
        import json
        
        try:
            # Create a simple booking class for SQLite data
            class SimpleBooking:
                def __init__(self, data):
                    self.id = data[0]
                    self.booking_reference = data[1]
                    self.guest_list = data[2] 
                    self.description = data[3]
                    self.customer_name = data[4]
                    self.customer_phone = data[5]
                    self.total_amount = data[6]
                    self.adults = data[7]
                    self.children = data[8]
                    self.infants = data[9]
                    # Add mock fields for PDF generation
                    self.flight_info = None
                    self.service_date = None
                    
            # Query SQLite directly 
            conn = sqlite3.connect('voucher_system.db')
            cursor = conn.cursor()
            
            # Try to find booking by ID first, then by reference
            booking_data = None
            try:
                booking_id = int(booking_ref)
                cursor.execute('SELECT * FROM bookings WHERE id = ?', (booking_id,))
                booking_data = cursor.fetchone()
            except ValueError:
                cursor.execute('SELECT * FROM bookings WHERE booking_reference = ?', (booking_ref,))
                booking_data = cursor.fetchone()
            
            conn.close()
            
            if not booking_data:
                app.logger.error(f"❌ Booking not found: {booking_ref}")
                return Response("Booking not found", status=404)
                
            # Create booking object
            booking = SimpleBooking(booking_data)
            
            # Generate PDF
            generator = WeasyPrintQuoteGenerator()
            pdf_path = generator.generate_quote_pdf(booking)
            
            # Read and return PDF
            if os.path.exists(pdf_path):
                with open(pdf_path, 'rb') as f:
                    pdf_data = f.read()
                
                app.logger.info(f"✅ Quote PDF generated successfully: {pdf_path} ({len(pdf_data)} bytes)")
                
                return Response(
                    pdf_data,
                    mimetype='application/pdf',
                    headers={
                        'Content-Disposition': f'inline; filename="Quote_{booking_ref}.pdf"',
                        'Content-Length': str(len(pdf_data))
                    }
                )
            else:
                app.logger.error(f"❌ PDF file not found: {pdf_path}")
                return Response("PDF generation failed - file not found", status=500)
                
        except Exception as e:
            import traceback
            app.logger.error(f"❌ Quote PDF generation error: {str(e)}")
            app.logger.error(f"❌ Stack trace: {traceback.format_exc()}")
            return Response(f"PDF generation failed: {str(e)}", status=500)
    
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
            'translations': TRANSLATIONS.get(get_current_language(), {}),
            'get_role_badge': get_role_badge
        }
    
    def get_role_badge(role):
        """Get Bootstrap badge class for role"""
        role_classes = {
            'Administrator': 'bg-danger',
            'Operation': 'bg-warning text-dark',
            'Manager': 'bg-info',
            'Staff': 'bg-primary',
            'Internship': 'bg-success',
            'Freelance': 'bg-secondary'
        }
        return role_classes.get(role, 'bg-secondary')
    
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
        """Format date in Thai format"""
        try:
            if isinstance(value, str):
                # Try to parse string date
                from datetime import datetime
                date_obj = datetime.strptime(value, '%Y-%m-%d')
            else:
                date_obj = value
            
            # Thai months
            thai_months = {
                1: 'มกราคม', 2: 'กุมภาพันธ์', 3: 'มีนาคม', 4: 'เมษายน',
                5: 'พฤษภาคม', 6: 'มิถุนายน', 7: 'กรกฎาคม', 8: 'สิงหาคม',
                9: 'กันยายน', 10: 'ตุลาคม', 11: 'พฤศจิกายน', 12: 'ธันวาคม'
            }
            
            thai_year = date_obj.year + 543
            thai_month = thai_months.get(date_obj.month, str(date_obj.month))
            
            return f"{date_obj.day} {thai_month} {thai_year}"
            
        except (ValueError, TypeError, AttributeError):
            return str(value) if value else ""
    
    @app.template_filter('from_json')
    def from_json_filter(value):
        """Parse JSON string to Python object"""
        import json
        if not value:
            return []
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, ValueError):
                return []
        return value  # Already a list/dict
    
    @app.template_filter('decode_guest_list')
    def decode_guest_list_filter(value):
        """Decode Unicode escape sequences in guest list and format with line breaks"""
        import re
        import json
        
        if not value or not isinstance(value, str):
            return ""
        
        try:
            # Decode Unicode escape sequences if present
            def decode_unicode_string(text):
                if not text or not isinstance(text, str):
                    return text
                try:
                    if '\\u' in text:
                        # Handle Unicode escape sequences
                        try:
                            decoded = text.encode().decode('unicode_escape')
                            return decoded
                        except:
                            # Manual replacement if encode/decode fails
                            def replace_unicode(match):
                                try:
                                    return chr(int(match.group(1), 16))
                                except:
                                    return match.group(0)
                            decoded = re.sub(r'\\u([0-9a-fA-F]{4})', replace_unicode, text)
                            return decoded
                    return text
                except Exception:
                    return text
            
            # First decode Unicode
            decoded_value = decode_unicode_string(value)
            
            # Handle different input formats
            if (',' in decoded_value and '"' in decoded_value) or decoded_value.startswith('['):
                # Handle comma-separated or JSON-like format
                try:
                    # Try JSON parsing first
                    if decoded_value.startswith('['):
                        names = json.loads(decoded_value)
                    else:
                        # Extract names from quoted comma-separated format
                        names = re.findall(r'"([^"]+)"', decoded_value)
                        if not names:
                            # Try without quotes
                            names = [name.strip() for name in decoded_value.split(',') if name.strip()]
                except json.JSONDecodeError:
                    # If JSON fails, try comma-separated
                    names = re.findall(r'"([^"]+)"', decoded_value)
                    if not names:
                        names = [name.strip().strip('"') for name in decoded_value.split(',') if name.strip()]
                
                # Format as numbered list
                if names:
                    formatted_names = []
                    for i, name in enumerate(names, 1):
                        clean_name = str(name).strip().strip('"\'')
                        if clean_name and clean_name not in ['None', 'null', '']:
                            formatted_names.append(f"{i}. {clean_name}")
                    return '<br>'.join(formatted_names)
            
            elif '\n' in decoded_value:
                # Handle newline-separated format
                names = [line.strip() for line in decoded_value.split('\n') if line.strip()]
                if names:
                    formatted_names = []
                    for i, name in enumerate(names, 1):
                        clean_name = str(name).strip()
                        if clean_name and clean_name not in ['None', 'null', '']:
                            formatted_names.append(f"{i}. {clean_name}")
                    return '<br>'.join(formatted_names)
            
            else:
                # Single name or simple format
                clean_name = decoded_value.strip()
                if clean_name and clean_name not in ['None', 'null', '']:
                    return f"1. {clean_name}"
            
            return decoded_value
            
        except Exception as e:
            # If all parsing fails, return the original value
            return str(value)
    
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
    
    # Test role endpoint
    @app.route('/test-role')
    def test_role():
        from flask import render_template, session
        return render_template('test_role.html')
    
    # Debug session endpoint
    @app.route('/debug-session')
    def debug_session():
        from flask import session, jsonify
        return jsonify({
            'user_role': session.get('user_role'),
            'username': session.get('username'),
            'user_id': session.get('user_id'),
            'all_session_keys': list(session.keys()),
            'is_admin': session.get('user_role') in ['admin', 'manager'],
            'session_data': dict(session)
        })
    
    # Force reload user from database on every request to ensure role changes take effect
    @app.before_request
    def refresh_user_from_db():
        """Refresh current_user from database to ensure role changes are applied"""
        from flask_login import current_user
        from models.user import User
        from flask import request
        
        if current_user.is_authenticated:
            # Skip if logging in or logging out
            if request.endpoint and ('auth.login' in str(request.endpoint) or 'auth.logout' in str(request.endpoint)):
                return
            
            try:
                # Get fresh user data directly from database
                fresh_user = db.session.query(User).filter_by(id=current_user.id).first()
                
                if fresh_user:
                    # DEBUG: Log the role information
                    app.logger.info(f"USER DEBUG: username={fresh_user.username}, role={fresh_user.role}, is_admin={fresh_user.is_admin}")
                    print(f"🔍 USER DEBUG: {fresh_user.username} | Role: {fresh_user.role} | Admin: {fresh_user.is_admin}")
                    
                    # Force update current_user attributes with fresh data
                    # This ensures the template always sees the latest role from database
                    current_user.role = fresh_user.role
                    current_user.is_admin = fresh_user.is_admin
                    current_user.email = fresh_user.email
                    
            except Exception as e:
                # Log error but don't break the request
                app.logger.error(f"Error refreshing user: {e}")
                print(f"Error refreshing user: {e}")
    
    # User loader - moved inside create_app() to ensure it works with app context
    @login_manager.user_loader
    def load_user(user_id):
        """Load user from database - always fresh from DB with no cache"""
        from models.user import User
        # Use a fresh query with expire_on_commit=False to ensure we get latest data
        user = db.session.query(User).filter_by(id=int(user_id)).first()
        if user:
            # Critical: Force expire ALL attributes to reload from database
            db.session.expire(user)
            # Now access role to force reload
            _ = user.role  # This triggers the DB query
        return user
    
    return app

# Provide a module-level app instance for shell / scripts (optional)
app = create_app()



if __name__ == '__main__':
    # Run the Flask development server
    app.run(host='0.0.0.0', port=5001, debug=False)
