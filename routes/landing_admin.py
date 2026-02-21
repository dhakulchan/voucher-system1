"""Landing Page Admin Routes"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from models.landing_product import LandingProduct
from extensions import db
from functools import wraps
import os
import logging
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

bp = Blueprint('landing_admin', __name__, url_prefix='/admin/landing')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'webm', 'mov'}

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

def allowed_video_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS

@bp.route('/')
@login_required
@admin_required
def index():
    """หน้าจัดการ Landing Products"""
    products = LandingProduct.query.order_by(
        LandingProduct.is_featured.desc(),
        LandingProduct.display_order.asc(),
        LandingProduct.created_at.desc()
    ).all()
    
    return render_template('landing/admin/index.html', products=products)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create():
    """สร้าง Product ใหม่"""
    if request.method == 'POST':
        group_id = request.form.get('group_id')
        product = LandingProduct(
            title=request.form.get('title'),
            subtitle=request.form.get('subtitle'),
            description=request.form.get('description'),
            external_url=request.form.get('external_url'),
            external_url_text=request.form.get('external_url_text', 'ดูรายละเอียด'),
            open_in_new_tab=request.form.get('open_in_new_tab') == 'on',
            category=request.form.get('category'),
            group_id=int(group_id) if group_id else None,
            is_active=request.form.get('is_active') == 'on',
            is_featured=request.form.get('is_featured') == 'on',
            display_order=int(request.form.get('display_order', 0)),
            highlight_badge=request.form.get('highlight_badge'),
            highlight_color=request.form.get('highlight_color', 'danger'),
            price_text=request.form.get('price_text'),
            seo_title=request.form.get('seo_title'),
            seo_description=request.form.get('seo_description'),
            created_by=current_user.id
        )
        
        # Upload banner image
        if 'banner_image' in request.files:
            file = request.files['banner_image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Add timestamp to prevent overwrite
                import time
                filename = f"{int(time.time())}_{filename}"
                upload_dir = os.path.join(current_app.root_path, 'static/images/landing')
                os.makedirs(upload_dir, exist_ok=True)
                upload_path = os.path.join(upload_dir, filename)
                file.save(upload_path)
                product.banner_image = f'images/landing/{filename}'
        
        # Upload video
        if 'video_file' in request.files:
            file = request.files['video_file']
            if file and file.filename and allowed_video_file(file.filename):
                filename = secure_filename(file.filename)
                import time
                filename = f"{int(time.time())}_{filename}"
                upload_dir = os.path.join(current_app.root_path, 'static/videos/landing')
                os.makedirs(upload_dir, exist_ok=True)
                upload_path = os.path.join(upload_dir, filename)
                file.save(upload_path)
                product.video_url = f'videos/landing/{filename}'
        
        # Upload video thumbnail
        if 'video_thumbnail' in request.files:
            file = request.files['video_thumbnail']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                import time
                filename = f"{int(time.time())}_{filename}"
                upload_dir = os.path.join(current_app.root_path, 'static/images/landing/video_thumbs')
                os.makedirs(upload_dir, exist_ok=True)
                upload_path = os.path.join(upload_dir, filename)
                file.save(upload_path)
                product.video_thumbnail = f'images/landing/video_thumbs/{filename}'
        
        # Video duration
        video_duration = request.form.get('video_duration', '').strip()
        if video_duration:
            product.video_duration = video_duration
        
        # Tags
        tags_input = request.form.get('tags', '')
        if tags_input:
            tags_list = [t.strip() for t in tags_input.split(',') if t.strip()]
            product.set_tags(tags_list)
        
        db.session.add(product)
        db.session.commit()
        
        flash('สร้าง Product สำเร็จ!', 'success')
        return redirect(url_for('landing_admin.index'))
    
    # GET: ดึง groups ทั้งหมด
    from models.landing_page_group import LandingPageGroup
    groups = LandingPageGroup.query.filter_by(is_active=True).order_by(LandingPageGroup.display_order).all()
    return render_template('landing/admin/create.html', groups=groups)

@bp.route('/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit(product_id):
    """แก้ไข Product"""
    product = LandingProduct.query.get_or_404(product_id)
    
    if request.method == 'POST':
        current_app.logger.info(f"🎬 VIDEO EDIT: POST request for product {product_id}")
        
        group_id = request.form.get('group_id')
        product.title = request.form.get('title')
        product.subtitle = request.form.get('subtitle')
        product.description = request.form.get('description')
        product.external_url = request.form.get('external_url')
        product.external_url_text = request.form.get('external_url_text', 'ดูรายละเอียด')
        product.open_in_new_tab = request.form.get('open_in_new_tab') == 'on'
        product.category = request.form.get('category')
        product.group_id = int(group_id) if group_id else None
        product.is_active = request.form.get('is_active') == 'on'
        product.is_featured = request.form.get('is_featured') == 'on'
        product.display_order = int(request.form.get('display_order', 0))
        product.highlight_badge = request.form.get('highlight_badge')
        product.highlight_color = request.form.get('highlight_color', 'danger')
        product.price_text = request.form.get('price_text')
        product.seo_title = request.form.get('seo_title')
        product.seo_description = request.form.get('seo_description')
        
        # Upload banner image
        if 'banner_image' in request.files:
            file = request.files['banner_image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Add timestamp to prevent overwrite
                import time
                filename = f"{int(time.time())}_{filename}"
                upload_dir = os.path.join(current_app.root_path, 'static/images/landing')
                os.makedirs(upload_dir, exist_ok=True)
                upload_path = os.path.join(upload_dir, filename)
                file.save(upload_path)
                product.banner_image = f'images/landing/{filename}'
        
        # Upload video
        current_app.logger.info(f"🎬 VIDEO EDIT: Checking for video_file...")
        if 'video_file' in request.files:
            file = request.files['video_file']
            current_app.logger.info(f"🎬 VIDEO EDIT: Found video_file - filename: '{file.filename}'")
            
            if file and file.filename and file.filename.strip():
                current_app.logger.info(f"🎬 VIDEO EDIT: File has content, checking extension...")
                if allowed_video_file(file.filename):
                    # Delete old video file if exists
                    if product.video_url:
                        old_video_path = os.path.join(current_app.root_path, 'static', product.video_url)
                        if os.path.exists(old_video_path):
                            try:
                                os.remove(old_video_path)
                                current_app.logger.info(f"✅ Deleted old video: {old_video_path}")
                            except Exception as e:
                                current_app.logger.warning(f"⚠️ Could not delete old video: {e}")
                    
                    filename = secure_filename(file.filename)
                    import time
                    filename = f"{int(time.time())}_{filename}"
                    upload_dir = os.path.join(current_app.root_path, 'static/videos/landing')
                    os.makedirs(upload_dir, exist_ok=True)
                    upload_path = os.path.join(upload_dir, filename)
                    
                    current_app.logger.info(f"🎬 VIDEO EDIT: Saving to {upload_path}...")
                    file.save(upload_path)
                    product.video_url = f'videos/landing/{filename}'
                    current_app.logger.info(f"🎬 VIDEO EDIT: ✅ SUCCESS! Video saved to {product.video_url}")
                    flash(f'✅ อัปโหลดวิดีโอสำเร็จ: {os.path.basename(filename)}', 'success')
                else:
                    current_app.logger.warning(f"🎬 VIDEO EDIT: ❌ File type not allowed: {file.filename}")
                    flash(f'❌ ไฟล์วิดีโอต้องเป็น MP4, WebM หรือ MOV เท่านั้น', 'danger')
            else:
                current_app.logger.info(f"🎬 VIDEO EDIT: ⚠️ Empty filename or no file selected")
        else:
            current_app.logger.info(f"🎬 VIDEO EDIT: ⚠️ No video_file in request")
        
        # Upload video thumbnail
        if 'video_thumbnail' in request.files:
            file = request.files['video_thumbnail']
            if file and file.filename and allowed_file(file.filename):
                # Delete old thumbnail if exists
                if product.video_thumbnail:
                    old_thumb_path = os.path.join(current_app.root_path, 'static', product.video_thumbnail)
                    if os.path.exists(old_thumb_path):
                        try:
                            os.remove(old_thumb_path)
                            current_app.logger.info(f"✅ Deleted old thumbnail: {old_thumb_path}")
                        except Exception as e:
                            current_app.logger.warning(f"⚠️ Could not delete old thumbnail: {e}")
                
                filename = secure_filename(file.filename)
                import time
                filename = f"{int(time.time())}_{filename}"
                upload_dir = os.path.join(current_app.root_path, 'static/images/landing/video_thumbs')
                os.makedirs(upload_dir, exist_ok=True)
                upload_path = os.path.join(upload_dir, filename)
                file.save(upload_path)
                product.video_thumbnail = f'images/landing/video_thumbs/{filename}'
                flash(f'✅ อัปโหลดรูปภาพตัวอย่างวิดีโอสำเร็จ', 'success')
        
        # Video duration
        video_duration = request.form.get('video_duration', '').strip()
        if video_duration:
            product.video_duration = video_duration
            logger.info(f"🎬 VIDEO EDIT: Duration set to {video_duration}")
        
        # Tags
        tags_input = request.form.get('tags', '')
        if tags_input:
            tags_list = [t.strip() for t in tags_input.split(',') if t.strip()]
            product.set_tags(tags_list)
        else:
            product.tags = None
        
        db.session.commit()
        logger.info(f"🎬 VIDEO EDIT: All changes committed to database")
        
        flash('แก้ไข Product สำเร็จ!', 'success')
        return redirect(url_for('landing_admin.index'))
    
    # Prepare tags for form
    tags_str = ', '.join(product.tags_list) if product.tags_list else ''
    
    # GET: ดึง groups ทั้งหมด
    from models.landing_page_group import LandingPageGroup
    groups = LandingPageGroup.query.filter_by(is_active=True).order_by(LandingPageGroup.display_order).all()
    
    return render_template('landing/admin/edit.html', product=product, tags_str=tags_str, groups=groups)

@bp.route('/delete/<int:product_id>', methods=['POST'])
@login_required
@admin_required
def delete(product_id):
    """ลบ Product"""
    product = LandingProduct.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    
    flash('ลบ Product สำเร็จ!', 'success')
    return redirect(url_for('landing_admin.index'))

@bp.route('/toggle-active/<int:product_id>', methods=['POST'])
@login_required
@admin_required
def toggle_active(product_id):
    """สลับสถานะ Active/Inactive"""
    product = LandingProduct.query.get_or_404(product_id)
    product.is_active = not product.is_active
    db.session.commit()
    
    status = 'เปิดใช้งาน' if product.is_active else 'ปิดใช้งาน'
    flash(f'{status} Product สำเร็จ!', 'success')
    return redirect(url_for('landing_admin.index'))

@bp.route('/toggle-featured/<int:product_id>', methods=['POST'])
@login_required
@admin_required
def toggle_featured(product_id):
    """สลับสถานะ Featured"""
    product = LandingProduct.query.get_or_404(product_id)
    product.is_featured = not product.is_featured
    db.session.commit()
    
    status = 'แนะนำ' if product.is_featured else 'ยกเลิกแนะนำ'
    flash(f'{status} Product สำเร็จ!', 'success')
    return redirect(url_for('landing_admin.index'))
@bp.route('/delete-video/<int:product_id>', methods=['POST'])
@login_required
@admin_required
def delete_video(product_id):
    """ลบวิดีโอ"""
    product = LandingProduct.query.get_or_404(product_id)
    
    # Delete video file if exists
    if product.video_url:
        video_path = os.path.join(current_app.root_path, 'static', product.video_url)
        if os.path.exists(video_path):
            try:
                os.remove(video_path)
                current_app.logger.info(f"✅ Deleted video file: {video_path}")
            except Exception as e:
                current_app.logger.error(f"❌ Error deleting video: {e}")
                flash(f'เกิดข้อผิดพลาดในการลบไฟล์วิดีโอ: {e}', 'danger')
                return redirect(url_for('landing_admin.edit', product_id=product_id))
    
    # Clear video field (keep thumbnail and duration)
    product.video_url = None
    
    db.session.commit()
    
    flash('ลบวิดีโอสำเร็จ!', 'success')
    return redirect(url_for('landing_admin.edit', product_id=product_id))


@bp.route('/delete-video-thumbnail/<int:product_id>', methods=['POST'])
@login_required
@admin_required
def delete_video_thumbnail(product_id):
    """ลบรูปภาพตัวอย่างวิดีโอ"""
    product = LandingProduct.query.get_or_404(product_id)
    
    # Delete thumbnail file if exists
    if product.video_thumbnail:
        thumb_path = os.path.join(current_app.root_path, 'static', product.video_thumbnail)
        if os.path.exists(thumb_path):
            try:
                os.remove(thumb_path)
                current_app.logger.info(f"✅ Deleted thumbnail file: {thumb_path}")
            except Exception as e:
                current_app.logger.error(f"❌ Error deleting thumbnail: {e}")
                flash(f'เกิดข้อผิดพลาดในการลบไฟล์รูปภาพ: {e}', 'danger')
                return redirect(url_for('landing_admin.edit', product_id=product_id))
    
    # Clear thumbnail field
    product.video_thumbnail = None
    
    db.session.commit()
    
    flash('ลบรูปภาพตัวอย่างวิดีโอสำเร็จ!', 'success')
    return redirect(url_for('landing_admin.edit', product_id=product_id))