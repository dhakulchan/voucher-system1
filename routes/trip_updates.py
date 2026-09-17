"""Trip Daily Updates — Admin management + public JSON/image serving.

Admin (login + Administrator): create/manage day-by-day updates (album + info)
per booking. Customers see them on the public Voucher page with a NEW badge.
"""
import os
import uuid
from datetime import date, datetime, timedelta
from functools import wraps

from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, current_app, abort, send_from_directory, jsonify)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from extensions import db
from models.booking import Booking
from models.voucher_update import VoucherUpdate, VoucherUpdateImage
from models.map_button import MapButton
from models.booking_map_button import BookingMapButton

bp = Blueprint('trip_updates', __name__, url_prefix='/admin/trip-updates')

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
MAX_IMAGES_PER_UPDATE = 10
MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8 MB
TRAVELING_STATUSES = ('vouchered', 'completed')
# Roles allowed to manage Trip Updates (upload/update/delete)
MANAGE_ROLES = ('Administrator', 'Staff')


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('กรุณาเข้าสู่ระบบ', 'warning')
            return redirect(url_for('auth.login'))
        if getattr(current_user, 'role', None) not in MANAGE_ROLES:
            flash('คุณไม่มีสิทธิ์เข้าถึงหน้านี้', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated


def _updates_dir(booking_id):
    return os.path.join(current_app.root_path, 'secure_images',
                        'trip_updates', str(booking_id))


def _allowed(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _file_size(file_storage):
    file_storage.stream.seek(0, os.SEEK_END)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    return size


def _purge_booking_updates(booking_id):
    """Delete all updates + image files for a booking (used by 'replace' option)."""
    img_dir = _updates_dir(booking_id)
    for u in VoucherUpdate.query.filter_by(booking_id=booking_id).all():
        for img in u.images:
            _remove_image_files(booking_id, img.image_path)
        db.session.delete(u)


def _set_booking_maps(booking_id, map_ids):
    """Replace a booking's Voucher Maps selection with the given map-button ids."""
    BookingMapButton.query.filter_by(booking_id=booking_id).delete()
    for mid in dict.fromkeys(map_ids):  # de-dupe, keep order
        db.session.add(BookingMapButton(booking_id=booking_id, map_button_id=mid))


THUMB_MAX_PX = 600


def _remove_image_files(booking_id, filename):
    """Remove an original image and its cached thumbnail (if any)."""
    src_dir = _updates_dir(booking_id)
    for path in (os.path.join(src_dir, filename),
                 os.path.join(src_dir, 'thumbs', filename)):
        if os.path.isfile(path):
            os.remove(path)


def ensure_thumbnail(booking_id, filename):
    """Return (dir, filename) for a cached thumbnail, generating it if needed.

    Falls back to the original image directory if generation fails.
    """
    src_dir = _updates_dir(booking_id)
    src = os.path.join(src_dir, filename)
    if not os.path.isfile(src):
        return None
    thumb_dir = os.path.join(src_dir, 'thumbs')
    thumb_path = os.path.join(thumb_dir, filename)
    if os.path.isfile(thumb_path) and \
            os.path.getmtime(thumb_path) >= os.path.getmtime(src):
        return thumb_dir, filename
    try:
        from PIL import Image
        os.makedirs(thumb_dir, exist_ok=True)
        im = Image.open(src)
        im.thumbnail((THUMB_MAX_PX, THUMB_MAX_PX))
        ext = filename.rsplit('.', 1)[-1].lower()
        if ext in ('jpg', 'jpeg') and im.mode not in ('RGB', 'L'):
            im = im.convert('RGB')
        im.save(thumb_path)
        return thumb_dir, filename
    except Exception:
        return src_dir, filename


def _trip_day_info(booking, on_day=None):
    """Return (current_day, total_days) for a booking's travel window."""
    on_day = on_day or date.today()
    if not booking.arrival_date or not booking.departure_date:
        return None, None
    total = (booking.departure_date - booking.arrival_date).days + 1
    current = (on_day - booking.arrival_date).days + 1
    return current, total


# ------------------------------------------------------------------
# Admin: dashboard (traveling today + search)
# ------------------------------------------------------------------
@bp.route('/', methods=['GET'])
@login_required
@admin_required
def index():
    today = date.today()

    # Date window (default = today). ?range=today|w3|custom
    range_key = request.args.get('range', 'today')
    if range_key == 'w3':
        win_start, win_end = today - timedelta(days=3), today + timedelta(days=3)
    elif range_key == 'custom':
        try:
            win_start = datetime.strptime(request.args.get('from', ''), '%Y-%m-%d').date()
        except ValueError:
            win_start = today
        try:
            win_end = datetime.strptime(request.args.get('to', ''), '%Y-%m-%d').date()
        except ValueError:
            win_end = today
    else:
        range_key = 'today'
        win_start = win_end = today

    # Parties traveling within the window
    traveling = Booking.query.filter(
        Booking.status.in_(TRAVELING_STATUSES),
        Booking.arrival_date <= win_end,
        Booking.departure_date >= win_start,
    ).order_by(Booking.arrival_date.asc()).all()

    counts = dict(
        db.session.query(VoucherUpdate.booking_id, db.func.count(VoucherUpdate.id))
        .group_by(VoucherUpdate.booking_id).all()
    )

    traveling_cards = []
    for b in traveling:
        cur, total = _trip_day_info(b, today)
        traveling_cards.append({
            'booking': b,
            'day_current': cur,
            'day_total': total,
            'update_count': counts.get(b.id, 0),
        })

    # Voucher Maps: all buttons + per-booking current selection
    map_buttons = MapButton.query.order_by(
        MapButton.display_order, MapButton.id).all()
    booking_map_ids = {}
    traveling_ids = [c['booking'].id for c in traveling_cards]
    if traveling_ids:
        rows = BookingMapButton.query.filter(
            BookingMapButton.booking_id.in_(traveling_ids)).all()
        for r in rows:
            booking_map_ids.setdefault(r.booking_id, []).append(r.map_button_id)

    # Search (ref / party name)
    q = (request.args.get('q') or '').strip()
    search_results = []
    if q:
        like = f'%{q}%'
        search_results = Booking.query.filter(
            db.or_(Booking.booking_reference.ilike(like),
                   Booking.party_name.ilike(like),
                   Booking.party_code.ilike(like))
        ).order_by(Booking.arrival_date.desc()).limit(30).all()

    return render_template('admin/trip_updates/index.html',
                           traveling=traveling_cards,
                           range_key=range_key,
                           win_start=win_start, win_end=win_end,
                           today=today, q=q, search_results=search_results,
                           update_counts=counts,
                           map_buttons=map_buttons,
                           booking_map_ids=booking_map_ids)


# ------------------------------------------------------------------
# Admin: manage one booking's updates
# ------------------------------------------------------------------
@bp.route('/booking/<int:booking_id>', methods=['GET'])
@login_required
@admin_required
def manage(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    updates = VoucherUpdate.query.filter_by(booking_id=booking_id) \
        .order_by(VoucherUpdate.update_date.desc(),
                  VoucherUpdate.created_at.desc()).all()
    cur, total = _trip_day_info(booking)
    return render_template('admin/trip_updates/manage.html',
                           booking=booking, updates=updates,
                           day_current=cur, day_total=total,
                           today=date.today(),
                           max_images=MAX_IMAGES_PER_UPDATE)


@bp.route('/booking/<int:booking_id>/create', methods=['POST'])
@login_required
@admin_required
def create(booking_id):
    booking = Booking.query.get_or_404(booking_id)

    title = (request.form.get('title') or '').strip()
    message = (request.form.get('message') or '').strip()
    date_str = (request.form.get('update_date') or '').strip()
    if not title:
        flash('กรุณากรอกหัวข้อ', 'warning')
        return redirect(url_for('trip_updates.manage', booking_id=booking_id))
    try:
        update_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        update_date = date.today()

    files = [f for f in request.files.getlist('images') if f and f.filename]
    if len(files) > MAX_IMAGES_PER_UPDATE:
        flash(f'อัปโหลดได้สูงสุด {MAX_IMAGES_PER_UPDATE} รูปต่ออัปเดต', 'warning')
        return redirect(url_for('trip_updates.manage', booking_id=booking_id))
    for f in files:
        if not _allowed(f.filename):
            flash('รองรับเฉพาะไฟล์ jpg, jpeg, png, webp', 'warning')
            return redirect(url_for('trip_updates.manage', booking_id=booking_id))
        if _file_size(f) > MAX_IMAGE_BYTES:
            flash('แต่ละรูปต้องไม่เกิน 8MB', 'warning')
            return redirect(url_for('trip_updates.manage', booking_id=booking_id))

    update = VoucherUpdate(
        booking_id=booking_id, update_date=update_date,
        title=title, message=message,
        created_by=getattr(current_user, 'id', None),
    )
    db.session.add(update)
    db.session.flush()  # get update.id

    img_dir = _updates_dir(booking_id)
    os.makedirs(img_dir, exist_ok=True)
    for order, f in enumerate(files):
        ext = f.filename.rsplit('.', 1)[1].lower()
        stored = f'{uuid.uuid4().hex}.{ext}'
        f.save(os.path.join(img_dir, stored))
        db.session.add(VoucherUpdateImage(
            update_id=update.id, image_path=stored, display_order=order,
        ))

    db.session.commit()
    flash('✅ เพิ่มอัปเดตสำเร็จ', 'success')
    return redirect(url_for('trip_updates.manage', booking_id=booking_id))


@bp.route('/bulk-create', methods=['POST'])
@login_required
@admin_required
def bulk_create():
    """Post one update to many selected bookings at once."""
    booking_ids = [int(b) for b in request.form.getlist('booking_ids') if b.isdigit()]
    if not booking_ids:
        flash('กรุณาเลือกอย่างน้อย 1 กรุ๊ป', 'warning')
        return redirect(url_for('trip_updates.index'))

    title = (request.form.get('title') or '').strip()
    message = (request.form.get('message') or '').strip()
    date_str = (request.form.get('update_date') or '').strip()
    purge_old = request.form.get('purge_old') == 'on'
    update_maps = request.form.get('update_maps') == 'on'
    map_ids = [int(m) for m in request.form.getlist('map_ids') if m.isdigit()]
    if not title:
        flash('กรุณากรอกหัวข้อ', 'warning')
        return redirect(url_for('trip_updates.index'))
    try:
        update_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        update_date = date.today()

    files = [f for f in request.files.getlist('images') if f and f.filename]
    if len(files) > MAX_IMAGES_PER_UPDATE:
        flash(f'อัปโหลดได้สูงสุด {MAX_IMAGES_PER_UPDATE} รูปต่ออัปเดต', 'warning')
        return redirect(url_for('trip_updates.index'))

    # Read each uploaded file once so it can be written to every selected booking.
    payloads = []  # list of (ext, bytes)
    for f in files:
        if not _allowed(f.filename):
            flash('รองรับเฉพาะไฟล์ jpg, jpeg, png, webp', 'warning')
            return redirect(url_for('trip_updates.index'))
        if _file_size(f) > MAX_IMAGE_BYTES:
            flash('แต่ละรูปต้องไม่เกิน 8MB', 'warning')
            return redirect(url_for('trip_updates.index'))
        payloads.append((f.filename.rsplit('.', 1)[1].lower(), f.read()))

    bookings = Booking.query.filter(Booking.id.in_(booking_ids)).all()
    created = 0
    for booking in bookings:
        if purge_old:
            _purge_booking_updates(booking.id)
        if update_maps:
            _set_booking_maps(booking.id, map_ids)
        update = VoucherUpdate(
            booking_id=booking.id, update_date=update_date,
            title=title, message=message,
            created_by=getattr(current_user, 'id', None),
        )
        db.session.add(update)
        db.session.flush()
        img_dir = _updates_dir(booking.id)
        os.makedirs(img_dir, exist_ok=True)
        for order, (ext, data) in enumerate(payloads):
            stored = f'{uuid.uuid4().hex}.{ext}'
            with open(os.path.join(img_dir, stored), 'wb') as fh:
                fh.write(data)
            db.session.add(VoucherUpdateImage(
                update_id=update.id, image_path=stored, display_order=order,
            ))
        created += 1

    db.session.commit()
    suffix = ' (ลบของเก่าแล้ว)' if purge_old else ''
    if update_maps:
        suffix += ' + ตั้งค่า Voucher Maps'
    flash(f'✅ โพสต์อัปเดตให้ {created} กรุ๊ปสำเร็จ{suffix}', 'success')
    return redirect(url_for('trip_updates.index'))


@bp.route('/update/<int:update_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_publish(update_id):
    update = VoucherUpdate.query.get_or_404(update_id)
    update.is_published = not update.is_published
    db.session.commit()
    flash('อัปเดตสถานะการแสดงผลแล้ว', 'success')
    return redirect(url_for('trip_updates.manage', booking_id=update.booking_id))


@bp.route('/update/<int:update_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_update(update_id):
    update = VoucherUpdate.query.get_or_404(update_id)
    booking_id = update.booking_id
    for img in update.images:
        _remove_image_files(booking_id, img.image_path)
    db.session.delete(update)
    db.session.commit()
    flash('🗑️ ลบอัปเดตสำเร็จ', 'success')
    return redirect(url_for('trip_updates.manage', booking_id=booking_id))


@bp.route('/image/<int:image_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_image(image_id):
    img = VoucherUpdateImage.query.get_or_404(image_id)
    booking_id = img.update.booking_id
    _remove_image_files(booking_id, img.image_path)
    db.session.delete(img)
    db.session.commit()
    flash('🗑️ ลบรูปสำเร็จ', 'success')
    return redirect(url_for('trip_updates.manage', booking_id=booking_id))


# ------------------------------------------------------------------
# Admin: image preview (login-gated)
# ------------------------------------------------------------------
@bp.route('/image/<int:image_id>')
@login_required
@admin_required
def serve_image(image_id):
    img = VoucherUpdateImage.query.get_or_404(image_id)
    booking_id = img.update.booking_id
    if request.args.get('thumb') == '1':
        res = ensure_thumbnail(booking_id, img.image_path)
        if res:
            return send_from_directory(res[0], res[1], max_age=604800)
    img_dir = _updates_dir(booking_id)
    if not os.path.isfile(os.path.join(img_dir, img.image_path)):
        abort(404)
    return send_from_directory(img_dir, img.image_path, max_age=604800)
