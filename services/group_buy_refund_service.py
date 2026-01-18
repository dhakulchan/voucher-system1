"""
Auto Refund System for Group Buy
จัดการคืนเงินอัตโนมัติเมื่อกลุ่มไม่สำเร็จ
"""
from extensions import db
from models.group_buy import GroupBuyCampaign, GroupBuyGroup, GroupBuyParticipant
from models.group_buy_payment import GroupBuyPayment
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def process_failed_group_refunds(group_id: int) -> dict:
    """
    คืนเงินให้สมาชิกทุกคนในกลุ่มที่ล้มเหลว
    
    Args:
        group_id: ID ของกลุ่มที่ล้มเหลว
    
    Returns:
        dict: สรุปผลการคืนเงิน
    """
    try:
        group = GroupBuyGroup.query.get(group_id)
        if not group:
            return {'success': False, 'error': 'Group not found'}
        
        if group.status not in ['expired', 'cancelled']:
            return {'success': False, 'error': f'Group status is {group.status}, cannot refund'}
        
        # ดึงสมาชิกทั้งหมดที่ชำระเงินแล้ว
        participants = GroupBuyParticipant.query.filter_by(
            group_id=group_id,
            payment_status='paid'
        ).all()
        
        refunded_count = 0
        failed_count = 0
        total_refunded = 0
        
        for participant in participants:
            if participant.payment_id:
                payment = GroupBuyPayment.query.get(participant.payment_id)
                
                if payment and payment.payment_status == 'paid':
                    # ทำการคืนเงิน
                    refund_result = process_single_refund(payment, reason='Group buy failed - insufficient participants')
                    
                    if refund_result['success']:
                        # อัพเดตสถานะ participant
                        participant.payment_status = 'refunded'
                        db.session.commit()
                        
                        refunded_count += 1
                        total_refunded += float(payment.total_amount)
                        logger.info(f"✅ Refunded payment {payment.id} for participant {participant.id}")
                    else:
                        failed_count += 1
                        logger.error(f"❌ Failed to refund payment {payment.id}: {refund_result.get('error')}")
        
        return {
            'success': True,
            'group_id': group_id,
            'refunded_count': refunded_count,
            'failed_count': failed_count,
            'total_refunded': total_refunded
        }
        
    except Exception as e:
        logger.error(f"❌ Error in process_failed_group_refunds: {e}")
        return {'success': False, 'error': str(e)}


def process_single_refund(payment: GroupBuyPayment, reason: str) -> dict:
    """
    คืนเงินสำหรับ payment เดียว
    
    Args:
        payment: GroupBuyPayment object
        reason: เหตุผลในการคืนเงิน
    
    Returns:
        dict: ผลลัพธ์การคืนเงิน
    """
    try:
        if payment.payment_status == 'refunded':
            return {'success': False, 'error': 'Already refunded'}
        
        # ตรวจสอบว่าชำระด้วยวิธีใด
        if payment.payment_method == 'stripe':
            # TODO: เรียก Stripe API เพื่อคืนเงิน
            # refund = stripe.Refund.create(
            #     charge=payment.stripe_charge_id,
            #     amount=int(payment.total_amount * 100)
            # )
            logger.info(f"⚠️ Stripe refund pending for payment {payment.id}")
            refund_success = True  # Mock success
            
        elif payment.payment_method in ['bank_transfer', 'qr_code']:
            # สำหรับการโอนเงิน/QR Code ต้องคืนเงินแบบ manual
            # เพียงแค่บันทึกสถานะว่าต้องคืนเงิน
            logger.info(f"⚠️ Manual refund required for payment {payment.id} (method: {payment.payment_method})")
            refund_success = True
        
        else:
            return {'success': False, 'error': f'Unknown payment method: {payment.payment_method}'}
        
        if refund_success:
            # อัพเดตสถานะ payment
            payment.payment_status = 'refunded'
            payment.refund_amount = payment.total_amount
            payment.refund_reason = reason
            payment.refunded_at = datetime.utcnow()
            payment.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            return {
                'success': True,
                'payment_id': payment.id,
                'refund_amount': float(payment.refund_amount),
                'method': payment.payment_method
            }
        
        return {'success': False, 'error': 'Refund processing failed'}
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Error in process_single_refund: {e}")
        return {'success': False, 'error': str(e)}


def process_expired_payments():
    """
    ตรวจสอบและยกเลิก payments ที่หมดเวลา (timeout)
    ควรรันเป็น scheduled task ทุก 5-10 นาที
    """
    try:
        now = datetime.utcnow()
        
        # ดึง payments ที่หมดเวลาแล้วแต่ยังค้าง
        expired_payments = GroupBuyPayment.query.filter(
            GroupBuyPayment.payment_status == 'pending',
            GroupBuyPayment.payment_timeout < now
        ).all()
        
        cancelled_count = 0
        
        for payment in expired_payments:
            payment.payment_status = 'failed'
            payment.admin_notes = 'Payment timeout - auto cancelled'
            payment.updated_at = now
            
            # อัพเดต participant status
            participant = GroupBuyParticipant.query.filter_by(payment_id=payment.id).first()
            if participant:
                participant.payment_status = 'failed'
            
            cancelled_count += 1
            logger.info(f"⏰ Cancelled expired payment {payment.id}")
        
        db.session.commit()
        
        return {
            'success': True,
            'cancelled_count': cancelled_count
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Error in process_expired_payments: {e}")
        return {'success': False, 'error': str(e)}


def auto_refund_failed_groups():
    """
    ตรวจสอบและคืนเงินอัตโนมัติสำหรับกลุ่มที่ล้มเหลว
    ควรรันเป็น scheduled task ทุก 1 ชั่วโมง
    """
    try:
        # ดึงกลุ่มที่ expire หรือ cancelled และยังไม่ได้คืนเงิน
        failed_groups = GroupBuyGroup.query.filter(
            GroupBuyGroup.status.in_(['expired', 'cancelled'])
        ).all()
        
        total_refunded = 0
        groups_processed = 0
        
        for group in failed_groups:
            # ตรวจสอบว่ามีสมาชิกที่ยังชำระเงินค้างอยู่หรือไม่
            paid_participants = GroupBuyParticipant.query.filter_by(
                group_id=group.id,
                payment_status='paid'
            ).count()
            
            if paid_participants > 0:
                result = process_failed_group_refunds(group.id)
                if result.get('success'):
                    total_refunded += result.get('total_refunded', 0)
                    groups_processed += 1
        
        logger.info(f"✅ Auto refund completed: {groups_processed} groups, ฿{total_refunded:,.2f} refunded")
        
        return {
            'success': True,
            'groups_processed': groups_processed,
            'total_refunded': total_refunded
        }
        
    except Exception as e:
        logger.error(f"❌ Error in auto_refund_failed_groups: {e}")
        return {'success': False, 'error': str(e)}


if __name__ == '__main__':
    from app import create_app
    app = create_app()
    
    with app.app_context():
        # ทดสอบรันฟังก์ชัน
        print("🔄 Processing expired payments...")
        result1 = process_expired_payments()
        print(f"Result: {result1}")
        
        print("\n🔄 Processing auto refunds...")
        result2 = auto_refund_failed_groups()
        print(f"Result: {result2}")
