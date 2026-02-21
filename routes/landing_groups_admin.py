"""Landing Page Groups Admin Routes"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from models.landing_page_group import LandingPageGroup
from models.landing_product import LandingProduct
from extensions import db
from functools import wraps
from datetime import datetime
import os
import random
import string
from werkzeug.utils import secure_filename

bp = Blueprint('landing_groups_admin', __name__, url_prefix='/admin/landing/groups')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def admin_required(f):
    """Decorator: ต้องเป็น Admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('กรุณาเข้าสู่ระบบ', 'warning')
            return redirect(url_for('auth.login'))
        
        # Check admin permission or Administrator role
        if not (current_user.role == 'Administrator'):
            flash('คุณไม่มีสิทธิ์เข้าถึงหน้านี้', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_unique_short_url(base_slug, max_attempts=10):
    """Generate unique short URL based on slug"""
    # Clean slug: remove spaces, special chars, keep only alphanumeric and hyphens
    clean_slug = ''.join(c for c in base_slug.lower() if c.isalnum() or c == '-')
    clean_slug = clean_slug[:15]  # Limit length
    
    # Try slug first
    if clean_slug and not LandingPageGroup.query.filter_by(short_url=clean_slug).first():
        return clean_slug
    
    # If slug exists, add random suffix
    for attempt in range(max_attempts):
        # Generate 4-character random string
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        short_url = f"{clean_slug}-{random_suffix}"
        
        if not LandingPageGroup.query.filter_by(short_url=short_url).first():
            return short_url
    
    # Fallback: use timestamp-based
    timestamp = int(datetime.now().timestamp()) % 100000
    return f"{clean_slug}-{timestamp}"

@bp.route('/')
@login_required
@admin_required
def index():
    """หน้าจัดการ Landing Page Groups"""
    groups = LandingPageGroup.query.order_by(
        LandingPageGroup.start_date.desc()
    ).all()
    
    return render_template('landing/admin/groups/index.html', groups=groups)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create():
    """สร้าง Group ใหม่"""
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('name', '').strip()
            slug = request.form.get('slug', '').strip()
            short_url = request.form.get('short_url', '').strip()
            description = request.form.get('description', '').strip()
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            theme_color = request.form.get('theme_color', '#3498db').strip()
            is_active = request.form.get('is_active') == 'on'
            display_order = request.form.get('display_order', 0, type=int)
            
            # Validate required fields
            if not name or not slug:
                flash('กรุณากรอกชื่อและ Slug', 'danger')
                return redirect(url_for('landing_groups_admin.create'))
            
            # Check if slug exists
            existing = LandingPageGroup.query.filter_by(slug=slug).first()
            if existing:
                flash(f'Slug "{slug}" ถูกใช้งานแล้ว', 'danger')
                return redirect(url_for('landing_groups_admin.create'))
            
            # Auto-generate short_url if not provided
            if not short_url:
                short_url = generate_unique_short_url(slug)
            else:
                # Check if provided short_url exists
                existing_short = LandingPageGroup.query.filter_by(short_url=short_url).first()
                if existing_short:
                    flash(f'Short URL "{short_url}" ถูกใช้งานแล้ว', 'danger')
                    return redirect(url_for('landing_groups_admin.create'))
            
            # Convert dates
            start_dt = datetime.strptime(start_date, '%Y-%m-%d') if start_date else None
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') if end_date else None
            
            # Handle banner image upload
            banner_image = None
            if 'banner_image' in request.files:
                file = request.files['banner_image']
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    # Add timestamp to avoid conflicts
                    name_parts = filename.rsplit('.', 1)
                    filename = f"{name_parts[0]}_{int(datetime.now().timestamp())}.{name_parts[1]}"
                    
                    upload_folder = os.path.join(current_app.root_path, 'static', 'images', 'landing', 'groups')
                    os.makedirs(upload_folder, exist_ok=True)
                    
                    filepath = os.path.join(upload_folder, filename)
                    file.save(filepath)
                    banner_image = f'images/landing/groups/{filename}'
            
            # Create new group
            group = LandingPageGroup(
                name=name,
                slug=slug,
                short_url=short_url,
                description=description,
                start_date=start_dt,
                end_date=end_dt,
                theme_color=theme_color,
                banner_image=banner_image,
                is_active=is_active,
                display_order=display_order
            )
            
            db.session.add(group)
            db.session.commit()
            
            flash(f'สร้าง Group "{name}" สำเร็จ!', 'success')
            return redirect(url_for('landing_groups_admin.index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'เกิดข้อผิดพลาด: {str(e)}', 'danger')
            return redirect(url_for('landing_groups_admin.create'))
    
    return render_template('landing/admin/groups/create.html')

@bp.route('/<int:group_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit(group_id):
    """แก้ไข Group"""
    group = LandingPageGroup.query.get_or_404(group_id)
    
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('name', '').strip()
            slug = request.form.get('slug', '').strip()
            short_url = request.form.get('short_url', '').strip()
            description = request.form.get('description', '').strip()
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            theme_color = request.form.get('theme_color', '#3498db').strip()
            is_active = request.form.get('is_active') == 'on'
            display_order = request.form.get('display_order', 0, type=int)
            
            # Validate required fields
            if not name or not slug:
                flash('กรุณากรอกชื่อและ Slug', 'danger')
                return redirect(url_for('landing_groups_admin.edit', group_id=group_id))
            
            # Check if slug exists (except current group)
            existing = LandingPageGroup.query.filter(
                LandingPageGroup.slug == slug,
                LandingPageGroup.id != group_id
            ).first()
            if existing:
                flash(f'Slug "{slug}" ถูกใช้งานแล้ว', 'danger')
                return redirect(url_for('landing_groups_admin.edit', group_id=group_id))
            
            # Auto-generate short_url if not provided or empty
            if not short_url:
                short_url = generate_unique_short_url(slug)
            else:
                # Check if provided short_url exists (except current group)
                existing_short = LandingPageGroup.query.filter(
                    LandingPageGroup.short_url == short_url,
                    LandingPageGroup.id != group_id
                ).first()
                if existing_short:
                    flash(f'Short URL "{short_url}" ถูกใช้งานแล้ว', 'danger')
                    return redirect(url_for('landing_groups_admin.edit', group_id=group_id))
            
            # Convert dates
            start_dt = datetime.strptime(start_date, '%Y-%m-%d') if start_date else None
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') if end_date else None
            
            # Handle banner image upload
            if 'banner_image' in request.files:
                file = request.files['banner_image']
                if file and file.filename and allowed_file(file.filename):
                    # Delete old image
                    if group.banner_image:
                        old_path = os.path.join(current_app.root_path, 'static', group.banner_image)
                        if os.path.exists(old_path):
                            os.remove(old_path)
                    
                    filename = secure_filename(file.filename)
                    name_parts = filename.rsplit('.', 1)
                    filename = f"{name_parts[0]}_{int(datetime.now().timestamp())}.{name_parts[1]}"
                    
                    upload_folder = os.path.join(current_app.root_path, 'static', 'images', 'landing', 'groups')
                    os.makedirs(upload_folder, exist_ok=True)
                    
                    filepath = os.path.join(upload_folder, filename)
                    file.save(filepath)
                    group.banner_image = f'images/landing/groups/{filename}'
            
            # Update group
            group.name = name
            group.slug = slug
            group.short_url = short_url
            group.description = description
            group.start_date = start_dt
            group.end_date = end_dt
            group.theme_color = theme_color
            group.is_active = is_active
            group.display_order = display_order
            
            db.session.commit()
            
            flash(f'แก้ไข Group "{name}" สำเร็จ!', 'success')
            return redirect(url_for('landing_groups_admin.index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'เกิดข้อผิดพลาด: {str(e)}', 'danger')
            return redirect(url_for('landing_groups_admin.edit', group_id=group_id))
    
    return render_template('landing/admin/groups/edit.html', group=group)

@bp.route('/<int:group_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete(group_id):
    """ลบ Group"""
    group = LandingPageGroup.query.get_or_404(group_id)
    
    try:
        # Check if group has products
        if group.products:
            flash(f'ไม่สามารถลบ Group "{group.name}" ได้ เนื่องจากมี {len(group.products)} Products อยู่', 'danger')
            return redirect(url_for('landing_groups_admin.index'))
        
        # Delete banner image
        if group.banner_image:
            image_path = os.path.join(current_app.root_path, 'static', group.banner_image)
            if os.path.exists(image_path):
                os.remove(image_path)
        
        name = group.name
        db.session.delete(group)
        db.session.commit()
        
        flash(f'ลบ Group "{name}" สำเร็จ!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'เกิดข้อผิดพลาด: {str(e)}', 'danger')
    
    return redirect(url_for('landing_groups_admin.index'))

@bp.route('/<int:group_id>/toggle-active', methods=['POST'])
@login_required
@admin_required
def toggle_active(group_id):
    """สลับสถานะ Active"""
    group = LandingPageGroup.query.get_or_404(group_id)
    
    try:
        group.is_active = not group.is_active
        db.session.commit()
        
        status = 'เปิดใช้งาน' if group.is_active else 'ปิดใช้งาน'
        return jsonify({'success': True, 'is_active': group.is_active, 'message': f'{status}สำเร็จ'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
