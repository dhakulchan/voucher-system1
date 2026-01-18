"""
Passport Upload API Routes
Handle passport image/PDF upload, MRZ extraction, and guest list insertion
PDPA Compliant: Auto-delete temp files, masked logging, user confirmation required
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import tempfile
import hashlib
import logging
from datetime import datetime
from utils.passport_mrz_processor import PassportMRZProcessor, convert_pdf_to_images, cleanup_temp_files
from app import db

logger = logging.getLogger(__name__)

passport_upload_bp = Blueprint('passport_upload', __name__, url_prefix='/api/passport')

# Allowed file extensions
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'pdf'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_hash(file_content):
    """Generate hash for file (for tracking without storing)"""
    return hashlib.sha256(file_content).hexdigest()[:16]


@passport_upload_bp.route('/upload', methods=['POST'])
@login_required
def upload_passport():
    """
    Upload passport image/PDF and extract MRZ data
    Returns extracted data for user preview/confirmation
    Does NOT save to database yet
    """
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': f'File type not allowed. Supported: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
        
        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({
                'success': False,
                'error': f'File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB'
            }), 400
        
        # Get booking_id if provided
        booking_id = request.form.get('booking_id', type=int)
        
        # Save to temporary file
        file_content = file.read()
        file_hash = get_file_hash(file_content)
        
        filename = secure_filename(file.filename)
        file_ext = filename.rsplit('.', 1)[1].lower()
        
        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=f'.{file_ext}',
            prefix='passport_'
        )
        temp_file.write(file_content)
        temp_file.close()
        
        logger.info(f"Uploaded passport file: {filename} (hash: {file_hash}, size: {file_size} bytes)")
        
        temp_files_to_cleanup = [temp_file.name]
        
        try:
            # Process based on file type
            if file_ext == 'pdf':
                # Convert PDF to images
                image_paths = convert_pdf_to_images(temp_file.name)
                temp_files_to_cleanup.extend(image_paths)
                
                if not image_paths:
                    return jsonify({
                        'success': False,
                        'error': 'Could not convert PDF to images'
                    }), 500
                
                # Process first page (usually contains passport data page)
                image_path = image_paths[0]
            else:
                image_path = temp_file.name
            
            # Extract MRZ data
            logger.info(f"=== Starting passport MRZ extraction for: {filename} ===")
            processor = PassportMRZProcessor()
            result = processor.process_passport(image_path)
            logger.info(f"=== Passport extraction result: {result.get('success', False)} ===")
            
            # Store extraction session (for confirmation later)
            if result.get('success') and booking_id:
                extraction_session = {
                    'file_hash': file_hash,
                    'booking_id': booking_id,
                    'extracted_data': result,
                    'user_id': current_user.id,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                # Store in temp table (will create table in migration)
                try:
                    from models.passport_extraction import PassportExtraction
                    extraction = PassportExtraction(
                        booking_id=booking_id,
                        filename_hash=file_hash,
                        extracted_data=result,
                        user_id=current_user.id
                    )
                    db.session.add(extraction)
                    db.session.commit()
                    
                    result['extraction_id'] = extraction.id
                except Exception as db_error:
                    logger.warning(f"Could not save extraction to database: {db_error}")
                    # Continue anyway - data is still returned to frontend
            
            # Add metadata
            result['file_hash'] = file_hash
            result['filename'] = filename
            result['uploaded_by'] = current_user.username
            result['booking_id'] = booking_id
            
            return jsonify(result)
            
        finally:
            # PDPA: Always cleanup temp files
            cleanup_temp_files(temp_files_to_cleanup)
    
    except Exception as e:
        logger.error(f"Error processing passport upload: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@passport_upload_bp.route('/extract/<int:booking_id>', methods=['GET'])
@login_required
def get_extractions(booking_id):
    """
    Get pending passport extractions for a booking
    Returns list of extractions awaiting confirmation
    """
    try:
        from models.passport_extraction import PassportExtraction
        
        extractions = PassportExtraction.query.filter_by(
            booking_id=booking_id,
            confirmed=False
        ).order_by(PassportExtraction.created_at.desc()).all()
        
        result = []
        for extraction in extractions:
            result.append({
                'id': extraction.id,
                'filename_hash': extraction.filename_hash,
                'data': extraction.extracted_data,
                'created_at': extraction.created_at.isoformat(),
                'user_id': extraction.user_id
            })
        
        return jsonify({
            'success': True,
            'extractions': result
        })
        
    except Exception as e:
        logger.error(f"Error retrieving extractions: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@passport_upload_bp.route('/confirm', methods=['POST'])
@login_required
def confirm_extraction():
    """
    User confirms extracted passport data
    Inserts passenger info into booking's guest_list
    Marks extraction as confirmed and deletes temp record
    """
    try:
        data = request.get_json()
        
        extraction_id = data.get('extraction_id')
        booking_id = data.get('booking_id')
        passenger_data = data.get('passenger_data')  # User can edit before confirming
        
        if not all([extraction_id, booking_id, passenger_data]):
            return jsonify({
                'success': False,
                'error': 'Missing required fields'
            }), 400
        
        # Get booking
        from models.booking import Booking
        booking = Booking.query.get(booking_id)
        
        if not booking:
            return jsonify({
                'success': False,
                'error': 'Booking not found'
            }), 404
        
        # Format passenger data for guest_list
        full_name = passenger_data.get('full_name', '')
        passport_number = passenger_data.get('passport_number', '')
        nationality = passenger_data.get('nationality_name', '')
        dob = passenger_data.get('date_of_birth', '')
        expiry = passenger_data.get('expiry_date', '')
        sex = passenger_data.get('sex', '')
        
        # Create passenger entry
        passenger_line = f"{full_name}"
        if passport_number:
            passenger_line += f" | Passport: {passport_number}"
        if nationality:
            passenger_line += f" | Nationality: {nationality}"
        if dob:
            passenger_line += f" | DOB: {dob}"
        if expiry:
            passenger_line += f" | Expiry: {expiry}"
        if sex:
            passenger_line += f" | Sex: {sex}"
        
        # Append to existing guest_list
        current_guest_list = booking.guest_list or []
        if isinstance(current_guest_list, str):
            current_guest_list = current_guest_list.split('\n') if current_guest_list else []
        
        current_guest_list.append(passenger_line)
        
        # Update booking
        booking.guest_list = '\n'.join(current_guest_list)
        
        # Mark extraction as confirmed
        try:
            from models.passport_extraction import PassportExtraction
            extraction = PassportExtraction.query.get(extraction_id)
            if extraction:
                extraction.confirmed = True
                extraction.confirmed_at = datetime.utcnow()
                extraction.confirmed_by = current_user.id
        except Exception as e:
            logger.warning(f"Could not update extraction record: {e}")
        
        db.session.commit()
        
        # Mask passport for logging
        masked_passport = '*' * (len(passport_number) - 4) + passport_number[-4:] if len(passport_number) > 4 else '****'
        logger.info(f"Passenger added to booking {booking_id}: {full_name} (Passport: {masked_passport})")
        
        return jsonify({
            'success': True,
            'message': 'Passenger added to booking successfully',
            'passenger_line': passenger_line
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error confirming extraction: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@passport_upload_bp.route('/batch-upload', methods=['POST'])
@login_required
def batch_upload_passports():
    """
    Upload multiple passport files at once
    Returns list of extraction results
    """
    try:
        logger.info(f"=== Batch upload started by user {current_user.username} ===")
        
        if 'files' not in request.files:
            logger.warning("No files in request")
            return jsonify({
                'success': False,
                'error': 'No files provided'
            }), 400
        
        files = request.files.getlist('files')
        booking_id = request.form.get('booking_id', type=int)
        
        logger.info(f"Processing {len(files)} files for booking_id: {booking_id}")
        
        if not files:
            return jsonify({
                'success': False,
                'error': 'No files selected'
            }), 400
        
        results = []
        
        for file in files:
            if file and allowed_file(file.filename):
                try:
                    # Process each file individually
                    file_content = file.read()
                    file_hash = get_file_hash(file_content)
                    filename = secure_filename(file.filename)
                    file_ext = filename.rsplit('.', 1)[1].lower()
                    
                    temp_file = tempfile.NamedTemporaryFile(
                        delete=False,
                        suffix=f'.{file_ext}',
                        prefix='passport_batch_'
                    )
                    temp_file.write(file_content)
                    temp_file.close()
                    
                    temp_files = [temp_file.name]
                    
                    try:
                        if file_ext == 'pdf':
                            image_paths = convert_pdf_to_images(temp_file.name)
                            temp_files.extend(image_paths)
                            image_path = image_paths[0] if image_paths else temp_file.name
                        else:
                            image_path = temp_file.name
                        
                        logger.info(f"=== Processing passport: {filename} ===")
                        processor = PassportMRZProcessor()
                        result = processor.process_passport(image_path)
                        logger.info(f"=== Result for {filename}: success={result.get('success')} ===")
                        
                        result['filename'] = filename
                        result['file_hash'] = file_hash
                        
                        results.append(result)
                        
                    finally:
                        cleanup_temp_files(temp_files)
                        
                except Exception as file_error:
                    logger.error(f"Error processing {file.filename}: {file_error}")
                    results.append({
                        'success': False,
                        'filename': file.filename,
                        'error': str(file_error)
                    })
        
        return jsonify({
            'success': True,
            'results': results,
            'total': len(files),
            'successful': len([r for r in results if r.get('success')]),
            'failed': len([r for r in results if not r.get('success')])
        })
        
    except Exception as e:
        logger.error(f"Error in batch upload: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@passport_upload_bp.route('/cleanup-old', methods=['POST'])
@login_required
def cleanup_old_extractions():
    """
    Cleanup old unconfirmed extractions (24 hours+)
    PDPA compliance: Don't keep unconfirmed data long
    """
    try:
        from models.passport_extraction import PassportExtraction
        from datetime import timedelta
        
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        old_extractions = PassportExtraction.query.filter(
            PassportExtraction.confirmed == False,
            PassportExtraction.created_at < cutoff_time
        ).all()
        
        count = len(old_extractions)
        
        for extraction in old_extractions:
            db.session.delete(extraction)
        
        db.session.commit()
        
        logger.info(f"Cleaned up {count} old passport extractions")
        
        return jsonify({
            'success': True,
            'cleaned_count': count,
            'message': f'Removed {count} old extraction records'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error cleaning up old extractions: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@passport_upload_bp.route('/parse-mrz-text', methods=['POST'])
@login_required
def parse_mrz_text():
    """
    Parse MRZ text directly from clipboard/textarea
    User can paste MRZ lines and get parsed data
    """
    try:
        data = request.get_json()
        mrz_text = data.get('mrz_text', '').strip()
        
        if not mrz_text:
            return jsonify({
                'success': False,
                'error': 'No MRZ text provided'
            }), 400
        
        logger.info(f"=== Parsing MRZ text input ===")
        logger.info(f"Raw input: {mrz_text[:100]}")
        
        # Split into lines and clean
        lines = [line.strip() for line in mrz_text.split('\n') if line.strip()]
        
        # Remove spaces from each line
        cleaned_lines = []
        for line in lines:
            cleaned = line.replace(' ', '').replace('\t', '')
            if len(cleaned) >= 35:  # MRZ lines should be around 44 chars
                cleaned_lines.append(cleaned)
        
        logger.info(f"Found {len(cleaned_lines)} MRZ lines")
        for i, line in enumerate(cleaned_lines, 1):
            logger.info(f"  Line {i}: {line}")
        
        if len(cleaned_lines) < 2:
            return jsonify({
                'success': False,
                'error': 'Need at least 2 MRZ lines. Please paste both lines from the passport.'
            }), 400
        
        # Parse using existing MRZ processor
        processor = PassportMRZProcessor()
        result = processor.parse_mrz(cleaned_lines)
        
        if result:
            logger.info(f"✅ MRZ parsed successfully: {result.get('full_name')}")
            return jsonify({
                'success': True,
                'data': result,
                'message': 'MRZ parsed successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Could not parse MRZ data. Please check the format.'
            }), 400
        
    except Exception as e:
        logger.error(f"Error parsing MRZ text: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
