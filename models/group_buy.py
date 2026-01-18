"""
Group Buy System Models
"""
from extensions import db
from utils.datetime_utils import naive_utc_now
from datetime import datetime, timedelta
import json
import secrets
import string

class GroupBuyCampaign(db.Model):
    """แคมเปญ Group Buy"""
    __tablename__ = 'group_buy_campaigns'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Campaign Info
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    product_type = db.Column(db.String(100), nullable=False)
    
    # Pricing
    regular_price = db.Column(db.Numeric(12, 2), nullable=False)
    group_price = db.Column(db.Numeric(12, 2), nullable=False)
    discount_percentage = db.Column(db.Numeric(5, 2))
    
    # Group Requirements
    min_participants = db.Column(db.Integer, nullable=False, default=2)
    max_participants = db.Column(db.Integer)
    
    # Time Limits
    duration_hours = db.Column(db.Integer, nullable=False, default=48)
    campaign_start_date = db.Column(db.DateTime, nullable=False)
    campaign_end_date = db.Column(db.DateTime, nullable=False)
    
    # Product Details
    product_details = db.Column(db.Text)  # JSON
    terms_conditions = db.Column(db.Text)
    admin_notes = db.Column(db.Text)  # หมายเหตุสำหรับ Admin (ไม่แสดงต่อลูกค้า)
    special_booker_codes = db.Column(db.Text)  # JSON array of special codes that allow multiple bookings
    
    # Travel Dates (NEW)
    travel_date_from = db.Column(db.Date)  # วันที่เดินทางไป
    travel_date_to = db.Column(db.Date)  # วันที่เดินทางกลับ
    
    # Pax (NEW)
    max_pax = db.Column(db.Integer)  # จำนวนผู้เดินทางสูงสุด (รวมทุกกลุ่ม)
    
    # Inventory
    total_slots = db.Column(db.Integer)
    available_slots = db.Column(db.Integer)
    
    # Status
    status = db.Column(db.String(50), default='draft')
    is_active = db.Column(db.Boolean, default=True)
    
    # Visibility
    is_public = db.Column(db.Boolean, default=True)
    featured = db.Column(db.Boolean, default=False)
    
    # Images
    banner_image = db.Column(db.String(500))
    gallery_images = db.Column(db.Text)  # JSON
    product_image = db.Column(db.String(500))  # Product image (1:1 ratio) - NEW
    image_title = db.Column(db.String(255))  # Title text to display on image - NEW
    image_title_position = db.Column(db.String(20), default='left')  # Position: left, center, right
    album_images = db.Column(db.Text)  # JSON array of album image paths - NEW
    
    # Payment Configuration
    payment_stripe_enabled = db.Column(db.Boolean, default=False)
    payment_stripe_fee_type = db.Column(db.String(20), default='percentage')  # percentage or fixed
    payment_stripe_fee_value = db.Column(db.Numeric(10, 2), default=0.00)
    payment_stripe_fee_label = db.Column(db.String(100), default='ค่าธรรมเนียม')
    payment_bank_enabled = db.Column(db.Boolean, default=True)
    payment_qr_enabled = db.Column(db.Boolean, default=False)
    payment_qr_image = db.Column(db.String(500))
    allow_partial_payment = db.Column(db.Boolean, default=False)  # อนุญาตให้จ่ายบางส่วน
    partial_payment_type = db.Column(db.String(20), default='percentage')  # fixed, percentage, full
    partial_payment_value = db.Column(db.Numeric(10, 2), default=30.00)  # จำนวนเงิน หรือ %
    
    # Auto Cancel Settings
    auto_cancel_enabled = db.Column(db.Boolean, default=False)  # เปิด/ปิดระบบยกเลิกอัตโนมัติ
    auto_cancel_hours = db.Column(db.Integer, default=4)  # ยกเลิกอัตโนมัติหลังจาก X ชั่วโมง (เริ่มต้น 4 ชม.)
    auto_cancel_send_email = db.Column(db.Boolean, default=True)  # ส่งอีเมลแจ้งเตือนเมื่อยกเลิก
    
    # Meta
    created_by = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=naive_utc_now)
    updated_at = db.Column(db.DateTime, default=naive_utc_now, onupdate=naive_utc_now)
    
    # Relationships
    groups = db.relationship('GroupBuyGroup', backref='campaign', lazy='dynamic')
    
    @property
    def is_active_now(self):
        """ตรวจสอบว่าแคมเปญกำลังทำงานอยู่หรือไม่"""
        now = naive_utc_now()
        return (
            self.is_active and 
            self.status == 'active' and
            self.campaign_start_date <= now <= self.campaign_end_date
        )
    
    @property
    def savings_amount(self):
        """จำนวนเงินที่ประหยัดได้"""
        return float(self.regular_price - self.group_price)
    
    @property
    def savings_percentage(self):
        """เปอร์เซ็นต์ส่วนลด"""
        if self.discount_percentage:
            return float(self.discount_percentage)
        return (self.savings_amount / float(self.regular_price)) * 100
    
    @property
    def inventory_used(self):
        """Inventory ที่ใช้ไปแล้ว - นับจากจำนวนกลุ่มจริง"""
        if not self.total_slots:
            return 0
        # นับจำนวนกลุ่มที่ active หรือ success
        used_groups = GroupBuyGroup.query.filter(
            GroupBuyGroup.campaign_id == self.id,
            GroupBuyGroup.status.in_(['active', 'success'])
        ).count()
        return used_groups
    
    @property
    def inventory_remaining(self):
        """Inventory ที่เหลือ - คำนวณจาก total_slots - inventory_used"""
        if not self.total_slots:
            return 0
        return max(0, self.total_slots - self.inventory_used)
    
    @property
    def total_inventory(self):
        """Total inventory (alias for total_slots)"""
        return self.total_slots
    
    def calculate_partial_payment(self, pax_count=1):
        """คำนวณยอดมัดจำตามการตั้งค่า
        
        Args:
            pax_count: จำนวนคนที่เดินทาง
            
        Returns:
            float: จำนวนเงินที่ต้องจ่ายมัดจำ
        """
        if not self.allow_partial_payment:
            # ถ้าไม่อนุญาตจ่ายบางส่วน ต้องจ่ายเต็ม
            return float(self.group_price) * pax_count
        
        payment_type = self.partial_payment_type or 'percentage'
        payment_value = float(self.partial_payment_value or 0)
        base_price = float(self.group_price)
        
        if payment_type == 'fixed':
            # จำนวนคงที่ต่อคน
            return payment_value * pax_count
        elif payment_type == 'percentage':
            # เปอร์เซ็นต์
            return (base_price * pax_count) * (payment_value / 100)
        elif payment_type == 'full':
            # เต็มจำนวน x pax_count
            return base_price * pax_count
        else:
            # default: เปอร์เซ็นต์ 30%
            return (base_price * pax_count) * 0.30
    
    def get_product_details(self):
        """แปลง JSON เป็น dict"""
        if self.product_details:
            try:
                return json.loads(self.product_details)
            except:
                return {}
        return {}
    
    def set_product_details(self, details_dict):
        """เซ็ต product details จาก dict"""
        self.product_details = json.dumps(details_dict, ensure_ascii=False)
    
    def get_gallery_images(self):
        """แปลง gallery images JSON"""
        if self.gallery_images:
            try:
                return json.loads(self.gallery_images)
            except:
                return []
        return []
    
    def to_dict(self):
        """แปลงเป็น dict สำหรับ API"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'product_type': self.product_type,
            'regular_price': float(self.regular_price),
            'group_price': float(self.group_price),
            'savings_amount': self.savings_amount,
            'savings_percentage': round(self.savings_percentage, 1),
            'min_participants': self.min_participants,
            'max_participants': self.max_participants,
            'duration_hours': self.duration_hours,
            'campaign_start_date': self.campaign_start_date.isoformat() if self.campaign_start_date else None,
            'campaign_end_date': self.campaign_end_date.isoformat() if self.campaign_end_date else None,
            'product_details': self.get_product_details(),
            'status': self.status,
            'is_active': self.is_active,
            'is_active_now': self.is_active_now,
            'banner_image': self.banner_image,
        }
    
    def get_special_booker_codes(self):
        """ดึงรายการรหัสพิเศษ"""
        if self.special_booker_codes:
            try:
                return json.loads(self.special_booker_codes)
            except:
                return []
        return []
    
    def set_special_booker_codes(self, codes_list):
        """เซ็ตรหัสพิเศษ
        
        Args:
            codes_list: list of dict [{'code': 'ABC123', 'name': 'ชื่อผู้จอง', 'note': 'หมายเหตุ'}]
        """
        self.special_booker_codes = json.dumps(codes_list, ensure_ascii=False)
    
    def add_special_booker_code(self, code, name='', note=''):
        """เพิ่มรหัสพิเศษ"""
        codes = self.get_special_booker_codes()
        
        # ตรวจสอบว่ารหัสซ้ำหรือไม่
        if any(c['code'].upper() == code.upper() for c in codes):
            return False, "รหัสนี้มีอยู่แล้ว"
        
        codes.append({
            'code': code.upper(),
            'name': name,
            'note': note,
            'created_at': datetime.now().isoformat()
        })
        self.set_special_booker_codes(codes)
        return True, "เพิ่มรหัสสำเร็จ"
    
    def remove_special_booker_code(self, code):
        """ลบรหัสพิเศษ"""
        codes = self.get_special_booker_codes()
        codes = [c for c in codes if c['code'].upper() != code.upper()]
        self.set_special_booker_codes(codes)
        return True
    
    def is_special_booker(self, code):
        """ตรวจสอบว่ารหัสนี้เป็นรหัสพิเศษหรือไม่"""
        if not code:
            return False
        codes = self.get_special_booker_codes()
        return any(c['code'].upper() == code.upper() for c in codes)

class GroupBuyGroup(db.Model):
    """กลุ่ม Group Buy ที่ลูกค้าสร้าง"""
    __tablename__ = 'group_buy_groups'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Campaign Reference
    campaign_id = db.Column(db.Integer, db.ForeignKey('group_buy_campaigns.id'), nullable=False)
    
    # Group Info
    group_code = db.Column(db.String(50), unique=True, nullable=False)
    group_name = db.Column(db.String(255))
    
    # Leader
    leader_customer_id = db.Column(db.Integer)
    leader_name = db.Column(db.String(255), nullable=False)
    leader_email = db.Column(db.String(255))
    leader_phone = db.Column(db.String(50))
    
    # Group Status
    status = db.Column(db.String(50), default='pending')
    current_participants = db.Column(db.Integer, default=0)
    required_participants = db.Column(db.Integer, nullable=False)
    
    # Time Management
    expires_at = db.Column(db.DateTime, nullable=False)
    completed_at = db.Column(db.DateTime)
    cancelled_at = db.Column(db.DateTime)
    
    # Payment
    payment_method = db.Column(db.String(50), default='hold')
    total_amount = db.Column(db.Numeric(12, 2), default=0)
    paid_amount = db.Column(db.Numeric(12, 2), default=0)
    
    # Share Link
    share_token = db.Column(db.String(100), unique=True, nullable=False)
    share_url = db.Column(db.Text)
    
    # Booking Integration
    master_booking_id = db.Column(db.Integer)
    
    # Meta
    created_at = db.Column(db.DateTime, default=naive_utc_now)
    updated_at = db.Column(db.DateTime, default=naive_utc_now, onupdate=naive_utc_now)
    
    # Relationships
    participants = db.relationship('GroupBuyParticipant', backref='group', lazy='dynamic')
    
    @staticmethod
    def generate_group_code():
        """สร้างรหัสกลุ่มแบบสุ่ม"""
        # Format: GB-XXXXXX (6 characters)
        chars = string.ascii_uppercase + string.digits
        code = ''.join(secrets.choice(chars) for _ in range(6))
        return f"GB-{code}"
    
    @staticmethod
    def generate_share_token():
        """สร้าง share token"""
        return secrets.token_urlsafe(32)
    
    @property
    def is_expired(self):
        """ตรวจสอบว่าหมดเวลาหรือยัง"""
        return naive_utc_now() > self.expires_at
    
    @property
    def time_remaining(self):
        """เวลาที่เหลือ (วินาที)"""
        if self.is_expired:
            return 0
        delta = self.expires_at - naive_utc_now()
        return int(delta.total_seconds())
    
    @property
    def time_remaining_formatted(self):
        """เวลาที่เหลือ (formatted)"""
        seconds = self.time_remaining
        if seconds <= 0:
            return "หมดเวลา"
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        
        if hours > 0:
            return f"{hours} ชั่วโมง {minutes} นาที"
        return f"{minutes} นาที"
    
    @property
    def progress_percentage(self):
        """เปอร์เซ็นต์ความสำเร็จ"""
        if self.required_participants == 0:
            return 0
        return round((self.current_participants / self.required_participants) * 100, 2)
    
    @property
    def total_pax_count(self):
        """ยอดรวมจำนวนคนทั้งหมดในกลุ่ม (รวม pax_count ของทุกคน)"""
        total = 0
        for participant in self.participants:
            total += participant.pax_count or 0
        return total
    
    @property
    def total_pax_for_campaign(self):
        """นับ pax รวมทั้งหมดในแคมเปญ (ทุกกลุ่มที่ active หรือ success)"""
        from sqlalchemy import func
        total = db.session.query(func.sum(GroupBuyParticipant.pax_count))\
            .join(GroupBuyGroup)\
            .filter(
                GroupBuyGroup.campaign_id == self.campaign_id,
                GroupBuyGroup.status.in_(['active', 'success']),
                GroupBuyParticipant.status == 'active'
            ).scalar() or 0
        return total
    
    @property
    def is_full(self):
        """ตรวจสอบว่ากลุ่มเต็มหรือยัง (เช็คทั้ง participants และ max_pax ของแคมเปญ)"""
        # เช็คจำนวน participants ในกลุ่ม
        if self.current_participants >= self.required_participants:
            return True
        
        # เช็ค max_pax ของแคมเปญ (ถ้ามี)
        if self.campaign and self.campaign.max_pax:
            total_pax = self.total_pax_for_campaign
            if total_pax >= self.campaign.max_pax:
                return True
        
        return False
    
    @property
    def spots_remaining(self):
        """จำนวนที่เหลือ"""
        return max(0, self.required_participants - self.current_participants)
    
    @property
    def status_display(self):
        """สถานะแบบแสดงผล (ภาษาไทย)"""
        status_map = {
            'active': 'กำลังรอ',
            'success': 'สำเร็จ',
            'failed': 'ล้มเหลว',
            'cancelled': 'ยกเลิก'
        }
        return status_map.get(self.status, self.status)
    
    def to_dict(self):
        """แปลงเป็น dict สำหรับ API"""
        return {
            'id': self.id,
            'group_code': self.group_code,
            'group_name': self.group_name,
            'leader_name': self.leader_name,
            'status': self.status,
            'current_participants': self.current_participants,
            'required_participants': self.required_participants,
            'progress_percentage': round(self.progress_percentage, 1),
            'spots_remaining': self.spots_remaining,
            'is_full': self.is_full,
            'is_expired': self.is_expired,
            'time_remaining': self.time_remaining,
            'time_remaining_formatted': self.time_remaining_formatted,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'share_url': self.share_url,
            'campaign': self.campaign.to_dict() if self.campaign else None,
        }

class GroupBuyParticipant(db.Model):
    """สมาชิกในกลุ่ม Group Buy"""
    __tablename__ = 'group_buy_participants'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # References
    group_id = db.Column(db.Integer, db.ForeignKey('group_buy_groups.id'), nullable=False)
    campaign_id = db.Column(db.Integer, db.ForeignKey('group_buy_campaigns.id'), nullable=False)
    
    # Participant Info
    customer_id = db.Column(db.Integer)
    participant_name = db.Column(db.String(255), nullable=False)
    participant_email = db.Column(db.String(255))
    participant_phone = db.Column(db.String(50))
    
    # Position
    is_leader = db.Column(db.Boolean, default=False)
    join_order = db.Column(db.Integer)
    
    # Details
    pax_count = db.Column(db.Integer, default=1)
    special_requests = db.Column(db.Text)
    
    # Payment Status
    payment_id = db.Column(db.Integer, db.ForeignKey('group_buy_payments.id'))
    payment_status = db.Column(db.String(50), default='pending')  # pending, paid, refunded, failed
    payment_amount = db.Column(db.Numeric(12, 2))
    payment_reference = db.Column(db.String(255))
    payment_date = db.Column(db.DateTime)
    
    # Booking Integration
    booking_id = db.Column(db.Integer)
    invoice_id = db.Column(db.Integer)
    
    # Authorization
    authorization_code = db.Column(db.String(255))
    authorization_expires_at = db.Column(db.DateTime)
    
    # Status
    status = db.Column(db.String(50), default='active')
    cancelled_at = db.Column(db.DateTime)
    cancel_reason = db.Column(db.Text)
    
    # Meta
    ip_address = db.Column(db.String(100))
    user_agent = db.Column(db.Text)
    referrer_participant_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=naive_utc_now)
    updated_at = db.Column(db.DateTime, default=naive_utc_now, onupdate=naive_utc_now)
    
    # Relationships
    payment = db.relationship('GroupBuyPayment', foreign_keys=[payment_id], backref='participant', uselist=False)
    
    def to_dict(self):
        """แปลงเป็น dict"""
        return {
            'id': self.id,
            'participant_name': self.participant_name,
            'is_leader': self.is_leader,
            'join_order': self.join_order,
            'pax_count': self.pax_count,
            'payment_status': self.payment_status,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

class GroupBuyNotification(db.Model):
    """การแจ้งเตือน Group Buy"""
    __tablename__ = 'group_buy_notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group_buy_groups.id'), nullable=False)
    participant_id = db.Column(db.Integer)
    
    notification_type = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text)
    
    sent_at = db.Column(db.DateTime)
    read_at = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=naive_utc_now)
