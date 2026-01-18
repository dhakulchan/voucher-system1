"""
Database model for passport extraction temporary storage
Stores extracted passport data pending user confirmation
Auto-cleanup after 24 hours (PDPA compliance)
"""

from extensions import db
from utils.datetime_utils import naive_utc_now
from sqlalchemy.dialects.mysql import JSON

class PassportExtraction(db.Model):
    """Temporary storage for passport MRZ extractions pending confirmation"""
    __tablename__ = 'passport_extractions'
    
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False, index=True)
    filename_hash = db.Column(db.String(32), nullable=False)  # SHA256 hash (first 16 chars)
    extracted_data = db.Column(JSON, nullable=False)  # Full MRZ extraction result
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    confirmed = db.Column(db.Boolean, default=False, nullable=False, index=True)
    confirmed_at = db.Column(db.DateTime, nullable=True)
    confirmed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=naive_utc_now, nullable=False, index=True)
    
    # Relationships
    booking = db.relationship('Booking', backref='passport_extractions', lazy=True)
    user = db.relationship('User', foreign_keys=[user_id], backref='passport_extractions', lazy=True)
    confirmer = db.relationship('User', foreign_keys=[confirmed_by], lazy=True)
    
    def __repr__(self):
        return f'<PassportExtraction {self.id} - Booking {self.booking_id}>'
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'booking_id': self.booking_id,
            'filename_hash': self.filename_hash,
            'extracted_data': self.extracted_data,
            'user_id': self.user_id,
            'confirmed': self.confirmed,
            'confirmed_at': self.confirmed_at.isoformat() if self.confirmed_at else None,
            'confirmed_by': self.confirmed_by,
            'created_at': self.created_at.isoformat()
        }
