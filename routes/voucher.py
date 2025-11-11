from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify, session, current_app
from flask_login import login_required, current_user
from models.booking import Booking
from models.customer import Customer
from extensions import db

# Import sharing models with error handling
try:
    from models.voucher_sharing import VoucherFile, VoucherLink
except ImportError:
    VoucherFile = None
    VoucherLink = None
from datetime import datetime
import os
import time
from werkzeug.utils import secure_filename
from PIL import Image as PILImage
import io
import hmac
import hashlib
import base64
from datetime import timedelta
from utils.datetime_utils import utc_now, utc_ts

try:
    from services.pdf_image import pdf_to_png_bytes_list, pdf_page_to_png_bytes, pdf_page_count
except Exception as e:  # fallback if import fails
    # Log root cause so admins can see why image rendering is unavailable (e.g. PyMuPDF wheel unsupported on this Python version)
    import logging, traceback
    _PDF_IMAGE_IMPORT_ERROR = f"{type(e).__name__}: {e}"
    logging.getLogger(__name__).error("PDF image module import failed: %s", _PDF_IMAGE_IMPORT_ERROR)
    logging.getLogger(__name__).debug("Traceback for PDF image import failure:\n%s", traceback.format_exc())
    pdf_to_png_bytes_list = None
    pdf_page_to_png_bytes = None
    pdf_page_count = None
else:
    _PDF_IMAGE_IMPORT_ERROR = None

voucher_bp = Blueprint('voucher', __name__)

def ensure_directories():
    """Ensure required directories exist with proper permissions"""
    dirs = [
        'static',
        'static/generated', 
        'static/uploads',
        'static/uploads/voucher_images'
    ]
    
    for dir_path in dirs:
        try:
            os.makedirs(dir_path, exist_ok=True)
            os.chmod(dir_path, 0o755)
        except Exception as e:
            current_app.logger.error(f'Failed to create directory {dir_path}: {e}')

# เรียกใช้เมื่อเริ่ม blueprint
try:
    ensure_directories()
except:
    pass  # ไม่ให้ error ตอน import

# Use absolute path for PNG cache directory in WSGI environment
def _get_png_cache_dir():
    # Production server path
    production_path = '/opt/bitnami/apache/htdocs/static/generated/png_cache'
    if os.path.exists('/opt/bitnami/apache/htdocs'):
        return production_path
    
    # Development path
    basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(basedir, 'static', 'generated', 'png_cache')

PNG_CACHE_DIR = _get_png_cache_dir()
try:
    os.makedirs(PNG_CACHE_DIR, exist_ok=True)
    os.chmod(PNG_CACHE_DIR, 0o755)  # Ensure proper permissions
    print(f"✅ PNG cache directory ready: {PNG_CACHE_DIR}")
except Exception as e:
    print(f"❌ PNG cache directory error: {e}")

def _ensure_pdf_image_loaded():  # pragma: no cover (diagnostic helper)
    """Attempt lazy import of pdf image helpers if previously failed at module import time.
    Updates globals and _PDF_IMAGE_IMPORT_ERROR.
    """
    global pdf_to_png_bytes_list, pdf_page_to_png_bytes, pdf_page_count, _PDF_IMAGE_IMPORT_ERROR
    if pdf_to_png_bytes_list is not None:
        return True
    try:
        from services.pdf_image import pdf_to_png_bytes_list as _l1, pdf_page_to_png_bytes as _l2, pdf_page_count as _l3
        pdf_to_png_bytes_list, pdf_page_to_png_bytes, pdf_page_count = _l1, _l2, _l3
        _PDF_IMAGE_IMPORT_ERROR = None
        current_app.logger.info('Lazy-loaded PDF image module successfully')
        return True
    except Exception as e:  # noqa
        import traceback
        _PDF_IMAGE_IMPORT_ERROR = f"{type(e).__name__}: {e}"
        current_app.logger.error('Lazy load pdf_image failed: %s', _PDF_IMAGE_IMPORT_ERROR)
        current_app.logger.debug('Lazy load traceback:\n%s', traceback.format_exc())
        return False

@voucher_bp.route('/image-module-status')
def voucher_image_module_status():
    """Diagnostic endpoint for PDF->PNG backend.
    Returns JSON: { available: bool, reason?: str }
    The 'reason' field only appears when unavailable.
    """
    ok = _ensure_pdf_image_loaded()
    payload = {'available': ok}
    if not ok and '_PDF_IMAGE_IMPORT_ERROR' in globals():
        payload['reason'] = _PDF_IMAGE_IMPORT_ERROR
    return jsonify(payload)

@voucher_bp.route('/image-env-debug')
def voucher_image_env_debug():  # pragma: no cover
    import sys, pkgutil
    mods = [m.name for m in pkgutil.iter_modules() if m.name.startswith('fitz') or m.name.startswith('pymupdf')]
    return jsonify({
        'exe': sys.executable,
        'version': sys.version,
        'fitz_loaded': 'fitz' in sys.modules,
        'fitz_spec': True if __import__('importlib.util').util.find_spec('fitz') else False,
        'available': pdf_to_png_bytes_list is not None,
        'modules_found': mods,
        'import_error': globals().get('_PDF_IMAGE_IMPORT_ERROR')
    })

def _voucher_png_cache_key(booking, scale: int) -> str:
    base_dt = booking.updated_at or booking.created_at or utc_now()
    ts = int(base_dt.timestamp())
    return f"b{booking.id}_t{ts}_s{scale}"

def _voucher_png_cache_path(booking, page_index: int, scale: int) -> str:
    key = _voucher_png_cache_key(booking, scale)
    return os.path.join(PNG_CACHE_DIR, f"{key}_p{page_index+1}.png")

def _ensure_voucher_png_cached(booking, pdf_bytes: bytes, page_index: int, scale: int, zoom: float):
    path = _voucher_png_cache_path(booking, page_index, scale)
    if os.path.exists(path):
        return path
    # generate single page
    if pdf_page_to_png_bytes is None:
        return None
    data = pdf_page_to_png_bytes(pdf_bytes, page_index, zoom=zoom)
    if not data:
        return None
    try:
        with open(path, 'wb') as fh:
            fh.write(data)
    except Exception:
        pass
    return path if os.path.exists(path) else None

def cleanup_png_cache(max_age_hours: int = 24):
    import time
    cutoff = time.time() - max_age_hours*3600
    removed = 0
    try:
        for fname in os.listdir(PNG_CACHE_DIR):
            fpath = os.path.join(PNG_CACHE_DIR, fname)
            try:
                if os.path.isfile(fpath) and os.path.getmtime(fpath) < cutoff:
                    os.remove(fpath); removed += 1
            except Exception:
                continue
    except Exception:
        pass
    return removed

@voucher_bp.route('/png-cache/cleanup')
@login_required
def trigger_png_cache_cleanup():
    hours = request.args.get('hours','24')
    try:
        hours_int = max(1, min(168, int(hours)))
    except ValueError:
        hours_int = 24
    removed = cleanup_png_cache(hours_int)
    return jsonify({'success': True, 'removed': removed, 'hours': hours_int})

def _sign_voucher_image_token(secret: str, booking, expires_minutes: int = 60) -> str:
    exp = int((utc_now() + timedelta(minutes=expires_minutes)).timestamp())
    # Use booking ID and creation time (more stable) instead of updated_at
    ts_base = int((booking.created_at or utc_now()).timestamp())
    base = f"{booking.id}:{ts_base}:{exp}".encode()
    sig = hmac.new(secret.encode(), base, hashlib.sha256).digest()
    token = base64.urlsafe_b64encode(base + b"." + sig).decode().rstrip('=')
    return token

def _verify_voucher_image_token(secret: str, token: str, booking) -> bool:
    try:
        # Fix base64 padding
        pad = '=' * (-len(token) % 4)
        raw = base64.urlsafe_b64decode(token + pad)
        
        # Split at last dot to separate base data from signature
        try:
            base, sig = raw.rsplit(b'.',1)
        except ValueError:
            current_app.logger.warning(f'Token verification failed: invalid token format')
            return False
            
        # Decode base data
        try:
            parts = base.decode('utf-8').split(':')
        except UnicodeDecodeError as e:
            current_app.logger.warning(f'Token verification failed: UTF-8 decode error: {str(e)}')
            return False
            
        if len(parts) != 3:
            current_app.logger.warning(f'Token verification failed: invalid parts count {len(parts)}')
            return False
        bid, ts, exp = parts
        if int(bid) != booking.id:
            current_app.logger.warning(f'Token verification failed: booking ID mismatch {bid} != {booking.id}')
            return False
        # Use creation timestamp (more stable) instead of updated_at
        cur_ts = int((booking.created_at or utc_now()).timestamp())
        token_ts = int(ts)
        if token_ts != cur_ts:
            current_app.logger.warning(f'Token verification failed: timestamp mismatch {token_ts} != {cur_ts} (booking created_at mismatch)')
            return False
        current_time = int(utc_now().timestamp())
        token_exp = int(exp)
        if token_exp < current_time:
            current_app.logger.warning(f'Token verification failed: token expired {token_exp} < {current_time}')
            return False
        expected = hmac.new(secret.encode(), base, hashlib.sha256).digest()
        is_valid = hmac.compare_digest(expected, sig)
        if not is_valid:
            current_app.logger.warning(f'Token verification failed: signature mismatch')
        return is_valid
    except Exception as e:
        current_app.logger.warning(f'Token verification failed: exception {str(e)}')
        return False

@voucher_bp.route('/test')
def test_list():
    """Test voucher list without login requirement"""
    # Get filter parameters
    status_filter = request.args.get('status', '')
    voucher_type_filter = request.args.get('voucher_type', '')
    search = request.args.get('search', '')
    date_from = request.args.get('date_from', '')
    
    # Build query to get all bookings that have vouchered status
    query = Booking.query.filter(Booking.status == 'vouchered')
    
    if status_filter:
        # Filter based on booking status (since vouchers are tied to bookings)
        query = query.filter(Booking.status == status_filter)
    
    if search:
        query = query.join(Customer).filter(
            db.or_(
                Customer.name.contains(search),
                Customer.email.contains(search),
                Booking.booking_reference.contains(search)
            )
        )
    
    vouchers = query.order_by(Booking.created_at.desc()).all()
    
    # Calculate stats for the dashboard - match main list route
    stats = {
        'active': Booking.query.filter(Booking.status == 'vouchered').count(),
        'used': 0,
        'expired': 0,
    }
    
    # For testing, let's use English template which is correctly structured
    try:
        print(f"DEBUG: Rendering template with {len(vouchers)} vouchers and stats {stats}")
        return render_template('voucher/list_en.html', vouchers=vouchers, stats=stats, now=datetime.now)
    except Exception as e:
        # Return simple error message for debugging
        print(f"DEBUG: Template error: {e}")
        return f"Error rendering template: {str(e)}"

@voucher_bp.route('/')
@voucher_bp.route('/list', endpoint='list')
@login_required
def list_vouchers():  # renamed from list to avoid shadowing built-in list
    """List all vouchers (only vouchered status)"""
    status_filter = request.args.get('status', '')
    voucher_type_filter = request.args.get('voucher_type', '')  # currently unused
    search = request.args.get('search', '')
    date_from = request.args.get('date_from', '')

    # Only bookings that have vouchered status
    query = Booking.query.filter(
        Booking.status == 'vouchered'
    )

    if search:
        query = query.join(Customer).filter(
            db.or_(
                Customer.first_name.contains(search),
                Customer.last_name.contains(search),
                Customer.email.contains(search),
                Booking.booking_reference.contains(search)
            )
        )

    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            query = query.filter(Booking.created_at >= date_from_obj)
        except ValueError:
            pass

    vouchers = query.order_by(Booking.created_at.desc()).all()

    # If no vouchered bookings exist, show empty list instead of redirecting
    stats = {
        'active': Booking.query.filter(Booking.status == 'vouchered').count(),
        'used': 0,
        'expired': 0,
    }

    language = session.get('language', 'en')
    template_name = f'voucher/list_{language}.html'
    try:
        return render_template(template_name, vouchers=vouchers, stats=stats, now=datetime.now)
    except:
        return render_template('voucher/list_en.html', vouchers=vouchers, stats=stats, now=datetime.now)

@voucher_bp.route('/<int:id>')
@login_required
def view(id):
    """Unified voucher view (English only while Thai disabled)"""
    booking = Booking.query.get_or_404(id)
    if booking.status not in ['confirmed', 'quoted', 'paid', 'vouchered', 'completed']:
        flash('Booking must be confirmed before viewing voucher', 'error')
        return redirect(url_for('booking.view', id=id))
    
    # Sync ARNO/QTNO from Invoice Ninja before displaying
    try:
        from services.booking_invoice import BookingInvoiceService
        bis = BookingInvoiceService()
        if bis.sync_booking_numbers(booking):
            db.session.commit()
    except Exception as e:
        # Non-fatal; continue rendering even if sync fails
        current_app.logger.warning(f'Failed to sync booking numbers for voucher view: {e}')
    
    try:
        from models.vendor import Supplier, Vendor
        vendors = Vendor.query.filter_by(active=True).order_by(Vendor.name.asc()).all()  # legacy variable
        suppliers = suppliers_list = Supplier.query.filter_by(active=True).order_by(Supplier.name.asc()).all()
    except Exception:
        vendors = []
        suppliers = []
    
    # Get voucher images for template
    voucher_images = booking.get_voucher_images()
    
    return render_template('voucher/unified_voucher.html', 
                         booking=booking, 
                         vendors=vendors, 
                         suppliers=suppliers,
                         voucher_images=voucher_images)

@voucher_bp.route('/<int:id>', methods=['POST'])
@login_required
def update(id):
    """Handle image upload + supplier only quick-save (multipart form fallback). JS rows save still via API."""
    booking = Booking.query.get_or_404(id)
    allowed_statuses = ['confirmed', 'quoted', 'paid', 'vouchered', 'completed']
    if booking.status not in allowed_statuses:
        flash('Invalid status for update', 'error')
        return redirect(url_for('voucher.view', id=id))
    file = request.files.get('voucher_image')
    if file and file.filename:
        _process_voucher_image_upload(file, booking)
    # Optional supplier select in form fallback
    sid = request.form.get('supplier_id')
    if sid:
        try:
            from models.vendor import Supplier
            sup = Supplier.query.get(int(sid))
            if sup and sup.active:
                booking.supplier_id = sup.id
                booking.vendor_id = sup.id
        except Exception:
            pass
    db.session.commit()
    flash('Updated', 'success')
    return redirect(url_for('voucher.view', id=id))

def _process_voucher_image_upload(file, booking):
    cfg = current_app.config
    max_size = cfg.get('VOUCHER_IMAGE_MAX_SIZE', 1_000_000)
    allowed = set(cfg.get('VOUCHER_IMAGE_ALLOWED_EXT', []))
    filename = secure_filename(file.filename)
    if '.' not in filename:
        current_app.logger.warning('Invalid image: no extension'); return None
    ext = filename.rsplit('.',1)[-1].lower()
    if allowed and ext not in allowed:
        current_app.logger.warning('Invalid image type'); return None
    file.seek(0, os.SEEK_END); sz = file.tell(); file.seek(0)
    if sz > max_size:
        current_app.logger.warning('Image too large (>1MB)'); return None
    rel_dir = 'uploads/voucher_images'
    # Use adaptive path for development vs production
    abs_dir = '/opt/bitnami/apache/htdocs/static/uploads/voucher_images' if os.path.exists('/opt/bitnami') else 'static/uploads/voucher_images'
    os.makedirs(abs_dir, exist_ok=True)
    new_name = f"booking_{booking.id}_{int(time.time())}.{ext}"
    abs_path = os.path.join(abs_dir, new_name)
    # Save temp then resize/compress if needed
    file.save(abs_path)
    try:
        with PILImage.open(abs_path) as im:
            im_format = im.format
            max_w = cfg.get('VOUCHER_IMAGE_MAX_WIDTH', 1600)
            if im.width > max_w:
                ratio = max_w / float(im.width)
                new_size = (max_w, int(im.height * ratio))
                im = im.resize(new_size, PILImage.LANCZOS)
            # Re-save compressed (if JPEG / WEBP)
            if im_format in {'JPEG','JPG','WEBP','PNG'}:
                quality = cfg.get('VOUCHER_IMAGE_QUALITY', 85)
                im.save(abs_path, optimize=True, quality=quality)
    except Exception as e:
        current_app.logger.warning(f'Image post-process failed: {e}')
    
    # Return relative path for multi-image system
    relative_path = f"{rel_dir}/{new_name}?v={int(time.time())}"
    return relative_path

@voucher_bp.route('/<int:id>/delete-image', methods=['POST'])
@login_required
def delete_image(id):
    booking = Booking.query.get_or_404(id)
    data = request.get_json() or {}
    image_id = data.get('image_id')
    
    try:
        # Handle multi-image deletion
        if image_id and image_id != 'main':
            current_images = booking.get_voucher_images()
            image_to_delete = None
            
            # Find the image to delete
            for img in current_images:
                if img.get('id') == image_id:
                    image_to_delete = img
                    break
            
            if image_to_delete:
                # Remove from filesystem
                image_path = image_to_delete.get('path', '')
                if image_path:
                    clean_path = image_path.split('?')[0]  # Remove query params
                    abs_path = os.path.join('static', clean_path)
                    if os.path.exists(abs_path):
                        os.remove(abs_path)
                
                # Remove from list
                current_images = [img for img in current_images if img.get('id') != image_id]
                booking.set_voucher_images(current_images)
                db.session.commit()
                return jsonify({'success': True})
        
        # For backward compatibility, handle main image deletion
        elif not image_id or image_id == 'main':
            path_rel = booking.voucher_image_path or ''
            if path_rel:
                # strip any query param
                clean_rel = path_rel.split('?')[0]
                abs_path = os.path.join('static', clean_rel)
                try:
                    if os.path.exists(abs_path):
                        os.remove(abs_path)
                except Exception as e:
                    current_app.logger.warning(f'Failed removing voucher image: {e}')
                booking.voucher_image_path = None
                db.session.commit()
                return jsonify({'success': True})
        
        return jsonify({'success': False, 'error': 'Image not found'})
        
    except Exception as e:
        current_app.logger.error(f'Error deleting image: {e}')
        return jsonify({'success': False, 'error': str(e)})

@voucher_bp.route('/<int:id>/upload-images', methods=['POST'])
@login_required
def upload_images(id):
    """AJAX multi-image upload returning JSON."""
    booking = Booking.query.get_or_404(id)
    
    # More lenient status check
    allowed_statuses = ['confirmed', 'quoted', 'paid', 'vouchered', 'completed']
    if booking.status not in allowed_statuses:
        current_app.logger.warning(f'Image upload denied: booking {id} has status {booking.status}, allowed: {allowed_statuses}')
        return jsonify({'success': False, 'error': f'Invalid booking status: {booking.status}'}), 400
    
    files = request.files.getlist('voucher_images')
    if not files or len(files) == 0:
        current_app.logger.warning(f'Image upload: No files received for booking {id}')
        return jsonify({'success': False, 'error': 'No files provided'}), 400
    
    uploaded_images = []
    max_size = 1048576  # 1MB
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    
    for file in files:
        if not file or not file.filename:
            current_app.logger.warning(f'Skipping empty file in upload for booking {id}')
            continue
            
        # Check file extension
        if not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
            current_app.logger.warning(f'Invalid file type for booking {id}: {file.filename}')
            return jsonify({'success': False, 'error': f'Invalid file type: {file.filename}. Allowed: {", ".join(allowed_extensions)}'}), 400
            
        # Check file size
        file.seek(0, 2)  # Seek to end
        size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if size > max_size:
            current_app.logger.warning(f'File too large for booking {id}: {file.filename} ({size} bytes)')
            return jsonify({'success': False, 'error': f'File too large: {file.filename} ({size} bytes, max: {max_size})'}), 400
        
        try:
            # Process each image and add to voucher_images list
            relative_path = _process_voucher_image_upload(file, booking)
            
            if relative_path:
                # Add to voucher_images list
                current_images = booking.get_voucher_images()
                image_id = f'img_{int(time.time())}_{len(current_images)}'
                
                # Extract filename and query parameter separately
                clean_path = relative_path.split('?')[0]
                query_param = relative_path.split('?')[1] if '?' in relative_path else ''
                base_url = url_for('static', filename=clean_path)
                if query_param:
                    base_url += f'?{query_param}'
                
                image_data = {
                    'id': image_id,
                    'url': base_url,
                    'filename': file.filename,
                    'path': relative_path
                }
                
                current_images.append(image_data)
                booking.set_voucher_images(current_images)
                
                uploaded_images.append(image_data)
                current_app.logger.info(f'Successfully uploaded image for booking {id}: {file.filename}')
            else:
                current_app.logger.error(f'Failed to process image for booking {id}: {file.filename}')
                return jsonify({'success': False, 'error': f'Failed to process image: {file.filename}'}), 500
                
        except Exception as e:
            current_app.logger.error(f'Upload exception for booking {id}, file {file.filename}: {str(e)}')
            return jsonify({'success': False, 'error': f'Upload failed for {file.filename}: {str(e)}'}), 500
    
    if uploaded_images:
        try:
            db.session.commit()
            current_app.logger.info(f'Successfully uploaded {len(uploaded_images)} images for booking {id}')
        except Exception as e:
            current_app.logger.error(f'Database commit failed for booking {id}: {str(e)}')
            return jsonify({'success': False, 'error': 'Database save failed'}), 500
    
    return jsonify({'success': True, 'images': uploaded_images})

@voucher_bp.route('/<int:id>/reorder-images', methods=['POST'])
@login_required
def reorder_images(id):
    """AJAX endpoint to save image order."""
    booking = Booking.query.get_or_404(id)
    data = request.get_json()
    image_order = data.get('image_order', [])
    
    # Store image order in booking metadata or separate table
    # For now, just return success - this would need proper implementation
    # based on your multi-image storage strategy
    
    return jsonify({'success': True})

@voucher_bp.route('/<int:id>/upload-image', methods=['POST'])
@login_required
def upload_image(id):
    """AJAX image upload returning JSON (non-flash)."""
    booking = Booking.query.get_or_404(id)
    allowed_statuses = ['confirmed', 'quoted', 'paid', 'vouchered', 'completed']
    if booking.status not in allowed_statuses:
        return jsonify({'success': False, 'error': f'Invalid booking status: {booking.status}'}), 400
    file = request.files.get('voucher_image')
    if not file or not file.filename:
        return jsonify({'success': False, 'error': 'No file'}), 400
    # Capture old path for cleanup handled in helper implicitly by overwrite semantics
    _process_voucher_image_upload(file, booking)
    db.session.commit()
    if booking.voucher_image_path:
        # Build full static URL with existing cache-bust param preserved
        stored = booking.voucher_image_path
        # stored like uploads/voucher_images/booking_1_...jpg?v=123
        fname, q = (stored.split('?',1) + [''])[:2]
        base_url = url_for('static', filename=fname)
        image_url = base_url + (f'?{q}' if q else '')
        return jsonify({'success': True, 'image_url': image_url})
    return jsonify({'success': False, 'error': 'Upload failed'}), 500

@voucher_bp.route('/<int:id>/view-only')
@login_required
def view_only(id):
    """Read-only voucher view (no editing controls)."""
    booking = Booking.query.get_or_404(id)
    if booking.status not in ['confirmed', 'quoted', 'paid', 'vouchered', 'completed']:
        flash('Booking must be confirmed before viewing voucher', 'error')
        return redirect(url_for('booking.view', id=id))
    # Sync numbers (non-fatal if fails) similar to edit view
    try:
        from services.booking_invoice import BookingInvoiceService
        bis = BookingInvoiceService()
        if bis.sync_booking_numbers(booking):
            db.session.commit()
    except Exception as e:
        current_app.logger.warning(f'Failed to sync booking numbers (view-only): {e}')
    return render_template('voucher/view_voucher.html', booking=booking)

@voucher_bp.route('/generate/<int:booking_id>')
@login_required
def generate(booking_id):
    """Generate voucher (mark or prepare)"""
    booking = Booking.query.get_or_404(booking_id)
    if booking.status != 'confirmed':
        flash('การจองต้องได้รับการยืนยันก่อนสร้างใบบัตร', 'error')
        return redirect(url_for('booking.view', id=booking_id))
    flash('สร้างใบบัตรสำเร็จ', 'success')
    return redirect(url_for('voucher.view', id=booking_id))

@voucher_bp.route('/generate-and-view/<int:booking_id>')
@login_required
def generate_and_view(booking_id):
    """Generate voucher, update status to vouchered, log activity, and redirect to view-only"""
    from models import Booking
    from datetime import datetime
    
    booking = Booking.query.get_or_404(booking_id)
    
    # If already vouchered, redirect to view-only directly
    if booking.status == 'vouchered':
        current_app.logger.info(f'Booking {booking_id} already vouchered, redirecting to view-only')
        flash('Voucher already generated! Redirecting to voucher view.', 'info')
        return redirect(url_for('voucher.view_only', id=booking_id))
    
    # Check if booking can be vouchered
    if booking.status not in ['paid', 'confirmed', 'quoted']:
        flash('Booking must be paid, confirmed, or quoted before generating voucher', 'error')
        return redirect(url_for('booking.view', id=booking_id))
    
    try:
        # Update booking status to vouchered
        old_status = booking.status
        booking.status = 'vouchered'
        
        # Add activity log
        try:
            from models.activity_log import ActivityLog
            activity = ActivityLog(
                booking_id=booking_id,
                action='status_change',
                description=f'Status changed from {old_status} to vouchered via Generate Voucher',
                user_id=None,  # You might want to add current user ID here
                created_at=datetime.utcnow()
            )
            db.session.add(activity)
        except Exception as log_error:
            current_app.logger.warning(f'Could not create activity log: {log_error}')
        
        # Commit changes
        db.session.commit()
        
        current_app.logger.info(f'✅ Booking {booking_id} status updated to vouchered')
        flash('Voucher generated successfully! Status updated to Vouchered.', 'success')
        
        # Redirect to view-only voucher page
        return redirect(url_for('voucher.view_only', id=booking_id))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'❌ Error generating voucher for booking {booking_id}: {e}')
        flash(f'Error generating voucher: {str(e)}', 'error')
        return redirect(url_for('booking.view', id=booking_id))

@voucher_bp.route('/download/<int:id>')
@login_required
def download(id):
    """Download voucher PDF"""
    booking = Booking.query.get_or_404(id)
    
    # แก้ไข: เพิ่ม status ที่ถูกต้อง
    if booking.status not in ['confirmed', 'quoted', 'paid', 'vouchered', 'completed']:
        flash('Booking must be confirmed before downloading voucher', 'error')
        return redirect(url_for('booking.view', id=id))
    
    try:
        from services.pdf_generator import PDFGenerator
        pdf_generator = PDFGenerator()
        
        # ✅ เพิ่มการสร้าง Quote PDF สำหรับ status "quoted"
        if booking.status == 'quoted':
            # สร้าง Quote PDF ตามรูปแบบในภาพ
            pdf_file = pdf_generator.generate_quote_document(booking)
            filename = pdf_file  # ใช้ชื่อไฟล์ที่ generator สร้างให้
        elif booking.booking_type == 'tour':
            pdf_file = pdf_generator.generate_tour_voucher(booking)
            filename = pdf_file  # ใช้ชื่อไฟล์ที่ generator สร้างให้ (Tour_voucher_v2_*)
        else:
            pdf_file = pdf_generator.generate_mpv_booking(booking)
            filename = pdf_file  # ใช้ชื่อไฟล์ที่ generator สร้างให้
        
        # Check if PDF file exists
        pdf_path = f'static/generated/{pdf_file}'
        if not os.path.exists(pdf_path):
            flash('ไม่สามารถสร้างไฟล์ PDF ได้', 'error')
            return redirect(url_for('voucher.view', id=id))
        
        return send_file(pdf_path, 
                        as_attachment=True, 
                        download_name=filename,
                        mimetype='application/pdf')
        
    except Exception as e:
        current_app.logger.error(f'Error generating PDF for booking {id}: {str(e)}')
        flash(f'เกิดข้อผิดพลาดในการสร้าง PDF: {str(e)}', 'error')
        return redirect(url_for('voucher.view', id=id))

@voucher_bp.route('/<int:id>/pdf')
@login_required
def generate_pdf(id):
    booking = Booking.query.get_or_404(id)
    if booking.status not in ['confirmed', 'quoted', 'paid', 'vouchered', 'completed']:
        flash('ต้องยืนยันก่อนสร้าง PDF', 'error')
        return redirect(url_for('voucher.view', id=id))
    
    try:
        from services.pdf_generator import PDFGenerator
        pdf_generator = PDFGenerator()
        
        # ✅ เพิ่มการสร้าง Quote PDF สำหรับ status "quoted"
        if booking.status == 'quoted':
            # สร้าง Quote PDF ตามรูปแบบในภาพ
            pdf_file = pdf_generator.generate_quote_document(booking)
            filename = pdf_file  # ใช้ชื่อไฟล์ที่ generator สร้างให้
        elif booking.booking_type == 'tour':
            # ✅ ใช้ TourVoucherWeasyPrintV2 สำหรับ Tour Voucher (HTML Template)
            from services.tour_voucher_weasyprint_v2 import TourVoucherWeasyPrintV2
            
            # ใช้ TourVoucherWeasyPrintV2 กับ HTML template สำหรับ Tour Voucher
            tour_generator = TourVoucherWeasyPrintV2()
            pdf_file = tour_generator.generate_tour_voucher_v2(booking)
            filename = pdf_file  # ใช้ชื่อไฟล์ที่ generator สร้างให้
        else:
            # booking_type อื่น ๆ ให้ใช้ Service Proposal header
            pdf_file = pdf_generator.generate_mpv_booking(booking)
            filename = pdf_file  # ใช้ชื่อไฟล์ที่ generator สร้างให้
        
        # จัดการ path ให้ถูกต้องตาม generator type
        if booking.booking_type == 'tour':
            # WeasyPrint generator ส่งกลับชื่อไฟล์, ต้องสร้าง full path
            pdf_path = f'static/generated/{pdf_file}'
        else:
            # PDF generator เดิมส่งกลับชื่อไฟล์
            pdf_path = f'static/generated/{pdf_file}'
            
        if not os.path.exists(pdf_path):
            flash('ไม่สามารถสร้างไฟล์ PDF ได้', 'error')
            return redirect(url_for('voucher.view', id=id))
            
        # Fix for compatibility - use attachment_filename instead of download_name for older Flask versions
        try:
            # Try the newer parameter name first
            return send_file(pdf_path, 
                            as_attachment=True, 
                            download_name=filename,
                            mimetype='application/pdf')
        except TypeError:
            # Fall back to older parameter name
            return send_file(pdf_path, 
                            as_attachment=True, 
                            attachment_filename=filename,
                            mimetype='application/pdf')
        
    except Exception as e:
        current_app.logger.error(f'Error generating PDF: {str(e)}')
        flash(f'Error generating PDF: {str(e)}', 'error')
        return redirect(url_for('voucher.view', id=id))

@voucher_bp.route('/<int:id>/quote-pdf')
@login_required
def generate_quote_pdf(id):
    """สร้าง Quote PDF เฉพาะ - ตามรูปแบบในภาพ"""
    booking = Booking.query.get_or_404(id)
    if booking.status not in ['confirmed', 'quoted', 'paid', 'vouchered', 'completed']:
        flash('ต้องยืนยันก่อนสร้าง Quote PDF', 'error')
        return redirect(url_for('voucher.view', id=id))
    
    try:
        from services.pdf_generator import PDFGenerator
        pdf_generator = PDFGenerator()
        
        # สร้าง Quote PDF ตามรูปแบบในภาพ: DHAKUL CHAN TRAVEL SERVICE
        pdf_file = pdf_generator.generate_quote_document(booking)
        
        pdf_path = f'static/generated/{pdf_file}'
        if not os.path.exists(pdf_path):
            flash('ไม่สามารถสร้างไฟล์ Quote PDF ได้', 'error')
            return redirect(url_for('voucher.view', id=id))
            
        return send_file(pdf_path, 
                        as_attachment=True, 
                        download_name=f'quote_{booking.booking_reference}.pdf',
                        mimetype='application/pdf')
        
    except Exception as e:
        current_app.logger.error(f'Error generating Quote PDF: {str(e)}')
        flash(f'Error generating Quote PDF: {str(e)}', 'error')
        return redirect(url_for('voucher.view', id=id))

@voucher_bp.route('/<int:id>/email', methods=['GET', 'POST'])
@login_required
def email_voucher(id):
    """Email tour voucher"""
    booking = Booking.query.get_or_404(id)
    
    if booking.booking_type != 'tour':
        flash('This booking is not a tour voucher', 'error')
        return redirect(url_for('booking.view', id=id))
    
    if request.method == 'POST':
        try:
            recipient_email = request.form.get('email') or booking.customer.email
            subject = request.form.get('subject') or f'Tour Voucher - {booking.booking_reference}'
            message = request.form.get('message') or 'Please find attached your tour voucher.'
            
            from services.email_service import EmailService
            from services.pdf_generator import PDFGenerator
            
            # Generate PDF
            pdf_generator = PDFGenerator()
            pdf_path = pdf_generator.generate_tour_voucher(booking)
            
            # Send email
            email_service = EmailService()
            email_service.send_voucher_email(
                recipient_email=recipient_email,
                subject=subject,
                message=message,
                pdf_path=f'static/generated/{pdf_path}',
                booking=booking
            )
            
            flash(f'Voucher emailed successfully to {recipient_email}!', 'success')
            return redirect(url_for('voucher.view', id=id))
            
        except Exception as e:
            flash(f'Error sending email: {str(e)}', 'error')
    
    return render_template('voucher/email.html', booking=booking)

@voucher_bp.route('/<int:id>/print')
@login_required
def print_voucher(id):
    booking = Booking.query.get_or_404(id)
    allowed_statuses = ['confirmed', 'quoted', 'paid', 'vouchered', 'completed']
    if booking.status not in allowed_statuses:
        flash('ต้องยืนยันก่อนพิมพ์', 'error')
        return redirect(url_for('voucher.view', id=id))
    return redirect(url_for('voucher.view', id=id))

@voucher_bp.route('/<int:id>/qr')
@login_required
def qr_code(id):
    """Generate QR code for voucher"""
    booking = Booking.query.get_or_404(id)
    
    from services.qr_generator import QRGenerator
    qr_generator = QRGenerator()
    
    try:
        qr_path = qr_generator.generate_voucher_qr(booking)
        return send_file(qr_path, mimetype='image/png')
    except Exception as e:
        flash(f'Error generating QR code: {str(e)}', 'error')
        return redirect(url_for('voucher.view', id=id))

@voucher_bp.route('/<int:id>/png')
@login_required
def voucher_png_combined(id):
    """Generate combined PNG (long vertical image) for voucher"""
    booking = Booking.query.get_or_404(id)
    
    # Check PDF image module availability
    if not _ensure_pdf_image_loaded():
        flash('PDF image module unavailable', 'error')
        return redirect(url_for('voucher.view', id=id))
    
    try:
        # Generate PDF bytes
        if booking.booking_type == 'tour':
            from services.tour_voucher_weasyprint_v2 import TourVoucherWeasyPrintV2
            tour_generator = TourVoucherWeasyPrintV2()
            pdf_bytes = tour_generator.generate_tour_voucher_v2_bytes(booking)
        else:
            from services.pdf_generator import PDFGenerator
            gen = PDFGenerator()
            pdf_bytes = gen.generate_tour_voucher_bytes(booking)
        
        if not pdf_bytes:
            flash('PDF generation failed', 'error')
            return redirect(url_for('voucher.view', id=id))
        
        # Generate combined PNG (long vertical image)
        from services.pdf_image import pdf_to_long_png_bytes
        scale = 200  # Default scale
        zoom = scale / 100.0
        combined_png_bytes = pdf_to_long_png_bytes(pdf_bytes, zoom=zoom)
        
        if not combined_png_bytes:
            flash('Combined PNG generation failed', 'error')
            return redirect(url_for('voucher.view', id=id))
        
        # Return PNG file
        import io
        buf = io.BytesIO(combined_png_bytes)
        buf.seek(0)
        return send_file(buf, mimetype='image/png', download_name=f'voucher_{booking.id}_combined.png')
        
    except Exception as e:
        flash(f'Error generating PNG: {str(e)}', 'error')
        return redirect(url_for('voucher.view', id=id))

@voucher_bp.route('/api/<int:id>/status', methods=['POST'])
@login_required
def update_status(id):
    """Update voucher status"""
    booking = Booking.query.get_or_404(id)
    
    try:
        new_status = request.json.get('status')
        if new_status in ['pending', 'confirmed', 'cancelled', 'completed']:
            booking.status = new_status
            db.session.commit()
            return jsonify({'success': True, 'message': f'Status updated to {new_status}'})
        else:
            return jsonify({'success': False, 'message': 'Invalid status'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@voucher_bp.route('/api/<int:id>/rows', methods=['POST'])
@login_required
def save_rows_api(id):
    booking = Booking.query.get_or_404(id)
    # ✅ อนุญาตให้แก้ไขได้ในสถานะ quoted ด้วย
    if booking.status not in ['confirmed', 'quoted', 'paid', 'vouchered', 'completed']:
        return jsonify({'success': False, 'message': 'Invalid status for editing'}), 400
    try:
        data = request.get_json() or {}
        current_app.logger.debug(f"save_rows_api raw data: {data}")
        rows = data.get('rows', [])
        current_app.logger.debug(f"rows type={type(rows)} value={rows}")
        # Use isinstance now that we no longer shadow built-in list
        if not isinstance(rows, list):
            return jsonify({'success': False, 'message': f'Rows must be list, got {type(rows).__name__}'}), 400
        cleaned_rows = []
        for idx, r in enumerate(rows):
            if not isinstance(r, dict):
                return jsonify({'success': False, 'message': f'Row {idx} not dict: {r}'}), 400
            cleaned_rows.append({
                'arrival': r.get('arrival',''),
                'departure': r.get('departure',''),
                'service_by': r.get('service_by',''),
                'type': r.get('type','')
            })
        booking.set_voucher_rows(cleaned_rows)
        desc = data.get('description')
        if isinstance(desc, str):
            booking.description = desc.strip() or None
        fi = data.get('flight_info')
        if isinstance(fi, str):
            booking.flight_info = fi.strip() or None
        gl = data.get('guest_list')
        if isinstance(gl, list):
            booking.set_guest_list([g.strip() for g in gl if isinstance(g,str) and g.strip()])
        
        # Handle voucher images
        vi = data.get('voucher_images')
        current_app.logger.debug(f"voucher_images received: {vi}")
        if isinstance(vi, list):
            current_app.logger.debug(f"Setting voucher_images with {len(vi)} items")
            booking.set_voucher_images(vi)
        else:
            current_app.logger.debug(f"voucher_images not a list or missing: {type(vi)}")

        # ลบ cache PNG voucher ทุกครั้งที่แก้ไขข้อมูล
        try:
            scale_list = [200, 150, 100, 300]  # รองรับหลายขนาด
            page_max = 5  # ลบได้สูงสุด 5 หน้า
            for scale in scale_list:
                for page_index in range(page_max):
                    from routes.voucher import _voucher_png_cache_path
                    cache_path = _voucher_png_cache_path(booking, page_index, scale)
                    if os.path.exists(cache_path):
                        os.remove(cache_path)
        except Exception as e:
            current_app.logger.warning(f'Failed to clear voucher PNG cache: {e}')
        # Supplier persistence
        supplier_id = data.get('supplier_id')
        if supplier_id is not None:
            if supplier_id == '' or supplier_id == 'null':
                booking.supplier_id = None
            else:
                try:
                    sid_int = int(supplier_id)
                    from models.vendor import Supplier  # local import to avoid cycles
                    sup = Supplier.query.get(sid_int)
                    if sup and sup.active:
                        booking.supplier_id = sup.id
                        # legacy mirror
                        booking.vendor_id = sup.id
                    else:
                        return jsonify({'success': False, 'message': 'Invalid supplier'}), 400
                except ValueError:
                    return jsonify({'success': False, 'message': 'Supplier id must be integer'}), 400
        db.session.commit()
        return jsonify({'success': True, 'count': len(cleaned_rows), 'supplier_id': booking.supplier_id})
    except Exception as e:
        import traceback
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e), 'trace': traceback.format_exc()}), 500

@voucher_bp.route('/search')
@login_required
def search():
    """Search vouchers"""
    query = request.args.get('q', '')
    status = request.args.get('status', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    bookings_query = Booking.query.filter(Booking.booking_type == 'tour')
    
    if query:
        bookings_query = bookings_query.filter(
            Booking.booking_reference.contains(query) |
            Booking.customer.has(Customer.name.contains(query))
        )
    
    if status:
        bookings_query = bookings_query.filter(Booking.status == status)
    
    if date_from:
        date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
        bookings_query = bookings_query.filter(Booking.traveling_period_start >= date_from_obj)
    
    if date_to:
        date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
        bookings_query = bookings_query.filter(Booking.traveling_period_end <= date_to_obj)
    
    bookings = bookings_query.order_by(Booking.created_at.desc()).limit(50).all()
    
    return render_template('voucher/search.html', 
                         bookings=bookings,
                         query=query,
                         status=status,
                         date_from=date_from,
                         date_to=date_to)

@voucher_bp.route('/create', methods=['GET','POST'])
@login_required
def create_voucher():
    """Simple create voucher workflow: user enters booking reference then redirect to unified view"""
    if request.method == 'POST':
        ref = (request.form.get('booking_reference') or '').strip()
        if not ref:
            flash('กรุณาใส่รหัสการจอง / Enter booking reference', 'error')
            return redirect(url_for('voucher.create_voucher'))
        booking = Booking.query.filter_by(booking_reference=ref).first()
        if not booking:
            flash(f'ไม่พบการจอง {ref}', 'error')
            return redirect(url_for('voucher.create_voucher'))
        allowed_statuses = ['confirmed', 'quoted', 'paid', 'vouchered', 'completed']
        if booking.status not in allowed_statuses:
            flash('ต้องยืนยันสถานะการจอง (confirmed) ก่อนสร้างใบบัตร', 'error')
            return redirect(url_for('booking.view', id=booking.id))
        return redirect(url_for('voucher.view', id=booking.id))
    # GET
    return render_template('voucher/create.html')

@voucher_bp.route('/<int:id>/image')
@login_required
def voucher_image_png(id):
    """Return voucher PDF rendered to PNG (auth required unless using share route).

    Query params:
      page=N (1-based)  -> single page PNG
      all=1             -> all pages zipped
      scale=200         -> percent scaling (default 200, min 50, max 300)
    Caching: stored under static/generated/png_cache with key by booking.updated_at + scale.
    """
    booking = Booking.query.get_or_404(id)
    allowed_statuses = ['confirmed', 'quoted', 'paid', 'vouchered', 'completed']
    if booking.status not in allowed_statuses:
        return jsonify({'success': False, 'message': f'Invalid booking status: {booking.status}'}), 400
    if not _ensure_pdf_image_loaded():
        return jsonify({'success': False, 'message': 'PDF image module unavailable', 'reason': _PDF_IMAGE_IMPORT_ERROR}), 500
    
    # ✅ ใช้ TourVoucherWeasyPrintV2 สำหรับ Tour Voucher (HTML Template)
    if booking.booking_type == 'tour':
        from services.tour_voucher_weasyprint_v2 import TourVoucherWeasyPrintV2
        tour_generator = TourVoucherWeasyPrintV2()
        pdf_bytes = tour_generator.generate_tour_voucher_v2_bytes(booking)
    else:
        from services.pdf_generator import PDFGenerator
        gen = PDFGenerator()
        pdf_bytes = gen.generate_tour_voucher_bytes(booking)
    
    if not pdf_bytes:
        return jsonify({'success': False, 'message': 'PDF generation failed'}), 500
        
    try:
        scale_param = request.args.get('scale')
        try:
            scale = int(scale_param) if scale_param else 200
        except ValueError:
            scale = 200
        scale = max(50, min(300, scale))
        zoom = scale / 100.0
        # Combined multi-page PNG (single vertical image)
        if request.args.get('combined') == '1':
            from services.pdf_image import pdf_to_long_png_bytes
            combined_png_bytes = pdf_to_long_png_bytes(pdf_bytes, zoom=zoom)
            if not combined_png_bytes:
                return jsonify({'success': False, 'message': 'Combined PNG generation failed'}), 500
            buf = io.BytesIO(combined_png_bytes)
            buf.seek(0)
            return send_file(buf, mimetype='image/png', download_name=f'voucher_{booking.id}_combined.png')
        
        # All pages zipped
        if request.args.get('all') == '1':
            pages_total = pdf_page_count(pdf_bytes)
            if not pages_total:
                return jsonify({'success': False, 'message': 'No pages'}), 500
            import zipfile
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                for p in range(pages_total):
                    cached_path = _ensure_voucher_png_cached(booking, pdf_bytes, p, scale, zoom)
                    if cached_path and os.path.exists(cached_path):
                        with open(cached_path,'rb') as fh:
                            zf.writestr(os.path.basename(cached_path), fh.read())
                    else:
                        # fallback direct render
                        from services.pdf_image import pdf_page_to_png_bytes
                        data = pdf_page_to_png_bytes(pdf_bytes, p, zoom=zoom)
                        zf.writestr(f'voucher_{booking.id}_p{p+1}.png', data)
            zip_buf.seek(0)
            return send_file(zip_buf, mimetype='application/zip', download_name=f'voucher_{booking.id}_images.zip')
        # Single page
        page_param = request.args.get('page', '1')
        try:
            page_index = max(1, int(page_param)) - 1
        except ValueError:
            page_index = 0
        cached_path = _ensure_voucher_png_cached(booking, pdf_bytes, page_index, scale, zoom)
        if cached_path and os.path.exists(cached_path):
            return send_file(cached_path, mimetype='image/png', download_name=os.path.basename(cached_path))
        from services.pdf_image import pdf_page_to_png_bytes
        png_bytes = pdf_page_to_png_bytes(pdf_bytes, page_index, zoom=zoom)
        if not png_bytes:
            return jsonify({'success': False, 'message': 'Invalid page'}), 400
        buf = io.BytesIO(png_bytes)
        buf.seek(0)
        return send_file(buf, mimetype='image/png', download_name=f'voucher_{booking.id}_p{page_index+1}.png')
    except Exception as e:
        current_app.logger.error(f'PNG render failed: {e}')
        return jsonify({'success': False, 'message': 'Render error'}), 500

@voucher_bp.route('/<int:id>/image-share')
def voucher_image_png_public(id):
    """Public (no login) voucher image share route. Requires valid token.

    Params: token, page / all / scale (same semantics as auth route)
    """
    booking = Booking.query.get_or_404(id)
    token = request.args.get('token','')
    secret = current_app.config.get('SECRET_KEY','')
    if not secret or not _verify_voucher_image_token(secret, token, booking):
        return jsonify({'success': False, 'message': 'Invalid token'}), 403
    # Reuse internal logic by temporarily faking login context? Simpler: duplicate minimal part.
    if not _ensure_pdf_image_loaded():
        return jsonify({'success': False, 'message': 'PDF image module unavailable', 'reason': _PDF_IMAGE_IMPORT_ERROR}), 500
    
    # ✅ ใช้ TourVoucherWeasyPrintV2 สำหรับ Tour Voucher (HTML Template)
    if booking.booking_type == 'tour':
        from services.tour_voucher_weasyprint_v2 import TourVoucherWeasyPrintV2
        tour_generator = TourVoucherWeasyPrintV2()
        pdf_bytes = tour_generator.generate_tour_voucher_v2_bytes(booking)
    else:
        from services.pdf_generator import PDFGenerator
        gen = PDFGenerator()
        pdf_bytes = gen.generate_tour_voucher_bytes(booking)
    
    if not pdf_bytes:
        return jsonify({'success': False, 'message': 'PDF generation failed'}), 500
        
    try:
        scale_param = request.args.get('scale')
        try:
            scale = int(scale_param) if scale_param else 200
        except ValueError:
            scale = 200
        scale = max(50, min(300, scale))
        zoom = scale / 100.0
        
        # Combined multi-page PNG (single vertical image)
        if request.args.get('combined') == '1':
            from services.pdf_image import pdf_to_long_png_bytes
            combined_png_bytes = pdf_to_long_png_bytes(pdf_bytes, zoom=zoom)
            if not combined_png_bytes:
                return jsonify({'success': False, 'message': 'Combined PNG generation failed'}), 500
            buf = io.BytesIO(combined_png_bytes)
            buf.seek(0)
            return send_file(buf, mimetype='image/png', download_name=f'voucher_{booking.id}_combined.png')
            buf.seek(0)
            return send_file(buf, mimetype='image/png', download_name=f'voucher_{booking.id}_combined.png')
        
        if request.args.get('all') == '1':
            pages_total = pdf_page_count(pdf_bytes)
            import zipfile
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                for p in range(pages_total):
                    cached_path = _ensure_voucher_png_cached(booking, pdf_bytes, p, scale, zoom)
                    if cached_path and os.path.exists(cached_path):
                        with open(cached_path,'rb') as fh:
                            zf.writestr(os.path.basename(cached_path), fh.read())
                    else:
                        from services.pdf_image import pdf_page_to_png_bytes
                        data = pdf_page_to_png_bytes(pdf_bytes, p, zoom=zoom)
                        zf.writestr(f'voucher_{booking.id}_p{p+1}.png', data)
            zip_buf.seek(0)
            return send_file(zip_buf, mimetype='application/zip', download_name=f'voucher_{booking.id}_images.zip')
        page_param = request.args.get('page', '1')
        try:
            page_index = max(1, int(page_param)) - 1
        except ValueError:
            page_index = 0
        cached_path = _ensure_voucher_png_cached(booking, pdf_bytes, page_index, scale, zoom)
        if cached_path and os.path.exists(cached_path):
            return send_file(cached_path, mimetype='image/png', download_name=os.path.basename(cached_path))
        from services.pdf_image import pdf_page_to_png_bytes
        data = pdf_page_to_png_bytes(pdf_bytes, page_index, zoom=zoom)
        if not data:
            return jsonify({'success': False, 'message': 'Invalid page'}), 400
        buf = io.BytesIO(data); buf.seek(0)
        return send_file(buf, mimetype='image/png', download_name=f'voucher_{booking.id}_p{page_index+1}.png')
    except Exception as e:
        import traceback
        current_app.logger.error(f'Public PNG render failed: {e}')
        current_app.logger.error(f'Traceback: {traceback.format_exc()}')
        return jsonify({'success': False, 'message': 'Render error', 'error': str(e)}), 500

@voucher_bp.route('/<int:id>/share-token', methods=['POST'])
@login_required
def generate_share_token(id):
    """Generate a time-limited public share token for voucher PNG access."""
    booking = Booking.query.get_or_404(id)
    
    # More lenient status check - same as image upload
    allowed_statuses = ['confirmed', 'quoted', 'paid', 'vouchered', 'completed']
    if booking.status not in allowed_statuses:
        current_app.logger.warning(f'Share token denied: booking {id} has status {booking.status}, allowed: {allowed_statuses}')
        return jsonify({'success': False, 'message': f'Invalid booking status: {booking.status}'}), 400
    
    secret = current_app.config.get('SECRET_KEY','')
    if not secret:
        return jsonify({'success': False, 'message': 'Missing secret'}), 500
    try:
        minutes = int(request.json.get('minutes', 60)) if request.is_json else 60
    except Exception:
        minutes = 60
    minutes = max(5, min(24*60, minutes))  # 5 min - 24h
    
    # Use the same token generation method as public booking sharing
    token = booking.generate_secure_token()  # This uses departure_date + 120 days
    
    # Return the new public booking URL format
    from flask import url_for
    public_url = url_for('public.view_booking_secure', token=token, _external=True)
    
    return jsonify({'success': True, 'token': token, 'url': public_url, 'expires_days': 120})

@voucher_bp.route('/debug/pdf/<int:id>')
@login_required
def debug_pdf(id):
    """Debug PDF generation"""
    booking = Booking.query.get_or_404(id)
    
    try:
        from services.pdf_generator import PDFGenerator
        pdf_generator = PDFGenerator()
        
        # ✅ ลองสร้าง PDF ตามสถานะใหม่
        if booking.status == 'quoted':
            pdf_file = pdf_generator.generate_quote_document(booking)
            doc_type = 'Quote Document (DHAKUL CHAN format)'
        elif booking.booking_type == 'tour':
            pdf_file = pdf_generator.generate_tour_voucher(booking)
            doc_type = 'Tour Voucher'
        else:
            pdf_file = pdf_generator.generate_mpv_booking(booking)
            doc_type = 'Service Proposal'
        
        pdf_path = f'static/generated/{pdf_file}'
        
        return jsonify({
            'success': True,
            'booking_id': booking.id,
            'booking_type': booking.booking_type,
            'status': booking.status,
            'document_type': doc_type,
            'pdf_file': pdf_file,
            'pdf_path': pdf_path,
            'file_exists': os.path.exists(pdf_path),
            'file_size': os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0,
            'workflow_step': {
                'confirmed': 'View, Edit, Upload Images, Generate PDF',
                'quoted': 'View/Edit, Download Quote PDF',
                'paid': 'All voucher features', 
                'vouchered': 'All features + sharing',
                'completed': 'Full access + archival'
            }.get(booking.status, 'Unknown status')
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@voucher_bp.route('/debug/quote_view_test/<int:id>')
@login_required 
def debug_quote_view_test(id):
    """Test Quote PDF view functionality"""
    booking = Booking.query.get_or_404(id)
    
    try:
        if booking.status == 'quoted':
            from services.pdf_generator import PDFGenerator
            pdf_generator = PDFGenerator()
            
            # Generate Quote PDF
            pdf_filename = pdf_generator.generate_quote_document(booking)
            pdf_path = f'static/generated/{pdf_filename}'
            
            if os.path.exists(pdf_path):
                # Return PDF directly for viewing
                from flask import send_file
                return send_file(pdf_path, as_attachment=False, download_name=f'quote_{booking.booking_reference}.pdf')
            else:
                return jsonify({
                    'success': False,
                    'error': 'PDF file not found after generation',
                    'pdf_path': pdf_path
                })
        else:
            return jsonify({
                'success': False,
                'error': f'Booking status is {booking.status}, not quoted'
            })
            
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@voucher_bp.route('/debug/quote_pdf/<int:id>')
@login_required
def debug_quote_pdf(id):
    """Debug Quote PDF generation specifically"""
    booking = Booking.query.get_or_404(id)
    
    try:
        from services.quote_pdf_generator import QuotePDFGenerator
        quote_generator = QuotePDFGenerator()
        
        # Generate Quote PDF
        pdf_filename = quote_generator.generate_quote_pdf(booking)
        pdf_path = f'static/generated/quotes/{pdf_filename}'
        
        return jsonify({
            'success': True,
            'booking_id': booking.id,
            'booking_status': booking.status,
            'quote_pdf_filename': pdf_filename,
            'quote_pdf_path': pdf_path,
            'file_exists': os.path.exists(pdf_path),
            'file_size': os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0,
            'quotes_dir_exists': os.path.exists('static/generated/quotes'),
            'message': 'Quote PDF generated successfully using DHAKUL CHAN format'
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc(),
            'booking_id': booking.id,
            'booking_status': booking.status
        })

@voucher_bp.route('/debug/quote_pdf_generate/<int:id>')
@login_required
def debug_quote_pdf_generate(id):
    """Force generate Quote PDF and return details"""
    booking = Booking.query.get_or_404(id)
    
    try:
        from services.pdf_generator import PDFGenerator
        pdf_generator = PDFGenerator()
        
        # Force generate Quote PDF
        pdf_filename = pdf_generator.generate_quote_document(booking)
        pdf_path = f'static/generated/{pdf_filename}'
        
        return jsonify({
            'success': True,
            'booking_id': booking.id,
            'booking_status': booking.status,
            'pdf_filename': pdf_filename,
            'pdf_path': pdf_path,
            'file_exists': os.path.exists(pdf_path),
            'file_size': os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0,
            'message': 'Quote PDF generated via PDFGenerator.generate_quote_document()'
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc(),
            'booking_id': booking.id,
            'booking_status': booking.status
        })

@voucher_bp.route('/debug/directories')
@login_required
def debug_directories():
    """Debug directories and permissions"""
    import stat
    
    dirs_to_check = [
        'static',
        'static/generated',
        'static/generated/quotes',
        'static/uploads',
        'static/uploads/voucher_images'
    ]
    
    results = {}
    for dir_path in dirs_to_check:
        try:
            exists = os.path.exists(dir_path)
            if exists:
                stat_info = os.stat(dir_path)
                results[dir_path] = {
                    'exists': True,
                    'is_dir': os.path.isdir(dir_path),
                    'permissions': oct(stat_info.st_mode)[-3:],
                    'writable': os.access(dir_path, os.W_OK)
                }
            else:
                results[dir_path] = {'exists': False}
        except Exception as e:
            results[dir_path] = {'error': str(e)}
    
    return jsonify(results)

# Email PDF Routes
@voucher_bp.route('/<int:id>/email-pdf', methods=['GET', 'POST'])
@login_required
def email_voucher_pdf(id):
    """Send voucher PDF via email"""
    booking = Booking.query.get_or_404(id)
    
    if request.method == 'POST':
        recipient_email = request.form.get('email', '').strip()
        
        if not recipient_email:
            flash('❌ Email address is required', 'error')
            return redirect(url_for('voucher.email_voucher_pdf', id=id))
        
        try:
            # Generate PDF first
            from services.weasyprint_generator import WeasyPrintGenerator
            generator = WeasyPrintGenerator()
            
            # Prepare booking data dict
            booking_data = {
                'booking_reference': booking.booking_reference,
                'customer_name': booking.customer.full_name if booking.customer else 'N/A',
                'customer_email': booking.customer.email if booking.customer else '',
                'customer_phone': booking.customer.phone if booking.customer else '',
                'adults': booking.adults or 0,
                'children': booking.children or 0,
                'infants': booking.infants or 0,
                'admin_notes': booking.admin_notes or '',
                'manager_memos': booking.manager_memos or '',
                'internal_note': booking.internal_note or ''
            }
            
            # Get products/services
            products = []
            if hasattr(booking, 'products') and booking.products:
                for product in booking.products:
                    # Handle product as object, dict, or str
                    if hasattr(product, 'name'):
                        name = product.name
                        description = getattr(product, 'description', '') or ''
                        price = getattr(product, 'price', 0) or 0
                    elif isinstance(product, dict):
                        name = product.get('name', '')
                        description = product.get('description', '')
                        price = product.get('price', 0)
                    else:
                        name = str(product)
                        description = ''
                        price = 0
                    products.append({
                        'name': name,
                        'description': description,
                        'price': price,
                        'quantity': 1
                    })
            
            # Generate PDF
            pdf_path = generator.generate_service_proposal(booking_data, products)
            
            if pdf_path and os.path.exists(pdf_path):
                # Send email
                from services.email_service import EmailService
                email_service = EmailService()
                email_service.send_voucher_pdf(recipient_email, pdf_path, booking)
                
                # Clean up temporary file
                os.unlink(pdf_path)
                
                flash(f'✅ Voucher PDF sent successfully to {recipient_email}', 'success')
                return redirect(url_for('voucher.view', id=id))
            else:
                flash('❌ Error generating voucher PDF', 'error')
                
        except Exception as e:
            current_app.logger.error(f"Error sending voucher PDF email: {str(e)}")
            flash(f'❌ Error sending email: {str(e)}', 'error')
    
    # GET request - show form
    return render_template('voucher/email_pdf_form.html', 
                         booking=booking, 
                         pdf_type='voucher',
                         action_url=url_for('voucher.email_voucher_pdf', id=id))


# File Sharing API Endpoints
@voucher_bp.route('/api/<int:voucher_id>/files', methods=['POST'])
@login_required
def upload_files(voucher_id):
    """Upload files for voucher sharing"""
    from werkzeug.utils import secure_filename
    import uuid
    
    # Check if sharing models are available
    if not VoucherFile:
        return jsonify({'success': False, 'error': 'File sharing not available'}), 503
    
    booking = Booking.query.get_or_404(voucher_id)
    
    try:
        files = request.files.getlist('files')
        title = request.form.get('title', '')
        uploaded_files = []
        
        # Create upload directory
        upload_dir = os.path.join('static', 'uploads', 'voucher_files')
        os.makedirs(upload_dir, exist_ok=True)
        
        for file in files:
            if file and file.filename:
                # Generate unique filename
                original_filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4()}_{original_filename}"
                file_path = os.path.join(upload_dir, unique_filename)
                
                # Save file
                file.save(file_path)
                
                # Create database record
                voucher_file = VoucherFile(
                    voucher_id=voucher_id,
                    filename=unique_filename,
                    original_filename=original_filename,
                    title=title,
                    file_path=file_path,
                    file_size=os.path.getsize(file_path),
                    mime_type=file.content_type
                )
                
                # Set expiry based on booking
                voucher_file.set_expiry_from_booking(booking)
                
                db.session.add(voucher_file)
                uploaded_files.append(voucher_file.to_dict())
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'files': uploaded_files,
            'message': f'Uploaded {len(uploaded_files)} files successfully'
        })
        
    except Exception as e:
        current_app.logger.error(f'Error uploading files: {e}')
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@voucher_bp.route('/api/<int:voucher_id>/files', methods=['GET'])
@login_required
def get_files(voucher_id):
    """Get files for voucher"""
    
    # Check if sharing models are available
    if not VoucherFile:
        return jsonify({'success': False, 'error': 'File sharing not available'}), 503
    
    booking = Booking.query.get_or_404(voucher_id)
    files = VoucherFile.query.filter_by(voucher_id=voucher_id, is_active=True).all()
    
    # Generate share token if files exist
    share_token = None
    if files:
        share_token = files[0].public_token  # Use first file's token as group token
    
    return jsonify({
        'success': True,
        'files': [f.to_dict() for f in files],
        'share_token': share_token
    })


@voucher_bp.route('/api/<int:voucher_id>/files/<int:file_id>', methods=['DELETE'])
@login_required
def delete_file_api(voucher_id, file_id):
    """Delete a voucher file"""
    
    booking = Booking.query.get_or_404(voucher_id)
    voucher_file = VoucherFile.query.filter_by(id=file_id, voucher_id=voucher_id).first_or_404()
    
    try:
        # Delete physical file
        if os.path.exists(voucher_file.file_path):
            os.remove(voucher_file.file_path)
        
        # Delete database record
        db.session.delete(voucher_file)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'File deleted successfully'})
        
    except Exception as e:
        current_app.logger.error(f'Error deleting file: {e}')
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@voucher_bp.route('/api/<int:voucher_id>/files/<int:file_id>', methods=['PUT'])
@login_required
def update_file_api(voucher_id, file_id):
    """Update file title"""
    
    booking = Booking.query.get_or_404(voucher_id)
    voucher_file = VoucherFile.query.filter_by(id=file_id, voucher_id=voucher_id).first_or_404()
    
    try:
        data = request.get_json()
        title = data.get('title', '').strip()
        
        # Update title
        voucher_file.title = title if title else None
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'File title updated successfully',
            'file': voucher_file.to_dict()
        })
        
    except Exception as e:
        current_app.logger.error(f'Error updating file title: {e}')
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@voucher_bp.route('/download/<int:file_id>')
@login_required
def download_file(file_id):
    """Download a voucher file"""
    
    voucher_file = VoucherFile.query.get_or_404(file_id)
    
    if not voucher_file.is_active or voucher_file.is_expired():
        flash('File not available or expired', 'error')
        return redirect(url_for('voucher.view', id=voucher_file.voucher_id))
    
    try:
        # Determine download filename with proper extension
        import os
        if hasattr(voucher_file, 'title') and voucher_file.title:
            # Get file extension from original filename
            _, original_ext = os.path.splitext(voucher_file.original_filename)
            # Check if title already has an extension
            title_name, title_ext = os.path.splitext(voucher_file.title)
            if title_ext:
                # Title already has extension, use as is
                download_filename = voucher_file.title
            else:
                # Title doesn't have extension, append from original
                download_filename = voucher_file.title + original_ext
        else:
            # No title, use original filename
            download_filename = voucher_file.original_filename
            
        return send_file(
            voucher_file.file_path,
            as_attachment=True,
            download_name=download_filename
        )
    except Exception as e:
        current_app.logger.error(f'Error downloading file: {e}')
        flash('Error downloading file', 'error')
        return redirect(url_for('voucher.view', id=voucher_file.voucher_id))


# External Links API Endpoints
@voucher_bp.route('/api/<int:voucher_id>/links', methods=['POST'])
@login_required
def add_link(voucher_id):
    """Add external link for voucher"""
    
    booking = Booking.query.get_or_404(voucher_id)
    data = request.get_json()
    
    try:
        voucher_link = VoucherLink(
            voucher_id=voucher_id,
            url=data['url'],
            title=data['title'],
            description=data.get('description', '')
        )
        
        db.session.add(voucher_link)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'link': voucher_link.to_dict(),
            'message': 'Link added successfully'
        })
        
    except Exception as e:
        current_app.logger.error(f'Error adding link: {e}')
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@voucher_bp.route('/api/<int:voucher_id>/links', methods=['GET'])
@login_required
def get_links(voucher_id):
    """Get links for voucher"""
    
    booking = Booking.query.get_or_404(voucher_id)
    links = VoucherLink.query.filter_by(voucher_id=voucher_id, is_active=True).all()
    
    # Generate share token if links exist
    share_token = None
    if links:
        share_token = links[0].public_token  # Use first link's token as group token
    
    return jsonify({
        'success': True,
        'links': [l.to_dict() for l in links],
        'share_token': share_token
    })


@voucher_bp.route('/api/<int:voucher_id>/links/<int:link_id>', methods=['DELETE'])
@login_required
def delete_link_api(voucher_id, link_id):
    """Delete a voucher link"""
    
    booking = Booking.query.get_or_404(voucher_id)
    voucher_link = VoucherLink.query.filter_by(id=link_id, voucher_id=voucher_id).first_or_404()
    
    try:
        db.session.delete(voucher_link)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Link deleted successfully'})
        
    except Exception as e:
        current_app.logger.error(f'Error deleting link: {e}')
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@voucher_bp.route('/api/<int:voucher_id>/links/<int:link_id>', methods=['PUT'])
@login_required
def update_link_api(voucher_id, link_id):
    """Update link title and description"""
    
    booking = Booking.query.get_or_404(voucher_id)
    voucher_link = VoucherLink.query.filter_by(id=link_id, voucher_id=voucher_id).first_or_404()
    
    try:
        data = request.get_json()
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        
        # Update fields
        if title:
            voucher_link.title = title
        if 'description' in data:  # Allow empty description
            voucher_link.description = description if description else None
            
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Link updated successfully',
            'link': voucher_link.to_dict()
        })
        
    except Exception as e:
        current_app.logger.error(f'Error updating link: {e}')
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# Public Access Endpoints
@voucher_bp.route('/public/<token>/files')
def public_files(token):
    """Public access to voucher files"""
    
    # Check if sharing models are available
    if not VoucherFile:
        return render_template('voucher/public_not_found.html'), 404
    
    try:
        # Find files by token
        files = VoucherFile.query.filter_by(public_token=token, is_active=True).all()
    except Exception as e:
        current_app.logger.error(f'Error querying files with token {token}: {e}')
        return render_template('voucher/public_not_found.html'), 404
    
    if not files:
        return render_template('voucher/public_not_found.html'), 404
    
    # Check if expired
    active_files = [f for f in files if not f.is_expired()]
    
    if not active_files:
        return render_template('voucher/public_expired.html'), 410
    
    # Get booking info
    try:
        booking = active_files[0].booking
    except Exception as e:
        current_app.logger.error(f'Error accessing booking relationship: {e}')
        return render_template('voucher/public_not_found.html'), 404
    
    return render_template('voucher/public_files.html', 
                         files=active_files, 
                         booking=booking,
                         token=token)


@voucher_bp.route('/public/<token>/links')
def public_links(token):
    """Public access to voucher links"""
    
    # Check if sharing models are available
    if not VoucherLink:
        return render_template('voucher/public_not_found.html'), 404
    
    try:
        # Find links by token
        links = VoucherLink.query.filter_by(public_token=token, is_active=True).all()
    except Exception as e:
        current_app.logger.error(f'Error querying links with token {token}: {e}')
        return render_template('voucher/public_not_found.html'), 404
    
    if not links:
        return render_template('voucher/public_not_found.html'), 404
    
    # Get booking info
    try:
        booking = links[0].booking
    except Exception as e:
        current_app.logger.error(f'Error accessing booking relationship: {e}')
        return render_template('voucher/public_not_found.html'), 404
    
    return render_template('voucher/public_links.html', 
                         links=links, 
                         booking=booking,
                         token=token)


# Cleanup expired files
@voucher_bp.route('/cleanup-expired-files')
@login_required
def cleanup_expired_files():
    """Cleanup expired voucher files"""
    from datetime import datetime
    
    try:
        expired_files = VoucherFile.query.filter(
            VoucherFile.expires_at < datetime.utcnow(),
            VoucherFile.is_active == True
        ).all()
        
        deleted_count = 0
        for file in expired_files:
            try:
                # Delete physical file
                if os.path.exists(file.file_path):
                    os.remove(file.file_path)
                
                # Mark as inactive
                file.is_active = False
                deleted_count += 1
                
            except Exception as e:
                current_app.logger.error(f'Error deleting expired file {file.id}: {e}')
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Cleaned up {deleted_count} expired files'
        })
        
    except Exception as e:
        current_app.logger.error(f'Error in cleanup: {e}')
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
