"""
Group Buy Service
จัดการ Business Logic สำหรับระบบ Group Buy
"""
from extensions import db
from models.group_buy import (
    GroupBuyCampaign, GroupBuyGroup, 
    GroupBuyParticipant, GroupBuyNotification
)
from models.booking import Booking
from models.customer import Customer
from utils.datetime_utils import naive_utc_now
from datetime import timedelta
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class GroupBuyService:
    """Service สำหรับจัดการ Group Buy"""
    
    def create_campaign(self, campaign_data):
        """สร้างแคมเปญ Group Buy ใหม่"""
        try:
            print(f"SERVICE: create_campaign called with keys: {list(campaign_data.keys())}")
            
            # Calculate discount percentage if not provided
            if 'discount_percentage' not in campaign_data:
                regular = Decimal(str(campaign_data['regular_price']))
                group = Decimal(str(campaign_data['group_price']))
                discount_pct = ((regular - group) / regular) * 100
                campaign_data['discount_percentage'] = discount_pct
                print(f"SERVICE: Calculated discount_percentage = {discount_pct}")
            
            # Set status to 'active' if not provided
            if 'status' not in campaign_data:
                campaign_data['status'] = 'active'
                print(f"SERVICE: Set status = active")
            
            # Set available_slots = total_slots เมื่อสร้างใหม่
            if 'total_slots' in campaign_data and campaign_data['total_slots']:
                campaign_data['available_slots'] = campaign_data['total_slots']
                print(f"SERVICE: Set available_slots = {campaign_data['available_slots']}")
            
            print(f"SERVICE: Creating GroupBuyCampaign object...")
            campaign = GroupBuyCampaign(**campaign_data)
            print(f"SERVICE: Adding to session...")
            db.session.add(campaign)
            print(f"SERVICE: Committing...")
            db.session.commit()
            print(f"SERVICE: Campaign created successfully with ID={campaign.id}")
            
            logger.info(f"Created Group Buy campaign: {campaign.id} - {campaign.name}")
            return campaign
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"SERVICE ERROR: {e}")
            print(error_trace)
            logger.error(f"Error creating campaign: {e}")
            logger.error(error_trace)
            db.session.rollback()
            raise  # Re-raise the exception instead of returning None
    
    def create_group(self, campaign_id, leader_info, custom_group_name=None):
        """
        สร้างกลุ่ม Group Buy ใหม่
        
        Args:
            campaign_id: ID ของแคมเปญ
            leader_info: dict {'name', 'email', 'phone', 'customer_id'(optional)}
            custom_group_name: ชื่อกลุ่ม (optional)
        """
        try:
            campaign = GroupBuyCampaign.query.get(campaign_id)
            if not campaign or not campaign.is_active_now:
                return None, "แคมเปญไม่พร้อมใช้งาน"
            
            # สร้างกลุ่ม
            group = GroupBuyGroup(
                campaign_id=campaign_id,
                group_code=GroupBuyGroup.generate_group_code(),
                group_name=custom_group_name or f"กลุ่ม {campaign.name}",
                leader_customer_id=leader_info.get('customer_id'),
                leader_name=leader_info['name'],
                leader_email=leader_info.get('email'),
                leader_phone=leader_info.get('phone'),
                status='active',
                required_participants=campaign.min_participants,
                expires_at=naive_utc_now() + timedelta(hours=campaign.duration_hours),
                share_token=GroupBuyGroup.generate_share_token(),
                payment_method='hold'
            )
            
            db.session.add(group)
            db.session.flush()
            
            # สร้าง share URL
            from flask import url_for
            try:
                group.share_url = url_for('public_group_buy.join_group', 
                                         token=group.share_token, 
                                         _external=True)
            except:
                # Fallback if not in request context
                group.share_url = f"/group-buy/join/{group.share_token}"
            
            # ตรวจสอบ max_pax ของแคมเปญก่อนสร้างกลุ่ม
            leader_pax_count = leader_info.get('pax_count', 1)
            if campaign.max_pax:
                # นับ pax ที่จ่ายเงินสำเร็จแล้วในแคมเปญ (เฉพาะกลุ่มที่ success หรือ participant ที่ paid)
                from sqlalchemy import func
                current_total_pax = db.session.query(func.sum(GroupBuyParticipant.pax_count))\
                    .join(GroupBuyGroup)\
                    .filter(
                        GroupBuyGroup.campaign_id == campaign_id,
                        GroupBuyGroup.status == 'success',  # เฉพาะกลุ่มที่สำเร็จแล้ว
                        GroupBuyParticipant.status == 'active'
                    ).scalar() or 0
                
                if current_total_pax + leader_pax_count > campaign.max_pax:
                    return None, f"ไม่สามารถจองได้ เนื่องจากจะเกินจำนวนผู้เดินทางสูงสุดของแคมเปญ ({campaign.max_pax} คน)"
            
            # เพิ่ม leader เป็นสมาชิกคนแรก
            leader_participant = GroupBuyParticipant(
                group_id=group.id,
                campaign_id=campaign_id,
                customer_id=leader_info.get('customer_id'),
                participant_name=leader_info['name'],
                participant_email=leader_info.get('email'),
                participant_phone=leader_info.get('phone'),
                is_leader=True,
                join_order=1,
                pax_count=leader_pax_count,
                payment_status='pending',
                payment_amount=campaign.calculate_partial_payment(leader_pax_count),
                status='active'
            )
            
            db.session.add(leader_participant)
            group.current_participants = 1  # นับจำนวนคน ไม่ใช่ pax
            
            db.session.commit()
            
            logger.info(f"Created group: {group.group_code} for campaign {campaign.name}")
            return (group, leader_participant), None
            
        except Exception as e:
            logger.error(f"Error creating group: {e}")
            db.session.rollback()
            return None, str(e)
    
    def join_group(self, group_code_or_token, participant_info, is_token=False):
        """
        เข้าร่วมกลุ่ม
        
        Args:
            group_code_or_token: รหัสกลุ่มหรือ share token
            participant_info: dict {'name', 'email', 'phone', 'customer_id'(optional), 'pax_count'}
            is_token: True ถ้าเป็น share_token, False ถ้าเป็น group_code
        """
        try:
            # ค้นหากลุ่ม
            if is_token:
                group = GroupBuyGroup.query.filter_by(share_token=group_code_or_token).first()
            else:
                group = GroupBuyGroup.query.filter_by(group_code=group_code_or_token).first()
            
            if not group:
                return None, "ไม่พบกลุ่มนี้"
            
            # ตรวจสอบสถานะกลุ่ม
            if group.status != 'active':
                return None, f"กลุ่มนี้อยู่ในสถานะ: {group.status}"
            
            if group.is_expired:
                group.status = 'failed'
                db.session.commit()
                return None, "กลุ่มนี้หมดเวลาแล้ว"
            
            if group.is_full:
                return None, "กลุ่มนี้เต็มแล้ว"
            
            # ตรวจสอบ max_pax ของแคมเปญก่อนเพิ่มสมาชิก
            pax_count = participant_info.get('pax_count', 1)
            if group.campaign.max_pax:
                current_total_pax = group.total_pax_for_campaign
                if current_total_pax + pax_count > group.campaign.max_pax:
                    return None, f"ไม่สามารถจองได้ เนื่องจากจะเกินจำนวนผู้เดินทางสูงสุดของแคมเปญ ({group.campaign.max_pax} คน)"
            
            # เพิ่มสมาชิก
            
            participant = GroupBuyParticipant(
                group_id=group.id,
                campaign_id=group.campaign_id,
                customer_id=participant_info.get('customer_id'),
                participant_name=participant_info['name'],
                participant_email=participant_info.get('email'),
                participant_phone=participant_info.get('phone'),
                is_leader=False,
                join_order=group.current_participants + 1,
                pax_count=pax_count,
                payment_status='pending',
                payment_amount=group.campaign.group_price * pax_count,
                special_requests=participant_info.get('special_requests'),
                status='active'
            )
            
            db.session.add(participant)
            group.current_participants += 1
            
            # ตรวจสอบว่ากลุ่มครบหรือยัง
            if group.is_full:
                self._handle_group_success(group)
            else:
                # ตรวจสอบ campaign limits (Pax และ Inventory)
                self._check_campaign_limits(group.campaign)
                
                # ส่งการแจ้งเตือน
                self._notify_new_member(group, participant)
            
            db.session.commit()
            
            logger.info(f"Participant {participant.participant_name} joined group {group.group_code}")
            return participant, None
            
        except Exception as e:
            logger.error(f"Error joining group: {e}")
            db.session.rollback()
            return None, str(e)
    
    def _check_campaign_limits(self, campaign):
        """
        ตรวจสอบ Campaign Limits
        - ถ้า Pax (max_pax) ครบ -> ปิด campaign (status=success)
        - ถ้า Inventory (total_slots) ครบ -> ปิด campaign (status=success)
        """
        try:
            # นับจำนวนผู้เข้าร่วมทั้งหมดในทุกกลุ่มที่สำเร็จ
            from sqlalchemy import func
            total_pax = db.session.query(func.sum(GroupBuyGroup.current_participants))\
                .filter(
                    GroupBuyGroup.campaign_id == campaign.id,
                    GroupBuyGroup.status == 'success'
                ).scalar() or 0
            
            # ตรวจสอบ Pax limit
            if campaign.max_pax and total_pax >= campaign.max_pax:
                logger.info(f"Campaign #{campaign.id} reached max_pax limit: {total_pax}/{campaign.max_pax}")
                campaign.status = 'success'
                campaign.is_active = False
                return True
            
            # ตรวจสอบ Inventory limit (available_slots = 0)
            if campaign.total_slots and campaign.available_slots <= 0:
                logger.info(f"Campaign #{campaign.id} reached inventory limit: 0/{campaign.total_slots}")
                campaign.status = 'success'
                campaign.is_active = False
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error checking campaign limits: {e}")
            return False
    
    def _handle_group_success(self, group):
        """จัดการเมื่อกลุ่มสำเร็จ (ครบคน)"""
        try:
            group.status = 'success'
            group.completed_at = naive_utc_now()
            
            # ลด available_slots ของ campaign ตามจำนวนกลุ่มที่สำเร็จ
            campaign = group.campaign
            if campaign.total_slots and campaign.available_slots > 0:
                campaign.available_slots -= 1
                logger.info(f"Campaign #{campaign.id} available_slots decreased: {campaign.available_slots + 1} -> {campaign.available_slots}")
            
            # สร้าง Master Booking
            booking = self._create_master_booking(group)
            if booking:
                group.master_booking_id = booking.id
            
            # สร้าง Booking สำหรับแต่ละคน
            for participant in group.participants:
                if participant.status == 'active':
                    participant_booking = self._create_participant_booking(group, participant)
                    if participant_booking:
                        participant.booking_id = participant_booking.id
            
            # ส่งการแจ้งเตือน
            self._notify_group_success(group)
            
            logger.info(f"Group {group.group_code} succeeded!")
            
        except Exception as e:
            logger.error(f"Error handling group success: {e}")
            raise
    
    def _create_master_booking(self, group):
        """สร้าง Master Booking สำหรับกลุ่ม"""
        try:
            campaign = group.campaign
            
            # ใช้ข้อมูล leader เป็น customer
            leader = group.participants.filter_by(is_leader=True).first()
            
            # หา customer_id หรือสร้างใหม่
            if leader.customer_id:
                customer = Customer.query.get(leader.customer_id)
            else:
                # สร้าง customer ใหม่
                customer = Customer(
                    name=leader.participant_name,
                    email=leader.participant_email or f"groupbuy_{group.group_code}@temp.com",
                    phone=leader.participant_phone or "",
                    customer_type='Visitor-Individual'
                )
                db.session.add(customer)
                db.session.flush()
            
            # สร้าง booking
            product_details = campaign.get_product_details()
            
            booking = Booking(
                customer_id=customer.id,
                booking_reference=f"GB-{group.group_code}",
                booking_type=campaign.product_type,
                status='confirmed',
                total_pax=group.current_participants,
                description=f"Group Buy: {campaign.name}",
                party_name=group.group_name,
                party_code=group.group_code,
                admin_notes=f"Group Buy Campaign ID: {campaign.id}\nGroup ID: {group.id}",
                total_amount=float(campaign.group_price) * group.current_participants,
                time_limit=naive_utc_now() + timedelta(hours=campaign.duration_hours)
            )
            
            db.session.add(booking)
            db.session.flush()
            
            logger.info(f"Created master booking: {booking.booking_reference}")
            return booking
            
        except Exception as e:
            logger.error(f"Error creating master booking: {e}")
            return None
    
    def _create_participant_booking(self, group, participant):
        """สร้าง Booking สำหรับสมาชิกแต่ละคน"""
        try:
            campaign = group.campaign
            
            # หา customer_id
            if participant.customer_id:
                customer = Customer.query.get(participant.customer_id)
            else:
                # สร้าง customer ใหม่
                customer = Customer(
                    name=participant.participant_name,
                    email=participant.participant_email or f"participant_{participant.id}@temp.com",
                    phone=participant.participant_phone or "",
                    customer_type='Visitor-Individual'
                )
                db.session.add(customer)
                db.session.flush()
            
            booking = Booking(
                customer_id=customer.id,
                booking_reference=f"GB-{group.group_code}-P{participant.join_order}",
                booking_type=campaign.product_type,
                status='confirmed',
                total_pax=participant.pax_count,
                description=f"Group Buy: {campaign.name} (สมาชิกกลุ่ม {group.group_code})",
                party_name=group.group_name,
                party_code=group.group_code,
                admin_notes=f"Group Buy Participant ID: {participant.id}\nGroup ID: {group.id}\nCampaign ID: {campaign.id}",
                total_amount=float(participant.payment_amount),
                time_limit=naive_utc_now() + timedelta(hours=campaign.duration_hours)
            )
            
            db.session.add(booking)
            db.session.flush()
            
            return booking
            
        except Exception as e:
            logger.error(f"Error creating participant booking: {e}")
            return None
    
    def check_expired_groups(self):
        """ตรวจสอบและจัดการกลุ่มที่หมดเวลา (ใช้กับ Cron Job)"""
        try:
            expired_groups = GroupBuyGroup.query.filter(
                GroupBuyGroup.status == 'active',
                GroupBuyGroup.expires_at < naive_utc_now()
            ).all()
            
            for group in expired_groups:
                if not group.is_full:
                    self._handle_group_failed(group)
            
            db.session.commit()
            
            logger.info(f"Checked {len(expired_groups)} expired groups")
            return len(expired_groups)
            
        except Exception as e:
            logger.error(f"Error checking expired groups: {e}")
            db.session.rollback()
            return 0
    
    def _handle_group_failed(self, group):
        """จัดการเมื่อกลุ่มล้มเหลว (ไม่ครบคน)"""
        try:
            group.status = 'failed'
            group.cancelled_at = naive_utc_now()
            
            # คืนเงิน/ยกเลิก authorization ถ้ามี
            for participant in group.participants:
                if participant.payment_status in ['authorized', 'paid']:
                    participant.payment_status = 'refunded'
                    # TODO: Implement actual refund logic here
            
            # ส่งการแจ้งเตือน
            self._notify_group_failed(group)
            
            logger.info(f"Group {group.group_code} failed (not enough participants)")
            
        except Exception as e:
            logger.error(f"Error handling group failure: {e}")
            raise
    
    def _notify_new_member(self, group, participant):
        """แจ้งเตือนเมื่อมีสมาชิกใหม่"""
        # TODO: Implement notification (LINE, Email, etc.)
        notification = GroupBuyNotification(
            group_id=group.id,
            notification_type='new_member',
            message=f"{participant.participant_name} เข้าร่วมกลุ่ม! ({group.current_participants}/{group.required_participants})"
        )
        db.session.add(notification)
    
    def _notify_group_success(self, group):
        """แจ้งเตือนเมื่อกลุ่มสำเร็จ"""
        # TODO: Implement notification
        notification = GroupBuyNotification(
            group_id=group.id,
            notification_type='group_success',
            message=f"ยินดีด้วย! กลุ่ม {group.group_code} สำเร็จแล้ว"
        )
        db.session.add(notification)
    
    def _notify_group_failed(self, group):
        """แจ้งเตือนเมื่อกลุ่มล้มเหลว"""
        # TODO: Implement notification
        notification = GroupBuyNotification(
            group_id=group.id,
            notification_type='group_failed',
            message=f"กลุ่ม {group.group_code} ไม่สำเร็จ (ไม่ครบจำนวนคน)"
        )
        db.session.add(notification)
    
    def get_active_campaigns(self, product_type=None, featured_only=False):
        """ดึงรายการแคมเปญที่กำลังทำงาน"""
        query = GroupBuyCampaign.query.filter(
            GroupBuyCampaign.is_active == True,
            GroupBuyCampaign.status == 'active',
            GroupBuyCampaign.is_public == True,
            GroupBuyCampaign.campaign_start_date <= naive_utc_now(),
            GroupBuyCampaign.campaign_end_date >= naive_utc_now()
        )
        
        if product_type:
            query = query.filter_by(product_type=product_type)
        
        if featured_only:
            query = query.filter_by(featured=True)
        
        return query.order_by(GroupBuyCampaign.featured.desc(), 
                             GroupBuyCampaign.created_at.desc()).all()
    
    def get_group_by_code(self, group_code):
        """ค้นหากลุ่มจากรหัส"""
        return GroupBuyGroup.query.filter_by(group_code=group_code).first()
    
    def get_group_by_token(self, share_token):
        """ค้นหากลุ่มจาก share token"""
        return GroupBuyGroup.query.filter_by(share_token=share_token).first()
