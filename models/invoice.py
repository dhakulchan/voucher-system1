from extensions import db
from utils.datetime_utils import naive_utc_now
import json
from decimal import Decimal

class Invoice(db.Model):
    __tablename__ = 'invoices'
    
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False)
    quote_id = db.Column(db.Integer, db.ForeignKey('quotes.id'), nullable=True)
    invoice_number = db.Column(db.String(100), unique=True, nullable=False)
    
    # Invoice Content
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # Pricing
    subtotal = db.Column(db.Numeric(12, 2), default=0)
    tax_rate = db.Column(db.Numeric(5, 2), default=7.0)  # 7% VAT in Thailand
    tax_amount = db.Column(db.Numeric(12, 2), default=0)
    discount_amount = db.Column(db.Numeric(12, 2), default=0)
    total_amount = db.Column(db.Numeric(12, 2), nullable=False)
    
    # Payment & Status Management
    status = db.Column(db.String(50), default='draft')  # draft, sent, paid, overdue, cancelled
    payment_status = db.Column(db.String(50), default='unpaid')  # unpaid, partial, paid, refunded
    paid_amount = db.Column(db.Numeric(12, 2), default=0)
    balance_due = db.Column(db.Numeric(12, 2))
    
    # Dates
    invoice_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    paid_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=naive_utc_now)
    updated_at = db.Column(db.DateTime, default=naive_utc_now, onupdate=naive_utc_now)
    
    # Document Generation
    pdf_path = db.Column(db.String(500))
    png_path = db.Column(db.String(500))
    
    # Sharing
    share_token = db.Column(db.String(100))
    public_url = db.Column(db.String(500))
    
    # Meta Data
    terms_conditions = db.Column(db.Text)
    notes = db.Column(db.Text)
    
    # Payment Information
    payment_method = db.Column(db.String(100))
    payment_reference = db.Column(db.String(200))
    bank_details = db.Column(db.Text)
    
    # Relationships
    booking = db.relationship('Booking', backref=db.backref('invoices', lazy=True))
    quote = db.relationship('Quote', backref=db.backref('invoices', lazy=True))
    line_items = db.relationship('InvoiceLineItem', backref='invoice', lazy=True, cascade='all, delete-orphan')
    payments = db.relationship('InvoicePayment', backref='invoice', lazy=True, cascade='all, delete-orphan')
    
    def __init__(self, **kwargs):
        super(Invoice, self).__init__(**kwargs)
        if not self.invoice_number:
            self.invoice_number = self.generate_invoice_number()
        if self.total_amount:
            self.balance_due = self.total_amount - self.paid_amount
    
    @staticmethod
    def generate_invoice_number():
        """Generate unique invoice number"""
        from datetime import datetime
        import random
        timestamp = datetime.now().strftime('%Y%m%d')
        random_num = random.randint(1000, 9999)
        return f"INV{timestamp}{random_num}"
    
    def calculate_totals(self):
        """Calculate invoice totals from line items"""
        self.subtotal = sum([item.total_amount for item in self.line_items])
        self.tax_amount = (self.subtotal * self.tax_rate / 100) if self.tax_rate else 0
        self.total_amount = self.subtotal + self.tax_amount - self.discount_amount
        self.balance_due = self.total_amount - self.paid_amount
        db.session.commit()
    
    def add_payment(self, amount, payment_method=None, reference=None, payment_date=None):
        """Add payment to invoice"""
        payment = InvoicePayment(
            invoice_id=self.id,
            amount=amount,
            payment_method=payment_method,
            reference=reference,
            payment_date=payment_date or naive_utc_now().date()
        )
        db.session.add(payment)
        
        # Update payment status
        self.paid_amount += amount
        self.balance_due = self.total_amount - self.paid_amount
        
        if self.paid_amount >= self.total_amount:
            self.payment_status = 'paid'
            self.paid_date = payment_date or naive_utc_now().date()
        elif self.paid_amount > 0:
            self.payment_status = 'partial'
        
        db.session.commit()
        return payment
    
    def to_dict(self):
        """Convert invoice to dictionary"""
        return {
            'id': self.id,
            'booking_id': self.booking_id,
            'quote_id': self.quote_id,
            'invoice_number': self.invoice_number,
            'title': self.title,
            'description': self.description,
            'subtotal': float(self.subtotal) if self.subtotal else 0,
            'tax_rate': float(self.tax_rate) if self.tax_rate else 0,
            'tax_amount': float(self.tax_amount) if self.tax_amount else 0,
            'discount_amount': float(self.discount_amount) if self.discount_amount else 0,
            'total_amount': float(self.total_amount) if self.total_amount else 0,
            'paid_amount': float(self.paid_amount) if self.paid_amount else 0,
            'balance_due': float(self.balance_due) if self.balance_due else 0,
            'status': self.status,
            'payment_status': self.payment_status,
            'invoice_date': self.invoice_date.isoformat() if self.invoice_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'paid_date': self.paid_date.isoformat() if self.paid_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'pdf_path': self.pdf_path,
            'png_path': self.png_path,
            'public_url': self.public_url,
            'terms_conditions': self.terms_conditions,
            'notes': self.notes,
            'payment_method': self.payment_method,
            'payment_reference': self.payment_reference,
            'line_items': [item.to_dict() for item in self.line_items],
            'payments': [payment.to_dict() for payment in self.payments]
        }

class InvoiceLineItem(db.Model):
    __tablename__ = 'invoice_line_items'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    
    # Line Item Details
    description = db.Column(db.String(500), nullable=False)
    quantity = db.Column(db.Numeric(10, 2), default=1)
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)
    total_amount = db.Column(db.Numeric(12, 2), nullable=False)
    
    # Sorting
    sort_order = db.Column(db.Integer, default=0)
    
    # Meta
    created_at = db.Column(db.DateTime, default=naive_utc_now)
    
    def __init__(self, **kwargs):
        super(InvoiceLineItem, self).__init__(**kwargs)
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

class InvoicePayment(db.Model):
    __tablename__ = 'invoice_payments'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    
    # Payment Details
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    payment_method = db.Column(db.String(100))  # cash, bank_transfer, credit_card, etc.
    reference = db.Column(db.String(200))  # transaction reference
    payment_date = db.Column(db.Date, nullable=False)
    
    # Meta
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=naive_utc_now)
    
    def to_dict(self):
        """Convert payment to dictionary"""
        return {
            'id': self.id,
            'amount': float(self.amount) if self.amount else 0,
            'payment_method': self.payment_method,
            'reference': self.reference,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
