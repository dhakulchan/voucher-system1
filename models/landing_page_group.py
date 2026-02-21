from extensions import db
from utils.datetime_utils import naive_utc_now

class LandingPageGroup(db.Model):
    __tablename__ = "landing_page_groups"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), nullable=False, unique=True)
    short_url = db.Column(db.String(50), unique=True)  # Short URL สำหรับ Social Media
    description = db.Column(db.Text)
    banner_image = db.Column(db.String(500))
    theme_color = db.Column(db.String(50), default="#667eea")
    icon = db.Column(db.String(10), default="✈️")  # Emoji icon for group
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    display_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=naive_utc_now)
    updated_at = db.Column(db.DateTime, default=naive_utc_now, onupdate=naive_utc_now)
    
    # Relationship to products
    products = db.relationship("LandingProduct", backref="group", lazy="dynamic")
    
    @property
    def product_count(self):
        return self.products.filter_by(is_active=True).count()
    
    @property
    def is_active_now(self):
        """ตรวจสอบว่า Group อยู่ในช่วงเวลาที่ active หรือไม่"""
        from datetime import datetime
        now = datetime.now()
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return self.is_active
