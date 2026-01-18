"""
Queue Management Routes
API และหน้าจอต่างๆ สำหรับระบบจัดการคิว
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, flash
from flask_login import login_required, current_user
from datetime import datetime, date
from models.queue import Queue
from models.queue_media import QueueMedia
from models.customer import Customer
from models.booking import Booking
from app import db
from werkzeug.utils import secure_filename
import logging
import os

queue_bp = Blueprint('queue', __name__, url_prefix='/queue')
logger = logging.getLogger(__name__)

# Upload configuration
UPLOAD_FOLDER = 'static/queue_media'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'webm', 'ogg'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_queue_number():
    """Generate unique queue number for today (Format: YYMMNN - 6 digits total)"""
    today = date.today()
    prefix = today.strftime('%y%m')  # YYMM (4 digits: YY + MM)
    
    # Find last queue number for today
    last_queue = Queue.query.filter(
        Queue.queue_number.like(f'{prefix}%')
    ).order_by(Queue.id.desc()).first()
    
    if last_queue:
        # Extract last 2 digits for running number
        last_num = int(last_queue.queue_number[-2:])  # Last 2 digits
        new_num = last_num + 1
    else:
        new_num = 0
    
    return f'{prefix}{new_num:02d}'  # 6-digit total: YYMMNN (26 + 01 + 00)



# ============================================================
# PUBLIC PAGES (ลูกค้าใช้งาน)
# ============================================================

@queue_bp.route('/welcome')
def welcome():
    """Public landing page with QR code"""
    return render_template('queue/index_public.html')


@queue_bp.route('/join')
def get_queue_form():
    """Mobile-friendly queue registration form"""
    return render_template('queue/join.html')


@queue_bp.route('/track/<queue_number>')
def track(queue_number):
    """Customer tracking page - accessible from QR code"""
    queue = Queue.query.filter_by(queue_number=queue_number).first_or_404()
    return render_template('queue/track.html', queue=queue)


# ============================================================
# STAFF PAGES (พนักงานใช้งาน - ต้อง Login)
# ============================================================

@queue_bp.route('/')
@login_required
def index():
    """Queue management dashboard - requires login"""
    today = date.today()
    queues = Queue.query.filter(
        db.func.date(Queue.created_at) == today
    ).order_by(Queue.created_at.desc()).all()
    
    return render_template('queue/dashboard.html', queues=queues)


@queue_bp.route('/display')
@login_required
def display():
    """Display screen for TV/Monitor - requires login"""
    return render_template('queue/display.html')


@queue_bp.route('/display/<token>')
def display_public(token):
    """Public display screen with token access - no login required"""
    from models.display_token import DisplayToken
    
    # Validate token
    display_token = DisplayToken.query.filter_by(token=token).first()
    
    if not display_token:
        return render_template('errors/404.html', message='Invalid display token'), 404
    
    if not display_token.is_valid():
        return render_template('errors/403.html', message='This display token has expired or is inactive'), 403
    
    # Record token access
    display_token.record_access()
    
    # Render the same display template
    return render_template('queue/display.html', token=token, public_mode=True)


@queue_bp.route('/counter/<counter_id>')
@login_required
def counter(counter_id):
    """Counter/booth staff interface - requires login and counter assignment"""
    # Check if user is assigned to this counter
    user_counter = current_user.assigned_counter
    
    # Admin can access any counter
    if not current_user.is_admin:
        if user_counter is None:
            flash('You have not been assigned to any counter. Please contact your administrator.', 'warning')
            return redirect(url_for('queue.index_public'))
        
        if str(user_counter) != str(counter_id):
            flash(f'Access denied. You are assigned to Counter {user_counter}.', 'danger')
            return redirect(url_for('queue.counter', counter_id=user_counter))
    
    return render_template('queue/counter.html', counter_id=counter_id)


@queue_bp.route('/history')
@login_required
def history():
    """Queue history page with date filtering - requires login"""
    return render_template('queue/history.html')


@queue_bp.route('/media-manager')
@login_required
def media_manager():
    """Media manager page for managing display content - requires login"""
    return render_template('queue/media_manager.html')


@queue_bp.route('/token-manager')
@login_required
def token_manager():
    """Token manager page for managing display tokens - requires login"""
    return render_template('queue/token_manager.html')


@queue_bp.route('/my-counter')
@login_required
def my_counter():
    """Redirect user to their assigned counter"""
    if current_user.assigned_counter:
        return redirect(url_for('queue.counter', counter_id=current_user.assigned_counter))
    else:
        flash('You have not been assigned to any counter yet. Please contact your administrator.', 'warning')
        return redirect(url_for('queue.index_public'))


@queue_bp.route('/counter-assignments')
@login_required
def counter_assignments():
    """Admin page to assign counters to users"""
    if not current_user.is_admin:
        flash('Access denied. Admin only.', 'danger')
        return redirect(url_for('main.dashboard'))
    return render_template('queue/counter_assignments.html')


# ============================================================
# API ENDPOINTS
# ============================================================

@queue_bp.route('/api/queues', methods=['GET'])
def get_queues():
    """Get all queues for today or by date range"""
    try:
        # Get date parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if start_date and end_date:
            # Filter by date range
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            queues = Queue.query.filter(
                db.func.date(Queue.created_at) >= start,
                db.func.date(Queue.created_at) <= end
            ).order_by(Queue.created_at.desc()).all()
        else:
            # Default to today
            today = date.today()
            queues = Queue.query.filter(
                db.func.date(Queue.created_at) == today
            ).order_by(Queue.created_at.asc()).all()
        
        return jsonify({
            'success': True,
            'queues': [q.to_dict() for q in queues],
            'waiting_count': len([q for q in queues if q.status == 'waiting']),
            'serving_count': len([q for q in queues if q.status == 'serving']),
            'completed_count': len([q for q in queues if q.status == 'completed'])
        })
    except Exception as e:
        logger.error(f"Error getting queues: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@queue_bp.route('/api/queue', methods=['POST'])
def create_queue():
    """Create new queue with customer information"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('customer_name'):
            return jsonify({'success': False, 'error': 'Customer name is required'}), 400
        if not data.get('customer_phone'):
            return jsonify({'success': False, 'error': 'Customer phone is required'}), 400
        if not data.get('service_type'):
            return jsonify({'success': False, 'error': 'Service type is required'}), 400
        
        queue = Queue(
            queue_number=generate_queue_number(),
            customer_name=data['customer_name'].strip(),
            customer_phone=data['customer_phone'].strip(),
            customer_email=data.get('customer_email', '').strip() if data.get('customer_email') else None,
            service_type=data['service_type'],
            priority=data.get('priority', 0),
            notes=data.get('notes')
        )
        
        db.session.add(queue)
        db.session.commit()
        
        logger.info(f"✅ New queue created: {queue.queue_number} for {queue.customer_name}")
        
        return jsonify({
            'success': True,
            'queue': queue.to_dict(),
            'tracking_url': f'/queue/track/{queue.queue_number}'
        })
    except Exception as e:
        logger.error(f"❌ Error creating queue: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@queue_bp.route('/api/queue/<int:queue_id>/status', methods=['GET'])
def get_queue_status(queue_id):
    """Get real-time queue status for customer tracking"""
    try:
        queue = Queue.query.get_or_404(queue_id)
        
        # Calculate position in queue
        position = 0
        waiting_before = 0
        
        if queue.status == 'waiting':
            today = date.today()
            # Count queues created before this one that are still waiting
            earlier_queues = Queue.query.filter(
                db.func.date(Queue.created_at) == today,
                Queue.status == 'waiting',
                Queue.created_at < queue.created_at
            ).order_by(Queue.priority.desc(), Queue.created_at.asc()).all()
            
            waiting_before = len(earlier_queues)
            position = waiting_before + 1
        
        return jsonify({
            'success': True,
            'queue': queue.to_dict(),
            'position': position,
            'waiting_before': waiting_before
        })
    except Exception as e:
        logger.error(f"Error getting queue status: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@queue_bp.route('/api/queue/<int:queue_id>/call', methods=['POST'])
def call_queue(queue_id):
    """Call customer to counter"""
    try:
        data = request.get_json()
        queue = Queue.query.get_or_404(queue_id)
        
        queue.status = 'serving'
        queue.called_at = datetime.utcnow()
        queue.counter = data.get('counter')
        
        db.session.commit()
        
        logger.info(f"📢 Queue {queue.queue_number} called to counter {queue.counter}")
        
        # TODO: Send SMS/Email notification to customer
        
        return jsonify({
            'success': True,
            'queue': queue.to_dict()
        })
    except Exception as e:
        logger.error(f"Error calling queue: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@queue_bp.route('/api/queue/<int:queue_id>/complete', methods=['POST'])
def complete_queue(queue_id):
    """Mark queue as completed"""
    try:
        queue = Queue.query.get_or_404(queue_id)
        
        queue.status = 'completed'
        queue.completed_at = datetime.utcnow()
        
        db.session.commit()
        
        logger.info(f"✅ Queue {queue.queue_number} completed")
        
        return jsonify({
            'success': True,
            'queue': queue.to_dict()
        })
    except Exception as e:
        logger.error(f"Error completing queue: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@queue_bp.route('/api/queue/<int:queue_id>/cancel', methods=['POST'])
def cancel_queue(queue_id):
    """Cancel queue"""
    try:
        queue = Queue.query.get_or_404(queue_id)
        
        queue.status = 'cancelled'
        queue.completed_at = datetime.utcnow()
        
        db.session.commit()
        
        logger.info(f"❌ Queue {queue.queue_number} cancelled")
        
        return jsonify({
            'success': True,
            'queue': queue.to_dict()
        })
    except Exception as e:
        logger.error(f"Error cancelling queue: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@queue_bp.route('/api/next', methods=['POST'])
def get_next():
    """Get next waiting customer (auto-call)"""
    try:
        data = request.get_json()
        counter = data.get('counter')
        
        # Priority: high priority first, then by created time
        next_queue = Queue.query.filter_by(status='waiting').order_by(
            Queue.priority.desc(),
            Queue.created_at.asc()
        ).first()
        
        if next_queue:
            next_queue.status = 'serving'
            next_queue.called_at = datetime.utcnow()
            next_queue.counter = counter
            db.session.commit()
            
            logger.info(f"🔔 Next queue {next_queue.queue_number} auto-called to counter {counter}")
            
            return jsonify({
                'success': True,
                'queue': next_queue.to_dict()
            })
        
        return jsonify({
            'success': False,
            'message': 'No waiting customers'
        })
    except Exception as e:
        logger.error(f"Error getting next queue: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@queue_bp.route('/api/queue/<int:queue_id>/apply-to-booking', methods=['POST'])
@login_required
def apply_to_booking(queue_id):
    """Create booking from queue customer data"""
    try:
        queue = Queue.query.get_or_404(queue_id)
        
        # Check or create customer
        customer = Customer.query.filter_by(phone=queue.customer_phone).first()
        
        if not customer:
            # Create new customer from queue data
            # Parse name into first and last name
            name_parts = queue.customer_name.strip().split(' ', 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ''
            
            customer = Customer(
                first_name=first_name,
                last_name=last_name,
                phone=queue.customer_phone,
                email=queue.customer_email if queue.customer_email else None,
                name=queue.customer_name
            )
            db.session.add(customer)
            db.session.flush()  # Get customer ID
            
            logger.info(f"✅ New customer created from queue: {customer.name} (ID: {customer.id})")
        else:
            logger.info(f"📝 Existing customer found: {customer.name} (ID: {customer.id})")
        
        # Generate booking reference
        from routes.booking import generate_booking_reference
        booking_ref = generate_booking_reference()
        
        # Create new booking
        booking = Booking(
            customer_id=customer.id,
            booking_reference=booking_ref,
            booking_type='package',  # Default type
            created_by=current_user.id,
            notes=f"Created from Queue #{queue.queue_number}\nService: {queue.service_type}\n{queue.notes or ''}"
        )
        
        db.session.add(booking)
        db.session.commit()
        
        logger.info(f"🎫 Booking #{booking.id} created from Queue #{queue.queue_number}")
        
        return jsonify({
            'success': True,
            'booking_id': booking.id,
            'booking_reference': booking_ref,
            'customer_id': customer.id,
            'customer_name': customer.name,
            'queue_number': queue.queue_number
        })
        
    except Exception as e:
        logger.error(f"❌ Error creating booking from queue: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# MEDIA MANAGEMENT API ENDPOINTS
# ============================================================

@queue_bp.route('/api/media', methods=['GET'])
def get_media_list():
    """Get all active media for display"""
    try:
        media_list = QueueMedia.query.filter_by(is_active=True).order_by(
            QueueMedia.display_order.asc(),
            QueueMedia.created_at.desc()
        ).all()
        
        return jsonify({
            'success': True,
            'media': [m.to_dict() for m in media_list]
        })
    except Exception as e:
        logger.error(f"Error getting media list: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@queue_bp.route('/api/media/all', methods=['GET'])
@login_required
def get_all_media():
    """Get all media (including inactive) for admin"""
    try:
        media_list = QueueMedia.query.order_by(
            QueueMedia.display_order.asc(),
            QueueMedia.created_at.desc()
        ).all()
        
        return jsonify({
            'success': True,
            'media': [m.to_dict() for m in media_list]
        })
    except Exception as e:
        logger.error(f"Error getting all media: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@queue_bp.route('/api/media', methods=['POST'])
@login_required
def create_media():
    """Upload new media (image/video)"""
    try:
        # Check if JSON request (YouTube URL)
        if request.is_json:
            data = request.get_json()
            youtube_url = data.get('youtube_url')
            
            if not youtube_url:
                return jsonify({'success': False, 'error': 'YouTube URL is required'}), 400
            
            # Safe int conversion
            try:
                duration = int(data.get('duration', 30))
            except (ValueError, TypeError):
                duration = 30
            
            try:
                display_order = int(data.get('display_order', 0))
            except (ValueError, TypeError):
                display_order = 0
            
            media = QueueMedia(
                title=data.get('title', 'YouTube Video'),
                description=data.get('description', ''),
                media_type='youtube',
                youtube_url=youtube_url,
                duration=duration,
                display_order=display_order,
                is_active=True,
                created_by=current_user.id
            )
        
        # Check if request has file (multipart/form-data)
        elif 'file' in request.files:
            file = request.files['file']
            
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{timestamp}_{filename}"
                
                # Ensure upload folder exists
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)
                
                # Determine media type
                ext = filename.rsplit('.', 1)[1].lower()
                media_type = 'video' if ext in ['mp4', 'webm', 'ogg'] else 'image'
                
                # Safe int conversion
                try:
                    duration = int(request.form.get('duration', 10))
                except (ValueError, TypeError):
                    duration = 10
                
                try:
                    display_order = int(request.form.get('display_order', 0))
                except (ValueError, TypeError):
                    display_order = 0
                
                media = QueueMedia(
                    title=request.form.get('title', 'Untitled'),
                    description=request.form.get('description', ''),
                    media_type=media_type,
                    file_path=f'/{filepath}',
                    duration=duration,
                    display_order=display_order,
                    is_active=True,
                    created_by=current_user.id
                )
            else:
                return jsonify({'success': False, 'error': 'Invalid file'}), 400
        
        # Form-data YouTube URL (legacy support)
        elif request.form.get('youtube_url'):
            # Safe int conversion
            try:
                duration = int(request.form.get('duration', 30))
            except (ValueError, TypeError):
                duration = 30
            
            try:
                display_order = int(request.form.get('display_order', 0))
            except (ValueError, TypeError):
                display_order = 0
                
            media = QueueMedia(
                title=request.form.get('title', 'YouTube Video'),
                description=request.form.get('description', ''),
                media_type='youtube',
                youtube_url=request.form.get('youtube_url'),
                duration=duration,
                display_order=display_order,
                is_active=True,
                created_by=current_user.id
            )
        else:
            return jsonify({'success': False, 'error': 'No file or URL provided'}), 400
        
        db.session.add(media)
        db.session.commit()
        
        logger.info(f"✅ New media created: {media.title}")
        return jsonify({'success': True, 'media': media.to_dict()})
        
    except Exception as e:
        logger.error(f"❌ Error creating media: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@queue_bp.route('/api/media/<int:media_id>', methods=['PUT'])
@login_required
def update_media(media_id):
    """Update media information"""
    try:
        media = QueueMedia.query.get_or_404(media_id)
        data = request.get_json()
        
        if 'title' in data:
            media.title = data['title']
        if 'description' in data:
            media.description = data['description']
        if 'duration' in data:
            media.duration = data['duration']
        if 'display_order' in data:
            media.display_order = data['display_order']
        if 'is_active' in data:
            media.is_active = data['is_active']
        
        media.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"✅ Media updated: {media.title}")
        return jsonify({'success': True, 'media': media.to_dict()})
        
    except Exception as e:
        logger.error(f"❌ Error updating media: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@queue_bp.route('/api/media/<int:media_id>', methods=['DELETE'])
@login_required
def delete_media(media_id):
    """Delete media"""
    try:
        media = QueueMedia.query.get_or_404(media_id)
        
        # Delete file if exists
        if media.file_path and media.file_path.startswith('/static/'):
            filepath = media.file_path[1:]  # Remove leading slash
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Deleted file: {filepath}")
        
        db.session.delete(media)
        db.session.commit()
        
        logger.info(f"✅ Media deleted: {media.title}")
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"❌ Error deleting media: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# DISPLAY TOKEN API ENDPOINTS
# ============================================================

@queue_bp.route('/api/tokens', methods=['GET'])
@login_required
def get_tokens():
    """Get all display tokens"""
    from models.display_token import DisplayToken
    try:
        tokens = DisplayToken.query.order_by(DisplayToken.created_at.desc()).all()
        return jsonify({
            'success': True,
            'tokens': [token.to_dict() for token in tokens]
        })
    except Exception as e:
        logger.error(f"❌ Error fetching tokens: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@queue_bp.route('/api/tokens', methods=['POST'])
@login_required
def create_token():
    """Create new display token"""
    from models.display_token import DisplayToken
    try:
        data = request.json
        
        # Generate new token
        new_token = DisplayToken(
            token=DisplayToken.generate_token(),
            name=data.get('name'),
            description=data.get('description'),
            expires_at=datetime.fromisoformat(data['expires_at']) if data.get('expires_at') else None,
            is_active=data.get('is_active', True),
            created_by=current_user.username if hasattr(current_user, 'username') else 'Admin'
        )
        
        db.session.add(new_token)
        db.session.commit()
        
        logger.info(f"✅ Token created: {new_token.name}")
        return jsonify({
            'success': True,
            'token': new_token.to_dict()
        })
        
    except Exception as e:
        logger.error(f"❌ Error creating token: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@queue_bp.route('/api/tokens/<int:token_id>', methods=['PUT'])
@login_required
def update_token(token_id):
    """Update display token"""
    from models.display_token import DisplayToken
    try:
        token = DisplayToken.query.get_or_404(token_id)
        data = request.json
        
        # Update fields
        if 'name' in data:
            token.name = data['name']
        if 'description' in data:
            token.description = data['description']
        if 'is_active' in data:
            token.is_active = data['is_active']
        if 'expires_at' in data:
            token.expires_at = datetime.fromisoformat(data['expires_at']) if data['expires_at'] else None
        
        db.session.commit()
        
        logger.info(f"✅ Token updated: {token.name}")
        return jsonify({
            'success': True,
            'token': token.to_dict()
        })
        
    except Exception as e:
        logger.error(f"❌ Error updating token: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@queue_bp.route('/api/tokens/<int:token_id>', methods=['DELETE'])
@login_required
def delete_token(token_id):
    """Delete display token"""
    from models.display_token import DisplayToken
    try:
        token = DisplayToken.query.get_or_404(token_id)
        
        db.session.delete(token)
        db.session.commit()
        
        logger.info(f"✅ Token deleted: {token.name}")
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"❌ Error deleting token: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@queue_bp.route('/api/tokens/<int:token_id>/regenerate', methods=['POST'])
@login_required
def regenerate_token(token_id):
    """Regenerate token string for security"""
    from models.display_token import DisplayToken
    try:
        token = DisplayToken.query.get_or_404(token_id)
        old_token = token.token
        
        # Generate new token
        token.token = DisplayToken.generate_token()
        token.access_count = 0
        token.last_accessed_at = None
        
        db.session.commit()
        
        logger.info(f"✅ Token regenerated: {token.name} (old: {old_token[:10]}...)")
        return jsonify({
            'success': True,
            'token': token.to_dict()
        })
        
    except Exception as e:
        logger.error(f"❌ Error regenerating token: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@queue_bp.route('/api/assign-counter', methods=['POST'])
@login_required
def assign_counter():
    """API endpoint to assign counter to user (Admin only)"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        counter_number = data.get('counter_number')
        
        if not user_id:
            return jsonify({'success': False, 'message': 'User ID is required'}), 400
        
        # Import User model
        from models.user import User
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        # Update user's assigned counter
        user.assigned_counter = counter_number
        db.session.commit()
        
        if counter_number:
            message = f'Successfully assigned Counter {counter_number} to {user.username}'
        else:
            message = f'Successfully unassigned counter from {user.username}'
        
        return jsonify({
            'success': True,
            'message': message
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error assigning counter: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@queue_bp.route('/api/users')
@login_required
def get_all_users():
    """API endpoint to get all users for counter assignment (Admin only)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        from models.user import User
        users = User.query.order_by(User.username).all()
        
        return jsonify([{
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'role': u.role,
            'is_admin': u.is_admin,
            'assigned_counter': u.assigned_counter
        } for u in users])
        
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        return jsonify({'error': str(e)}), 500


logger.info("✅ Queue management routes registered")
