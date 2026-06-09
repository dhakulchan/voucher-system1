"""Info Images — Secure serve + Admin upload"""
import os
from flask import Blueprint, send_from_directory, abort, render_template, \
    request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from functools import wraps
from werkzeug.utils import secure_filename

bp = Blueprint('info_images', __name__)

# ------------------------------------------------------------------
# Allowed image names & their filenames on disk
# ------------------------------------------------------------------
INFO_IMAGES = {
    'why-choose-us': 'Why-Choose-Us.jpg',
    'about-us':      'about-dhakulchan-info.jpg',
}

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp', 'gif'}


def _secure_images_dir():
    return os.path.join(current_app.root_path, 'secure_images')


def _allowed(filename: str) -> bool:
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('กรุณาเข้าสู่ระบบ', 'warning')
            return redirect(url_for('auth.login'))
        if current_user.role != 'Administrator':
            flash('คุณไม่มีสิทธิ์เข้าถึงหน้านี้', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated


# ------------------------------------------------------------------
# Public: serve image via alias (hides real file path)
# ------------------------------------------------------------------
@bp.route('/landing/info-image/<name>')
def serve(name):
    """Serve a secure info image — URL does not reveal the real file path."""
    if name not in INFO_IMAGES:
        abort(404)
    img_dir = _secure_images_dir()
    filename = INFO_IMAGES[name]
    filepath = os.path.join(img_dir, filename)
    if not os.path.isfile(filepath):
        abort(404)
    return send_from_directory(img_dir, filename,
                               max_age=0,
                               as_attachment=False)


# ------------------------------------------------------------------
# Admin: upload / manage info images
# ------------------------------------------------------------------
@bp.route('/admin/info-images/', methods=['GET'])
@login_required
@admin_required
def admin_index():
    img_dir = _secure_images_dir()
    os.makedirs(img_dir, exist_ok=True)
    status = {}
    for key, fname in INFO_IMAGES.items():
        status[key] = {
            'filename': fname,
            'exists': os.path.isfile(os.path.join(img_dir, fname)),
        }
    return render_template('admin/info_images/index.html', status=status)


@bp.route('/admin/info-images/upload/<name>', methods=['POST'])
@login_required
@admin_required
def admin_upload(name):
    if name not in INFO_IMAGES:
        flash('ไม่พบชื่อภาพที่ระบุ', 'danger')
        return redirect(url_for('info_images.admin_index'))

    file = request.files.get('image')
    if not file or not file.filename:
        flash('กรุณาเลือกไฟล์ภาพ', 'warning')
        return redirect(url_for('info_images.admin_index'))

    if not _allowed(file.filename):
        flash('รองรับเฉพาะไฟล์ jpg, jpeg, png, webp, gif', 'warning')
        return redirect(url_for('info_images.admin_index'))

    img_dir = _secure_images_dir()
    os.makedirs(img_dir, exist_ok=True)
    dest_filename = INFO_IMAGES[name]
    save_path = os.path.join(img_dir, dest_filename)
    file.save(save_path)

    labels = {'why-choose-us': 'ทำไมต้องเลือกเรา', 'about-us': 'รู้จักเรา'}
    flash(f'✅ อัพโหลดภาพ "{labels[name]}" สำเร็จ!', 'success')
    return redirect(url_for('info_images.admin_index'))


@bp.route('/admin/info-images/delete/<name>', methods=['POST'])
@login_required
@admin_required
def admin_delete(name):
    if name not in INFO_IMAGES:
        flash('ไม่พบชื่อภาพที่ระบุ', 'danger')
        return redirect(url_for('info_images.admin_index'))

    img_dir = _secure_images_dir()
    filepath = os.path.join(img_dir, INFO_IMAGES[name])
    if os.path.isfile(filepath):
        os.remove(filepath)
        flash('🗑️ ลบภาพสำเร็จ', 'success')
    else:
        flash('ไม่พบไฟล์ที่ต้องการลบ', 'warning')
    return redirect(url_for('info_images.admin_index'))
