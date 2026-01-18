"""
Auto Cancel Unpaid Group Buy Participants
ยกเลิกการจองอัตโนมัติสำหรับผู้ที่ยังไม่ชำระเงินตามเวลาที่กำหนด
"""
from app import create_app
from extensions import db
from models.group_buy import GroupBuyCampaign, GroupBuyGroup, GroupBuyParticipant
from models.group_buy_payment import GroupBuyPayment
from utils.datetime_utils import naive_utc_now
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

def auto_cancel_expired_participants():
    """ยกเลิกการจองที่หมดเวลาอัตโนมัติ"""
    app = create_app()
    with app.app_context():
        try:
            now = naive_utc_now()
            cancelled_count = 0
            
            # ดึงแคมเปญทั้งหมดที่เปิดใช้งาน
            campaigns = GroupBuyCampaign.query.filter_by(is_active=True).all()
            
            for campaign in campaigns:
                # ข้ามถ้าไม่ได้เปิดใช้งาน auto cancel
                if not campaign.auto_cancel_enabled:
                    continue
                
                if not campaign.auto_cancel_hours:
                    continue
                
                # คำนวณเวลาหมดอายุ
                cancel_threshold = now - timedelta(hours=campaign.auto_cancel_hours)
                
                # หา participants ที่ยังไม่ชำระเงินและเกินเวลาที่กำหนด
                expired_participants = GroupBuyParticipant.query.join(
                    GroupBuyGroup
                ).filter(
                    GroupBuyGroup.campaign_id == campaign.id,
                    GroupBuyParticipant.payment_status == 'pending',
                    GroupBuyParticipant.status == 'active',
                    GroupBuyParticipant.created_at < cancel_threshold
                ).all()
                
                for participant in expired_participants:
                    try:
                        # บันทึกข้อมูลก่อนยกเลิก
                        old_pax_count = participant.pax_count
                        group = participant.group
                        
                        # อัปเดตสถานะเป็นยกเลิก
                        participant.status = 'cancelled'
                        participant.cancelled_at = now
                        participant.cancel_reason = f'ยกเลิกอัตโนมัติ - เกินเวลาชำระเงิน ({campaign.auto_cancel_hours} ชม.)'
                        
                        # คืนจำนวน pax ให้แคมเปญ
                        if campaign.available_slots is not None:
                            campaign.available_slots += old_pax_count
                        
                        # อัปเดตจำนวนสมาชิกในกลุ่ม
                        group.current_participants -= old_pax_count
                        
                        cancelled_count += 1
                        
                        # ส่งอีเมลแจ้งเตือนถ้าเปิดใช้งาน
                        if campaign.auto_cancel_send_email:
                            try:
                                from flask_mail import Message
                                from extensions import mail
                                
                                subject = f'แจ้งยกเลิกการจองอัตโนมัติ - {campaign.name}'
                                html_body = f"""
                                <h3>แจ้งยกเลิกการจองอัตโนมัติ</h3>
                                <p>เรียน คุณ{participant.participant_name}</p>
                                <p>การจองของท่านสำหรับ <strong>{campaign.name}</strong> ถูกยกเลิกอัตโนมัติเนื่องจากไม่ได้ชำระเงินภายในเวลาที่กำหนด</p>
                                <p>กลุ่ม: {group.group_code}</p>
                                <p>จำนวน: {old_pax_count} คน</p>
                                <p>เวลาที่ต้องชำระ: {campaign.auto_cancel_hours} ชั่วโมง</p>
                                <br>
                                <p>หากต้องการจองใหม่ กรุณาเข้าสู่ระบบและทำการจองอีกครั้ง</p>
                                <p>หากมีข้อสงสัย กรุณาติดต่อเจ้าหน้าที่</p>
                                """
                                
                                msg = Message(subject,
                                            recipients=[participant.participant_email],
                                            html=html_body)
                                mail.send(msg)
                                logger.info(f"Auto cancel notification sent to {participant.participant_email}")
                            except Exception as e:
                                logger.error(f"Failed to send auto cancel email: {e}")
                        
                        logger.info(f"Auto cancelled participant #{participant.id} from campaign #{campaign.id}")
                        
                    except Exception as e:
                        logger.error(f"Error cancelling participant #{participant.id}: {e}")
                        continue
            
            # บันทึกการเปลี่ยนแปลง
            db.session.commit()
            
            if cancelled_count > 0:
                logger.info(f"✅ Auto cancelled {cancelled_count} expired participants")
                print(f"✅ Auto cancelled {cancelled_count} expired participants")
            else:
                logger.info("✅ No expired participants to cancel")
                print("✅ No expired participants to cancel")
                
            return cancelled_count
            
        except Exception as e:
            logger.error(f"Error in auto cancel job: {e}")
            db.session.rollback()
            print(f"❌ Error: {e}")
            raise

if __name__ == '__main__':
    auto_cancel_expired_participants()
