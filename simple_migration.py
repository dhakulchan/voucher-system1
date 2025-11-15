#!/usr/bin/env python3
"""
Simple migration script for initial deployment
"""

import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import secrets

def create_app():
    app = Flask(__name__)
    
    # Configuration
    db_password = sys.argv[1] if len(sys.argv) > 1 else 'default_password'
    
    app.config['SECRET_KEY'] = secrets.token_urlsafe(32)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://voucher_user:{db_password}@localhost/voucher_db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db = SQLAlchemy(app)
    migrate = Migrate(app, db)
    
    return app, db

if __name__ == '__main__':
    app, db = create_app()
    
    print("🔄 Creating database tables...")
    with app.app_context():
        try:
            db.create_all()
            print("✅ Database tables created successfully!")
        except Exception as e:
            print(f"❌ Error creating tables: {e}")
            sys.exit(1)
    
    print("✅ Simple migration completed!")