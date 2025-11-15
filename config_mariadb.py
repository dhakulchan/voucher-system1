"""
Enhanced Database Configuration for MariaDB
Configuration file for the unified voucher system
"""

import os
from datetime import timedelta

class Config:
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'voucher-system-secure-key-2025'
    
    # MariaDB Database Configuration
    MYSQL_HOST = os.environ.get('MYSQL_HOST') or 'localhost'
    MYSQL_USER = os.environ.get('MYSQL_USER') or 'voucher_user'
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD') or 'VoucherSecure123!'
    MYSQL_DB = os.environ.get('MYSQL_DB') or 'voucher_db'
    MYSQL_CHARSET = 'utf8mb4'
    
    # SQLAlchemy configuration for MariaDB
    SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}?charset={MYSQL_CHARSET}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_timeout': 20,
        'pool_recycle': -1,
        'pool_pre_ping': True,
        'echo': False  # Set to True for debugging SQL queries
    }
    
    # Application settings
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    TESTING = False
    
    # File upload configuration
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or '/opt/bitnami/projects/voucher-ro/static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # PDF Generation settings
    PDF_TEMPLATE_FOLDER = os.environ.get('PDF_TEMPLATE_FOLDER') or '/opt/bitnami/projects/voucher-ro/templates/pdf'
    PDF_OUTPUT_FOLDER = os.environ.get('PDF_OUTPUT_FOLDER') or '/opt/bitnami/projects/voucher-ro/static/generated_pdfs'
    PNG_OUTPUT_FOLDER = os.environ.get('PNG_OUTPUT_FOLDER') or '/opt/bitnami/projects/voucher-ro/static/generated_pngs'
    
    # WeasyPrint configuration
    WEASYPRINT_BASE_URL = os.environ.get('WEASYPRINT_BASE_URL') or 'http://localhost:5000'
    WEASYPRINT_TIMEOUT = int(os.environ.get('WEASYPRINT_TIMEOUT', '30'))
    
    # Templates
    QUOTE_TEMPLATE = 'quote_template_final_qt.html'
    VOUCHER_TEMPLATE = 'voucher_template_final.html'
    
    # Social sharing configuration
    LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
    LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
    
    FACEBOOK_APP_ID = os.environ.get('FACEBOOK_APP_ID')
    FACEBOOK_APP_SECRET = os.environ.get('FACEBOOK_APP_SECRET')
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Security settings
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    
    # Logging configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', '/opt/bitnami/projects/voucher-ro/logs/app.log')
    
    # Email configuration (for notifications)
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', '587'))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
    
    # Cache configuration
    CACHE_TYPE = 'simple'  # Use Redis in production
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Rate limiting
    RATELIMIT_STORAGE_URL = 'memory://'
    
class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_ENGINE_OPTIONS = {
        **Config.SQLALCHEMY_ENGINE_OPTIONS,
        'echo': True  # Show SQL queries in development
    }

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # Enhanced security for production
    SESSION_COOKIE_SECURE = True
    PREFERRED_URL_SCHEME = 'https'
    
    # Production logging
    LOG_LEVEL = 'WARNING'
    
    # Use Redis for caching in production
    CACHE_TYPE = 'redis'
    CACHE_REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    WTF_CSRF_ENABLED = False
    
    # Use separate test database
    MYSQL_DB = 'voucher_db_test'
    SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{Config.MYSQL_USER}:{Config.MYSQL_PASSWORD}@{Config.MYSQL_HOST}/{MYSQL_DB}?charset={Config.MYSQL_CHARSET}'

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get configuration based on environment"""
    return config[os.environ.get('FLASK_ENV', 'default')]