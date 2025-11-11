from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from extensions import db
from utils.datetime_utils import naive_utc_now
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='Staff')
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=naive_utc_now)
    updated_at = db.Column(db.DateTime, default=naive_utc_now, onupdate=naive_utc_now)
    
    def set_password(self, password):
        """Set password hash for user"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if provided password matches user's password"""
        return check_password_hash(self.password_hash, password)
    
    @classmethod
    def create_user(cls, username, email, password, is_admin=False, role=None):
        """Create a new user"""
        if role is None:
            role = 'Administrator' if is_admin else 'Staff'
            
        user = cls(
            username=username,
            email=email,
            role=role,
            is_admin=is_admin
        )
        user.set_password(password)
        return user
    
    def __repr__(self):
        return f'<User {self.username}>'
