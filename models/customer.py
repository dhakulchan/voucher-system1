from extensions import db
from utils.datetime_utils import naive_utc_now
from sqlalchemy import Column, Integer, String, Text, DECIMAL, DateTime
from datetime_fix import SafeDateTime
from extensions import db
# Initialize datetime compatibility - TEMPORARILY DISABLED
import datetime_fix



class Customer(db.Model):
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    # ฟิลด์เดิม
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    address = db.Column(db.Text)
    invoice_ninja_client_id = db.Column(db.Integer)  # Invoice Ninja client ID
    created_at = db.Column(SafeDateTime, default=naive_utc_now)
    updated_at = db.Column(SafeDateTime, default=naive_utc_now, onupdate=naive_utc_now)

    # ฟิลด์ใหม่ (อาจถูกเติมโดยสคริปต์ migration ถ้ายังไม่มีใน DB)
    first_name = db.Column(db.String(150))
    last_name = db.Column(db.String(150))
    nationality = db.Column(db.String(120))
    notes = db.Column(db.Text)

    # Relationships
    bookings = db.relationship('Booking', backref='customer', lazy=True)

    @property
    def full_name(self):
        if self.first_name or self.last_name:
            return f"{self.first_name or ''} {self.last_name or ''}".strip()
        return self.name

    def sync_name(self):
        """อัปเดตฟิลด์ name ให้สอดคล้องกับ first_name / last_name"""
        if self.first_name or self.last_name:
            combined = f"{self.first_name or ''} {self.last_name or ''}".strip()
            if combined:
                self.name = combined

    def __repr__(self):
        return f'<Customer {self.full_name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'full_name': self.full_name,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'phone': self.phone,
            'address': self.address,
            'nationality': self.nationality,
            'notes': self.notes,
            'invoice_ninja_client_id': self.invoice_ninja_client_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
