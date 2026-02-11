"""
Group Buy Public Routes
หน้าสำหรับลูกค้าทั่วไป - สร้างกลุ่ม/เข้าร่วมกลุ่ม
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session, current_app
from models.group_buy import GroupBuyCampaign, GroupBuyGroup, GroupBuyParticipant
from models.review import CampaignReview
from services.group_buy_service import GroupBuyService
from extensions import db
from utils.turnstile import verify_turnstile_from_request
import logging

bp = Blueprint('public_group_buy', __name__, url_prefix='/group-buy')
logger = logging.getLogger(__name__)
service = GroupBuyService()

@bp.route('/')
def index():
    """หน้าแรก - แสดงแคมเปญ Group Buy ทั้งหมด"""
    product_type = request.args.get('type')
    featured_only = request.args.get('featured') == '1'
    
    campaigns = service.get_active_campaigns(
        product_type=product_type,
        featured_only=featured_only
    )
    
    return render_template('group_buy/public/index.html', campaigns=campaigns)

@bp.route('/campaign/<int:campaign_id>')
def view_campaign(campaign_id):
    """ดูรายละเอียดแคมเปญ"""
    campaign = GroupBuyCampaign.query.get_or_404(campaign_id)
    
    if not campaign.is_active_now or not campaign.is_public:
        flash('แคมเปญนี้ไม่เปิดให้ใช้งาน', 'warning')
        return redirect(url_for('public_group_buy.index'))
    
    # ดึงกลุ่มที่กำลัง active
    active_groups = GroupBuyGroup.query.filter_by(
        campaign_id=campaign_id,
        status='active'
    ).order_by(GroupBuyGroup.created_at.desc()).limit(10).all()
    
    # ดึงรีวิวที่อนุมัติแล้ว
    reviews = CampaignReview.query.filter_by(
        campaign_id=campaign_id,
        is_approved=True
    ).order_by(CampaignReview.created_at.desc()).all()
    
    return render_template('group_buy/public/campaign_detail_improved.html',
                         campaign=campaign,
                         active_groups=active_groups,
                         reviews=reviews)

@bp.route('/campaign/<int:campaign_id>/create-group', methods=['GET', 'POST'])
def create_group(campaign_id):
    """สร้างกลุ่มใหม่"""
    campaign = GroupBuyCampaign.query.get_or_404(campaign_id)
    
    if not campaign.is_active_now:
        flash('แคมเปญนี้ไม่เปิดให้ใช้งาน', 'warning')
        return redirect(url_for('public_group_buy.view_campaign', campaign_id=campaign_id))
    
    if request.method == 'POST':
        try:
            # ตรวจสอบ Turnstile token
            turnstile_valid, turnstile_msg = verify_turnstile_from_request(request)
            if not turnstile_valid:
                flash(turnstile_msg, 'danger')
                return render_template('group_buy/public/create_group.html', campaign=campaign)
            
            leader_info = {
                'name': request.form.get('name'),
                'email': request.form.get('email'),
                'phone': request.form.get('phone'),
                'pax_count': int(request.form.get('pax_count', 1))
            }
            
            # ✅ รับรหัสพิเศษจากฟอร์ม
            special_code = request.form.get('special_code', '').strip().upper()
            
            # ✅ ตรวจสอบว่ามีรหัสพิเศษหรือไม่
            is_special_booker = campaign.is_special_booker(special_code) if special_code else False
            
            # ✅ ป้องกันการจองซ้ำ: ตรวจสอบ Email เฉพาะคนที่ไม่มีรหัสพิเศษ
            if not is_special_booker:
                from models.group_buy import GroupBuyParticipant
                existing_participant = GroupBuyParticipant.query.join(GroupBuyGroup).filter(
                    GroupBuyGroup.campaign_id == campaign_id,
                    GroupBuyParticipant.participant_email == leader_info['email'],
                    GroupBuyParticipant.payment_status.in_(['pending', 'paid', 'authorized'])
                ).first()
                
                if existing_participant:
                    flash(f'อีเมล {leader_info["email"]} มีการจองในแคมเปญนี้อยู่แล้ว กรุณาใช้อีเมลอื่นหรือติดต่อเจ้าหน้าที่', 'warning')
                    return render_template('group_buy/public/create_group.html', campaign=campaign, 
                                         turnstile_site_key=current_app.config.get('TURNSTILE_SITE_KEY'))
            else:
                # ✅ ผู้จองพิเศษ - ให้จองได้ซ้ำ
                logger.info(f"Special booker code used: {special_code} for {leader_info['email']}")
            
            # เก็บข้อมูลใน session เพื่อไปหน้ายืนยัน
            session['pending_booking'] = {
                'campaign_id': campaign_id,
                'name': leader_info['name'],
                'email': leader_info['email'],
                'phone': leader_info['phone'],
                'pax_count': leader_info['pax_count'],
                'group_name': request.form.get('group_name'),
                'special_code': special_code if is_special_booker else None  # เก็บรหัสไว้
            }
            
            # ไปหน้ายืนยันข้อมูล
            return redirect(url_for('public_group_buy.confirm_booking', campaign_id=campaign_id))
                
        except Exception as e:
            logger.error(f"Error in create_group: {e}")
            flash('เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง', 'danger')
            return render_template('group_buy/public/create_group.html', campaign=campaign,
                                 turnstile_site_key=current_app.config.get('TURNSTILE_SITE_KEY'))
    
    return render_template('group_buy/public/create_group.html', campaign=campaign,
                         turnstile_site_key=current_app.config.get('TURNSTILE_SITE_KEY'))

@bp.route('/campaign/<int:campaign_id>/confirm', methods=['GET', 'POST'])
def confirm_booking(campaign_id):
    """
    Smart Progressive Registration Flow
    - ตรวจสอบอีเมลอัตโนมัติ
    - แสดง Login Form สำหรับลูกค้าเก่า
    - แสดง Registration Form สำหรับลูกค้าใหม่
    - Auto-create account เมื่อยืนยัน
    """
    from models.group_buy import GroupBuyCampaign
    from services.group_buy_service import GroupBuyService
    from services.points_service import PointsService
    from models.customer import Customer
    from models.user import User
    from flask_login import login_user, current_user
    
    campaign = GroupBuyCampaign.query.get_or_404(campaign_id)
    
    # ตรวจสอบว่ามีข้อมูลใน session หรือไม่
    booking_data = session.get('pending_booking')
    if not booking_data or booking_data.get('campaign_id') != campaign_id:
        flash('ไม่พบข้อมูลการจอง กรุณากรอกข้อมูลใหม่อีกครั้ง', 'warning')
        return redirect(url_for('public_group_buy.view_campaign', campaign_id=campaign_id))
    
    # ========== GET REQUEST - ตรวจสอบอีเมลและแสดง UI ที่เหมาะสม ==========
    if request.method == 'GET':
        # 🔍 Smart Email Detection
        existing_user = User.query.filter_by(email=booking_data['email']).first()
        
        has_account = bool(existing_user)
        available_points = 0
        customer = None
        
        if existing_user:
            # ลูกค้าเก่า - ดึงข้อมูลแต้ม
            customer = Customer.query.filter_by(user_id=existing_user.id).first()
            if customer:
                points_service = PointsService()
                customer_points_obj = points_service.get_customer_points(customer.id)
                available_points = customer_points_obj.available_points if customer_points_obj else 0
        
        return render_template('group_buy/public/confirm_booking.html',
            campaign=campaign,
            booking_data=booking_data,
            has_account=has_account,
            available_points=available_points,
            customer=customer
        )
    
    # ========== POST REQUEST - ประมวลผล Login/Registration ==========
    if request.method == 'POST':
        try:
            password = request.form.get('password')
            password_confirm = request.form.get('password_confirm')
            
            if not password:
                flash('กรุณาระบุรหัสผ่าน', 'danger')
                return redirect(url_for('public_group_buy.confirm_booking', campaign_id=campaign_id))
            
            # 🔍 ตรวจสอบว่ามี user อยู่แล้วหรือไม่
            existing_user = User.query.filter_by(email=booking_data['email']).first()
            
            if existing_user:
                # ========== SCENARIO B: ลูกค้าเก่า - Login ==========
                if not existing_user.check_password(password):
                    flash('รหัสผ่านไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง', 'danger')
                    return redirect(url_for('public_group_buy.confirm_booking', campaign_id=campaign_id))
                
                # ✅ Login สำเร็จ
                login_user(existing_user, remember=True)
                
                # ดึง customer profile
                customer = Customer.query.filter_by(user_id=existing_user.id).first()
                if customer:
                    session['booking_customer_id'] = customer.id
                
                logger.info(f"✅ Existing customer logged in: {existing_user.email}")
            
            else:
                # ========== SCENARIO A: ลูกค้าใหม่ - Auto Register ==========
                
                # Validate password
                if password != password_confirm:
                    flash('รหัสผ่านไม่ตรงกัน กรุณาลองใหม่อีกครั้ง', 'danger')
                    return redirect(url_for('public_group_buy.confirm_booking', campaign_id=campaign_id))
                
                if len(password) < 6:
                    flash('รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร', 'danger')
                    return redirect(url_for('public_group_buy.confirm_booking', campaign_id=campaign_id))
                
                # สร้าง username จากอีเมล
                username = booking_data['email'].split('@')[0]
                base_username = username
                counter = 1
                while User.query.filter_by(username=username).first():
                    username = f"{base_username}{counter}"
                    counter += 1
                
                # 🎉 สร้าง User ใหม่
                new_user = User.create_user(
                    username=username,
                    email=booking_data['email'],
                    password=password,
                    is_admin=False,
                    role='Customer'
                )
                db.session.add(new_user)
                db.session.flush()
                
                # 🎉 สร้าง Customer Profile
                new_customer = Customer(
                    name=booking_data['name'],
                    email=booking_data['email'],
                    phone=booking_data['phone'],
                    customer_type='Visitor-Individual',
                    user_id=new_user.id,
                    created_by=new_user.id
                )
                db.session.add(new_customer)
                db.session.commit()
                
                # ✅ Login อัตโนมัติ
                login_user(new_user, remember=True)
                session['booking_customer_id'] = new_customer.id
                
                flash('🎉 สมัครสมาชิกสำเร็จ! คุณจะได้รับแต้มสะสมจากการจองนี้', 'success')
                logger.info(f"✅ New customer auto-registered: {new_user.email}")
            
            # ========== จัดการแต้มสะสม (เฉพาะลูกค้าที่ Login แล้ว) ==========
            service = GroupBuyService()
            points_service = PointsService()
            
            try:
                points_used = int(request.form.get('points_used', 0) or 0)
            except (ValueError, TypeError):
                points_used = 0
            
            discount_amount = 0
            
            if points_used > 0 and current_user.is_authenticated:
                customer = Customer.query.filter_by(user_id=current_user.id).first()
                if customer:
                    # ตรวจสอบว่าแลกแต้มได้หรือไม่
                    can_redeem = points_service.can_redeem(customer.id, points_used)
                    if can_redeem:
                        discount_amount = points_service.calculate_discount(points_used)
                        # เก็บข้อมูลไว้ใน session เพื่อหักแต้มหลังชำระเงิน
                        session['pending_points_redemption'] = {
                            'customer_id': customer.id,
                            'points': points_used,
                            'discount': discount_amount
                        }
                        logger.info(f"💎 Points redemption: {points_used} points = ฿{discount_amount} discount")
                    else:
                        flash('คะแนนของคุณไม่เพียงพอ', 'warning')
                        points_used = 0
                        discount_amount = 0
            
            # ========== สร้างกลุ่มใหม่ หรือ เข้าร่วมกลุ่มที่มีอยู่ ==========
            if 'group_name' in booking_data:
                # สร้างกลุ่มใหม่
                leader_info = {
                    'name': booking_data['name'],
                    'email': booking_data['email'],
                    'phone': booking_data['phone'],
                    'pax_count': booking_data['pax_count']
                }
                custom_group_name = booking_data.get('group_name')
                
                result, error = service.create_group(
                    campaign_id=campaign_id,
                    leader_info=leader_info,
                    custom_group_name=custom_group_name
                )
                
                if result:
                    group, leader_participant = result
                    
                    # 🔗 Link participant กับ customer (สำคัญมาก!)
                    if current_user.is_authenticated:
                        customer = Customer.query.filter_by(user_id=current_user.id).first()
                        if customer:
                            leader_participant.customer_id = customer.id
                            db.session.commit()
                            logger.info(f"🔗 Linked participant to customer: {customer.id}")
                    
                    session['group_created'] = group.id
                    session['participant_id'] = leader_participant.id
                    session['pending_payment_campaign'] = campaign_id
                    session.pop('pending_booking', None)
                    flash('ยืนยันการจองสำเร็จ! กรุณาชำระเงินเพื่อยืนยันการเข้าร่วม', 'success')
                    
                    # Redirect ไป My Bookings ถ้า auto-login สำเร็จ
                    if current_user.is_authenticated and current_user.role == 'Customer':
                        return redirect(url_for('customer.my_bookings'))
                    
                    return redirect(url_for('group_buy_payment.select_method', 
                                          campaign_id=campaign_id))
                else:
                    flash(f'ไม่สามารถสร้างกลุ่มได้: {error}', 'danger')
                    return redirect(url_for('public_group_buy.create_group', campaign_id=campaign_id))
            
            else:
                # เข้าร่วมกลุ่มที่มีอยู่
                participant_info = {
                    'name': booking_data['name'],
                    'email': booking_data['email'],
                    'phone': booking_data['phone'],
                    'pax_count': booking_data['pax_count'],
                    'special_requests': booking_data.get('special_requests', '')
                }
                
                # ถ้ามี group_id หมายถึงเข้าร่วมผ่าน join_group
                if 'group_id' in booking_data:
                    from models.group_buy import GroupBuyGroup
                    group = GroupBuyGroup.query.get(booking_data['group_id'])
                    
                    if not group:
                        flash('ไม่พบกลุ่มที่ต้องการเข้าร่วม', 'danger')
                        return redirect(url_for('public_group_buy.view_campaign', campaign_id=campaign_id))
                    
                    if group.share_token == session.get('join_token'):
                        # เข้าร่วมผ่าน token (share link)
                        result, error = service.join_group(
                            group_code_or_token=session.get('join_token'),
                            participant_info=participant_info,
                            is_token=True
                        )
                    else:
                        # เข้าร่วมผ่าน group_code (จากหน้า campaign)
                        result, error = service.join_group(
                            group_code_or_token=group.group_code,
                            participant_info=participant_info,
                            is_token=False
                        )
                else:
                    flash('ข้อมูลการจองไม่ถูกต้อง', 'danger')
                    return redirect(url_for('public_group_buy.view_campaign', campaign_id=campaign_id))
                
                if result:
                    participant = result
                    
                    # 🔗 Link participant กับ customer
                    if current_user.is_authenticated:
                        customer = Customer.query.filter_by(user_id=current_user.id).first()
                        if customer:
                            participant.customer_id = customer.id
                            db.session.commit()
                            logger.info(f"🔗 Linked participant to customer: {customer.id}")
                    
                    session['participant_id'] = participant.id
                    session['pending_payment_campaign'] = campaign_id
                    session.pop('pending_booking', None)
                    session.pop('join_token', None)
                    flash('ยืนยันการจองสำเร็จ! กรุณาชำระเงินเพื่อยืนยันการเข้าร่วม', 'success')
                    
                    # Redirect ไป My Bookings ถ้า auto-login สำเร็จ
                    if current_user.is_authenticated and current_user.role == 'Customer':
                        return redirect(url_for('customer.my_bookings'))
                    
                    return redirect(url_for('group_buy_payment.select_method', 
                                          campaign_id=campaign_id))
                else:
                    flash(f'ไม่สามารถเข้าร่วมกลุ่มได้: {error}', 'danger')
                    return redirect(url_for('public_group_buy.view_campaign', campaign_id=campaign_id))
                    
        except Exception as e:
            db.session.rollback()
            import traceback
            logger.error(f"❌ Error in confirm_booking: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            flash(f'เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง', 'danger')
            return redirect(url_for('public_group_buy.confirm_booking', campaign_id=campaign_id))
    
    # ไม่ควรเกิดขึ้น แต่เผื่อ fallback
    return redirect(url_for('public_group_buy.view_campaign', campaign_id=campaign_id))

@bp.route('/join/<token>')
def join_group(token):
    """เข้าหน้า Join ผ่าน Share Link"""
    group = service.get_group_by_token(token)
    
    if not group:
        flash('ไม่พบกลุ่มนี้', 'danger')
        return redirect(url_for('public_group_buy.index'))
    
    if group.status != 'active':
        flash(f'กลุ่มนี้อยู่ในสถานะ: {group.status_display}', 'warning')
        return redirect(url_for('public_group_buy.group_status', 
                              group_code=group.group_code))
    
    if group.is_expired:
        flash('กลุ่มนี้หมดเวลาแล้ว', 'warning')
        return redirect(url_for('public_group_buy.group_status', 
                              group_code=group.group_code))
    
    if group.is_full:
        flash('กลุ่มนี้เต็มแล้ว', 'warning')
        return redirect(url_for('public_group_buy.group_status', 
                              group_code=group.group_code))
    
    return render_template('group_buy/public/join_group.html', 
                         group=group,
                         campaign=group.campaign,
                         turnstile_site_key=current_app.config.get('TURNSTILE_SITE_KEY'))

@bp.route('/join/<token>/submit', methods=['POST'])
def submit_join(token):
    """ส่งข้อมูลเข้าร่วมกลุ่ม"""
    try:
        # ตรวจสอบ Turnstile token
        turnstile_valid, turnstile_msg = verify_turnstile_from_request(request)
        if not turnstile_valid:
            flash(turnstile_msg, 'danger')
            return redirect(url_for('public_group_buy.join_group', token=token))
        
        # ดึงข้อมูลกลุ่ม
        group = service.get_group_by_token(token)
        if not group:
            flash('ไม่พบกลุ่มนี้', 'danger')
            return redirect(url_for('public_group_buy.index'))
        
        participant_info = {
            'name': request.form.get('name'),
            'email': request.form.get('email'),
            'phone': request.form.get('phone'),
            'pax_count': int(request.form.get('pax_count', 1)),
            'special_requests': request.form.get('special_requests')
        }
        
        # ✅ รับรหัสพิเศษจากฟอร์ม
        special_code = request.form.get('special_code', '').strip().upper()
        
        # ✅ ตรวจสอบว่ามีรหัสพิเศษหรือไม่
        is_special_booker = group.campaign.is_special_booker(special_code) if special_code else False
        
        # ✅ ป้องกันการจองซ้ำ: ตรวจสอบ Email เฉพาะคนที่ไม่มีรหัสพิเศษ
        if not is_special_booker:
            from models.group_buy import GroupBuyParticipant
            existing_in_group = GroupBuyParticipant.query.filter_by(
                group_id=group.id,
                participant_email=participant_info['email']
            ).first()
            
            if existing_in_group:
                flash(f'อีเมล {participant_info["email"]} มีในกลุ่มนี้อยู่แล้ว กรุณาใช้อีเมลอื่น', 'warning')
                return redirect(url_for('public_group_buy.join_group', token=token))
        else:
            # ✅ ผู้จองพิเศษ - ให้เข้าร่วมได้ซ้ำ
            logger.info(f'Special booker code used: {special_code} for {participant_info["email"]} in join group')
        
        # เก็บข้อมูลใน session เพื่อไปหน้ายืนยัน
        session['pending_booking'] = {
            'campaign_id': group.campaign_id,
            'group_id': group.id,
            'name': participant_info['name'],
            'email': participant_info['email'],
            'phone': participant_info['phone'],
            'pax_count': participant_info['pax_count'],
            'special_requests': participant_info.get('special_requests', ''),
            'special_code': special_code if is_special_booker else None  # เก็บรหัสไว้
        }
        session['join_token'] = token
        
        # ไปหน้ายืนยันข้อมูล
        return redirect(url_for('public_group_buy.confirm_booking', campaign_id=group.campaign_id))
            
    except Exception as e:
        logger.error(f"Error in submit_join: {e}")
        flash('เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง', 'danger')
        return redirect(url_for('public_group_buy.join_group', token=token))

@bp.route('/group/<group_code>')
def group_status(group_code):
    """หน้าสถานะกลุ่ม - แสดงความคืบหน้า"""
    group = service.get_group_by_code(group_code)
    
    if not group:
        flash('ไม่พบกลุ่มนี้', 'danger')
        return redirect(url_for('public_group_buy.index'))
    
    participants = GroupBuyParticipant.query.filter_by(
        group_id=group.id
    ).order_by(GroupBuyParticipant.join_order).all()
    
    return render_template('group_buy/public/group_status.html',
                         group=group,
                         campaign=group.campaign,
                         participants=participants)

@bp.route('/my-groups')
def my_groups():
    """กลุ่มของฉัน (ใช้ session tracking)"""
    # TODO: เชื่อมกับระบบ login ของลูกค้า
    participant_id = session.get('participant_id')
    group_created = session.get('group_created')
    
    my_participations = []
    my_created_groups = []
    
    if participant_id:
        participant = GroupBuyParticipant.query.get(participant_id)
        if participant:
            my_participations.append(participant)
    
    if group_created:
        group = GroupBuyGroup.query.get(group_created)
        if group:
            my_created_groups.append(group)
    
    return render_template('group_buy/public/my_groups.html',
                         my_participations=my_participations,
                         my_created_groups=my_created_groups)

@bp.route('/api/group/<group_code>/status')
def api_group_status(group_code):
    """API: สถานะกลุ่มแบบ real-time (สำหรับ AJAX polling)"""
    group = service.get_group_by_code(group_code)
    
    if not group:
        return jsonify({'error': 'Group not found'}), 404
    
    data = {
        'status': group.status,
        'status_display': group.status_display,
        'current_participants': group.current_participants,
        'required_participants': group.required_participants,
        'progress_percentage': group.progress_percentage,
        'is_full': group.is_full,
        'is_expired': group.is_expired,
        'time_remaining': group.time_remaining,
        'participants': [
            {
                'name': p.participant_name,
                'join_order': p.join_order,
                'pax_count': p.pax_count
            }
            for p in group.participants.order_by(GroupBuyParticipant.join_order).all()
        ]
    }
    
    return jsonify(data)

@bp.route('/api/campaign/<int:campaign_id>/active-groups')
def api_campaign_active_groups(campaign_id):
    """API: กลุ่มที่กำลัง active ของแคมเปญ"""
    groups = GroupBuyGroup.query.filter_by(
        campaign_id=campaign_id,
        status='active'
    ).order_by(GroupBuyGroup.created_at.desc()).all()
    
    data = [
        {
            'id': g.id,
            'group_code': g.group_code,
            'group_name': g.group_name,
            'current_participants': g.current_participants,
            'required_participants': g.required_participants,
            'progress_percentage': g.progress_percentage,
            'time_remaining': g.time_remaining,
            'leader_name': g.leader_name
        }
        for g in groups
    ]
    
    return jsonify(data)

# ==================== REVIEW SYSTEM ROUTES ====================

@bp.route('/campaign/<int:campaign_id>/review', methods=['GET'])
def review_form(campaign_id):
    """หน้าฟอร์มเขียนรีวิว"""
    from models.booking import Booking
    
    campaign = GroupBuyCampaign.query.get_or_404(campaign_id)
    booking_id = request.args.get('booking_id')
    
    booking = None
    if booking_id:
        booking = Booking.query.get(booking_id)
    
    return render_template('group_buy/public/review_form.html',
                         campaign=campaign,
                         booking=booking,
                         booking_id=booking_id)

@bp.route('/campaign/<int:campaign_id>/submit-review', methods=['POST'])
def submit_review(campaign_id):
    """ส่งรีวิว"""
    from models.review import CampaignReview, ReviewImage, CustomerPoints, PointTransaction
    from models.booking import Booking
    from werkzeug.utils import secure_filename
    import os
    from datetime import datetime
    
    try:
        campaign = GroupBuyCampaign.query.get_or_404(campaign_id)
        
        # รับข้อมูลจากฟอร์ม
        booking_id = request.form.get('booking_id')
        rating = int(request.form.get('rating', 5))
        comment = request.form.get('comment', '').strip()
        
        # Validate
        if not booking_id or not comment:
            return jsonify({'success': False, 'message': 'กรุณากรอกข้อมูลให้ครบถ้วน'}), 400
        
        if len(comment) < 10:
            return jsonify({'success': False, 'message': 'รีวิวต้องมีอย่างน้อย 10 ตัวอักษร'}), 400
        
        if len(comment) > 1000:
            return jsonify({'success': False, 'message': 'รีวิวต้องไม่เกิน 1000 ตัวอักษร'}), 400
        
        # ตรวจสอบ Booking
        booking = Booking.query.get(booking_id)
        if not booking:
            return jsonify({'success': False, 'message': 'ไม่พบข้อมูลการจอง'}), 404
        
        # ตรวจสอบว่าเคยรีวิวแล้วหรือยัง
        existing_review = CampaignReview.query.filter_by(
            campaign_id=campaign_id,
            booking_id=booking_id
        ).first()
        
        if existing_review:
            return jsonify({'success': False, 'message': 'คุณได้รีวิวการจองนี้แล้ว'}), 400
        
        # สร้างรีวิว
        review = CampaignReview(
            campaign_id=campaign_id,
            booking_id=booking_id,
            customer_id=booking.customer_id,
            rating=rating,
            comment=comment,
            is_approved=False  # รออนุมัติ
        )
        db.session.add(review)
        db.session.flush()  # เพื่อให้ได้ review.id
        
        # จัดการรูปภาพ
        uploaded_files = request.files.getlist('images')
        image_count = 0
        
        for file in uploaded_files:
            if file and file.filename:
                if image_count >= 5:
                    break
                
                # ตรวจสอบ extension
                allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
                filename = secure_filename(file.filename)
                if '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                    # สร้างชื่อไฟล์ใหม่
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    ext = filename.rsplit('.', 1)[1].lower()
                    new_filename = f"review_{review.id}_{timestamp}_{image_count}.{ext}"
                    
                    # บันทึกไฟล์
                    upload_folder = os.path.join(current_app.root_path, 'static/uploads/reviews')
                    os.makedirs(upload_folder, exist_ok=True)
                    filepath = os.path.join(upload_folder, new_filename)
                    file.save(filepath)
                    
                    # บันทึกข้อมูลรูปภาพ
                    review_image = ReviewImage(
                        review_id=review.id,
                        image_path=f'uploads/reviews/{new_filename}'
                    )
                    db.session.add(review_image)
                    image_count += 1
        
        # คำนวณแต้มที่จะได้รับ
        base_points = 50
        photo_bonus = 20 if image_count > 0 else 0
        long_review_bonus = 10 if len(comment) > 100 else 0
        total_points = base_points + photo_bonus + long_review_bonus
        
        # อัพเดทหรือสร้าง CustomerPoints
        customer_points = CustomerPoints.query.filter_by(
            customer_id=booking.customer_id
        ).first()
        
        if not customer_points:
            customer_points = CustomerPoints(customer_id=booking.customer_id)
            db.session.add(customer_points)
        
        customer_points.total_points += total_points
        
        # บันทึก transaction
        transaction = PointTransaction(
            customer_id=booking.customer_id,
            points=total_points,
            transaction_type='earn',
            description=f'รีวิวทัวร์ {campaign.name}',
            booking_id=booking_id
        )
        db.session.add(transaction)
        
        # อัพเดท booking
        booking.has_reviewed = True
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'ส่งรีวิวเรียบร้อยแล้ว รอการอนุมัติจาก Admin',
            'points_earned': total_points,
            'review_id': review.id
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error submitting review: {e}")
        return jsonify({'success': False, 'message': 'เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง'}), 500

@bp.route('/api/campaign/<int:campaign_id>/reviews')
def get_reviews(campaign_id):
    """API: ดึงรีวิวของแคมเปญ"""
    from models.review import CampaignReview
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # ดึงเฉพาะรีวิวที่ approved แล้ว
    reviews_query = CampaignReview.query.filter_by(
        campaign_id=campaign_id,
        is_approved=True
    ).order_by(CampaignReview.created_at.desc())
    
    pagination = reviews_query.paginate(page=page, per_page=per_page, error_out=False)
    
    reviews_data = []
    for review in pagination.items:
        reviews_data.append({
            'id': review.id,
            'rating': review.rating,
            'comment': review.comment,
            'customer_name': review.customer.name if review.customer else 'ลูกค้า',
            'created_at': review.created_at.isoformat(),
            'images': [img.image_path for img in review.images]
        })
    
    return jsonify({
        'reviews': reviews_data,
        'total': pagination.total,
        'page': page,
        'pages': pagination.pages
    })

@bp.route('/api/campaign/<int:campaign_id>/review-stats')
def get_review_stats(campaign_id):
    """API: สถิติรีวิวของแคมเปญ"""
    from models.review import CampaignReview
    from sqlalchemy import func
    
    # นับจำนวนรีวิวที่ approved
    total_reviews = CampaignReview.query.filter_by(
        campaign_id=campaign_id,
        is_approved=True
    ).count()
    
    # คะแนนเฉลี่ย
    avg_rating = db.session.query(func.avg(CampaignReview.rating)).filter(
        CampaignReview.campaign_id == campaign_id,
        CampaignReview.is_approved == True
    ).scalar() or 0
    
    # จำนวนรีวิวแต่ละระดับ
    rating_distribution = {}
    for rating in range(1, 6):
        count = CampaignReview.query.filter_by(
            campaign_id=campaign_id,
            rating=rating,
            is_approved=True
        ).count()
        rating_distribution[str(rating)] = count
    
    return jsonify({
        'average_rating': round(float(avg_rating), 1),
        'total_reviews': total_reviews,
        'rating_distribution': rating_distribution
    })

# ==================== POINTS SYSTEM ROUTES ====================

@bp.route('/customer/points-profile')
def points_profile():
    """หน้าแสดงแต้มสะสมและประวัติ"""
    from models.review import CustomerPoints, PointTransaction, CampaignReview
    from models.booking import Booking
    
    # TODO: ต้องมีระบบ login ก่อน - ตอนนี้ใช้ customer_id จาก query string
    customer_id = request.args.get('customer_id', type=int)
    
    if not customer_id:
        flash('กรุณาระบุ Customer ID', 'warning')
        return redirect(url_for('public_group_buy.index'))
    
    # ดึงข้อมูลแต้ม
    customer_points = CustomerPoints.query.filter_by(customer_id=customer_id).first()
    if not customer_points:
        customer_points = CustomerPoints(
            customer_id=customer_id,
            total_points=0,
            used_points=0
        )
    
    # ดึงประวัติ transactions
    transactions = PointTransaction.query.filter_by(
        customer_id=customer_id
    ).order_by(PointTransaction.created_at.desc()).limit(50).all()
    
    # ดึงรีวิวที่เคยเขียน
    reviews = CampaignReview.query.filter_by(
        customer_id=customer_id
    ).order_by(CampaignReview.created_at.desc()).all()
    
    # ดึงการจองทั้งหมด
    bookings = Booking.query.filter_by(
        customer_id=customer_id
    ).order_by(Booking.created_at.desc()).all()
    
    return render_template('customer/points_profile.html',
                         customer_points=customer_points,
                         transactions=transactions,
                         reviews=reviews,
                         bookings=bookings)

@bp.route('/api/check-points')
def check_points():
    """API: ตรวจสอบแต้มคงเหลือ"""
    from models.review import CustomerPoints
    
    customer_id = request.args.get('customer_id', type=int)
    if not customer_id:
        return jsonify({'error': 'Missing customer_id'}), 400
    
    customer_points = CustomerPoints.query.filter_by(customer_id=customer_id).first()
    
    if not customer_points:
        return jsonify({
            'customer_id': customer_id,
            'total_points': 0,
            'used_points': 0,
            'available_points': 0
        })
    
    return jsonify({
        'customer_id': customer_id,
        'total_points': customer_points.total_points,
        'used_points': customer_points.used_points,
        'available_points': customer_points.available_points
    })

@bp.route('/api/check-points-by-email')
def check_points_by_email():
    """API: ตรวจสอบแต้มคงเหลือจาก email"""
    from models.review import CustomerPoints
    from models.customer import Customer
    
    email = request.args.get('email')
    if not email:
        return jsonify({'error': 'Missing email'}), 400
    
    # หา customer จาก email
    customer = Customer.query.filter_by(email=email).first()
    if not customer:
        return jsonify({
            'email': email,
            'total_points': 0,
            'used_points': 0,
            'available_points': 0
        })
    
    customer_points = CustomerPoints.query.filter_by(customer_id=customer.id).first()
    
    if not customer_points:
        return jsonify({
            'email': email,
            'customer_id': customer.id,
            'total_points': 0,
            'used_points': 0,
            'available_points': 0
        })
    
    return jsonify({
        'email': email,
        'customer_id': customer.id,
        'total_points': customer_points.total_points,
        'used_points': customer_points.used_points,
        'available_points': customer_points.available_points
    })

@bp.route('/api/redeem-points', methods=['POST'])
def redeem_points_api():
    """API: แลกแต้มเป็นส่วนลด"""
    from models.review import CustomerPoints, PointTransaction
    from services.points_service import PointsService
    
    try:
        data = request.get_json()
        customer_id = data.get('customer_id')
        points = data.get('points', 0)
        booking_id = data.get('booking_id')
        
        if not customer_id or points <= 0:
            return jsonify({'success': False, 'error': 'Invalid parameters'}), 400
        
        # ใช้ PointsService
        points_service = PointsService()
        
        # ตรวจสอบว่าแลกได้หรือไม่
        can_redeem, message = points_service.can_redeem(customer_id, points)
        if not can_redeem:
            return jsonify({'success': False, 'error': message}), 400
        
        # คำนวณส่วนลด
        discount_amount = points_service.calculate_discount(points)
        
        # แลกแต้ม
        success, result = points_service.redeem_points(customer_id, points, booking_id)
        
        if success:
            return jsonify({
                'success': True,
                'points_used': points,
                'discount_amount': discount_amount,
                'remaining_points': result
            })
        else:
            return jsonify({'success': False, 'error': result}), 400
            
    except Exception as e:
        logger.error(f"Error redeeming points: {e}")
        return jsonify({'success': False, 'error': 'เกิดข้อผิดพลาด'}), 500
