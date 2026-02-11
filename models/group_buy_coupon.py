"""
Group Buy Coupon Models
"""
from extensions import db
from utils.datetime_utils import naive_utc_now
from datetime import datetime

class GroupBuyCoupon(db.Model):
    """โมเดลสำหรับคูปองส่วนลด Group Buy"""
    __tablename__ = 'group_buy_coupons'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    
    # Discount configuration
    discount_type = db.Column(db.String(20), nullable=False, default='fixed')  # 'fixed' or 'percentage'
    discount_value = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Usage limits
    max_uses = db.Column(db.Integer)  # NULL = unlimited
    used_count = db.Column(db.Integer, default=0)
    max_uses_per_user = db.Column(db.Integer, default=1)
    
    # Conditions
    min_purchase_amount = db.Column(db.Numeric(10, 2), default=0.00)
    campaign_id = db.Column(db.Integer, db.ForeignKey('group_buy_campaigns.id', ondelete='SET NULL'))
    
    # Validity period
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    
    # Status
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=naive_utc_now)
    created_by = db.Column(db.Integer)
    updated_at = db.Column(db.DateTime, default=naive_utc_now, onupdate=naive_utc_now)
    
    # Relationships
    campaign = db.relationship('GroupBuyCampaign', backref='coupons')
    usage_logs = db.relationship('GroupBuyCouponUsage', backref='coupon', lazy='dynamic')
    
    def is_valid(self, campaign_id=None, amount=0, customer_email=None):
        """ตรวจสอบว่าคูปองใช้ได้หรือไม่"""
        now = naive_utc_now()
        
        # Check active status
        if not self.is_active:
            return False, "คูปองนี้ถูกปิดใช้งาน"
        
        # Check date range
        if now < self.start_date:
            return False, "คูปองยังไม่เริ่มใช้งาน"
        if now > self.end_date:
            return False, "คูปองหมดอายุแล้ว"
        
        # Check max uses - count from usage table instead of used_count field
        if self.max_uses:
            actual_usage_count = GroupBuyCouponUsage.query.filter_by(coupon_id=self.id).count()
            if actual_usage_count >= self.max_uses:
                return False, "คูปองถูกใช้หมดแล้ว"
        
        # Check campaign restriction
        if self.campaign_id and campaign_id and self.campaign_id != campaign_id:
            return False, "คูปองนี้ใช้ไม่ได้กับแคมเปญนี้"
        
        # Check minimum purchase
        if amount < float(self.min_purchase_amount):
            return False, f"ยอดซื้อขั้นต่ำ ฿{self.min_purchase_amount:,.2f}"
        
        # Check per-user limit
        if customer_email and self.max_uses_per_user:
            user_usage = self.usage_logs.filter_by(customer_email=customer_email).count()
            if user_usage >= self.max_uses_per_user:
                return False, "คุณใช้คูปองนี้ครบจำนวนแล้ว"
        
        return True, "ใช้ได้"
    
    def calculate_discount(self, amount):
        """คำนวณส่วนลด"""
        if self.discount_type == 'fixed':
            return min(float(self.discount_value), amount)
        elif self.discount_type == 'percentage':
            return amount * (float(self.discount_value) / 100)
        return 0
    
    def increment_usage(self):
        """เพิ่มจำนวนการใช้งาน"""
        self.used_count = (self.used_count or 0) + 1
    
    @property
    def is_unlimited(self):
        """ตรวจสอบว่าเป็นคูปองไม่จำกัดจำนวนหรือไม่"""
        return self.max_uses is None
    
    @property
    def remaining_uses(self):
        """จำนวนครั้งที่เหลือใช้ได้ - count from usage table"""
        if self.is_unlimited:
            return None
        actual_usage_count = GroupBuyCouponUsage.query.filter_by(coupon_id=self.id).count()
        return max(0, self.max_uses - actual_usage_count)
    
    def __repr__(self):
        return f'<GroupBuyCoupon {self.code}>'


class GroupBuyCouponUsage(db.Model):
    """บันทึกการใช้คูปอง"""
    __tablename__ = 'group_buy_coupon_usage'
    
    id = db.Column(db.Integer, primary_key=True)
    coupon_id = db.Column(db.Integer, db.ForeignKey('group_buy_coupons.id', ondelete='CASCADE'), nullable=False)
    participant_id = db.Column(db.Integer, db.ForeignKey('group_buy_participants.id', ondelete='SET NULL'))
    payment_id = db.Column(db.Integer)
    campaign_id = db.Column(db.Integer, db.ForeignKey('group_buy_campaigns.id', ondelete='SET NULL'))
    
    discount_amount = db.Column(db.Numeric(10, 2), nullable=False)
    original_amount = db.Column(db.Numeric(10, 2), nullable=False)
    final_amount = db.Column(db.Numeric(10, 2), nullable=False)
    customer_email = db.Column(db.String(255), index=True)
    
    used_at = db.Column(db.DateTime, default=naive_utc_now)
    
    def __repr__(self):
        return f'<CouponUsage {self.id}: {self.coupon.code if self.coupon else "N/A"}>'
