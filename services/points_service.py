"""
Points Redemption Service
บริการสำหรับการใช้คะแนนแลกส่วนลด
"""
from models.review import CustomerPoints, PointTransaction
from extensions import db
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PointsService:
    """บริการจัดการคะแนนสะสม"""
    
    @staticmethod
    def get_customer_points(customer_id):
        """ดึงคะแนนของลูกค้า"""
        points = CustomerPoints.query.filter_by(customer_id=customer_id).first()
        if not points:
            points = CustomerPoints(customer_id=customer_id)
            db.session.add(points)
            db.session.commit()
        return points
    
    @staticmethod
    def can_redeem(customer_id, points_to_use):
        """ตรวจสอบว่าสามารถใช้คะแนนได้หรือไม่"""
        customer_points = PointsService.get_customer_points(customer_id)
        return customer_points.available_points >= points_to_use
    
    @staticmethod
    def calculate_discount(points):
        """คำนวณส่วนลดจากคะแนน (100 คะแนน = 100 บาท)"""
        return points
    
    @staticmethod
    def redeem_points(customer_id, points_to_use, booking_id=None, description=None):
        """ใช้คะแนนแลกส่วนลด
        
        Args:
            customer_id: ID ของลูกค้า
            points_to_use: จำนวนคะแนนที่ต้องการใช้
            booking_id: ID ของการจอง (optional)
            description: คำอธิบายการใช้คะแนน
            
        Returns:
            dict: {'success': bool, 'discount': int, 'remaining_points': int, 'message': str}
        """
        try:
            # ตรวจสอบคะแนน
            customer_points = PointsService.get_customer_points(customer_id)
            
            if points_to_use <= 0:
                return {
                    'success': False,
                    'message': 'จำนวนคะแนนต้องมากกว่า 0'
                }
            
            if customer_points.available_points < points_to_use:
                return {
                    'success': False,
                    'message': f'คะแนนไม่พอ (มีเพียง {customer_points.available_points} คะแนน)'
                }
            
            # คำนวณส่วนลด
            discount_amount = PointsService.calculate_discount(points_to_use)
            
            # หักคะแนน
            customer_points.available_points -= points_to_use
            customer_points.used_points += points_to_use
            
            # บันทึกประวัติ
            transaction = PointTransaction(
                customer_id=customer_id,
                transaction_type='redeem',
                points=points_to_use,
                balance_after=customer_points.available_points,
                source_type='booking',
                source_id=booking_id,
                description=description or f'ใช้คะแนนแลกส่วนลด {discount_amount} บาท'
            )
            db.session.add(transaction)
            db.session.commit()
            
            logger.info(f"Points redeemed: Customer {customer_id} used {points_to_use} points for {discount_amount} THB discount")
            
            return {
                'success': True,
                'discount': discount_amount,
                'remaining_points': customer_points.available_points,
                'message': f'ใช้คะแนน {points_to_use} คะแนน ได้ส่วนลด {discount_amount} บาท'
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error redeeming points: {str(e)}")
            return {
                'success': False,
                'message': 'เกิดข้อผิดพลาดในการใช้คะแนน'
            }
    
    @staticmethod
    def add_points(customer_id, points, source_type, source_id=None, description=None):
        """เพิ่มคะแนนให้ลูกค้า
        
        Args:
            customer_id: ID ของลูกค้า
            points: จำนวนคะแนนที่ต้องการเพิ่ม
            source_type: ประเภทของการได้คะแนน (review, booking, referral, etc.)
            source_id: ID ของแหล่งที่มา
            description: คำอธิบาย
            
        Returns:
            bool: True ถ้าสำเร็จ, False ถ้าล้มเหลว
        """
        try:
            customer_points = PointsService.get_customer_points(customer_id)
            
            # เพิ่มคะแนน
            customer_points.total_points += points
            customer_points.available_points += points
            customer_points.lifetime_points += points
            
            # บันทึกประวัติ
            transaction = PointTransaction(
                customer_id=customer_id,
                transaction_type='earn',
                points=points,
                balance_after=customer_points.available_points,
                source_type=source_type,
                source_id=source_id,
                description=description or f'ได้รับคะแนนจาก {source_type}'
            )
            db.session.add(transaction)
            db.session.commit()
            
            logger.info(f"Points added: Customer {customer_id} earned {points} points from {source_type}")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding points: {str(e)}")
            return False
    
    @staticmethod
    def get_max_redeemable_points(customer_id, max_amount=None):
        """คำนวณจำนวนคะแนนสูงสุดที่สามารถใช้ได้
        
        Args:
            customer_id: ID ของลูกค้า
            max_amount: ยอดเงินสูงสุดที่สามารถลดได้ (optional)
            
        Returns:
            int: จำนวนคะแนนสูงสุดที่ใช้ได้
        """
        customer_points = PointsService.get_customer_points(customer_id)
        available = customer_points.available_points
        
        if max_amount:
            # จำกัดจำนวนคะแนนตามยอดเงินสูงสุด (100 คะแนน = 100 บาท)
            max_points = int(max_amount)
            return min(available, max_points)
        
        return available
