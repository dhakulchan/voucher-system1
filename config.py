import os
from datetime import timedelta

class Config:
    # Basic Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database Configuration
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        # Use MariaDB for local development
        SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://voucher_user:voucher_secure_2024@localhost:3306/voucher_enhanced?charset=utf8mb4'
    else:
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # SQLAlchemy Engine Options for MariaDB
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_size': 10,
        'max_overflow': 20,
        'echo': False  # Set to True for SQL debug logging
    }
    
    # SQLAlchemy Session Options
    SQLALCHEMY_SESSION_OPTIONS = {
        'autoflush': True,
        'autocommit': False,
        'expire_on_commit': False  # Keep objects accessible after commit
    }
    
    # Session Configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # Email Configuration
    SMTP_SERVER = os.environ.get('SMTP_SERVER') or 'smtp.gmail.com'
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
    SMTP_USERNAME = os.environ.get('SMTP_USERNAME')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
    
    # Company Information
    COMPANY_NAME = os.environ.get('COMPANY_NAME') or 'บริษัท ดักุลจันทร์ ทราเวล เซอร์วิส (ประเทศไทย) จำกัด'
    COMPANY_NAME_EN = os.environ.get('COMPANY_NAME_EN') or 'DHAKUL CHAN TRAVEL SERVICE (THAILAND) CO.,LTD.'
    COMPANY_ADDRESS = os.environ.get('COMPANY_ADDRESS') or '710, 716, 704, 706 ถนนประชาอุทิศ แขวงสามเสนนอก เขตห้วยขวาง กรุงเทพฯ 10310'
    COMPANY_ADDRESS_EN = os.environ.get('COMPANY_ADDRESS_EN') or '710, 716, 704, 706 Prachautid Road, Samsennok, Huai Kwang, Bangkok 10310'
    COMPANY_PHONE = os.environ.get('COMPANY_PHONE') or '+662 2744216'
    COMPANY_MOBILE = os.environ.get('COMPANY_MOBILE') or '+662 2744216'
    COMPANY_EMAIL = os.environ.get('COMPANY_EMAIL') or 'support@dhakulchan.com'
    COMPANY_WEBSITE = os.environ.get('COMPANY_WEBSITE') or 'www.dhakulchan.net'
    COMPANY_LINE_OA = os.environ.get('COMPANY_LINE_OA') or '@dhakulchan'
    COMPANY_TAX_ID = os.environ.get('COMPANY_TAX_ID') or '0105567890123'
    
    # Company2 Information (for Tour Vouchers)
    COMPANY_NAME2 = os.environ.get('COMPANY_NAME2') or 'DHAKUL CHAN NICE HOLIDAYS DISCOVERY GROUP COMPANY LIMITED.'
    COMPANY_NAME_EN2 = os.environ.get('COMPANY_NAME_EN2') or 'DHAKUL CHAN NICE HOLIDAYS DISCOVERY GROUP COMPANY LIMITED.'
    COMPANY_ADDRESS2 = os.environ.get('COMPANY_ADDRESS2') or 'Flat C13, 21/F, Mai Wah Industrial Bldg., No. 1–7 Wah Shing Street, Kwai Chung, NT. Hong Kong'
    COMPANY_ADDRESS_EN2 = os.environ.get('COMPANY_ADDRESS_EN2') or 'Flat C13, 21/F, Mai Wah Industrial Bldg., No. 1–7 Wah Shing Street, Kwai Chung, NT. Hong Kong'
    COMPANY_PHONE2 = os.environ.get('COMPANY_PHONE2') or '+852 2392 1155'
    COMPANY_MOBILE2 = os.environ.get('COMPANY_MOBILE2') or '+852 23921177'
    COMPANY_EMAIL2 = os.environ.get('COMPANY_EMAIL2') or 'info@dhakulchan.net'
    COMPANY_WEBSITE2 = os.environ.get('COMPANY_WEBSITE2') or 'www.dhakulchan.net'
    COMPANY_TAX_ID2 = os.environ.get('COMPANY_TAX_ID2') or '01231234567890'
    
    # TinyMCE API Key
    TINYMCE_API_KEY = os.environ.get('TINYMCE_API_KEY') or ''
    
    # Localization
    DEFAULT_LANGUAGE = os.environ.get('DEFAULT_LANGUAGE') or 'en'
    CURRENCY_SYMBOL = os.environ.get('CURRENCY_SYMBOL') or '฿'
    CURRENCY_CODE = os.environ.get('CURRENCY_CODE') or 'THB'
    DATE_FORMAT = os.environ.get('DATE_FORMAT') or '%d/%m/%Y'
    TIME_FORMAT = os.environ.get('TIME_FORMAT') or '%H:%M'
    
    # File Upload Configuration
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Public URL Configuration
    # For development, you can set PUBLIC_BASE_URL=http://localhost:5001 in environment
    # For production, it should be https://service.dhakulchan.net
    PUBLIC_BASE_URL = os.environ.get('PUBLIC_BASE_URL') or 'https://service.dhakulchan.net'
    FORCE_HTTPS_DOMAINS = ['service.dhakulchan.net', 'dhakulchan.net']
    
    # Development mode detection
    DEVELOPMENT_MODE = os.environ.get('FLASK_ENV') == 'development' or os.environ.get('DEBUG') == 'True'

    # PDF Configuration
    PDF_LOGO_TARGET_HEIGHT = float(os.environ.get('PDF_LOGO_TARGET_HEIGHT', '55'))  # points
    PDF_LOGO_MAX_WIDTH = float(os.environ.get('PDF_LOGO_MAX_WIDTH', '180'))  # points
    PDF_LICENSE_LABEL = os.environ.get('PDF_LICENSE_LABEL', 'T.A.T License')
    PDF_LICENSE_VALUE = os.environ.get('PDF_LICENSE_VALUE', '11/03589')
    PDF_ALLOWED_TAGS = [t.strip() for t in os.environ.get('PDF_ALLOWED_TAGS', 'b,strong,i,em,u,br,p,ul,ol,li').split(',') if t.strip()]
    PDF_TERMS_LIST_STYLE = os.environ.get('PDF_TERMS_LIST_STYLE', 'number')
    PDF_TERMS_INCLUDE_VOUCHER = os.environ.get('PDF_TERMS_INCLUDE_VOUCHER', 'true').lower() in {'1','true','yes'}
