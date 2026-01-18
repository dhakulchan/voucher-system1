"""
Enhanced Models for MariaDB Unified Voucher System
SQLAlchemy ORM models with complete workflow support
"""

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event, text
from sqlalchemy.orm import relationship, foreign
from datetime import datetime, date, timedelta
import json
import secrets
import string

db = SQLAlchemy()

# Import BookingTask model
from models.booking_task import BookingTask

class NumberSequence(db.Model):
    """Number sequences for booking, quote, voucher numbering"""
    __tablename__ = 'number_sequences'
    
    id = db.Column(db.Integer, primary_key=True)
    sequence_type = db.Column(db.Enum('booking', 'quote', 'voucher'), unique=True, nullable=False)
    current_number = db.Column(db.Integer, nullable=False, default=1000)
    prefix = db.Column(db.String(10), nullable=False, default='')
    suffix = db.Column(db.String(10), nullable=False, default='')
    format_template = db.Column(db.String(50), nullable=False, default='%s%06d%s')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @classmethod
    def get_next_number(cls, sequence_type):
        """Get next number for sequence type"""
        sequence = cls.query.filter_by(sequence_type=sequence_type).first()
        if not sequence:
            # Create default sequence
            sequence = cls(
                sequence_type=sequence_type,
                current_number=1000,
                prefix=sequence_type.upper()[:2],
                format_template=f'{sequence_type.upper()[:2]}%06d'
            )
            db.session.add(sequence)
        
        sequence.current_number += 1
        db.session.commit()
        return sequence.current_number, sequence.format_template

class Customer(db.Model):
    """Enhanced customer model"""
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    country = db.Column(db.String(100))
    postal_code = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    bookings = relationship('Booking', back_populates='customer', lazy='dynamic')
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def to_dict(self):
        return {
            'id': self.id,
            'full_name': self.full_name,
            'email': self.email,
            'phone': self.phone,
            'address': self.address,
            'city': self.city,
            'country': self.country
        }

class Booking(db.Model):
    """Enhanced booking model with workflow support"""
    __tablename__ = 'bookings'
    
    id = db.Column(db.Integer, primary_key=True)
    booking_number = db.Column(db.String(50), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    booking_date = db.Column(db.Date, nullable=False)
    return_date = db.Column(db.Date)
    adults = db.Column(db.Integer, default=1)
    children = db.Column(db.Integer, default=0)
    infants = db.Column(db.Integer, default=0)
    
    # Workflow status
    status = db.Column(db.Enum('draft', 'confirmed', 'cancelled', 'completed'), default='draft')
    
    # Flight information
    departure_flight = db.Column(db.String(100))
    departure_time = db.Column(db.Time)
    arrival_flight = db.Column(db.String(100))
    arrival_time = db.Column(db.Time)
    departure_airport = db.Column(db.String(100))
    arrival_airport = db.Column(db.String(100))
    
    # Guest list and special requirements
    guest_list = db.Column(db.Text)
    special_requirements = db.Column(db.Text)
    dietary_requirements = db.Column(db.Text)
    
    # Financial fields
    total_amount = db.Column(db.Numeric(10, 2), default=0.00)
    deposit_amount = db.Column(db.Numeric(10, 2), default=0.00)
    is_paid = db.Column(db.Boolean, default=False)
    payment_status = db.Column(db.Enum('unpaid', 'partial', 'paid', 'refunded'), default='unpaid')
    payment_method = db.Column(db.String(50))
    payment_reference = db.Column(db.String(100))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime)
    
    # Quote reference (denormalized for quick access)
    quote_id = db.Column(db.Integer, db.ForeignKey('quotes.id', ondelete='SET NULL'), nullable=True)
    quote_number = db.Column(db.String(50), nullable=True)
    
    # Metadata
    notes = db.Column(db.Text)
    internal_notes = db.Column(db.Text)
    
    # Relationships
    customer = relationship('Customer', back_populates='bookings')
    products = relationship('BookingProduct', back_populates='booking', cascade='all, delete-orphan')
    quotes = relationship('Quote', back_populates='booking', cascade='all, delete-orphan', 
                         foreign_keys='Quote.booking_id')
    vouchers = relationship('Voucher', back_populates='booking', cascade='all, delete-orphan')
    
    @property
    def total_guests(self):
        return (self.adults or 0) + (self.children or 0) + (self.infants or 0)
    
    @property
    def balance_amount(self):
        return (self.total_amount or 0) - (self.deposit_amount or 0)
    
    def can_create_quote(self):
        """Check if booking can have a quote created"""
        return self.status in ['confirmed'] and not self.quotes.filter_by(status='accepted').first()
    
    def get_active_quote(self):
        """Get active quote for this booking"""
        return self.quotes.filter(Quote.status.in_(['draft', 'sent', 'accepted'])).first()
    
    def to_dict(self):
        return {
            'id': self.id,
            'booking_number': self.booking_number,
            'customer': self.customer.to_dict() if self.customer else None,
            'booking_date': self.booking_date.isoformat() if self.booking_date else None,
            'total_guests': self.total_guests,
            'status': self.status,
            'total_amount': float(self.total_amount) if self.total_amount else 0,
            'payment_status': self.payment_status
        }

class BookingProduct(db.Model):
    """Booking products/services"""
    __tablename__ = 'booking_products'
    
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False)
    product_name = db.Column(db.String(200), nullable=False)
    product_type = db.Column(db.String(100))
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    description = db.Column(db.Text)
    
    # Relationships
    booking = relationship('Booking', back_populates='products')
    
    @property
    def total_price(self):
        return (self.quantity or 0) * (self.unit_price or 0)
    
    def to_dict(self):
        return {
            'id': self.id,
            'product_name': self.product_name,
            'quantity': self.quantity,
            'unit_price': float(self.unit_price) if self.unit_price else 0,
            'total_price': float(self.total_price)
        }

class Quote(db.Model):
    """Enhanced quote model"""
    __tablename__ = 'quotes'
    
    id = db.Column(db.Integer, primary_key=True)
    quote_number = db.Column(db.String(50), unique=True, nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False)
    
    # Quote status workflow
    status = db.Column(db.Enum('draft', 'sent', 'accepted', 'rejected', 'expired'), default='draft')
    
    # Pricing details
    subtotal = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    tax_amount = db.Column(db.Numeric(10, 2), default=0.00)
    discount_amount = db.Column(db.Numeric(10, 2), default=0.00)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    
    # Validity
    valid_until = db.Column(db.Date)
    
    # Quote generation info
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    sent_at = db.Column(db.DateTime)
    accepted_at = db.Column(db.DateTime)
    
    # Document paths
    pdf_path = db.Column(db.String(255))
    png_path = db.Column(db.String(255))
    
    # Templates used
    template_used = db.Column(db.String(100), default='quote_template_final_qt.html')
    
    # Metadata
    notes = db.Column(db.Text)
    terms_conditions = db.Column(db.Text)
    
    # Relationships
    booking = relationship('Booking', back_populates='quotes', foreign_keys=[booking_id])
    vouchers = relationship('Voucher', back_populates='quote', cascade='all, delete-orphan')
    document_shares = relationship('DocumentShare', 
                                 primaryjoin="and_(Quote.id==foreign(DocumentShare.document_id), DocumentShare.document_type=='quote')",
                                 cascade='all, delete-orphan')
    
    def can_create_voucher(self):
        """Check if quote can have a voucher created"""
        return (self.status == 'accepted' and 
                self.booking.payment_status == 'paid' and 
                not self.vouchers.filter_by(status='active').first())
    
    def get_share_url(self):
        """Get public share URL"""
        share = self.document_shares.filter_by(share_type='public_link').first()
        if share:
            return f"/share/quote/{share.share_token}"
        return None
    
    def to_dict(self):
        return {
            'id': self.id,
            'quote_number': self.quote_number,
            'booking': self.booking.to_dict() if self.booking else None,
            'status': self.status,
            'total_amount': float(self.total_amount) if self.total_amount else 0,
            'valid_until': self.valid_until.isoformat() if self.valid_until else None,
            'generated_at': self.generated_at.isoformat() if self.generated_at else None
        }

class Voucher(db.Model):
    """Enhanced voucher model"""
    __tablename__ = 'vouchers'
    
    id = db.Column(db.Integer, primary_key=True)
    voucher_number = db.Column(db.String(50), unique=True, nullable=False)
    quote_id = db.Column(db.Integer, db.ForeignKey('quotes.id'), nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False)
    
    # Voucher status
    status = db.Column(db.Enum('active', 'used', 'expired', 'cancelled'), default='active')
    
    # Voucher details
    issue_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date)
    
    # Service details
    service_date = db.Column(db.Date)
    service_time = db.Column(db.Time)
    pickup_location = db.Column(db.String(255))
    dropoff_location = db.Column(db.String(255))
    
    # Document paths
    pdf_path = db.Column(db.String(255))
    png_path = db.Column(db.String(255))
    
    # QR code for verification
    qr_code_data = db.Column(db.Text)
    qr_code_path = db.Column(db.String(255))
    
    # Usage tracking
    used_at = db.Column(db.DateTime)
    used_by = db.Column(db.String(100))
    
    # Templates used
    template_used = db.Column(db.String(100), default='voucher_template_final.html')
    
    # Metadata
    notes = db.Column(db.Text)
    special_instructions = db.Column(db.Text)
    
    # Relationships
    quote = relationship('Quote', back_populates='vouchers')
    booking = relationship('Booking', back_populates='vouchers')
    document_shares = relationship('DocumentShare',
                                 primaryjoin="and_(Voucher.id==foreign(DocumentShare.document_id), DocumentShare.document_type=='voucher')",
                                 cascade='all, delete-orphan')
    
    def is_valid(self):
        """Check if voucher is still valid"""
        if self.status != 'active':
            return False
        if self.expiry_date and date.today() > self.expiry_date:
            return False
        return True
    
    def get_share_url(self):
        """Get public share URL"""
        share = self.document_shares.filter_by(share_type='public_link').first()
        if share:
            return f"/share/voucher/{share.share_token}"
        return None
    
    def to_dict(self):
        return {
            'id': self.id,
            'voucher_number': self.voucher_number,
            'quote': self.quote.to_dict() if self.quote else None,
            'booking': self.booking.to_dict() if self.booking else None,
            'status': self.status,
            'service_date': self.service_date.isoformat() if self.service_date else None,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'is_valid': self.is_valid()
        }

class DocumentShare(db.Model):
    """Document sharing tracking for social features"""
    __tablename__ = 'document_shares'
    
    id = db.Column(db.Integer, primary_key=True)
    document_type = db.Column(db.Enum('quote', 'voucher'), nullable=False)
    document_id = db.Column(db.Integer, nullable=False)
    share_token = db.Column(db.String(100), unique=True, nullable=False)
    share_type = db.Column(db.Enum('line_oa', 'line_message', 'facebook', 'twitter', 'email', 'public_link'), nullable=False)
    
    # Share tracking
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    accessed_count = db.Column(db.Integer, default=0)
    last_accessed_at = db.Column(db.DateTime)
    
    # Share metadata
    shared_by = db.Column(db.String(100))
    recipient_info = db.Column(db.Text)
    
    def is_expired(self):
        """Check if share link has expired"""
        return self.expires_at and datetime.utcnow() > self.expires_at
    
    @classmethod
    def create_share_token(cls, document_type, document_id, share_type, expires_days=30):
        """Create new share token"""
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(days=expires_days) if expires_days else None
        
        share = cls(
            document_type=document_type,
            document_id=document_id,
            share_token=token,
            share_type=share_type,
            expires_at=expires_at
        )
        db.session.add(share)
        db.session.commit()
        return token

class ActivityLog(db.Model):
    """Activity log for workflow tracking - matches existing table schema"""
    __tablename__ = 'activity_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer)  # Add missing booking_id column
    user_id = db.Column(db.Integer)
    action = db.Column(db.String(100))
    description = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @classmethod
    def log_activity(cls, entity_type, entity_id, action, description=None, old_status=None, new_status=None):
        """Log an activity - compatible with existing activity_logs table"""
        from extensions import db as app_db
        
        # Create log with booking_id properly set
        log = cls(
            booking_id=entity_id if entity_type == 'booking' else None,
            action=action,
            description=description,
            user_id=None,  # Will be set by the database if needed
            ip_address=None,
            user_agent=None
        )
        app_db.session.add(log)
        app_db.session.commit()

class DocumentGeneration(db.Model):
    """Document generation tracking"""
    __tablename__ = 'document_generations'
    
    id = db.Column(db.Integer, primary_key=True)
    document_type = db.Column(db.Enum('quote_pdf', 'quote_png', 'voucher_pdf', 'voucher_png'), nullable=False)
    entity_type = db.Column(db.Enum('quote', 'voucher'), nullable=False)
    entity_id = db.Column(db.Integer, nullable=False)
    template_used = db.Column(db.String(100))
    generation_status = db.Column(db.Enum('success', 'error'), nullable=False)
    file_path = db.Column(db.String(255))
    file_size = db.Column(db.Integer)
    generation_time_ms = db.Column(db.Integer)
    error_message = db.Column(db.Text)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)

# Event listeners for automatic numbering
@event.listens_for(Booking, 'before_insert')
def generate_booking_number(mapper, connection, target):
    """Auto-generate booking number"""
    if not target.booking_number:
        next_num, format_template = NumberSequence.get_next_number('booking')
        target.booking_number = f"BK{date.today().strftime('%Y%m%d')}{next_num:06d}"

@event.listens_for(Quote, 'before_insert')
def generate_quote_number(mapper, connection, target):
    """Auto-generate quote number using app_settings"""
    if not target.quote_number:
        # Get next_quote_number from app_settings
        result = connection.execute(
            text("SELECT setting_value FROM app_settings WHERE setting_key = 'next_quote_number'")
        ).fetchone()
        
        if result and result[0]:
            current_value = str(result[0]).strip()
            
            # Remove QT prefix if exists
            if current_value.startswith('QT'):
                current_value = current_value[2:]
            
            try:
                next_number = int(current_value)
                target.quote_number = f'QT{next_number}'
                
                # Update app_settings with next number
                connection.execute(
                    text("UPDATE app_settings SET setting_value = :next_value, updated_at = NOW() WHERE setting_key = 'next_quote_number'"),
                    {"next_value": str(next_number + 1)}
                )
            except ValueError:
                # Fallback to default
                target.quote_number = 'QT2601001'
                connection.execute(
                    text("UPDATE app_settings SET setting_value = '2601002', updated_at = NOW() WHERE setting_key = 'next_quote_number'")
                )
        else:
            # Initialize if not exists
            target.quote_number = 'QT2601001'
            connection.execute(
                text("INSERT INTO app_settings (setting_key, setting_value, updated_at) VALUES ('next_quote_number', '2601002', NOW()) ON DUPLICATE KEY UPDATE setting_value = '2601002', updated_at = NOW()")
            )

@event.listens_for(Voucher, 'before_insert')
def generate_voucher_number(mapper, connection, target):
    """Auto-generate voucher number"""
    if not target.voucher_number:
        next_num, format_template = NumberSequence.get_next_number('voucher')
        target.voucher_number = f"VC{date.today().strftime('%Y%m%d')}{next_num:06d}"

# Activity logging listeners
@event.listens_for(Booking.status, 'set')
def log_booking_status_change(target, value, oldvalue, initiator):
    """Log booking status changes"""
    if oldvalue != value and oldvalue is not None:
        ActivityLog.log_activity('booking', target.id, 'status_change', 
                               f'Status changed from {oldvalue} to {value}',
                               oldvalue, value)

@event.listens_for(Quote.status, 'set')
def log_quote_status_change(target, value, oldvalue, initiator):
    """Log quote status changes"""
    if oldvalue != value and oldvalue is not None:
        ActivityLog.log_activity('quote', target.id, 'status_change',
                               f'Status changed from {oldvalue} to {value}',
                               oldvalue, value)

@event.listens_for(Voucher.status, 'set')
def log_voucher_status_change(target, value, oldvalue, initiator):
    """Log voucher status changes"""
    if oldvalue != value and oldvalue is not None:
        ActivityLog.log_activity('voucher', target.id, 'status_change',
                               f'Status changed from {oldvalue} to {value}',
                               oldvalue, value)