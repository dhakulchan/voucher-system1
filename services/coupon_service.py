"""
Group Buy Coupon Service
Business logic for coupon management
"""
from models.group_buy_coupon import GroupBuyCoupon, GroupBuyCouponUsage
from extensions import db
from utils.datetime_utils import naive_utc_now
from sqlalchemy import and_

class CouponService:
    """Service สำหรับจัดการคูปอง"""
    
    @staticmethod
    def validate_and_apply_coupon(code, campaign_id, amount, customer_email=None):
        """
        ตรวจสอบและใช้คูปอง
        
        Args:
            code: รหัสคูปอง
            campaign_id: ID แคมเปญ
            amount: ยอดเงิน
            customer_email: อีเมลลูกค้า
            
        Returns:
            tuple: (success, message, discount_amount, coupon_obj)
        """
        if not code:
            return False, "กรุณากรอกรหัสคูปอง", 0, None
        
        # Find coupon
        coupon = GroupBuyCoupon.query.filter_by(code=code.strip().upper()).first()
        
        if not coupon:
            return False, "ไม่พบรหัสคูปองนี้", 0, None
        
        # Validate coupon
        is_valid, message = coupon.is_valid(
            campaign_id=campaign_id,
            amount=amount,
            customer_email=customer_email
        )
        
        if not is_valid:
            return False, message, 0, None
        
        # Calculate discount
        discount = coupon.calculate_discount(amount)
        
        return True, "ใช้คูปองสำเร็จ", discount, coupon
    
    @staticmethod
    def record_usage(coupon, participant_id, campaign_id, original_amount, discount_amount, customer_email=None, payment_id=None):
        """
        บันทึกการใช้คูปอง
        
        Args:
            coupon: GroupBuyCoupon object
            participant_id: ID ผู้เข้าร่วม
            campaign_id: ID แคมเปญ
            original_amount: ยอดเงินก่อนส่วนลด
            discount_amount: จำนวนส่วนลด
            customer_email: อีเมลลูกค้า
            payment_id: ID การชำระเงิน
            
        Returns:
            GroupBuyCouponUsage object
        """
        usage = GroupBuyCouponUsage(
            coupon_id=coupon.id,
            participant_id=participant_id,
            payment_id=payment_id,
            campaign_id=campaign_id,
            original_amount=original_amount,
            discount_amount=discount_amount,
            final_amount=original_amount - discount_amount,
            customer_email=customer_email
        )
        
        db.session.add(usage)
        
        # Increment usage count
        coupon.increment_usage()
        
        return usage
    
    @staticmethod
    def get_active_coupons(campaign_id=None):
        """
        ดึงคูปองที่ใช้งานได้
        
        Args:
            campaign_id: ID แคมเปญ (None = ทุกแคมเปญ)
            
        Returns:
            List of GroupBuyCoupon
        """
        now = naive_utc_now()
        
        query = GroupBuyCoupon.query.filter(
            GroupBuyCoupon.is_active == True,
            GroupBuyCoupon.start_date <= now,
            GroupBuyCoupon.end_date >= now
        )
        
        if campaign_id:
            query = query.filter(
                db.or_(
                    GroupBuyCoupon.campaign_id == campaign_id,
                    GroupBuyCoupon.campaign_id == None
                )
            )
        else:
            query = query.filter(GroupBuyCoupon.campaign_id == None)
        
        return query.all()
    
    @staticmethod
    def create_coupon(code, description, discount_type, discount_value, 
                     start_date, end_date, created_by,
                     max_uses=None, max_uses_per_user=1, 
                     min_purchase_amount=0, campaign_id=None):
        """
        สร้างคูปองใหม่
        
        Returns:
            tuple: (success, message, coupon_obj)
        """
        # Check duplicate code
        existing = GroupBuyCoupon.query.filter_by(code=code.strip().upper()).first()
        if existing:
            return False, "รหัสคูปองนี้มีอยู่แล้ว", None
        
        # Validate dates
        if start_date >= end_date:
            return False, "วันเริ่มต้นต้องอยู่ก่อนวันสิ้นสุด", None
        
        # Validate discount value
        if discount_type == 'percentage' and (discount_value <= 0 or discount_value > 100):
            return False, "ส่วนลดเปอร์เซ็นต์ต้องอยู่ระหว่าง 1-100", None
        
        if discount_value <= 0:
            return False, "ส่วนลดต้องมากกว่า 0", None
        
        coupon = GroupBuyCoupon(
            code=code.strip().upper(),
            description=description,
            discount_type=discount_type,
            discount_value=discount_value,
            max_uses=max_uses,
            max_uses_per_user=max_uses_per_user,
            min_purchase_amount=min_purchase_amount,
            campaign_id=campaign_id,
            start_date=start_date,
            end_date=end_date,
            created_by=created_by,
            is_active=True
        )
        
        try:
            db.session.add(coupon)
            db.session.commit()
            return True, "สร้างคูปองสำเร็จ", coupon
        except Exception as e:
            db.session.rollback()
            return False, f"เกิดข้อผิดพลาด: {str(e)}", None
    
    @staticmethod
    def get_usage_stats(coupon_id):
        """
        ดึงสถิติการใช้งานคูปอง
        
        Returns:
            dict: สถิติการใช้งาน
        """
        coupon = GroupBuyCoupon.query.get(coupon_id)
        if not coupon:
            return None
        
        # นับจำนวนการใช้จริงจาก usage table
        usage_count = GroupBuyCouponUsage.query.filter_by(coupon_id=coupon_id).count()
        
        total_discount = db.session.query(
            db.func.sum(GroupBuyCouponUsage.discount_amount)
        ).filter_by(coupon_id=coupon_id).scalar() or 0
        
        unique_users = db.session.query(
            db.func.count(db.distinct(GroupBuyCouponUsage.customer_email))
        ).filter_by(coupon_id=coupon_id).scalar() or 0
        
        return {
            'coupon': coupon,
            'usage_count': usage_count,  # จำนวนการใช้จริง
            'total_discount': float(total_discount),
            'unique_users': unique_users,
            'remaining_uses': coupon.remaining_uses
        }
