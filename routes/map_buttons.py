"""Map Buttons — Admin management of global reference-map buttons shown on the
public Voucher page. Buttons open an image in the lightbox.
"""
import os
import uuid
from functools import wraps

from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, current_app)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from extensions import db
from models.map_button import MapButton

bp = Blueprint('map_buttons', __name__, url_prefix='/admin/map-buttons')

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp', 'gif'}
MANAGE_ROLES = ('Administrator', 'Staff')
DEFAULT_ICON = 'fas fa-map-marked-alt'


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('กรุณาเข้าสู่ระบบ', 'warning')
            return redirect(url_for('auth.login'))
        allowed = (getattr(current_user, 'role', None) in MANAGE_ROLES
                   or current_user.has_sidebar_menu('map_buttons'))
        if not allowed:
            flash('คุณไม่มีสิทธิ์เข้าถึงหน้านี้', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated


def _upload_dir():
    return os.path.join(current_app.root_path, 'static', 'uploads', 'map_buttons')


def _allowed(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _resolve_image(existing=''):
    """Return an image URL from an uploaded file (preferred) or a pasted URL."""
    file = request.files.get('image_file')
    if file and file.filename:
        if not _allowed(file.filename):
            return None, 'รองรับเฉพาะไฟล์ jpg, jpeg, png, webp, gif'
        os.makedirs(_upload_dir(), exist_ok=True)
        ext = file.filename.rsplit('.', 1)[1].lower()
        stored = f'{uuid.uuid4().hex}.{ext}'
        file.save(os.path.join(_upload_dir(), stored))
        return url_for('static', filename=f'uploads/map_buttons/{stored}'), None
    url = (request.form.get('image_url') or '').strip()
    return (url or existing), None


@bp.route('/', methods=['GET'])
@login_required
@admin_required
def index():
    buttons = MapButton.query.order_by(MapButton.display_order, MapButton.id).all()
    return render_template('admin/map_buttons/index.html', buttons=buttons,
                           default_icon=DEFAULT_ICON)


@bp.route('/save-selection', methods=['POST'])
@login_required
@admin_required
def save_selection():
    """Update is_active for all buttons based on submitted checkboxes."""
    active_ids = set(int(x) for x in request.form.getlist('active_ids') if x.isdigit())
    for b in MapButton.query.all():
        b.is_active = b.id in active_ids
    db.session.commit()
    flash('✅ บันทึกการเลือกปุ่มที่แสดงแล้ว', 'success')
    return redirect(url_for('map_buttons.index'))


@bp.route('/add', methods=['POST'])
@login_required
@admin_required
def add():
    label = (request.form.get('label') or '').strip()
    icon = (request.form.get('icon') or '').strip() or DEFAULT_ICON
    if not label:
        flash('กรุณากรอกชื่อปุ่ม', 'warning')
        return redirect(url_for('map_buttons.index'))
    image_url, err = _resolve_image()
    if err:
        flash(err, 'warning')
        return redirect(url_for('map_buttons.index'))
    if not image_url:
        flash('กรุณาใส่ลิงก์รูป หรืออัปโหลดไฟล์', 'warning')
        return redirect(url_for('map_buttons.index'))
    max_order = db.session.query(db.func.max(MapButton.display_order)).scalar() or 0
    db.session.add(MapButton(label=label, image_url=image_url, icon=icon,
                             display_order=max_order + 1, is_active=True))
    db.session.commit()
    flash('✅ เพิ่มปุ่มสำเร็จ', 'success')
    return redirect(url_for('map_buttons.index'))


@bp.route('/<int:button_id>/edit', methods=['POST'])
@login_required
@admin_required
def edit(button_id):
    b = MapButton.query.get_or_404(button_id)
    b.label = (request.form.get('label') or b.label).strip()
    b.icon = (request.form.get('icon') or '').strip() or DEFAULT_ICON
    image_url, err = _resolve_image(existing=b.image_url)
    if err:
        flash(err, 'warning')
        return redirect(url_for('map_buttons.index'))
    b.image_url = image_url
    db.session.commit()
    flash('✅ แก้ไขปุ่มสำเร็จ', 'success')
    return redirect(url_for('map_buttons.index'))


@bp.route('/<int:button_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete(button_id):
    b = MapButton.query.get_or_404(button_id)
    db.session.delete(b)
    db.session.commit()
    flash('🗑️ ลบปุ่มสำเร็จ', 'success')
    return redirect(url_for('map_buttons.index'))
