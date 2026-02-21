"""Landing Page Product Model"""
from extensions import db
from utils.datetime_utils import naive_utc_now
import json

class LandingProduct(db.Model):
    """Products สำหรับหน้า Landing Page - แยกต่างหากจาก Group Buy"""
    __tablename__ = 'landing_products'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Product Info
    title = db.Column(db.String(255), nullable=False)
    subtitle = db.Column(db.String(500))
    description = db.Column(db.Text)
    
    # Banner Image (1:1)
    banner_image = db.Column(db.String(500))
    banner_position = db.Column(db.Integer, default=0)
    
    # External Link
    external_url = db.Column(db.String(1000), nullable=False)
    external_url_text = db.Column(db.String(100), default='ดูรายละเอียด')
    open_in_new_tab = db.Column(db.Boolean, default=True)
    
    # Video
    video_url = db.Column(db.String(500))
    video_thumbnail = db.Column(db.String(500))
    video_duration = db.Column(db.String(20))
    
    # Category
    category = db.Column(db.String(100))
    tags = db.Column(db.Text)
    
    # Group (โปรโมชั่น)
    group_id = db.Column(db.Integer, db.ForeignKey('landing_page_groups.id'), nullable=True)
    
    # Display Settings
    is_active = db.Column(db.Boolean, default=True)
    is_featured = db.Column(db.Boolean, default=False)
    display_order = db.Column(db.Integer, default=0)
    
    # Highlight
    highlight_badge = db.Column(db.String(100))
    highlight_color = db.Column(db.String(50), default='danger')
    price_text = db.Column(db.String(100))
    
    # SEO
    seo_title = db.Column(db.String(255))
    seo_description = db.Column(db.Text)
    
    # Meta
    created_by = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=naive_utc_now)
    updated_at = db.Column(db.DateTime, default=naive_utc_now, onupdate=naive_utc_now)
    
    @property
    def tags_list(self):
        """แปลง JSON tags เป็น list"""
        if self.tags:
            try:
                return json.loads(self.tags)
            except:
                return []
        return []
    
    def set_tags(self, tags_list):
        """ตั้งค่า tags จาก list"""
        self.tags = json.dumps(tags_list, ensure_ascii=False) if tags_list else None
    
    def __repr__(self):
        return f'<LandingProduct {self.id}: {self.title}>'
