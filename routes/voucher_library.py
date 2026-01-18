from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_login import login_required, current_user
from models.voucher_album import VoucherAlbum
from extensions import db
from werkzeug.utils import secure_filename
from PIL import Image
import os
from datetime import datetime

voucher_library_bp = Blueprint('voucher_library', __name__)

# Configuration
UPLOAD_FOLDER = 'static/uploads/voucher_albums'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB in bytes

def ensure_upload_folder():
    """Ensure upload folder exists"""
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_image_size(file):
    """Validate image file size"""
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)  # Reset file pointer
    return file_size <= MAX_FILE_SIZE, file_size

@voucher_library_bp.route('/list')
@login_required
def list_albums():
    """Display list of voucher albums"""
    page = request.args.get('page', 1, type=int)
    per_page = 12  # Show 12 images per page
    
    # Get all albums ordered by newest first
    pagination = VoucherAlbum.query.order_by(VoucherAlbum.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    albums = pagination.items
    
    return render_template('voucher_library/list.html', 
                         albums=albums,
                         pagination=pagination)

@voucher_library_bp.route('/upload', methods=['POST'])
@login_required
def upload():
    """Upload new voucher album image"""
    try:
        # Validate form data
        title = request.form.get('title', '').strip()
        remarks = request.form.get('remarks', '').strip()
        
        if not title:
            return jsonify({'success': False, 'error': 'Title is required'}), 400
        
        # Check if file is present
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No image file provided'}), 400
        
        file = request.files['image']
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Invalid file type. Allowed: PNG, JPG, JPEG, GIF, WEBP'}), 400
        
        # Validate file size
        is_valid_size, file_size = validate_image_size(file)
        if not is_valid_size:
            return jsonify({'success': False, 'error': f'File size exceeds 2MB limit (size: {round(file_size/(1024*1024), 2)}MB)'}), 400
        
        # Ensure upload folder exists
        ensure_upload_folder()
        
        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        original_filename = secure_filename(file.filename)
        filename = f"{timestamp}_{original_filename}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        # Save file
        file.save(filepath)
        
        # Create database record
        album = VoucherAlbum(
            title=title,
            remarks=remarks,
            image_path=filepath,
            file_size=file_size
        )
        
        db.session.add(album)
        db.session.commit()
        
        flash('Voucher album image uploaded successfully!', 'success')
        return jsonify({'success': True, 'album_id': album.id})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@voucher_library_bp.route('/edit/<int:album_id>', methods=['POST'])
@login_required
def edit(album_id):
    """Edit voucher album details"""
    try:
        album = VoucherAlbum.query.get_or_404(album_id)
        
        # Update title and remarks
        title = request.form.get('title', '').strip()
        remarks = request.form.get('remarks', '').strip()
        
        if not title:
            return jsonify({'success': False, 'error': 'Title is required'}), 400
        
        album.title = title
        album.remarks = remarks
        
        # Check if new image is uploaded
        if 'image' in request.files and request.files['image'].filename != '':
            file = request.files['image']
            
            if not allowed_file(file.filename):
                return jsonify({'success': False, 'error': 'Invalid file type'}), 400
            
            # Validate file size
            is_valid_size, file_size = validate_image_size(file)
            if not is_valid_size:
                return jsonify({'success': False, 'error': f'File size exceeds 2MB limit'}), 400
            
            # Delete old file
            if os.path.exists(album.image_path):
                try:
                    os.remove(album.image_path)
                except:
                    pass
            
            # Save new file
            ensure_upload_folder()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            original_filename = secure_filename(file.filename)
            filename = f"{timestamp}_{original_filename}"
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            
            album.image_path = filepath
            album.file_size = file_size
        
        db.session.commit()
        
        flash('Voucher album updated successfully!', 'success')
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@voucher_library_bp.route('/delete/<int:album_id>', methods=['POST'])
@login_required
def delete(album_id):
    """Delete voucher album"""
    try:
        album = VoucherAlbum.query.get_or_404(album_id)
        
        # Delete file from filesystem
        if os.path.exists(album.image_path):
            try:
                os.remove(album.image_path)
            except Exception as e:
                print(f"Warning: Could not delete file {album.image_path}: {e}")
        
        # Delete database record
        db.session.delete(album)
        db.session.commit()
        
        flash('Voucher album deleted successfully!', 'success')
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@voucher_library_bp.route('/get/<int:album_id>')
@login_required
def get_album(album_id):
    """Get voucher album details for editing"""
    try:
        album = VoucherAlbum.query.get_or_404(album_id)
        return jsonify({'success': True, 'album': album.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# API endpoint for fetching albums list (for multi-select in voucher page)
@voucher_library_bp.route('/api/list')
@login_required
def api_list_albums():
    """API endpoint to get all voucher albums for selection"""
    try:
        albums = VoucherAlbum.query.order_by(VoucherAlbum.created_at.desc()).all()
        return jsonify({
            'success': True,
            'albums': [album.to_dict() for album in albums]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
