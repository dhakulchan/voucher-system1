"""
Quote model for QT workflow - Enhanced booking workflow with social media sharing
"""
from extensions import db
from datetime import datetime, timedelta
import secrets
import string
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Numeric
from sqlalchemy.orm import relationship

class Quote(db.Model):
    """Enhanced Quote model for QT workflow with social media sharing"""
    __tablename__ = 'quotes'
    
    # Primary Fields
    id = Column(Integer, primary_key=True)
    quote_number = Column(String(20), unique=True, nullable=False)  # QT20250909001
    booking_id = Column(Integer, ForeignKey('bookings.id'), nullable=False)
    
    # Quote Status and Information
    quote_date = Column(DateTime, default=datetime.utcnow)
    valid_until = Column(DateTime, nullable=False)
    status = Column(String(20), default='draft')  # draft, sent, accepted, expired, converted
    title = Column(String(200), nullable=False)
    description = Column(Text)
    validity_days = Column(Integer, default=30)
    
    # Financial Information  
    subtotal = db.Column(Numeric(10, 2), nullable=False, default=0.00)
    tax_rate = db.Column(Numeric(5, 2), default=7.00)  # 7% VAT
    tax_amount = db.Column(Numeric(10, 2), nullable=False, default=0.00)
    discount_amount = db.Column(Numeric(10, 2), nullable=False, default=0.00)
    total_amount = db.Column(Numeric(10, 2), nullable=False, default=0.00)
    currency = Column(String(3), default='THB')
    
    # Quote Details
    terms_conditions = Column(Text)
    notes = Column(Text)
    
    # Workflow Integration
    converted_to_invoice = Column(Boolean, default=False)
    converted_invoice_number = Column(String(50))  # Store invoice number instead of FK
    
    # Enhanced Sharing and Access
    share_token = Column(String(100), unique=True)
    public_url = Column(String(500))
    is_public = Column(Boolean, default=False)
    public_expiry = Column(DateTime)
    
    # Document Generation
    pdf_path = Column(String(500))
    png_path = Column(String(500))
    pdf_generated = Column(Boolean, default=False)
    png_generated = Column(Boolean, default=False)
    
    # Social Media Sharing
    facebook_shared = Column(Boolean, default=False)
    line_shared = Column(Boolean, default=False)
    instagram_shared = Column(Boolean, default=False)
    shared_count = Column(Integer, default=0)
    
    # Tracking
    view_count = Column(Integer, default=0)
    last_viewed_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    sent_at = Column(DateTime)
    
    # Relationships - Use back_populates to avoid backref conflicts
    # booking = relationship("Booking", back_populates="quotes", foreign_keys=[booking_id])  # Temporarily disabled
    
    def __init__(self, booking_id, **kwargs):
        super(Quote, self).__init__(**kwargs)
        self.booking_id = booking_id
        if not self.quote_number:
            self.quote_number = self._generate_quote_number()
        if not self.share_token:
            self.share_token = self.generate_share_token()
        if not self.valid_until and self.validity_days:
            self.valid_until = datetime.utcnow() + timedelta(days=self.validity_days)
        if not self.title:
            # Since booking relationship is disabled, use a generic title
            self.title = f"Travel Quote #{self.quote_number}"
        
    def generate_share_token(self):
        """Generate a unique share token"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(64))
        
    def _generate_quote_number(self):
        """Generate unique quote number starting from QT25110001"""
        from datetime import datetime
        
        # Find the highest existing quote number from both quotes and bookings tables
        # Check quotes table
        last_quote = Quote.query.filter(
            Quote.quote_number.like('QT2511%')
        ).order_by(Quote.quote_number.desc()).first()
        
        # Check bookings table  
        from models.booking import Booking
        last_booking_quote = Booking.query.filter(
            Booking.quote_number.like('QT2511%')
        ).order_by(Booking.quote_number.desc()).first()
        
        # Get the highest number from both sources
        max_number = 0
        
        if last_quote and last_quote.quote_number.startswith('QT2511'):
            try:
                numeric_part = last_quote.quote_number[6:]  # Remove 'QT2511' prefix
                max_number = max(max_number, int(numeric_part))
            except (ValueError, IndexError):
                pass
                
        if last_booking_quote and last_booking_quote.quote_number.startswith('QT2511'):
            try:
                numeric_part = last_booking_quote.quote_number[6:]  # Remove 'QT2511' prefix
                max_number = max(max_number, int(numeric_part))
            except (ValueError, IndexError):
                pass
        
        new_number = max_number + 1
        
        # Make sure the number is unique by checking both tables
        while True:
            candidate_number = f'QT2511{new_number:04d}'
            existing_quote = Quote.query.filter(Quote.quote_number == candidate_number).first()
            existing_booking = Booking.query.filter(Booking.quote_number == candidate_number).first()
            if not existing_quote and not existing_booking:
                return candidate_number
            new_number += 1
    
    @property
    def is_expired(self):
        """Check if quote is expired"""
        return datetime.utcnow() > self.valid_until
    
    @property
    def days_until_expiry(self):
        """Get days until expiry"""
        if not self.valid_until:
            return None
        delta = self.valid_until - datetime.utcnow()
        return max(0, delta.days)
    
    @property
    def is_valid(self):
        """Check if quote is still valid"""
        return not self.is_expired and self.status not in ['expired', 'converted']
    
    def mark_as_sent(self):
        """Mark quote as sent"""
        self.status = 'sent'
        self.sent_at = datetime.utcnow()
        self.is_public = True
        if not self.public_expiry:
            self.public_expiry = datetime.utcnow() + timedelta(days=self.validity_days)
    
    def mark_as_accepted(self):
        """Mark quote as accepted"""
        self.status = 'accepted'
    
    def mark_as_expired(self):
        """Mark quote as expired"""
        self.status = 'expired'
        self.is_public = False
    
    def mark_as_converted(self):
        """Mark quote as converted to booking"""
        self.status = 'converted'
    
    def increment_view(self):
        """Increment view count"""
        self.view_count += 1
        self.last_viewed_at = datetime.utcnow()
    
    def increment_share(self, platform=None):
        """Increment share count and mark platform as shared"""
        self.shared_count += 1
        if platform == 'facebook':
            self.facebook_shared = True
        elif platform == 'line':
            self.line_shared = True
        elif platform == 'instagram':
            self.instagram_shared = True
    
    def get_public_url(self, base_url):
        """Get public sharing URL"""
        return f"{base_url}/quote/public/{self.share_token}"
    
    def get_pdf_url(self, base_url):
        """Get PDF download URL"""
        return f"{base_url}/quote/{self.id}/pdf"
    
    def get_png_url(self, base_url):
        """Get PNG download URL"""
        return f"{base_url}/quote/{self.id}/png"
    
    def get_facebook_share_url(self, base_url):
        """Get Facebook share URL"""
        quote_url = self.get_public_url(base_url)
        return f"https://www.facebook.com/sharer/sharer.php?u={quote_url}"
    
    def get_line_share_url(self, base_url):
        """Get LINE share URL"""
        quote_url = self.get_public_url(base_url)
        text = f"Check out this travel quote: {self.title}"
        return f"https://line.me/R/msg/text/?{text}%0A{quote_url}"
    
    def calculate_totals(self):
        """Calculate quote totals"""
        self.total_amount = self.subtotal + self.tax_amount - self.discount_amount
        return self.total_amount
    
    def extend_expiry(self, days):
        """Extend quote expiry by specified days"""
        if self.valid_until:
            self.valid_until += timedelta(days=days)
        else:
            self.valid_until = datetime.utcnow() + timedelta(days=days)
        
        # Update public expiry if quote is public
        if self.is_public:
            self.public_expiry = self.valid_until
    
    def revoke_public_access(self):
        """Revoke public access to quote"""
        self.is_public = False
        self.public_expiry = None
    
    def grant_public_access(self, days=None):
        """Grant public access to quote"""
        self.is_public = True
        if days:
            self.public_expiry = datetime.utcnow() + timedelta(days=days)
        elif self.valid_until:
            self.public_expiry = self.valid_until
        else:
            self.public_expiry = datetime.utcnow() + timedelta(days=30)
    
    @classmethod
    def create_from_booking(cls, booking):
        """Create a new quote from booking data"""
        quote = cls(
            booking_id=booking.id,
            title=f"Travel Quote for {booking.customer_name}",
            description=f"Quote for {booking.destination} tour",
            subtotal=booking.total_price or 0.0,
            total_amount=booking.total_price or 0.0
        )
        return quote

    def can_convert_to_invoice(self):
        """Check if quote can be converted to invoice"""
        return (self.status == 'accepted' and 
                not self.converted_to_invoice and 
                not self.is_expired)
    
    def to_dict(self):
        """Convert quote to dictionary"""
        return {
            'id': self.id,
            'quote_number': self.quote_number,
            'booking_id': self.booking_id,
            'status': self.status,
            'title': getattr(self, 'title', ''),
            'description': getattr(self, 'description', ''),
            'quote_date': self.quote_date.isoformat() if self.quote_date else None,
            'valid_until': self.valid_until.isoformat() if self.valid_until else None,
            'total_amount': float(self.total_amount) if self.total_amount else 0,
            'currency': getattr(self, 'currency', 'THB'),
            'converted_to_invoice': self.converted_to_invoice,
            'is_expired': self.is_expired,
            'days_until_expiry': self.days_until_expiry,
            'is_valid': self.is_valid,
            'view_count': getattr(self, 'view_count', 0),
            'shared_count': getattr(self, 'shared_count', 0),
            'share_token': getattr(self, 'share_token', None),
            'public_url': getattr(self, 'public_url', None),
            'is_public': getattr(self, 'is_public', False)
        }

class QuoteLineItem(db.Model):
    """Quote line items for detailed pricing breakdown"""
    __tablename__ = 'quote_line_items'
    
    id = Column(Integer, primary_key=True)
    quote_id = Column(Integer, ForeignKey('quotes.id'), nullable=False)
    
    # Line Item Details
    description = Column(String(500), nullable=False)
    quantity = Column(Numeric(10, 2), default=1)
    unit_price = Column(Numeric(12, 2), nullable=False)
    total_amount = Column(Numeric(12, 2), nullable=False)
    
    # Sorting
    sort_order = Column(Integer, default=0)
    
    # Meta
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    quote = relationship("Quote", backref="line_items")
    
    def __init__(self, **kwargs):
        super(QuoteLineItem, self).__init__(**kwargs)
        if self.quantity and self.unit_price:
            self.total_amount = self.quantity * self.unit_price
    
    def to_dict(self):
        """Convert line item to dictionary"""
        return {
            'id': self.id,
            'description': self.description,
            'quantity': float(self.quantity) if self.quantity else 0,
            'unit_price': float(self.unit_price) if self.unit_price else 0,
            'total_amount': float(self.total_amount) if self.total_amount else 0,
            'sort_order': self.sort_order
        }
