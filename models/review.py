"""
Review System Models
ระบบรีวิวและคะแนนสะสม
"""
from extensions import db
from datetime import datetime


class CampaignReview(db.Model):
    """รีวิวแคมเปญ"""
    __tablename__ = 'campaign_reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('group_buy_campaigns.id', ondelete='CASCADE'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id', ondelete='CASCADE'), nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id', ondelete='SET NULL'), nullable=True)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    review_text = db.Column(db.Text, nullable=True)
    is_approved = db.Column(db.Boolean, default=False)
    is_featured = db.Column(db.Boolean, default=False)
    helpful_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    campaign = db.relationship('GroupBuyCampaign', foreign_keys=[campaign_id])
    customer = db.relationship('Customer', foreign_keys=[customer_id])
    images = db.relationship('ReviewImage', backref='review', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<CampaignReview {self.id}: Campaign {self.campaign_id} - {self.rating} stars>'


class ReviewImage(db.Model):
    """รูปภาพรีวิว"""
    __tablename__ = 'review_images'
    
    id = db.Column(db.Integer, primary_key=True)
    review_id = db.Column(db.Integer, db.ForeignKey('campaign_reviews.id', ondelete='CASCADE'), nullable=False)
    image_path = db.Column(db.String(500), nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    display_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ReviewImage {self.id}: Review {self.review_id}>'


class CustomerPoints(db.Model):
    """คะแนนสะสมของลูกค้า"""
    __tablename__ = 'customer_points'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id', ondelete='CASCADE'), nullable=False, unique=True)
    total_points = db.Column(db.Integer, default=0)  # คะแนนทั้งหมดที่เคยได้
    available_points = db.Column(db.Integer, default=0)  # คะแนนที่ใช้ได้
    used_points = db.Column(db.Integer, default=0)  # คะแนนที่ใช้ไปแล้ว
    expired_points = db.Column(db.Integer, default=0)  # คะแนนที่หมดอายุ
    lifetime_points = db.Column(db.Integer, default=0)  # คะแนนตลอดชีพ
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # ลบ relationship transactions ออก เพราะ PointTransaction ไม่มี FK มา CustomerPoints
    # transactions = db.relationship('PointTransaction', backref='customer_points', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<CustomerPoints {self.id}: Customer {self.customer_id} - {self.available_points} points>'
    
    def can_redeem(self, points):
        """ตรวจสอบว่ามีคะแนนพอจะใช้หรือไม่"""
        return self.available_points >= points


class PointTransaction(db.Model):
    """ประวัติการได้/ใช้คะแนน"""
    __tablename__ = 'point_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id', ondelete='CASCADE'), nullable=False)
    transaction_type = db.Column(db.Enum('earn', 'redeem', 'expire', 'adjustment', name='transaction_type_enum'), nullable=False)
    points = db.Column(db.Integer, nullable=False)
    balance_after = db.Column(db.Integer, nullable=False)
    source_type = db.Column(db.String(50), nullable=True)  # review, booking, referral, admin
    source_id = db.Column(db.Integer, nullable=True)  # ID ของแหล่งที่มา
    description = db.Column(db.String(500), nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<PointTransaction {self.id}: Customer {self.customer_id} - {self.transaction_type} {self.points} points>'
    
    @property
    def is_expired(self):
        """ตรวจสอบว่าคะแนนหมดอายุหรือไม่"""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False
