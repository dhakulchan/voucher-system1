"""
Group Buy Public Routes
หน้าสำหรับลูกค้าทั่วไป - สร้างกลุ่ม/เข้าร่วมกลุ่ม
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session, current_app
from models.group_buy import GroupBuyCampaign, GroupBuyGroup, GroupBuyParticipant
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
    
    return render_template('group_buy/public/campaign_detail_improved.html',
                         campaign=campaign,
                         active_groups=active_groups)

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
    """หน้ายืนยันข้อมูลก่อนชำระเงิน"""
    from models.group_buy import GroupBuyCampaign
    from services.group_buy_service import GroupBuyService
    
    campaign = GroupBuyCampaign.query.get_or_404(campaign_id)
    
    # ตรวจสอบว่ามีข้อมูลใน session หรือไม่
    booking_data = session.get('pending_booking')
    if not booking_data or booking_data.get('campaign_id') != campaign_id:
        flash('ไม่พบข้อมูลการจอง กรุณากรอกข้อมูลใหม่อีกครั้ง', 'warning')
        return redirect(url_for('public_group_buy.view_campaign', campaign_id=campaign_id))
    
    if request.method == 'POST':
        try:
            service = GroupBuyService()
            
            # สร้างกลุ่มใหม่ หรือ เข้าร่วมกลุ่มที่มีอยู่
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
                    session['group_created'] = group.id
                    session['participant_id'] = leader_participant.id
                    session['pending_payment_campaign'] = campaign_id
                    session.pop('pending_booking', None)
                    flash('ยืนยันการจองสำเร็จ! กรุณาชำระเงินเพื่อยืนยันการเข้าร่วม', 'success')
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
                    
                    if group and group.share_token == session.get('join_token'):
                        # เข้าร่วมผ่าน token (share link)
                        result, error = service.join_group(
                            group_code_or_token=session.get('join_token'),
                            participant_info=participant_info,
                            is_token=True
                        )
                    else:
                        # เข้าร่วมผ่าน UI ปกติ (จากหน้า campaign)
                        result, error = service.join_existing_group(
                            group_id=booking_data['group_id'],
                            participant_info=participant_info
                        )
                else:
                    flash('ข้อมูลการจองไม่ถูกต้อง', 'danger')
                    return redirect(url_for('public_group_buy.view_campaign', campaign_id=campaign_id))
                
                if result:
                    participant = result
                    session['participant_id'] = participant.id
                    session['pending_payment_campaign'] = campaign_id
                    session.pop('pending_booking', None)
                    session.pop('join_token', None)
                    flash('ยืนยันการจองสำเร็จ! กรุณาชำระเงินเพื่อยืนยันการเข้าร่วม', 'success')
                    return redirect(url_for('group_buy_payment.select_method', 
                                          campaign_id=campaign_id))
                else:
                    flash(f'ไม่สามารถเข้าร่วมกลุ่มได้: {error}', 'danger')
                    return redirect(url_for('public_group_buy.view_campaign', campaign_id=campaign_id))
                    
        except Exception as e:
            logger.error(f"Error in confirm_booking: {e}")
            flash('เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง', 'danger')
            return redirect(url_for('public_group_buy.view_campaign', campaign_id=campaign_id))
    
    # GET request - แสดงหน้ายืนยัน
    return render_template('group_buy/public/confirm_booking.html', 
                         campaign=campaign,
                         booking_data=booking_data)
    
    from flask import current_app
    return render_template('group_buy/public/create_group.html', 
                         campaign=campaign,
                         turnstile_site_key=current_app.config.get('TURNSTILE_SITE_KEY'))

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
