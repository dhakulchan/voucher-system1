"""
Group Buy Admin Routes
จัดการแคมเปญ Group Buy โดย Admin
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from functools import wraps
from models.group_buy import GroupBuyCampaign, GroupBuyGroup, GroupBuyParticipant
from models.group_buy_payment import GroupBuyPayment, GroupBuyBankAccount
from services.group_buy_service import GroupBuyService
from extensions import db
from utils.datetime_utils import naive_utc_now
from utils.timezone_helper import now_thailand, get_thailand_timestamp
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import logging
import os
import json

bp = Blueprint('group_buy_admin', __name__, url_prefix='/backoffice/group-buy')
logger = logging.getLogger(__name__)
service = GroupBuyService()

# Error handler for request too large
@bp.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    """จัดการ error เมื่อข้อมูลที่ส่งมาใหญ่เกินไป"""
    flash('ข้อมูลที่ส่งมามีขนาดใหญ่เกินไป กรุณาลดขนาดรูปภาพหรือเนื้อหา', 'danger')
    return redirect(request.referrer or url_for('group_buy_admin.list_campaigns')), 413

# Permission-based Decorators
def group_buy_permission_required(action):
    """Decorator: ตรวจสอบ permission สำหรับ Group Buy"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('กรุณาเข้าสระบบ', 'warning')
                return redirect(url_for('auth.login'))
            
            # Check permission
            if not current_user.has_permission('group_buy', action):
                flash('คุณไม่มีสิทธิ์เข้าถึงหน้านี้', 'danger')
                return redirect(url_for('dashboard.index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Legacy decorators for backward compatibility
def admin_required(f):
    """Decorator: ต้องเป็น Admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('กรุณาเข้าสู่ระบบ', 'warning')
            return redirect(url_for('auth.login'))
        
        # Check admin permission or Administrator role
        if not (current_user.role == 'Administrator' or current_user.has_permission('group_buy', 'delete_campaign')):
            flash('คุณไม่มีสิทธิ์เข้าถึงหน้านี้', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function

def manager_required(f):
    """Decorator: ต้องเป็น Manager หรือ Admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('กรุณาเข้าสู่ระบบ', 'warning')
            return redirect(url_for('auth.login'))
        
        # Check view permission
        if not current_user.has_permission('group_buy', 'view'):
            flash('คุณไม่มีสิทธิ์เข้าถึงหน้านี้', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/')
@login_required
@manager_required
def index():
    """หน้าหลัก Group Buy Admin"""
    campaigns = GroupBuyCampaign.query.order_by(
        GroupBuyCampaign.created_at.desc()
    ).all()
    
    # สถิติ
    active_campaigns = sum(1 for c in campaigns if c.is_active_now)
    total_groups = GroupBuyGroup.query.count()
    successful_groups = GroupBuyGroup.query.filter_by(status='success').count()
    active_groups = GroupBuyGroup.query.filter_by(status='active').count()
    
    return render_template('group_buy/admin/index.html',
                         campaigns=campaigns,
                         stats={
                             'active_campaigns': active_campaigns,
                             'total_groups': total_groups,
                             'successful_groups': successful_groups,
                             'active_groups': active_groups
                         })

@bp.route('/campaigns')
@login_required
@manager_required
def campaigns():
    """รายการแคมเปญทั้งหมด"""
    campaigns = GroupBuyCampaign.query.order_by(
        GroupBuyCampaign.featured.desc(),
        GroupBuyCampaign.created_at.desc()
    ).all()
    
    return render_template('group_buy/admin/campaigns.html', campaigns=campaigns)

@bp.route('/campaigns/create', methods=['GET', 'POST'])
@login_required
@group_buy_permission_required('create_campaign')
def create_campaign():
    """สร้างแคมเปญใหม่"""
    if request.method == 'POST':
        try:
            data = request.form.to_dict()
            print("=" * 60)
            print(f"CREATE CAMPAIGN - Raw form data: {data}")
            logger.info(f"Creating campaign with data: {data}")
            
            # Handle product image upload
            if 'product_image' in request.files:
                file = request.files['product_image']
                if file and file.filename:
                    # Generate unique filename
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'jpg'
                    new_filename = f"group_buy_{timestamp}.{ext}"
                    
                    # Save to static/uploads/group_buy/
                    upload_folder = os.path.join('static', 'uploads', 'group_buy')
                    os.makedirs(upload_folder, exist_ok=True)
                    filepath = os.path.join(upload_folder, new_filename)
                    
                    file.save(filepath)
                    data['product_image'] = filepath
                    print(f"Product image saved: {filepath}")
                    logger.info(f"Product image uploaded: {filepath}")
            
            # Handle image title
            if 'image_title' in data:
                data['image_title'] = data['image_title'].strip() if data['image_title'] else None
                print(f"Image title: {data['image_title']}")
            
            # Handle image title position
            if 'image_title_position' in data:
                position = data['image_title_position'].strip() if data['image_title_position'] else 'left'
                if position in ['left', 'center', 'right']:
                    data['image_title_position'] = position
                else:
                    data['image_title_position'] = 'left'
                print(f"Image title position: {data['image_title_position']}")
            else:
                data['image_title_position'] = 'left'
            
            # Handle album images upload (multiple files)
            album_items = []
            if 'album_images' in request.files:
                files = request.files.getlist('album_images')
                titles = request.form.getlist('album_titles')  # Get titles for each image
                
                for idx, file in enumerate(files):
                    if file and file.filename:
                        filename = secure_filename(file.filename)
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'jpg'
                        new_filename = f"album_{timestamp}.{ext}"
                        
                        upload_folder = os.path.join('static', 'uploads', 'group_buy')
                        os.makedirs(upload_folder, exist_ok=True)
                        filepath = os.path.join(upload_folder, new_filename)
                        
                        file.save(filepath)
                        
                        # Create object with path and title
                        title = titles[idx].strip() if idx < len(titles) and titles[idx] else ''
                        album_items.append({
                            'path': filepath,
                            'title': title
                        })
                        print(f"Album image saved: {filepath}, title: {title}")
                
                if album_items:
                    data['album_images'] = json.dumps(album_items)
                    print(f"Album images saved: {len(album_items)} files")
                    logger.info(f"Album images uploaded: {album_items}")
            
            # แปลง date strings เป็น datetime (รองรับ DD/MM/YYYY format)
            try:
                # แปลงจาก DD/MM/YYYY เป็น datetime
                campaign_start = data['campaign_start_date'].strip()
                campaign_end = data['campaign_end_date'].strip()
                
                data['campaign_start_date'] = datetime.strptime(campaign_start, '%d/%m/%Y')
                data['campaign_end_date'] = datetime.strptime(campaign_end, '%d/%m/%Y')
                print(f"Campaign dates converted (DD/MM/YYYY): {campaign_start} -> {data['campaign_start_date']}")
            except ValueError:
                # Fallback to YYYY-MM-DD format
                data['campaign_start_date'] = datetime.strptime(data['campaign_start_date'], '%Y-%m-%d')
                data['campaign_end_date'] = datetime.strptime(data['campaign_end_date'], '%Y-%m-%d')
                print(f"Campaign dates converted (YYYY-MM-DD)")
            
            print(f"Dates converted successfully")
            
            # แปลง travel dates ถ้ามี (รองรับ DD/MM/YYYY)
            if 'travel_date_from' in data and data['travel_date_from'].strip():
                try:
                    data['travel_date_from'] = datetime.strptime(data['travel_date_from'], '%d/%m/%Y').date()
                except ValueError:
                    data['travel_date_from'] = datetime.strptime(data['travel_date_from'], '%Y-%m-%d').date()
                print(f"Travel date from: {data['travel_date_from']}")
            else:
                data['travel_date_from'] = None
                
            if 'travel_date_to' in data and data['travel_date_to'].strip():
                try:
                    data['travel_date_to'] = datetime.strptime(data['travel_date_to'], '%d/%m/%Y').date()
                except ValueError:
                    data['travel_date_to'] = datetime.strptime(data['travel_date_to'], '%Y-%m-%d').date()
                print(f"Travel date to: {data['travel_date_to']}")
            else:
                data['travel_date_to'] = None
            
            # แปลง numeric fields
            numeric_fields = [
                'regular_price', 'group_price', 'min_participants', 
                'max_participants', 'duration_hours', 
                'total_slots', 'max_pax'  # เพิ่ม max_pax
            ]
            for field in numeric_fields:
                if field in data and data[field].strip():  # ตรวจสอบว่าไม่ใช่ค่าว่าง
                    value = data[field]
                    data[field] = float(value) if '.' in value else int(value)
                    print(f"Converted {field} = {data[field]}")
                    logger.info(f"Converted {field} = {data[field]}")
                elif field in data:
                    # ถ้าเป็นค่าว่าง ให้ลบออกหรือใส่ค่า default
                    if field in ['max_participants', 'total_slots', 'max_pax']:
                        data[field] = 0
                        print(f"Set {field} = 0 (empty/optional)")
                        logger.info(f"Set {field} = 0 (empty/optional)")
            
            # แปลง boolean fields
            boolean_fields = ['is_active', 'is_public', 'featured', 'allow_partial_payment']
            for field in boolean_fields:
                data[field] = field in request.form
            print(f"Boolean fields converted")
            
            # Handle partial payment configuration
            if data.get('allow_partial_payment'):
                data['partial_payment_type'] = request.form.get('partial_payment_type', 'percentage')
                partial_value = request.form.get('partial_payment_value', '30.00')
                try:
                    data['partial_payment_value'] = float(partial_value)
                except (ValueError, TypeError):
                    data['partial_payment_value'] = 30.00
                print(f"Partial payment: {data['partial_payment_type']} = {data['partial_payment_value']}")
            
            # Rename fields to match model
            if 'terms_and_conditions' in data:
                data['terms_conditions'] = data.pop('terms_and_conditions')
                print(f"Renamed terms_and_conditions to terms_conditions")
            
            # Remove fields that don't exist in model
            fields_to_remove = ['album_titles']  # Not in model - album_titles is only for form input
            for field in fields_to_remove:
                removed = data.pop(field, None)
                if removed:
                    print(f"Removed {field} (not in model)")
            
            print(f"Final data keys: {list(data.keys())}")
            print(f"Calling service.create_campaign...")
            logger.info(f"Final data before service call: {data}")
            
            campaign = service.create_campaign(data)
            
            print(f"Service returned: {campaign}")
            if campaign:
                print(f"Campaign created successfully: ID={campaign.id}")
                logger.info(f"Campaign created successfully: {campaign.id}")
                flash(f'สร้างแคมเปญ "{campaign.name}" สำเร็จ', 'success')
                return redirect(url_for('group_buy_admin.view_campaign', campaign_id=campaign.id))
            else:
                print(f"ERROR: service.create_campaign returned None")
                logger.error("service.create_campaign returned None")
                flash('เกิดข้อผิดพลาดในการสร้างแคมเปญ (service returned None)', 'danger')
                
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"EXCEPTION in create_campaign:")
            print(error_trace)
            logger.error(f"Error creating campaign: {e}")
            logger.error(error_trace)
            flash(f'เกิดข้อผิดพลาด: {str(e)}', 'danger')
        
        print("=" * 60)
    
    # Default values
    default_start = naive_utc_now().date()
    default_end = (naive_utc_now() + timedelta(days=30)).date()
    
    return render_template('group_buy/admin/create_campaign.html',
                         default_start=default_start,
                         default_end=default_end)

@bp.route('/campaigns/<int:campaign_id>')
@login_required
@manager_required
def view_campaign(campaign_id):
    """ดูรายละเอียดแคมเปญ"""
    campaign = GroupBuyCampaign.query.get_or_404(campaign_id)
    
    # ดึงกลุ่มทั้งหมดของแคมเปญนี้
    groups = GroupBuyGroup.query.filter_by(campaign_id=campaign_id).order_by(
        GroupBuyGroup.created_at.desc()
    ).all()
    
    # สถิติของแคมเปญ
    total_groups = len(groups)
    successful_groups = sum(1 for g in groups if g.status == 'success')
    active_groups = sum(1 for g in groups if g.status == 'active')
    failed_groups = sum(1 for g in groups if g.status == 'failed')
    
    # นับจำนวนผู้เข้าร่วมจริงจาก GroupBuyParticipant ที่ชำระเงินแล้ว
    from models.group_buy import GroupBuyParticipant
    total_participants = db.session.query(db.func.sum(GroupBuyParticipant.pax_count)).join(
        GroupBuyGroup, GroupBuyParticipant.group_id == GroupBuyGroup.id
    ).filter(
        GroupBuyGroup.campaign_id == campaign_id,
        GroupBuyParticipant.payment_status.in_(['paid', 'authorized'])
    ).scalar() or 0
    
    total_revenue = sum(
        float(g.campaign.group_price) * g.current_participants 
        for g in groups if g.status == 'success'
    )
    
    stats = {
        'total_groups': total_groups,
        'successful_groups': successful_groups,
        'active_groups': active_groups,
        'failed_groups': failed_groups,
        'total_participants': int(total_participants),
        'total_revenue': total_revenue,
        'success_rate': (successful_groups / total_groups * 100) if total_groups > 0 else 0
    }
    
    return render_template('group_buy/admin/view_campaign.html',
                         campaign=campaign,
                         groups=groups,
                         stats=stats)

@bp.route('/campaigns/<int:campaign_id>/edit', methods=['GET', 'POST'])
@login_required
@group_buy_permission_required('edit_campaign')
def edit_campaign(campaign_id):
    """แก้ไขแคมเปญ"""
    campaign = GroupBuyCampaign.query.get_or_404(campaign_id)
    
    if request.method == 'POST':
        try:
            # Log request size for debugging
            content_length = request.content_length
            print("=" * 60)
            print(f"EDIT CAMPAIGN #{campaign_id}")
            print(f"Content-Length: {content_length} bytes ({content_length / 1024 / 1024:.2f} MB)")
            print(f"Form keys: {list(request.form.keys())}")
            
            # Update fields
            campaign.name = request.form.get('name')
            campaign.description = request.form.get('description')
            campaign.product_type = request.form.get('product_type')
            
            # Prices
            regular_price_str = request.form.get('regular_price', '').strip()
            group_price_str = request.form.get('group_price', '').strip()
            
            if not regular_price_str or not group_price_str:
                raise ValueError('กรุณากรอกราคาปกติและราคากลุ่ม')
            
            campaign.regular_price = float(regular_price_str)
            campaign.group_price = float(group_price_str)
            
            # Price description (NEW)
            campaign.price_description = request.form.get('price_description', '').strip() or None
            
            # Recalculate discount
            discount_pct = ((campaign.regular_price - campaign.group_price) / campaign.regular_price) * 100
            campaign.discount_percentage = discount_pct
            
            # Participants
            min_participants_str = request.form.get('min_participants', '').strip()
            max_participants_str = request.form.get('max_participants', '0').strip()
            
            if not min_participants_str:
                raise ValueError('กรุณากรอกจำนวนสมาชิกขั้นต่ำ')
            
            campaign.min_participants = int(min_participants_str)
            campaign.max_participants = int(max_participants_str) if max_participants_str else 0
            
            # Timing
            duration_hours_str = request.form.get('duration_hours', '').strip()
            if not duration_hours_str:
                raise ValueError('กรุณากรอกระยะเวลารอรวมกลุ่ม')
            
            campaign.duration_hours = int(duration_hours_str)
            
            # Campaign dates - รองรับ DD/MM/YYYY format
            campaign_start_str = request.form.get('campaign_start_date', '').strip()
            campaign_end_str = request.form.get('campaign_end_date', '').strip()
            
            try:
                campaign.campaign_start_date = datetime.strptime(campaign_start_str, '%d/%m/%Y')
                campaign.campaign_end_date = datetime.strptime(campaign_end_str, '%d/%m/%Y')
            except ValueError:
                # Fallback to YYYY-MM-DD
                campaign.campaign_start_date = datetime.strptime(campaign_start_str, '%Y-%m-%d')
                campaign.campaign_end_date = datetime.strptime(campaign_end_str, '%Y-%m-%d')
            
            # Inventory
            total_slots_str = request.form.get('total_slots', '0').strip()
            campaign.total_slots = int(total_slots_str) if total_slots_str else 0
            
            # Max Pax (NEW)
            max_pax_str = request.form.get('max_pax', '0').strip()
            campaign.max_pax = int(max_pax_str) if max_pax_str else 0
            
            # Travel dates (NEW) - รองรับ DD/MM/YYYY
            travel_from_str = request.form.get('travel_date_from', '').strip()
            travel_to_str = request.form.get('travel_date_to', '').strip()
            
            if travel_from_str:
                try:
                    campaign.travel_date_from = datetime.strptime(travel_from_str, '%d/%m/%Y').date()
                except ValueError:
                    campaign.travel_date_from = datetime.strptime(travel_from_str, '%Y-%m-%d').date()
            else:
                campaign.travel_date_from = None
                
            if travel_to_str:
                try:
                    campaign.travel_date_to = datetime.strptime(travel_to_str, '%d/%m/%Y').date()
                except ValueError:
                    campaign.travel_date_to = datetime.strptime(travel_to_str, '%Y-%m-%d').date()
            else:
                campaign.travel_date_to = None
            
            # Handle product image upload (NEW)
            if 'product_image' in request.files:
                file = request.files['product_image']
                if file and file.filename:
                    # Generate unique filename
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'jpg'
                    new_filename = f"group_buy_{timestamp}.{ext}"
                    
                    # Save to static/uploads/group_buy/
                    upload_folder = os.path.join('static', 'uploads', 'group_buy')
                    os.makedirs(upload_folder, exist_ok=True)
                    filepath = os.path.join(upload_folder, new_filename)
                    
                    file.save(filepath)
                    campaign.product_image = filepath
                    print(f"Product image updated: {filepath}")
            
            # Handle image title (NEW)
            campaign.image_title = request.form.get('image_title', '').strip() or None
            print(f"Image title: {campaign.image_title}")
            
            # Handle image title position (NEW)
            position = request.form.get('image_title_position', 'left').strip()
            if position in ['left', 'center', 'right']:
                campaign.image_title_position = position
            else:
                campaign.image_title_position = 'left'
            print(f"Image title position: {campaign.image_title_position}")
            
            # Handle payment settings (NEW)
            campaign.payment_stripe_enabled = request.form.get('payment_stripe_enabled') == 'on'
            campaign.payment_stripe_fee_type = request.form.get('payment_stripe_fee_type', 'percentage')
            campaign.payment_stripe_fee_value = float(request.form.get('payment_stripe_fee_value', 0) or 0)
            campaign.payment_stripe_fee_label = request.form.get('payment_stripe_fee_label', '').strip() or None
            campaign.payment_bank_enabled = request.form.get('payment_bank_enabled') == 'on'
            campaign.payment_qr_enabled = request.form.get('payment_qr_enabled') == 'on'
            
            # Handle QR image upload
            if 'payment_qr_image' in request.files:
                file = request.files['payment_qr_image']
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'png'
                    new_filename = f"qr_{timestamp}.{ext}"
                    
                    upload_folder = os.path.join('static', 'uploads', 'qr_codes')
                    os.makedirs(upload_folder, exist_ok=True)
                    filepath = os.path.join(upload_folder, new_filename)
                    
                    file.save(filepath)
                    campaign.payment_qr_image = filepath
            
            # Handle album images upload (NEW)
            if 'album_images' in request.files:
                files = request.files.getlist('album_images')
                titles = request.form.getlist('album_titles')  # Get titles for each new image
                album_items = []
                
                for idx, file in enumerate(files):
                    if file and file.filename:
                        filename = secure_filename(file.filename)
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'jpg'
                        new_filename = f"album_{timestamp}.{ext}"
                        
                        upload_folder = os.path.join('static', 'uploads', 'group_buy')
                        os.makedirs(upload_folder, exist_ok=True)
                        filepath = os.path.join(upload_folder, new_filename)
                        
                        file.save(filepath)
                        
                        # Create object with path and title
                        title = titles[idx].strip() if idx < len(titles) and titles[idx] else ''
                        album_items.append({
                            'path': filepath,
                            'title': title
                        })
                        print(f"Album image uploaded: {filepath}, title: {title}")
                
                if album_items:
                    # Merge with existing album images if any
                    existing_album = campaign.album_images
                    existing_items = []
                    if existing_album:
                        try:
                            existing_items = json.loads(existing_album)
                            # Ensure existing items are in correct format
                            if existing_items and isinstance(existing_items[0], str):
                                # Convert old format (array of strings) to new format
                                existing_items = [{'path': path, 'title': ''} for path in existing_items]
                        except:
                            pass
                    
                    all_items = existing_items + album_items
                    campaign.album_images = json.dumps(all_items)
                    print(f"Album images updated: {len(all_items)} total files")
            
            # Handle album order (NEW - for reordering)
            album_order = request.form.get('album_order', '').strip()
            if album_order:
                try:
                    ordered_paths = json.loads(album_order)
                    existing_album = campaign.album_images
                    if existing_album:
                        existing_items = json.loads(existing_album)
                        # Ensure format
                        if existing_items and isinstance(existing_items[0], str):
                            existing_items = [{'path': path, 'title': ''} for path in existing_items]
                        
                        # Reorder based on ordered_paths
                        path_to_item = {item['path'] if isinstance(item, dict) else item: item for item in existing_items}
                        reordered_items = []
                        for path in ordered_paths:
                            if path in path_to_item:
                                item = path_to_item[path]
                                if isinstance(item, str):
                                    reordered_items.append({'path': item, 'title': ''})
                                else:
                                    reordered_items.append(item)
                        
                        if reordered_items:
                            campaign.album_images = json.dumps(reordered_items)
                            print(f"Album reordered: {len(reordered_items)} items")
                except Exception as e:
                    print(f"Error processing album order: {e}")
            
            # Flags
            campaign.is_active = 'is_active' in request.form
            campaign.is_public = 'is_public' in request.form
            campaign.featured = 'featured' in request.form
            
            # Display order
            try:
                campaign.display_order = int(request.form.get('display_order', 0))
            except (ValueError, TypeError):
                campaign.display_order = 0
            
            # Handle partial payment configuration
            campaign.allow_partial_payment = 'allow_partial_payment' in request.form
            if campaign.allow_partial_payment:
                campaign.partial_payment_type = request.form.get('partial_payment_type', 'percentage')
                partial_value = request.form.get('partial_payment_value', '30.00')
                try:
                    campaign.partial_payment_value = float(partial_value)
                except (ValueError, TypeError):
                    campaign.partial_payment_value = 30.00
                print(f"Partial payment updated: {campaign.partial_payment_type} = {campaign.partial_payment_value}")
            else:
                campaign.partial_payment_type = None
                campaign.partial_payment_value = None
                print(f"Partial payment disabled")
            
            # Handle auto cancel configuration
            campaign.auto_cancel_enabled = 'auto_cancel_enabled' in request.form
            auto_cancel_hours = request.form.get('auto_cancel_hours', '4')
            try:
                campaign.auto_cancel_hours = int(auto_cancel_hours)
            except (ValueError, TypeError):
                campaign.auto_cancel_hours = 4
            campaign.auto_cancel_send_email = 'auto_cancel_send_email' in request.form
            
            # Other fields (ใช้ชื่อ field ที่ตรงกับ model)
            campaign.terms_conditions = request.form.get('terms_and_conditions', '')
            campaign.admin_notes = request.form.get('admin_notes', '')
            campaign.product_details = request.form.get('product_details', '')
            
            print(f"Updating text fields:")
            print(f"  terms_conditions: {len(campaign.terms_conditions)} chars")
            print(f"  admin_notes: {len(campaign.admin_notes)} chars")
            print(f"  product_details: {len(campaign.product_details)} chars")
            
            db.session.commit()
            print(f"✅ Campaign #{campaign_id} updated successfully")
            print("=" * 60)
            flash(f'อัพเดทแคมเปญ "{campaign.name}" สำเร็จ', 'success')
            return redirect(url_for('group_buy_admin.view_campaign', campaign_id=campaign.id))
            
        except Exception as e:
            logger.error(f"Error updating campaign: {e}")
            db.session.rollback()
            flash(f'เกิดข้อผิดพลาด: {str(e)}', 'danger')
    
    return render_template('group_buy/admin/edit_campaign.html', campaign=campaign)

@bp.route('/campaigns/<int:campaign_id>/clone', methods=['GET'])
@login_required
@group_buy_permission_required('create_campaign')
def clone_campaign(campaign_id):
    """คัดลอกแคมเปญ"""
    try:
        # Get original campaign
        original = GroupBuyCampaign.query.get_or_404(campaign_id)
        
        # Create new campaign with copied data
        new_campaign = GroupBuyCampaign(
            name=f"{original.name} (Copy)",
            product_type=original.product_type,
            product_details=original.product_details,
            description=original.description,
            terms_conditions=original.terms_conditions,
            admin_notes=original.admin_notes,
            
            # Pricing
            regular_price=original.regular_price,
            group_price=original.group_price,
            
            # Requirements
            min_participants=original.min_participants,
            max_participants=original.max_participants,
            duration_hours=original.duration_hours,
            
            # Dates - set new dates (1 month from now)
            campaign_start_date=datetime.now() + timedelta(days=30),
            campaign_end_date=datetime.now() + timedelta(days=60),
            travel_date_from=original.travel_date_from + timedelta(days=30) if original.travel_date_from else None,
            travel_date_to=original.travel_date_to + timedelta(days=30) if original.travel_date_to else None,
            
            # Pax
            max_pax=original.max_pax,
            
            # Inventory
            total_slots=original.total_slots,
            available_slots=original.total_slots,  # Reset to full
            
            # Status - set as draft
            status='draft',
            is_active=False,
            is_public=False,
            featured=False,
            
            # Images
            product_image=original.product_image,
            image_title=original.image_title,
            image_title_position=getattr(original, 'image_title_position', None),
            
            # Special codes
            special_booker_codes=original.special_booker_codes,
            
            # Partial payment
            allow_partial_payment=getattr(original, 'allow_partial_payment', False),
            partial_payment_type=getattr(original, 'partial_payment_type', None),
            partial_payment_value=getattr(original, 'partial_payment_value', None),
            
            # Auto cancel
            auto_cancel_enabled=getattr(original, 'auto_cancel_enabled', False),
            auto_cancel_hours=getattr(original, 'auto_cancel_hours', 4),
            
            # Timestamps
            created_at=naive_utc_now(),
            updated_at=naive_utc_now()
        )
        
        db.session.add(new_campaign)
        db.session.commit()
        
        flash(f'คัดลอกแคมเปญสำเร็จ! กรุณาตรวจสอบและแก้ไขข้อมูลก่อนเปิดใช้งาน', 'success')
        return redirect(url_for('group_buy_admin.edit_campaign', campaign_id=new_campaign.id))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error cloning campaign: {e}")
        flash(f'เกิดข้อผิดพลาดในการคัดลอกแคมเปญ: {str(e)}', 'danger')
        return redirect(url_for('group_buy_admin.campaigns'))

@bp.route('/campaigns/<int:campaign_id>/toggle-status', methods=['POST'])
@login_required
@group_buy_permission_required('edit_campaign')
def toggle_campaign_status(campaign_id):
    """เปิด/ปิดแคมเปญ"""
    campaign = GroupBuyCampaign.query.get_or_404(campaign_id)
    campaign.is_active = not campaign.is_active
    
    # Update status field to match is_active
    if campaign.is_active:
        campaign.status = 'active'
    else:
        campaign.status = 'inactive'
    
    db.session.commit()
    
    status = "เปิดใช้งาน" if campaign.is_active else "ปิดใช้งาน"
    flash(f'{status}แคมเปญ "{campaign.name}" แล้ว', 'success')
    
    return redirect(url_for('group_buy_admin.view_campaign', campaign_id=campaign_id))

@bp.route('/groups')
@login_required
@group_buy_permission_required('view_groups')
def groups():
    """รายการกลุ่มทั้งหมด"""
    status_filter = request.args.get('status', 'all')
    campaign_id = request.args.get('campaign_id', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)  # แสดง 50 รายการต่อหน้า
    
    query = GroupBuyGroup.query
    
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    if campaign_id:
        query = query.filter_by(campaign_id=campaign_id)
    
    # ใช้ paginate แทน all() เพื่อแบ่งหน้า
    pagination = query.order_by(GroupBuyGroup.created_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    campaigns = GroupBuyCampaign.query.all()
    
    return render_template('group_buy/admin/groups.html',
                         groups=pagination.items,
                         pagination=pagination,
                         campaigns=campaigns,
                         status_filter=status_filter)

@bp.route('/groups/<int:group_id>')
@login_required
@manager_required
def view_group(group_id):
    """ดูรายละเอียดกลุ่ม"""
    from sqlalchemy.orm import joinedload
    
    group = GroupBuyGroup.query.get_or_404(group_id)
    participants = GroupBuyParticipant.query.filter_by(
        group_id=group_id
    ).options(
        joinedload(GroupBuyParticipant.payment)
    ).order_by(GroupBuyParticipant.join_order).all()
    
    return render_template('group_buy/admin/view_group.html',
                         group=group,
                         participants=participants)

@bp.route('/groups/<int:group_id>/manual-success', methods=['POST'])
@login_required
@group_buy_permission_required('force_success')
def manual_group_success(group_id):
    """Admin บังคับให้กลุ่มสำเร็จ (แม้ไม่ครบคน)"""
    group = GroupBuyGroup.query.get_or_404(group_id)
    
    if group.status != 'active':
        flash('กลุ่มนี้ไม่อยู่ในสถานะ active', 'warning')
        return redirect(url_for('group_buy_admin.view_group', group_id=group_id))
    
    try:
        service._handle_group_success(group)
        db.session.commit()
        flash('กลุ่มถูกกำหนดเป็น "สำเร็จ" แล้ว', 'success')
    except Exception as e:
        logger.error(f"Error in manual group success: {e}")
        db.session.rollback()
        flash(f'เกิดข้อผิดพลาด: {str(e)}', 'danger')
    
    return redirect(url_for('group_buy_admin.view_group', group_id=group_id))

@bp.route('/groups/<int:group_id>/cancel', methods=['POST'])
@login_required
@group_buy_permission_required('cancel_group')
def cancel_group(group_id):
    """Admin ยกเลิกกลุ่ม"""
    group = GroupBuyGroup.query.get_or_404(group_id)
    
    if group.status not in ['active', 'pending']:
        flash('ไม่สามารถยกเลิกกลุ่มในสถานะนี้ได้', 'warning')
        return redirect(url_for('group_buy_admin.view_group', group_id=group_id))
    
    try:
        service._handle_group_failed(group)
        db.session.commit()
        flash('ยกเลิกกลุ่มแล้ว', 'success')
    except Exception as e:
        logger.error(f"Error cancelling group: {e}")
        db.session.rollback()
        flash(f'เกิดข้อผิดพลาด: {str(e)}', 'danger')
    
    return redirect(url_for('group_buy_admin.view_group', group_id=group_id))

@bp.route('/participants/<int:participant_id>/send-payment-link', methods=['POST'])
@login_required
@manager_required
def send_payment_link(participant_id):
    """ส่งลิงก์ชำระเงินให้ลูกค้า"""
    from flask_mail import Message
    from extensions import mail
    
    participant = GroupBuyParticipant.query.get_or_404(participant_id)
    
    if participant.payment_status != 'pending':
        flash('สามารถส่งลิงก์ได้เฉพาะรายการที่รอดำเนินการเท่านั้น', 'warning')
        return redirect(url_for('group_buy_admin.view_group', group_id=participant.group_id))
    
    # หา payment จาก participant
    if participant.payment_id:
        payment = GroupBuyPayment.query.get(participant.payment_id)
    else:
        payment = None
    
    # ถ้าไม่มี payment record ให้ใช้ข้อมูลจาก participant
    if not payment:
        payment = participant  # ใช้ participant เป็น payment object เพราะมี field เหมือนกัน
    
    try:
        campaign = participant.group.campaign
        payment_url = url_for('group_buy_payment.select_method', 
                            campaign_id=campaign.id, 
                            _external=True)
        
        # สร้างอีเมล
        subject = f'เชิญชวนชำระเงิน Group Buy - {campaign.name}'
        
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Sarabun', Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; }}
                .section {{ background: white; padding: 20px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .section h3 {{ color: #0ea5e9; margin-top: 0; border-bottom: 2px solid #0ea5e9; padding-bottom: 10px; }}
                .info-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee; }}
                .info-label {{ font-weight: bold; color: #555; }}
                .info-value {{ color: #333; }}
                .amount {{ font-size: 1.5em; color: #0891b2; font-weight: bold; text-align: center; padding: 15px; background: #ecfeff; border-radius: 8px; }}
                .btn {{ display: inline-block; padding: 15px 40px; background: linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%); color: white; text-decoration: none; border-radius: 8px; margin: 20px 0; font-size: 1.1em; font-weight: bold; box-shadow: 0 4px 6px rgba(14,165,233,0.3); }}
                .btn:hover {{ box-shadow: 0 6px 8px rgba(14,165,233,0.4); }}
                .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #777; font-size: 0.9em; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>💳 เชิญชวนชำระเงิน Group Buy</h1>
                    <p>กรุณาดำเนินการชำระเงินเพื่อยืนยันการเข้าร่วม</p>
                </div>
                
                <div class="content">
                    <div class="section">
                        <h3>👋 สวัสดีคุณ {payment.participant_name}</h3>
                        <p>คุณได้ทำการเข้าร่วมกลุ่ม Group Buy แล้ว กรุณาดำเนินการชำระเงินเพื่อยืนยันการเข้าร่วมของคุณ</p>
                    </div>
                    
                    <div class="section">
                        <h3>📋 รายละเอียดการจอง</h3>
                        <div class="info-row">
                            <span class="info-label">แคมเปญ:</span>
                            <span class="info-value">{campaign.name}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">รหัสกลุ่ม:</span>
                            <span class="info-value">{payment.group.group_code}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">ชื่อกลุ่ม:</span>
                            <span class="info-value">{payment.group.group_name}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">จำนวนผู้เดินทาง:</span>
                            <span class="info-value">{payment.pax_count} คน</span>
                        </div>
                        {f'<div class="info-row"><span class="info-label">วันเดินทาง:</span><span class="info-value">{campaign.travel_date_from.strftime("%d/%m/%Y")} - {campaign.travel_date_to.strftime("%d/%m/%Y")}</span></div>' if campaign.travel_date_from and campaign.travel_date_to else ''}
                        <div class="amount">
                            ยอดที่ต้องชำระ: ฿{payment.payment_amount:,.0f}
                        </div>
                    </div>
                    
                    <div class="warning">
                        <strong>⏰ หมายเหตุ:</strong> กรุณาชำระเงินภายในระยะเวลาที่กำหนด มิฉะนั้นที่นั่งของคุณอาจถูกยกเลิก
                    </div>
                    
                    <div style="text-align: center;">
                        <a href="{payment_url}" class="btn">👉 คลิกเพื่อชำระเงิน</a>
                    </div>
                    
                    <div class="section">
                        <h3>💳 วิธีการชำระเงิน</h3>
                        <p>เมื่อคลิกปุ่มด้านบน คุณจะสามารถเลือกช่องทางการชำระเงินได้ ดังนี้:</p>
                        <ul>
                            <li><strong>โอนผ่านธนาคาร</strong> - โอนเงินผ่านบัญชีธนาคาร</li>
                            <li><strong>QR Payment</strong> - สแกน QR Code เพื่อชำระเงิน</li>
                            <li><strong>บัตรเครดิต/เดบิต</strong> - ชำระผ่าน Stripe</li>
                        </ul>
                    </div>
                </div>
                
                <div class="footer">
                    <p>© 2026 Dhakul Chan Nice Holidays. All Rights Reserved.</p>
                    <p>หากมีคำถาม กรุณาติดต่อ: support@dhakulchan.com | โทร: 02-123-4567</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg = Message(
            subject=subject,
            recipients=[payment.participant_email],
            bcc=['support@dhakulchan.com'],
            html=html_body
        )
        
        mail.send(msg)
        flash(f'✅ ส่งลิงก์ชำระเงินไปที่ {participant.participant_email} เรียบร้อยแล้ว', 'success')
        logger.info(f"Payment link sent to {participant.participant_email} for participant #{participant.id}")
        
    except Exception as e:
        logger.error(f"Error sending payment link: {e}")
        flash(f'❌ เกิดข้อผิดพลาดในการส่งอีเมล: {str(e)}', 'danger')
    
    return redirect(url_for('group_buy_admin.view_group', group_id=participant.group_id))

@bp.route('/participants/<int:participant_id>/mark-paid', methods=['POST'])
@login_required
@manager_required
def mark_participant_paid(participant_id):
    """อัปเดตสถานะการชำระเงินเป็น Paid"""
    participant = GroupBuyParticipant.query.get_or_404(participant_id)
    
    try:
        from utils.datetime_utils import naive_utc_now
        from datetime import datetime
        from werkzeug.utils import secure_filename
        import os
        
        # รับข้อมูลจากฟอร์ม
        payment_method = request.form.get('payment_method', 'manual')
        payment_reference = request.form.get('payment_reference', '')
        payment_date_str = request.form.get('payment_date')
        
        # แปลงวันที่
        if payment_date_str:
            try:
                payment_date = datetime.fromisoformat(payment_date_str)
            except:
                payment_date = naive_utc_now()
        else:
            payment_date = naive_utc_now()
        
        # อัปเดตสถานะ
        participant.payment_status = 'paid'
        participant.payment_date = payment_date
        participant.payment_reference = payment_reference
        
        # สร้างหรืออัปเดต payment record
        if participant.payment_id:
            payment = GroupBuyPayment.query.get(participant.payment_id)
            if payment:
                payment.payment_method = payment_method
                payment.payment_status = 'paid'
                payment.paid_at = payment_date
        else:
            # สร้าง payment record ใหม่
            payment = GroupBuyPayment(
                booking_id=participant.booking_id or 0,
                campaign_id=participant.campaign_id,
                customer_name=participant.participant_name,
                customer_email=participant.participant_email,
                customer_phone=participant.participant_phone,
                payment_method=payment_method,
                payment_status='paid',
                amount=participant.payment_amount,
                fee_amount=0,
                total_amount=participant.payment_amount,
                paid_at=payment_date
            )
            db.session.add(payment)
            db.session.flush()
            participant.payment_id = payment.id
        
        # จัดการไฟล์ slip
        if 'slip_image' in request.files:
            file = request.files['slip_image']
            if file and file.filename:
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'png'
                new_filename = f"slip_{participant_id}_{timestamp}.{ext}"
                
                upload_folder = os.path.join('static', 'uploads', 'payment_slips')
                os.makedirs(upload_folder, exist_ok=True)
                filepath = os.path.join(upload_folder, new_filename)
                
                file.save(filepath)
                if payment:
                    payment.slip_image = filepath
        
        db.session.commit()
        flash(f'✅ บันทึกการชำระเงินของ {participant.participant_name} สำเร็จ', 'success')
        logger.info(f"Admin marked participant #{participant.id} as paid via {payment_method}")
        
    except Exception as e:
        logger.error(f"Error marking participant as paid: {e}")
        db.session.rollback()
        flash(f'❌ เกิดข้อผิดพลาด: {str(e)}', 'danger')
    
    return redirect(url_for('group_buy_admin.view_group', group_id=participant.group_id))

@bp.route('/campaigns/<int:campaign_id>/delete-product-image', methods=['POST'])
@login_required
@manager_required
def delete_product_image(campaign_id):
    """ลบรูปภาพสินค้าหลัก"""
    try:
        campaign = GroupBuyCampaign.query.get_or_404(campaign_id)
        
        if campaign.product_image:
            # ลบไฟล์จริงถ้ามี
            import os
            file_path = campaign.product_image
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"Deleted product image file: {file_path}")
                except Exception as e:
                    logger.error(f"Error deleting file {file_path}: {e}")
            
            # อัปเดตฐานข้อมูล
            campaign.product_image = None
            db.session.commit()
            logger.info(f"Product image removed from campaign #{campaign_id}")
            
            return jsonify({'success': True, 'message': 'ลบรูปภาพสินค้าสำเร็จ'})
        else:
            return jsonify({'success': False, 'message': 'ไม่มีรูปภาพสินค้า'})
            
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Error deleting product image: {e}\n{error_trace}")
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/campaigns/<int:campaign_id>/delete-album-image', methods=['POST'])
@login_required
@manager_required
def delete_album_image(campaign_id):
    """ลบรูปภาพจาก Album"""
    try:
        campaign = GroupBuyCampaign.query.get_or_404(campaign_id)
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'ไม่มีข้อมูล'}), 400
            
        image_path = data.get('image_path')
        
        if not image_path:
            return jsonify({'success': False, 'message': 'ไม่พบ image_path'}), 400
        
        if not campaign.album_images:
            return jsonify({'success': False, 'message': 'ไม่มี Album ภาพ'}), 400
        
        # Parse album images
        import json
        try:
            album_list = json.loads(campaign.album_images)
        except:
            return jsonify({'success': False, 'message': 'รูปแบบ Album ไม่ถูกต้อง'}), 400
        
        # ลบรูปที่ตรงกับ path
        new_album_list = []
        deleted = False
        
        for item in album_list:
            if isinstance(item, dict):
                if item.get('path') != image_path:
                    new_album_list.append(item)
                else:
                    deleted = True
                    # ลบไฟล์จริง
                    import os
                    file_path = item['path']
                    if os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                            logger.info(f"Deleted album image file: {file_path}")
                        except Exception as e:
                            logger.error(f"Error deleting file {file_path}: {e}")
            else:
                # รูปแบบเก่า (string)
                if item != image_path:
                    new_album_list.append(item)
                else:
                    deleted = True
                    # ลบไฟล์จริง
                    import os
                    if os.path.exists(item):
                        try:
                            os.remove(item)
                            logger.info(f"Deleted album image file: {item}")
                        except Exception as e:
                            logger.error(f"Error deleting file {item}: {e}")
        
        if not deleted:
            return jsonify({'success': False, 'message': 'ไม่พบรูปภาพที่ต้องการลบ'}), 404
        
        # อัปเดตฐานข้อมูล
        campaign.album_images = json.dumps(new_album_list) if new_album_list else None
        db.session.commit()
        logger.info(f"Album image removed from campaign #{campaign_id}")
        
        return jsonify({'success': True, 'message': 'ลบรูปภาพจาก Album สำเร็จ'})
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Error deleting album image: {e}\n{error_trace}")
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/api/campaigns/<int:campaign_id>/stats')
@login_required
@manager_required
def campaign_stats_api(campaign_id):
    """API: สถิติของแคมเปญ (สำหรับ AJAX)"""
    campaign = GroupBuyCampaign.query.get_or_404(campaign_id)
    
    groups = GroupBuyGroup.query.filter_by(campaign_id=campaign_id).all()
    
    stats = {
        'total_groups': len(groups),
        'successful_groups': sum(1 for g in groups if g.status == 'success'),
        'active_groups': sum(1 for g in groups if g.status == 'active'),
        'failed_groups': sum(1 for g in groups if g.status == 'failed'),
        'total_participants': sum(g.current_participants for g in groups),
        'inventory_used': campaign.inventory_used,
        'inventory_remaining': campaign.inventory_remaining
    }
    
    return jsonify(stats)

@bp.route('/participants/<int:participant_id>/cancel', methods=['POST'])
@login_required
@manager_required
def cancel_participant(participant_id):
    """ยกเลิกการจองของ Participant"""
    try:
        participant = GroupBuyParticipant.query.get_or_404(participant_id)
        group = participant.group
        campaign = group.campaign
        
        # ตรวจสอบสถานะ
        if participant.status == 'cancelled':
            flash('การจองนี้ถูกยกเลิกไปแล้ว', 'warning')
            return redirect(url_for('group_buy_admin.view_group', group_id=participant.group_id))
        
        # บันทึกข้อมูลเดิมก่อนยกเลิก
        old_pax_count = participant.pax_count
        participant_email = participant.participant_email
        participant_name = participant.participant_name
        
        # อัปเดตสถานะเป็นยกเลิก
        participant.status = 'cancelled'
        participant.cancelled_at = naive_utc_now()
        participant.cancel_reason = f'ยกเลิกโดย Admin ({current_user.username})'
        
        # คืนจำนวน pax ให้แคมเปญ
        if campaign.available_slots is not None:
            campaign.available_slots += old_pax_count
        
        # อัปเดตจำนวนสมาชิกในกลุ่ม
        group.current_participants -= old_pax_count
        
        # คืนเงินถ้าชำระเงินแล้ว
        if participant.payment_id and participant.payment_status == 'paid':
            payment = GroupBuyPayment.query.get(participant.payment_id)
            if payment and payment.payment_status == 'paid':
                payment.payment_status = 'refunded'
                payment.refunded_at = naive_utc_now()
                payment.refunded_by = current_user.id
                payment.refund_reason = 'ยกเลิกโดย Admin'
                payment.refund_amount = payment.total_amount
        
        db.session.commit()
        
        # ส่งอีเมลแจ้งเตือนถ้าเปิดใช้งาน
        if campaign.auto_cancel_send_email:
            try:
                from flask_mail import Message
                from extensions import mail
                
                subject = f'แจ้งยกเลิกการจอง - {campaign.name}'
                html_body = f"""
                <h3>แจ้งยกเลิกการจอง</h3>
                <p>เรียน คุณ{participant_name}</p>
                <p>การจองของท่านสำหรับ <strong>{campaign.name}</strong> ถูกยกเลิกแล้ว</p>
                <p>กลุ่ม: {group.group_code}</p>
                <p>จำนวน: {old_pax_count} คน</p>
                <p>เหตุผล: ยกเลิกโดย Admin</p>
                <br>
                <p>หากมีข้อสงสัย กรุณาติดต่อเจ้าหน้าที่</p>
                """
                
                msg = Message(subject,
                            recipients=[participant_email],
                            html=html_body)
                mail.send(msg)
                logger.info(f"Cancel notification sent to {participant_email}")
            except Exception as e:
                logger.error(f"Failed to send cancel email: {e}")
        
        flash(f'ยกเลิกการจองของ {participant_name} เรียบร้อย', 'success')
        logger.info(f"Participant #{participant_id} cancelled by {current_user.username}")
        
    except Exception as e:
        logger.error(f"Error cancelling participant: {e}")
        db.session.rollback()
        flash(f'เกิดข้อผิดพลาด: {str(e)}', 'danger')
    
    return redirect(url_for('group_buy_admin.view_group', group_id=participant.group_id))

@bp.route('/participants/<int:participant_id>/move', methods=['POST'])
@login_required
@manager_required
def move_participant(participant_id):
    """ย้ายสมาชิกไปยังกลุ่มอื่น"""
    try:
        participant = GroupBuyParticipant.query.get_or_404(participant_id)
        source_group = participant.group
        target_group_id = request.form.get('target_group_id', type=int)
        
        if not target_group_id:
            flash('กรุณาเลือกกลุ่มปลายทาง', 'warning')
            return redirect(url_for('group_buy_admin.view_group', group_id=source_group.id))
        
        target_group = GroupBuyGroup.query.get_or_404(target_group_id)
        
        # ตรวจสอบเงื่อนไข
        if participant.is_leader:
            flash('ไม่สามารถย้าย Leader ของกลุ่มได้', 'danger')
            return redirect(url_for('group_buy_admin.view_group', group_id=source_group.id))
        
        if participant.status == 'cancelled':
            flash('ไม่สามารถย้ายสมาชิกที่ถูกยกเลิกแล้ว', 'danger')
            return redirect(url_for('group_buy_admin.view_group', group_id=source_group.id))
        
        if source_group.campaign_id != target_group.campaign_id:
            flash('ไม่สามารถย้ายไปยังแคมเปญที่ต่างกันได้', 'danger')
            return redirect(url_for('group_buy_admin.view_group', group_id=source_group.id))
        
        if target_group.status != 'active':
            flash('กลุ่มปลายทางไม่อยู่ในสถานะ active', 'danger')
            return redirect(url_for('group_buy_admin.view_group', group_id=source_group.id))
        
        if target_group.is_expired:
            flash('กลุ่มปลายทางหมดอายุแล้ว', 'danger')
            return redirect(url_for('group_buy_admin.view_group', group_id=source_group.id))
        
        # ตรวจสอบที่ว่าง
        available_slots = target_group.required_participants - target_group.current_participants
        if available_slots < participant.pax_count:
            flash(f'กลุ่มปลายทางมีที่ว่างไม่พอ (ต้องการ {participant.pax_count} ที่, มีว่าง {available_slots} ที่)', 'danger')
            return redirect(url_for('group_buy_admin.view_group', group_id=source_group.id))
        
        # บันทึกข้อมูลเดิม
        old_group_id = source_group.id
        old_group_name = source_group.group_name or source_group.group_code
        new_group_name = target_group.group_name or target_group.group_code
        
        # ย้ายสมาชิก
        participant.group_id = target_group_id
        
        # อัปเดตจำนวนสมาชิกในกลุ่มเดิม
        source_group.current_participants -= participant.pax_count
        
        # อัปเดตจำนวนสมาชิกในกลุ่มใหม่
        target_group.current_participants += participant.pax_count
        
        # เปลี่ยน join_order ในกลุ่มใหม่
        max_join_order = db.session.query(db.func.max(GroupBuyParticipant.join_order))\
            .filter_by(group_id=target_group_id).scalar() or 0
        participant.join_order = max_join_order + 1
        
        # ตรวจสอบว่ากลุ่มใหม่ครบคนหรือไม่
        if target_group.is_full and target_group.status == 'active':
            target_group.status = 'success'
            target_group.completed_at = naive_utc_now()
            logger.info(f"Group #{target_group.id} is now full after moving participant #{participant_id}")
            
            # เรียก service เพื่อสร้าง booking
            try:
                service._handle_group_success(target_group)
            except Exception as e:
                logger.error(f"Error handling group success after move: {e}")
        
        db.session.commit()
        
        flash(f'✅ ย้าย {participant.participant_name} จาก "{old_group_name}" ไปยัง "{new_group_name}" เรียบร้อยแล้ว', 'success')
        
        # Log activity
        logger.info(f"Participant #{participant_id} moved from group #{old_group_id} to #{target_group_id} by {current_user.username}")
        
        return redirect(url_for('group_buy_admin.view_group', group_id=target_group_id))
        
    except Exception as e:
        logger.error(f"Error moving participant: {e}")
        db.session.rollback()
        flash(f'เกิดข้อผิดพลาด: {str(e)}', 'danger')
        return redirect(url_for('group_buy_admin.view_group', group_id=source_group.id if 'source_group' in locals() else participant.group_id))

@bp.route('/campaigns/<int:campaign_id>/quick-booking', methods=['GET', 'POST'])
@login_required
@manager_required
def quick_booking(campaign_id):
    """ฟอร์มจองด่วนสำหรับ Admin (ช่วยลูกค้าจอง)"""
    campaign = GroupBuyCampaign.query.get_or_404(campaign_id)
    
    if request.method == 'POST':
        try:
            # รับข้อมูลจากฟอร์ม
            booking_type = request.form.get('booking_type')  # 'new_group' or 'join_group'
            name = request.form.get('name')
            email = request.form.get('email')
            phone = request.form.get('phone')
            pax_count = int(request.form.get('pax_count', 1))
            payment_status = request.form.get('payment_status', 'pending')  # 'paid' or 'pending'
            group_name = request.form.get('group_name', '')
            group_id = request.form.get('group_id')
            
            # Validate
            if not all([name, email, phone]):
                flash('กรุณากรอกข้อมูลให้ครบถ้วน', 'warning')
                return redirect(url_for('group_buy_admin.quick_booking', campaign_id=campaign_id))
            
            # ตรวจสอบอีเมลซ้ำ
            if booking_type == 'new_group':
                existing = GroupBuyParticipant.query.filter(
                    GroupBuyParticipant.campaign_id == campaign_id,
                    GroupBuyParticipant.participant_email == email,
                    GroupBuyParticipant.payment_status.in_(['pending', 'paid'])
                ).first()
                
                if existing:
                    flash(f'อีเมล {email} มีการจองในแคมเปญนี้อยู่แล้ว', 'warning')
                    return redirect(url_for('group_buy_admin.quick_booking', campaign_id=campaign_id))
            
            elif booking_type == 'join_group' and group_id:
                existing = GroupBuyParticipant.query.filter_by(
                    group_id=int(group_id),
                    participant_email=email
                ).first()
                
                if existing:
                    flash(f'อีเมล {email} มีในกลุ่มนี้อยู่แล้ว', 'warning')
                    return redirect(url_for('group_buy_admin.quick_booking', campaign_id=campaign_id))
            
            # สร้างการจอง
            if booking_type == 'new_group':
                # สร้างกลุ่มใหม่
                leader_info = {
                    'name': name,
                    'email': email,
                    'phone': phone,
                    'pax_count': pax_count
                }
                
                result, error = service.create_group(
                    campaign_id=campaign_id,
                    leader_info=leader_info,
                    custom_group_name=group_name if group_name else None
                )
                
                if result:
                    group, participant = result
                    
                    # อัปเดต payment status ถ้าเลือก paid
                    if payment_status == 'paid':
                        participant.payment_status = 'paid'
                        participant.payment_date = now_thailand()
                    
                    # บันทึกว่าจองโดย admin
                    participant.notes = f"จองโดย Admin: {current_user.username}"
                    db.session.commit()
                    
                    flash(f'สร้างกลุ่มและจองสำเร็จ! กลุ่ม: {group.group_code}', 'success')
                    logger.info(f"Admin {current_user.username} created quick booking for {email} in campaign {campaign_id}")
                    return redirect(url_for('group_buy_admin.view_group', group_id=group.id))
                else:
                    flash(f'ไม่สามารถสร้างกลุ่มได้: {error}', 'danger')
                    
            elif booking_type == 'join_group' and group_id:
                # เข้าร่วมกลุ่มที่มีอยู่
                group = GroupBuyGroup.query.get(int(group_id))
                
                if not group:
                    flash('ไม่พบกลุ่มที่เลือก', 'danger')
                    return redirect(url_for('group_buy_admin.quick_booking', campaign_id=campaign_id))
                
                participant_info = {
                    'name': name,
                    'email': email,
                    'phone': phone,
                    'pax_count': pax_count
                }
                
                # ใช้ join_group แทน join_existing_group
                result, error = service.join_group(
                    group_code_or_token=group.group_code,
                    participant_info=participant_info,
                    is_token=False
                )
                
                if result:
                    participant = result
                    
                    # อัปเดต payment status ถ้าเลือก paid
                    if payment_status == 'paid':
                        participant.payment_status = 'paid'
                        participant.payment_date = now_thailand()
                    
                    # บันทึกว่าจองโดย admin
                    participant.notes = f"จองโดย Admin: {current_user.username}"
                    db.session.commit()
                    
                    flash(f'เข้าร่วมกลุ่มสำเร็จ!', 'success')
                    logger.info(f"Admin {current_user.username} added participant {email} to group {group_id}")
                    return redirect(url_for('group_buy_admin.view_group', group_id=int(group_id)))
                else:
                    flash(f'ไม่สามารถเข้าร่วมกลุ่มได้: {error}', 'danger')
            else:
                flash('กรุณาเลือกประเภทการจอง', 'warning')
                
        except Exception as e:
            logger.error(f"Error in quick booking: {e}")
            db.session.rollback()
            flash(f'เกิดข้อผิดพลาด: {str(e)}', 'danger')
    
    # GET request - แสดงฟอร์ม
    # ดึงกลุ่มที่ยังไม่เต็มและไม่หมดอายุ
    available_groups = GroupBuyGroup.query.filter(
        GroupBuyGroup.campaign_id == campaign_id,
        GroupBuyGroup.status == 'active',
        GroupBuyGroup.current_participants < GroupBuyGroup.required_participants,
        GroupBuyGroup.expires_at > now_thailand()
    ).order_by(GroupBuyGroup.created_at.desc()).all()
    
    return render_template('group_buy/admin/quick_booking.html',
                         campaign=campaign,
                         available_groups=available_groups)

@bp.route('/campaign/<int:campaign_id>/special-codes', methods=['GET'])
@login_required
@manager_required
def manage_special_codes(campaign_id):
    """จัดการรหัสผู้จองพิเศษ"""
    campaign = GroupBuyCampaign.query.get_or_404(campaign_id)
    codes = campaign.get_special_booker_codes()
    
    return render_template('group_buy/admin/special_codes.html',
                         campaign=campaign,
                         codes=codes)

@bp.route('/campaign/<int:campaign_id>/special-codes/add', methods=['POST'])
@login_required
@manager_required
def add_special_code(campaign_id):
    """เพิ่มรหัสพิเศษ"""
    campaign = GroupBuyCampaign.query.get_or_404(campaign_id)
    
    code = request.form.get('code', '').strip().upper()
    name = request.form.get('name', '').strip()
    note = request.form.get('note', '').strip()
    
    if not code:
        return jsonify({'success': False, 'message': 'กรุณากรอกรหัส'}), 400
    
    success, message = campaign.add_special_booker_code(code, name, note)
    
    if success:
        db.session.commit()
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'message': message}), 400

@bp.route('/campaign/<int:campaign_id>/special-codes/remove', methods=['POST'])
@login_required
@manager_required
def remove_special_code(campaign_id):
    """ลบรหัสพิเศษ"""
    campaign = GroupBuyCampaign.query.get_or_404(campaign_id)
    
    code = request.form.get('code', '').strip().upper()
    
    if not code:
        return jsonify({'success': False, 'message': 'กรุณาระบุรหัส'}), 400
    
    campaign.remove_special_booker_code(code)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'ลบรหัสสำเร็จ'})


@bp.route('/upload-editor-image', methods=['POST'])
@login_required
@group_buy_permission_required('edit_campaign')
def upload_editor_image():
    """อัปโหลดรูปภาพสำหรับ WYSIWYG editor"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file type
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        filename = secure_filename(file.filename)
        if '.' not in filename or filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
            return jsonify({'error': 'Invalid file type. Allowed: PNG, JPG, GIF, WEBP'}), 400
        
        # Generate unique filename
        import uuid
        from datetime import datetime
        ext = filename.rsplit('.', 1)[1].lower()
        unique_filename = f"editor_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{ext}"
        
        # Save to uploads/group_buy/editor directory
        upload_dir = os.path.join('static', 'uploads', 'group_buy', 'editor')
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, unique_filename)
        file.save(file_path)
        
        # Return URL for the uploaded image
        image_url = f"/static/uploads/group_buy/editor/{unique_filename}"
        
        logger.info(f"Editor image uploaded: {image_url} by user {current_user.id}")
        
        return jsonify({'url': image_url}), 200
        
    except Exception as e:
        logger.error(f"Error uploading editor image: {str(e)}")
        return jsonify({'error': 'Upload failed'}), 500

