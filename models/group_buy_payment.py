"""
Payment System Models for Group Buy
"""
from extensions import db
from datetime import datetime

def naive_utc_now():
    """Return timezone-naive UTC datetime"""
    return datetime.utcnow()

class GroupBuyBankAccount(db.Model):
    """Bank accounts for receiving payments"""
    __tablename__ = 'group_buy_bank_accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    bank_name = db.Column(db.String(100), nullable=False)
    account_number = db.Column(db.String(50), nullable=False)
    account_name = db.Column(db.String(200), nullable=False)
    bank_logo = db.Column(db.String(500))
    is_active = db.Column(db.Boolean, default=True)
    display_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=naive_utc_now)
    updated_at = db.Column(db.DateTime, default=naive_utc_now, onupdate=naive_utc_now)
    
    def to_dict(self):
        return {
            'id': self.id,
            'bank_name': self.bank_name,
            'account_number': self.account_number,
            'account_name': self.account_name,
            'bank_logo': self.bank_logo,
            'is_active': self.is_active,
            'display_order': self.display_order
        }

class GroupBuyPayment(db.Model):
    """Payment transactions for Group Buy"""
    __tablename__ = 'group_buy_payments'
    
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, nullable=False)
    campaign_id = db.Column(db.Integer, nullable=False)
    group_id = db.Column(db.Integer)
    
    customer_name = db.Column(db.String(200))
    customer_email = db.Column(db.String(200))
    customer_phone = db.Column(db.String(50))
    
    payment_method = db.Column(db.String(50), nullable=False)  # stripe, bank_transfer, qr_code
    payment_status = db.Column(db.String(50), default='pending')  # pending, paid, refunded, failed
    
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    fee_amount = db.Column(db.Numeric(10, 2), default=0.00)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Bank Transfer fields
    bank_account_id = db.Column(db.Integer)
    transfer_date = db.Column(db.Date)
    transfer_time = db.Column(db.Time)
    slip_image = db.Column(db.String(500))
    
    # Stripe fields
    stripe_payment_intent_id = db.Column(db.String(200))
    stripe_charge_id = db.Column(db.String(200))
    
    # Admin verification
    admin_verified_by = db.Column(db.Integer)
    admin_verified_at = db.Column(db.DateTime)
    admin_notes = db.Column(db.Text)
    
    # Payment timestamp
    paid_at = db.Column(db.DateTime)
    
    # Refund fields
    refund_amount = db.Column(db.Numeric(10, 2))
    refund_reason = db.Column(db.Text)
    refunded_at = db.Column(db.DateTime)
    refunded_by = db.Column(db.Integer)
    
    # Payment timeout (15 minutes)
    payment_timeout = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=naive_utc_now)
    updated_at = db.Column(db.DateTime, default=naive_utc_now, onupdate=naive_utc_now)
    
    @property
    def status_label(self):
        """Return Thai status label"""
        labels = {
            'pending': 'รอดำเนินการ',
            'paid': 'ชำระเงินสำเร็จ',
            'refunded': 'คืนเงินแล้ว',
            'failed': 'ล้มเหลว'
        }
        return labels.get(self.payment_status, self.payment_status)
    
    @property
    def method_label(self):
        """Return Thai method label"""
        labels = {
            'stripe': 'บัตรเครดิต/เดบิต (Stripe)',
            'bank_transfer': 'โอนเงินผ่านธนาคาร',
            'qr_code': 'สแกน QR Code'
        }
        return labels.get(self.payment_method, self.payment_method)
    
    def to_dict(self):
        return {
            'id': self.id,
            'booking_id': self.booking_id,
            'campaign_id': self.campaign_id,
            'group_id': self.group_id,
            'customer_name': self.customer_name,
            'customer_email': self.customer_email,
            'customer_phone': self.customer_phone,
            'payment_method': self.payment_method,
            'method_label': self.method_label,
            'payment_status': self.payment_status,
            'status_label': self.status_label,
            'amount': float(self.amount) if self.amount else 0,
            'fee_amount': float(self.fee_amount) if self.fee_amount else 0,
            'total_amount': float(self.total_amount) if self.total_amount else 0,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
