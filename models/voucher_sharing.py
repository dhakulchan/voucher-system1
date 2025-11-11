"""
Voucher Sharing Models for Files and External Links
"""
from extensions import db
from datetime import datetime, timedelta
import secrets
import string

class VoucherFile(db.Model):
    __tablename__ = 'voucher_files'
    
    id = db.Column(db.Integer, primary_key=True)
    voucher_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(255))
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    mime_type = db.Column(db.String(100))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    public_token = db.Column(db.String(64), unique=True)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationship
    booking = db.relationship('Booking', backref='voucher_files')
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.public_token:
            self.public_token = self.generate_token()
    
    @staticmethod
    def generate_token():
        """Generate unique public access token"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(64))
    
    def set_expiry_from_booking(self, booking):
        """Set expiry date based on booking departure date + 120 days"""
        if booking and booking.departure_date:
            self.expires_at = booking.departure_date + timedelta(days=120)
        elif booking and booking.traveling_period_end:
            self.expires_at = booking.traveling_period_end + timedelta(days=120)
        else:
            # Fallback: 120 days from now
            self.expires_at = datetime.utcnow() + timedelta(days=120)
    
    def is_expired(self):
        """Check if file is expired"""
        return self.expires_at and datetime.utcnow() > self.expires_at
    
    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'title': self.title,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'public_token': self.public_token,
            'is_active': self.is_active
        }


class VoucherLink(db.Model):
    __tablename__ = 'voucher_links'
    
    id = db.Column(db.Integer, primary_key=True)
    voucher_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False)
    url = db.Column(db.Text, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    public_token = db.Column(db.String(64), unique=True)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationship
    booking = db.relationship('Booking', backref='voucher_links')
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.public_token:
            self.public_token = self.generate_token()
    
    @staticmethod
    def generate_token():
        """Generate unique public access token"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(64))
    
    def to_dict(self):
        return {
            'id': self.id,
            'url': self.url,
            'title': self.title,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'public_token': self.public_token,
            'is_active': self.is_active
        }