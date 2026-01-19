"""
Booking Calendar and Daily Report Routes
"""
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from models.booking import Booking
from models.booking_task import BookingTask
from models.user import User
from extensions import db
from datetime import datetime, date, timedelta
from utils.logging_config import get_logger
from services.email_service import EmailService
from config import Config
import pytz
import os
import requests

logger = get_logger(__name__)
email_service = EmailService()

# This will be registered in app.py
calendar_bp = Blueprint('booking_calendar', __name__, url_prefix='/booking')


# ============================================================================
# CALENDAR BOOKING MANAGEMENT
# ============================================================================

@calendar_bp.route('/calendar')
@login_required
def calendar_view():
    """Calendar view for booking management"""
    return render_template('booking/calendar.html')


@calendar_bp.route('/api/users')
@login_required
def get_users():
    """Get all users for task assignment dropdown"""
    try:
        users = User.query.order_by(User.username).all()
        return jsonify({
            'users': [{'id': u.id, 'username': u.username} for u in users]
        })
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        return jsonify({'error': str(e)}), 500


@calendar_bp.route('/api/calendar/events')
@login_required
def calendar_events():
    """API endpoint to get calendar events for FullCalendar"""
    try:
        start_date = request.args.get('start')
        end_date = request.args.get('end')
        
        # Build query
        query = Booking.query
        
        if start_date and end_date:
            # Handle timezone format from FullCalendar (e.g., 2025-11-30T00:00:00+07:00)
            # Remove timezone info for simple date parsing
            start_str = start_date.split('T')[0] if 'T' in start_date else start_date
            end_str = end_date.split('T')[0] if 'T' in end_date else end_date
            start = datetime.strptime(start_str, '%Y-%m-%d').date()
            end = datetime.strptime(end_str, '%Y-%m-%d').date()
            
            # Get bookings within date range
            query = query.filter(
                db.or_(
                    db.and_(Booking.arrival_date >= start, Booking.arrival_date <= end),
                    db.and_(Booking.departure_date >= start, Booking.departure_date <= end),
                    db.and_(Booking.arrival_date <= start, Booking.departure_date >= end)
                )
            )
        
        # JOIN with users table to get creator information
        bookings_with_users = db.session.query(
            Booking, User.username, User.role
        ).outerjoin(
            User, Booking.created_by == User.id
        ).filter(
            Booking.id.in_([b.id for b in query.all()])
        ).all()
        
        events = []
        for booking, created_by_name, created_by_role in bookings_with_users:
            if not booking.arrival_date:
                continue
            
            # Operation status icons
            operation_icons = {
                'No': '⏳',
                'Yes': '✅',
                'Cancel': '❌'
            }
            operation_icon = operation_icons.get(booking.operation_status or 'No', '⏳')
                
            # Check for Time Limit and Due Date alerts (using Thailand timezone)
            # Convert to naive datetime for comparison with database
            now = datetime.now(Config.TIMEZONE).replace(tzinfo=None)
            time_limit_alert = False
            due_date_alert = False
            
            # Due Date Alert: today >= due_date (ครบ/เลยเวลายืนยัน/ชำระเงินแล้ว)
            # จำกัดกว่า - เฉพาะ booking ที่ยังไม่ได้ชำระเงิน
            if booking.due_date and booking.status not in ['paid', 'vouchered', 'completed', 'cancelled']:
                due_date_obj = datetime.combine(booking.due_date, datetime.min.time())
                if now >= due_date_obj:
                    due_date_alert = True
            
            # Time Limit Alert: time_limit >= today (ถึงกำหนดวันดำเนินการแล้ว)
            # กว้างกว่า - ครอบคลุมทุก status (แม้ชำระเงินแล้วก็ยังต้องเตือน)
            if booking.time_limit and booking.status not in ['completed', 'cancelled']:
                if booking.time_limit >= now:
                    time_limit_alert = True
            
            # Color based on status
            color_map = {
                'draft': '#6c757d',
                'pending': '#ffc107',
                'confirmed': '#17a2b8',
                'quoted': '#fd7e14',
                'paid': '#28a745',
                'vouchered': '#20c997',
                'completed': '#6610f2',
                'cancelled': '#9e9e9e'
            }
            
            # Use traveling_period for calendar display (แสดงตามช่วงเดินทาง)
            start_date = booking.traveling_period_start or booking.arrival_date
            end_date = booking.traveling_period_end or booking.departure_date
            
            # FullCalendar requires 'end' to be the day AFTER the last day (exclusive)
            # Add 1 day to end_date to make it inclusive display
            if end_date:
                from datetime import timedelta
                end_date_display = end_date + timedelta(days=1)
            else:
                end_date_display = None
            
            event = {
                'id': booking.id,
                'title': f"{operation_icon} {booking.booking_reference} - {booking.customer.name if booking.customer else 'N/A'}",
                'start': start_date.isoformat() if start_date else booking.arrival_date.isoformat(),
                'end': end_date_display.isoformat() if end_date_display else None,
                'backgroundColor': color_map.get(booking.status, '#6c757d'),
                'borderColor': color_map.get(booking.status, '#6c757d'),
                'extendedProps': {
                    'bookingReference': booking.booking_reference,
                    'type': booking.booking_type or 'N/A',
                    'travelingFrom': booking.arrival_date.strftime('%Y-%m-%d') if booking.arrival_date else 'N/A',
                    'travelingTo': booking.departure_date.strftime('%Y-%m-%d') if booking.departure_date else 'N/A',
                    'grandTotal': float(booking.total_amount) if booking.total_amount else 0,
                    'currency': booking.currency or 'THB',
                    'timeLimit': booking.time_limit.strftime('%Y-%m-%d %H:%M') if booking.time_limit else 'N/A',
                    'dueDate': booking.due_date.strftime('%Y-%m-%d') if booking.due_date else 'N/A',
                    'passengers': booking.total_pax or 0,
                    'adults': booking.adults or 0,
                    'children': booking.children or 0,
                    'infants': booking.infants or 0,
                    'customerName': booking.customer.name if booking.customer else 'N/A',
                    'customerEmail': booking.customer.email if booking.customer else 'N/A',
                    'customerPhone': booking.customer.phone if booking.customer else 'N/A',
                    'createdBy': created_by_name or 'Unknown',
                    'createdByRole': created_by_role or 'Staff',
                    'createdById': booking.created_by,
                    'operationStatus': booking.operation_status or 'No',
                    'operationIcon': operation_icon,
                    'status': booking.status,
                    'description': booking.description or '',
                    'partyName': booking.party_name or '',
                    'timeLimitAlert': time_limit_alert,
                    'dueDateAlert': due_date_alert
                }
            }
            events.append(event)
        
        return jsonify(events)
    except Exception as e:
        logger.error(f"Error fetching calendar events: {e}")
        return jsonify({'error': str(e)}), 500


@calendar_bp.route('/api/calendar/conflicts')
@login_required
def check_booking_conflicts():
    """Check for booking conflicts (double bookings)"""
    try:
        arrival_date = request.args.get('arrival_date')
        departure_date = request.args.get('departure_date')
        booking_id = request.args.get('booking_id')
        
        if not arrival_date or not departure_date:
            return jsonify({'error': 'Missing dates'}), 400
        
        start = datetime.strptime(arrival_date, '%Y-%m-%d').date()
        end = datetime.strptime(departure_date, '%Y-%m-%d').date()
        
        # Find overlapping bookings
        query = Booking.query.filter(
            Booking.status.in_(['confirmed', 'paid', 'vouchered']),
            db.or_(
                db.and_(Booking.arrival_date >= start, Booking.arrival_date < end),
                db.and_(Booking.departure_date > start, Booking.departure_date <= end),
                db.and_(Booking.arrival_date <= start, Booking.departure_date >= end)
            )
        )
        
        if booking_id:
            query = query.filter(Booking.id != int(booking_id))
        
        conflicts = query.all()
        
        return jsonify({
            'has_conflicts': len(conflicts) > 0,
            'count': len(conflicts),
            'conflicts': [{
                'id': b.id,
                'reference': b.booking_reference,
                'customer': b.customer.name if b.customer else 'N/A',
                'arrival': b.arrival_date.strftime('%Y-%m-%d'),
                'departure': b.departure_date.strftime('%Y-%m-%d'),
                'status': b.status
            } for b in conflicts]
        })
    except Exception as e:
        logger.error(f"Error checking conflicts: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# DAILY REPORT
# ============================================================================

@calendar_bp.route('/daily-report')
@login_required
def daily_report():
    """Daily booking report view"""
    report_date = request.args.get('date', date.today().isoformat())
    return render_template('booking/daily_report.html', report_date=report_date)


@calendar_bp.route('/api/daily-report/data')
@login_required
def daily_report_data():
    """API endpoint to get daily report data"""
    try:
        date_from = request.args.get('date_from', date.today().isoformat())
        date_to = request.args.get('date_to', date_from)
        
        start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
        end_date = datetime.strptime(date_to, '%Y-%m-%d').date()
        
        # Get bookings with user information
        bookings_with_users = db.session.query(
            Booking, User.username, User.role
        ).outerjoin(
            User, Booking.created_by == User.id
        ).filter(
            db.or_(
                db.and_(Booking.arrival_date >= start_date, Booking.arrival_date <= end_date),
                db.and_(Booking.departure_date >= start_date, Booking.departure_date <= end_date)
            )
        ).order_by(Booking.arrival_date.asc()).all()
        
        # Calculate statistics
        stats = {
            'total_bookings': len(bookings_with_users),
            'by_status': {},
            'by_type': {},
            'by_operation_status': {},
            'total_revenue': 0,
            'total_passengers': 0
        }
        
        booking_list = []
        for booking, created_by_name, created_by_role in bookings_with_users:
            status = booking.status or 'unknown'
            booking_type = booking.booking_type or 'unknown'
            operation_status = booking.operation_status or 'No'
            
            stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
            stats['by_type'][booking_type] = stats['by_type'].get(booking_type, 0) + 1
            stats['by_operation_status'][operation_status] = stats['by_operation_status'].get(operation_status, 0) + 1
            
            if booking.total_amount:
                stats['total_revenue'] += float(booking.total_amount)
            if booking.total_pax:
                stats['total_passengers'] += booking.total_pax
            
            # Operation status icons
            operation_icons = {
                'No': '⏳',
                'Yes': '✅',
                'Cancel': '❌'
            }
            
            booking_list.append({
                'id': booking.id,
                'reference': booking.booking_reference,
                'type': booking.booking_type or 'N/A',
                'customer': booking.customer.name if booking.customer else 'N/A',
                'arrival_date': booking.arrival_date.strftime('%Y-%m-%d') if booking.arrival_date else 'N/A',
                'departure_date': booking.departure_date.strftime('%Y-%m-%d') if booking.departure_date else 'N/A',
                'pax': booking.total_pax or 0,
                'amount': float(booking.total_amount) if booking.total_amount else 0,
                'currency': booking.currency or 'THB',
                'status': booking.status,
                'operation_status': operation_status,
                'operation_icon': operation_icons.get(operation_status, '⏳'),
                'created_by': created_by_name or 'Unknown',
                'created_by_role': created_by_role or 'Staff',
                'created_by_id': booking.created_by,
                'created_at': booking.created_at.strftime('%Y-%m-%d %H:%M') if booking.created_at else 'N/A'
            })
        
        return jsonify({
            'stats': stats,
            'bookings': booking_list,
            'date_range': {'from': start_date.isoformat(), 'to': end_date.isoformat()}
        })
    except Exception as e:
        logger.error(f"Error generating daily report: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# BOOKING NOTES & TODOS
# ============================================================================

@calendar_bp.route('/api/booking/<int:booking_id>', methods=['GET'])
@login_required
def get_booking_details(booking_id):
    """Get booking details for copy message"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        return jsonify({
            'success': True,
            'booking': {
                'id': booking.id,
                'booking_reference': booking.booking_reference,
                'booking_type': booking.booking_type,
                'arrival_date': booking.arrival_date.isoformat() if booking.arrival_date else None,
                'departure_date': booking.departure_date.isoformat() if booking.departure_date else None,
                'adults': booking.adults,
                'children': booking.children,
                'infants': booking.infants,
                'guest_list': booking.guest_list
            }
        })
    except Exception as e:
        logger.error(f"Error fetching booking details: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@calendar_bp.route('/api/booking/<int:booking_id>/notes', methods=['GET'])
@login_required
def get_booking_notes(booking_id):
    """Get notes for a booking"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        return jsonify({
            'notes': booking.notes or '',
            'admin_notes': booking.admin_notes or ''
        })
    except Exception as e:
        logger.error(f"Error fetching notes: {e}")
        return jsonify({'error': str(e)}), 500


@calendar_bp.route('/api/booking/<int:booking_id>/notes', methods=['POST'])
@login_required
def update_booking_notes(booking_id):
    """Update notes for a booking"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        data = request.get_json()
        
        booking.notes = data.get('notes', booking.notes)
        if current_user.is_admin or current_user.role in ['Administrator', 'Manager']:
            booking.admin_notes = data.get('admin_notes', booking.admin_notes)
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Notes updated successfully'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating notes: {e}")
        return jsonify({'error': str(e)}), 500


@calendar_bp.route('/api/booking/<int:booking_id>/operation-status', methods=['POST'])
@login_required
def update_operation_status(booking_id):
    """Update operation status for a booking"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        data = request.get_json()
        
        new_status = data.get('operation_status')
        
        # Validate status
        valid_statuses = ['No', 'Yes', 'Cancel']
        if new_status not in valid_statuses:
            return jsonify({'error': 'Invalid operation status'}), 400
        
        booking.operation_status = new_status
        db.session.commit()
        
        # Get operation icon
        operation_icons = {
            'No': '⏳',
            'Yes': '✅',
            'Cancel': '❌'
        }
        
        logger.info(f"Operation status updated for booking {booking_id}: {new_status}")
        return jsonify({
            'success': True, 
            'message': 'Operation status updated successfully',
            'operation_status': new_status,
            'operation_icon': operation_icons.get(new_status, '⏳')
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating operation status: {e}")
        return jsonify({'error': str(e)}), 500


@calendar_bp.route('/api/booking/<int:booking_id>/tasks', methods=['GET'])
@login_required
def get_booking_tasks(booking_id):
    """Get all tasks for a booking with sub-tasks"""
    try:
        # Get only parent tasks (not sub-tasks)
        from sqlalchemy import case
        
        tasks = BookingTask.query.filter_by(
            booking_id=booking_id,
            parent_task_id=None
        ).order_by(
            BookingTask.is_completed.asc(),
            case(
                (BookingTask.deadline.is_(None), 1),
                else_=0
            ),
            BookingTask.deadline.asc(),
            BookingTask.created_at.desc()
        ).all()
        
        tasks_data = [task.to_dict(include_subtasks=True) for task in tasks]
        logger.info(f"Fetched {len(tasks_data)} tasks for booking {booking_id}")
        
        return jsonify({
            'success': True,
            'tasks': tasks_data
        })
    except Exception as e:
        logger.error(f"Error fetching tasks for booking {booking_id}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'tasks': []}), 500


@calendar_bp.route('/api/booking/<int:booking_id>/tasks', methods=['POST'])
@login_required
def create_booking_task(booking_id):
    """Create a new task item"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        data = request.get_json()
        
        # Parse deadline if provided
        deadline = None
        if data.get('deadline'):
            try:
                deadline = datetime.strptime(data.get('deadline'), '%Y-%m-%d').date()
            except ValueError:
                pass
        
        task = BookingTask(
            booking_id=booking_id,
            parent_task_id=data.get('parent_task_id'),
            title=data.get('title') or data.get('text'),  # Support both field names
            description=data.get('description'),
            priority=data.get('priority', 'normal'),
            category=data.get('category'),
            status=data.get('status', BookingTask.STATUS_PENDING),
            assigned_to=data.get('assigned_to'),
            deadline=deadline,
            created_by=current_user.id
        )
        
        db.session.add(task)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'task': task.to_dict(include_subtasks=True)
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating task: {e}")
        return jsonify({'error': str(e)}), 500


@calendar_bp.route('/api/booking/tasks/<int:task_id>', methods=['PUT'])
@login_required
def update_booking_task(task_id):
    """Update a task item"""
    try:
        task = BookingTask.query.get_or_404(task_id)
        data = request.get_json()
        
        if 'title' in data:
            task.title = data['title']
        if 'text' in data:  # Support both field names
            task.title = data['text']
        if 'description' in data:
            task.description = data['description']
        if 'confirmation' in data:
            task.confirmation = data['confirmation']
        if 'reservation' in data:
            task.reservation = data['reservation']
        if 'is_completed' in data:
            if data['is_completed']:
                task.mark_as_completed()
            else:
                task.mark_as_pending()
        if 'status' in data:
            task.status = data['status']
            if data['status'] == BookingTask.STATUS_COMPLETED:
                task.is_completed = True
                task.completed_at = datetime.utcnow()
            elif task.is_completed:
                task.is_completed = False
                task.completed_at = None
        if 'priority' in data:
            task.priority = data['priority']
        if 'category' in data:
            task.category = data['category']
        if 'assigned_to' in data:
            task.assigned_to = data['assigned_to']
        if 'deadline' in data:
            try:
                task.deadline = datetime.strptime(data['deadline'], '%Y-%m-%d').date() if data['deadline'] else None
            except ValueError:
                pass
        
        task.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'task': task.to_dict(include_subtasks=True)
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating task: {e}")
        return jsonify({'error': str(e)}), 500


@calendar_bp.route('/api/booking/tasks/<int:task_id>', methods=['GET'])
@login_required
def get_single_task(task_id):
    """Get single task details"""
    try:
        task = BookingTask.query.get_or_404(task_id)
        task_data = task.to_dict(include_subtasks=True)
        
        # Add booking service detail/itinerary
        if task.booking:
            task_data['booking_service_detail'] = task.booking.description or ''
        
        return jsonify({
            'success': True,
            'task': task_data
        })
    except Exception as e:
        logger.error(f"Error fetching task {task_id}: {e}")
        return jsonify({'error': str(e)}), 500


@calendar_bp.route('/api/booking/tasks/<int:task_id>/send-notification', methods=['POST'])
@login_required  
def send_task_notification(task_id):
    """Send email notification to assigned user"""
    try:
        task = BookingTask.query.get_or_404(task_id)
        
        if not task.assignee or not task.assignee.email:
            return jsonify({'success': False, 'error': 'No assignee or email found'}), 400
        
        booking = task.booking
        
        # Build task URL
        task_url = f"{request.host_url}booking/calendar?task_id={task.id}"
        
        # Email subject and body
        subject = f"[Task Assignment] {task.title}"
        
        # Format description with line breaks
        description_html = ''
        if task.description:
            description_formatted = task.description.replace('\n', '<br>')
            description_html = f'<p><strong>รายละเอียด:</strong><br>{description_formatted}</p>'
        
        # Format confirmation with line breaks
        confirmation_html = ''
        if task.confirmation:
            confirmation_formatted = task.confirmation.replace('\n', '<br>')
            confirmation_html = f'<p><strong>ยืนยันการจอง / Confirmation:</strong><br>{confirmation_formatted}</p>'
        
        body = f"""
<h2>คุณได้รับมอบหมาย Task ใหม่</h2>

<h3>รายละเอียด Task:</h3>
<ul>
    <li><strong>หัวข้อ:</strong> {task.title}</li>
    <li><strong>ความสำคัญ:</strong> {task.priority.upper()}</li>
    <li><strong>Deadline:</strong> {task.deadline.strftime('%d/%m/%Y') if task.deadline else 'ไม่ระบุ'}</li>
    <li><strong>Booking:</strong> {booking.booking_reference}</li>
    <li><strong>ลูกค้า:</strong> {booking.customer.name if booking.customer else 'N/A'}</li>
</ul>

{description_html}

{confirmation_html}

<p><a href="{task_url}" style="display: inline-block; padding: 10px 20px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px;">ดู Task</a></p>

<hr>
<p><small>Email นี้ถูกส่งอัตโนมัติจากระบบ Task Management</small></p>
        """
        
        # Send email
        email_service.send_email(
            to_email=task.assignee.email,
            subject=subject,
            body=body
        )
        
        logger.info(f"✅ Task notification sent to {task.assignee.email} for task #{task_id}")
        
        return jsonify({
            'success': True,
            'message': 'Notification sent successfully'
        })
        
    except Exception as e:
        logger.error(f"Error sending task notification: {e}")
        return jsonify({'error': str(e)}), 500


@calendar_bp.route('/api/booking/tasks/<int:task_id>/send-email', methods=['POST'])
@login_required
def send_task_email(task_id):
    """Send email with task details to assigned user with CC to support"""
    try:
        task = BookingTask.query.get_or_404(task_id)
        data = request.get_json()
        message_content = data.get('message', '')
        
        if not task.assignee or not task.assignee.email:
            return jsonify({'success': False, 'error': 'No assignee or email found'}), 400
        
        booking = task.booking
        task_url = f"{request.host_url}booking/calendar?task_id={task.id}"
        
        # Email subject
        subject = f"[Task] {task.title} - {booking.booking_reference if booking else 'N/A'}"
        
        # Convert message to HTML (preserve line breaks)
        html_message = message_content.replace('\n', '<br>')
        
        # Email body
        body = f"""
<div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">
    <h2 style="color: #333;">Task Details</h2>
    
    <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
        <pre style="white-space: pre-wrap; font-family: Arial, sans-serif; margin: 0;">{html_message}</pre>
    </div>
    
    <p style="margin-top: 20px;">
        <a href="{task_url}" style="display: inline-block; padding: 12px 24px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">
            View Task in System
        </a>
    </p>
    
    <hr style="margin: 30px 0; border: none; border-top: 1px solid #ddd;">
    
    <p style="color: #666; font-size: 12px;">
        <strong>Sent by:</strong> {current_user.username}<br>
        <strong>Date:</strong> {datetime.now(Config.TIMEZONE).strftime('%d/%m/%Y %H:%M:%S')}
    </p>
    
    <p style="color: #999; font-size: 11px; margin-top: 20px;">
        This email was sent automatically from the Task Management System.
    </p>
</div>
        """
        
        # Send email with CC to support
        email_service.send_email(
            to_email=task.assignee.email,
            subject=subject,
            body=body,
            cc_email='support@dhakulchan.com'
        )
        
        logger.info(f"✅ Task email sent to {task.assignee.email} (CC: support@dhakulchan.com) for task #{task_id}")
        
        return jsonify({
            'success': True,
            'message': f'Email sent successfully to {task.assignee.email}'
        })
        
    except Exception as e:
        logger.error(f"Error sending task email: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@calendar_bp.route('/api/booking/tasks/<int:task_id>/send-line', methods=['POST'])
@login_required
def send_task_line(task_id):
    """Send LINE message using Messaging API"""
    try:
        task = BookingTask.query.get_or_404(task_id)
        data = request.get_json()
        message_content = data.get('message', '')
        
        # Get LINE Messaging API credentials from environment or config
        line_token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN') or Config.LINE_CHANNEL_ACCESS_TOKEN
        line_group_id = os.environ.get('LINE_GROUP_ID') or Config.LINE_GROUP_ID
        
        if not line_token:
            return jsonify({
                'success': False, 
                'error': 'LINE Channel Access Token not configured. Please set LINE_CHANNEL_ACCESS_TOKEN in environment variables.'
            }), 400
        
        if not line_group_id:
            return jsonify({
                'success': False,
                'error': 'LINE Group ID not configured. Please set LINE_GROUP_ID in environment variables.'
            }), 400
        
        # Send LINE message using Messaging API
        headers = {
            'Authorization': f'Bearer {line_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'to': line_group_id,
            'messages': [
                {
                    'type': 'text',
                    'text': message_content
                }
            ]
        }
        
        response = requests.post(
            'https://api.line.me/v2/bot/message/push',
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            logger.info(f"✅ LINE message sent for task #{task_id}")
            return jsonify({
                'success': True,
                'message': 'LINE message sent successfully'
            })
        else:
            logger.error(f"LINE API error: {response.status_code} - {response.text}")
            return jsonify({
                'success': False,
                'error': f'LINE API error: {response.status_code} - {response.text}'
            }), 500
            
    except Exception as e:
        logger.error(f"Error sending LINE message: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@calendar_bp.route('/api/tasks/all', methods=['GET'])
@login_required
def get_all_tasks():
    """Get all tasks with booking and customer info"""
    try:
        tasks = BookingTask.query.filter_by(parent_task_id=None).order_by(
            BookingTask.is_completed.asc(),
            BookingTask.deadline.asc(),
            BookingTask.created_at.desc()
        ).all()
        
        tasks_data = []
        for task in tasks:
            task_dict = task.to_dict(include_subtasks=False)
            
            # Add booking info
            if task.booking:
                task_dict['booking_reference'] = task.booking.booking_reference
                task_dict['customer_name'] = task.booking.customer.name if task.booking.customer else None
            
            tasks_data.append(task_dict)
        
        return jsonify({
            'success': True,
            'tasks': tasks_data
        })
    except Exception as e:
        logger.error(f"Error fetching all tasks: {e}")
        return jsonify({'error': str(e)}), 500


@calendar_bp.route('/task-list')
@login_required
def task_list_view():
    """Task list view"""
    return render_template('booking/task_list.html')


@calendar_bp.route('/api/tasks/check-deadlines', methods=['GET'])
@login_required
def check_task_deadlines():
    """Check for tasks with approaching or overdue deadlines and send alerts"""
    try:
        from sqlalchemy import and_
        today = date.today()
        tomorrow = today + timedelta(days=1)
        
        # Find overdue tasks
        overdue_tasks = BookingTask.query.filter(
            and_(
                BookingTask.deadline < today,
                BookingTask.is_completed == False,
                BookingTask.parent_task_id.is_(None)
            )
        ).all()
        
        # Find tasks due today
        due_today = BookingTask.query.filter(
            and_(
                BookingTask.deadline == today,
                BookingTask.is_completed == False,
                BookingTask.parent_task_id.is_(None)
            )
        ).all()
        
        # Find tasks due tomorrow
        due_tomorrow = BookingTask.query.filter(
            and_(
                BookingTask.deadline == tomorrow,
                BookingTask.is_completed == False,
                BookingTask.parent_task_id.is_(None)
            )
        ).all()
        
        alerts = []
        
        # Send emails for overdue tasks
        for task in overdue_tasks:
            if task.assignee and task.assignee.email:
                try:
                    days_overdue = (today - task.deadline).days
                    subject = f"⚠️ [OVERDUE] Task: {task.title}"
                    body = f"""
<h2 style="color: #dc3545;">Task เลยกำหนดแล้ว {days_overdue} วัน!</h2>

<h3>รายละเอียด Task:</h3>
<ul>
    <li><strong>หัวข้อ:</strong> {task.title}</li>
    <li><strong>Deadline:</strong> {task.deadline.strftime('%d/%m/%Y')} (เลยมาแล้ว {days_overdue} วัน)</li>
    <li><strong>ความสำคัญ:</strong> {task.priority.upper()}</li>
    <li><strong>Booking:</strong> {task.booking.booking_reference if task.booking else 'N/A'}</li>
</ul>

{f'<p><strong>รายละเอียด:</strong><br>{task.description}</p>' if task.description else ''}

<p style="color: #dc3545;"><strong>กรุณาดำเนินการให้เสร็จโดยเร็วที่สุด!</strong></p>

<p><a href="{request.host_url}booking/calendar?task_id={task.id}" style="display: inline-block; padding: 10px 20px; background-color: #dc3545; color: white; text-decoration: none; border-radius: 5px;">ดู Task</a></p>
                    """
                    
                    email_service.send_email(
                        to_email=task.assignee.email,
                        subject=subject,
                        body=body
                    )
                    alerts.append({
                        'task_id': task.id,
                        'type': 'overdue',
                        'email_sent': True
                    })
                except Exception as e:
                    logger.error(f"Error sending overdue alert for task {task.id}: {e}")
        
        # Send emails for tasks due today
        for task in due_today:
            if task.assignee and task.assignee.email:
                try:
                    subject = f"🔔 [DUE TODAY] Task: {task.title}"
                    body = f"""
<h2 style="color: #ff9800;">Task ครบกำหนดวันนี้!</h2>

<h3>รายละเอียด Task:</h3>
<ul>
    <li><strong>หัวข้อ:</strong> {task.title}</li>
    <li><strong>Deadline:</strong> วันนี้ ({task.deadline.strftime('%d/%m/%Y')})</li>
    <li><strong>ความสำคัญ:</strong> {task.priority.upper()}</li>
    <li><strong>Booking:</strong> {task.booking.booking_reference if task.booking else 'N/A'}</li>
</ul>

{f'<p><strong>รายละเอียด:</strong><br>{task.description}</p>' if task.description else ''}

<p><a href="{request.host_url}booking/calendar?task_id={task.id}" style="display: inline-block; padding: 10px 20px; background-color: #ff9800; color: white; text-decoration: none; border-radius: 5px;">ดู Task</a></p>
                    """
                    
                    email_service.send_email(
                        to_email=task.assignee.email,
                        subject=subject,
                        body=body
                    )
                    alerts.append({
                        'task_id': task.id,
                        'type': 'due_today',
                        'email_sent': True
                    })
                except Exception as e:
                    logger.error(f"Error sending due today alert for task {task.id}: {e}")
        
        # Send emails for tasks due tomorrow (reminder)
        for task in due_tomorrow:
            if task.assignee and task.assignee.email:
                try:
                    subject = f"🔔 [REMINDER] Task due tomorrow: {task.title}"
                    body = f"""
<h2 style="color: #2196f3;">Task ครบกำหนดพรุ่งนี้</h2>

<h3>รายละเอียด Task:</h3>
<ul>
    <li><strong>หัวข้อ:</strong> {task.title}</li>
    <li><strong>Deadline:</strong> พรุ่งนี้ ({task.deadline.strftime('%d/%m/%Y')})</li>
    <li><strong>ความสำคัญ:</strong> {task.priority.upper()}</li>
    <li><strong>Booking:</strong> {task.booking.booking_reference if task.booking else 'N/A'}</li>
</ul>

{f'<p><strong>รายละเอียด:</strong><br>{task.description}</p>' if task.description else ''}

<p><a href="{request.host_url}booking/calendar?task_id={task.id}" style="display: inline-block; padding: 10px 20px; background-color: #2196f3; color: white; text-decoration: none; border-radius: 5px;">ดู Task</a></p>
                    """
                    
                    email_service.send_email(
                        to_email=task.assignee.email,
                        subject=subject,
                        body=body
                    )
                    alerts.append({
                        'task_id': task.id,
                        'type': 'due_tomorrow',
                        'email_sent': True
                    })
                except Exception as e:
                    logger.error(f"Error sending tomorrow reminder for task {task.id}: {e}")
        
        return jsonify({
            'success': True,
            'overdue_count': len(overdue_tasks),
            'due_today_count': len(due_today),
            'due_tomorrow_count': len(due_tomorrow),
            'alerts_sent': len(alerts),
            'alerts': alerts
        })
        
    except Exception as e:
        logger.error(f"Error checking task deadlines: {e}")
        return jsonify({'error': str(e)}), 500


@calendar_bp.route('/api/tasks/alert-count', methods=['GET'])
@login_required
def get_task_alert_count():
    """Get count of tasks with alerts (overdue and due today) for current user"""
    try:
        from sqlalchemy import and_, or_
        today = date.today()
        
        # Count overdue and due today tasks assigned to current user
        alert_count = BookingTask.query.filter(
            and_(
                or_(
                    BookingTask.deadline < today,
                    BookingTask.deadline == today
                ),
                BookingTask.is_completed == False,
                BookingTask.assigned_to == current_user.id,
                BookingTask.parent_task_id.is_(None)
            )
        ).count()
        
        return jsonify({
            'success': True,
            'alert_count': alert_count
        })
    except Exception as e:
        logger.error(f"Error getting alert count: {e}")
        return jsonify({'error': str(e), 'alert_count': 0}), 500


@calendar_bp.route('/api/booking/tasks/<int:task_id>', methods=['DELETE'])
@login_required
def delete_booking_task(task_id):
    """Delete a task item (and its sub-tasks due to CASCADE)"""
    try:
        task = BookingTask.query.get_or_404(task_id)
        db.session.delete(task)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Task deleted successfully'
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting task: {e}")
        return jsonify({'error': str(e)}), 500


@calendar_bp.route('/api/calendar/check-alerts', methods=['GET'])
@login_required
def check_booking_alerts():
    """Check for Time Limit and Due Date alerts and send notifications (one time per booking per day)"""
    try:
        import pymysql
        
        # Use Thailand timezone, convert to naive for database comparison
        now = datetime.now(Config.TIMEZONE).replace(tzinfo=None)
        today = now.date()
        alerts_sent = {
            'time_limit': [],
            'due_date': []
        }
        
        # Helper function to check if alert was already sent today
        def was_alert_sent_today(booking_id, alert_type):
            """Check if alert was already sent today for this booking"""
            try:
                connection = pymysql.connect(
                    host='localhost',
                    user='voucher_user',
                    password='VoucherSecure2026!',
                    database='voucher_enhanced',
                    charset='utf8mb4'
                )
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT COUNT(*) FROM alert_tracking 
                        WHERE booking_id = %s AND alert_type = %s AND alert_date = %s
                    """, (booking_id, alert_type, today))
                    count = cursor.fetchone()[0]
                    return count > 0
            except Exception as e:
                logger.error(f"Error checking alert tracking: {e}")
                return False
            finally:
                if 'connection' in locals():
                    connection.close()
        
        # Helper function to record sent alert
        def record_sent_alert(booking_id, alert_type):
            """Record that alert was sent today"""
            try:
                connection = pymysql.connect(
                    host='localhost',
                    user='voucher_user',
                    password='VoucherSecure2026!',
                    database='voucher_enhanced',
                    charset='utf8mb4'
                )
                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO alert_tracking (booking_id, alert_type, alert_date, sent_at)
                        VALUES (%s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE sent_at = %s
                    """, (booking_id, alert_type, today, now, now))
                    connection.commit()
                    logger.info(f"✅ Alert tracking recorded: booking={booking_id}, type={alert_type}, date={today}")
            except Exception as e:
                logger.error(f"Error recording alert tracking: {e}")
            finally:
                if 'connection' in locals():
                    connection.close()
        
        # Check Due Date alerts (for bookings not yet paid)
        # เงื่อนไข: now >= due_date (ครบ/เลยเวลายืนยัน/ชำระเงินแล้ว)
        # จำกัดกว่า - เฉพาะ booking ที่ยังไม่ได้ชำระเงิน
        due_date_bookings = Booking.query.filter(
            Booking.due_date <= now.date(),  # now >= due_date
            Booking.status.in_(['draft', 'pending', 'confirmed', 'quoted']),
            Booking.due_date.isnot(None)
        ).all()
        
        for booking in due_date_bookings:
            try:
                # Check if already sent today (one time per booking per day)
                if was_alert_sent_today(booking.id, 'due_date'):
                    logger.info(f"⏭️ Skipping due_date alert for booking {booking.id} - already sent today")
                    continue
                
                if email_service.send_due_date_alert(booking):
                    # Record that alert was sent
                    record_sent_alert(booking.id, 'due_date')
                    
                    alerts_sent['due_date'].append({
                        'id': booking.id,
                        'reference': booking.booking_reference,
                        'customer': booking.customer.name if booking.customer else 'N/A',
                        'due_date': booking.due_date.strftime('%Y-%m-%d')
                    })
            except Exception as e:
                logger.error(f"Failed to send due date alert for booking {booking.id}: {e}")
        
        # Check Time Limit alerts (for all active bookings)
        # เงื่อนไข: time_limit >= now (ถึงกำหนดวันดำเนินการแล้ว)
        # กว้างกว่า - ครอบคลุมทุก status (แม้ชำระเงินแล้วก็ยังต้องเตือน)
        time_limit_bookings = Booking.query.filter(
            Booking.time_limit >= now,  # time_limit >= now
            Booking.status.notin_(['completed', 'cancelled']),
            Booking.time_limit.isnot(None)
        ).all()
        
        for booking in time_limit_bookings:
            try:
                # Check if already sent today (one time per booking per day)
                if was_alert_sent_today(booking.id, 'time_limit'):
                    logger.info(f"⏭️ Skipping time_limit alert for booking {booking.id} - already sent today")
                    continue
                
                if email_service.send_time_limit_alert(booking):
                    # Record that alert was sent
                    record_sent_alert(booking.id, 'time_limit')
                    
                    alerts_sent['time_limit'].append({
                        'id': booking.id,
                        'reference': booking.booking_reference,
                        'customer': booking.customer.name if booking.customer else 'N/A',
                        'time_limit': booking.time_limit.strftime('%Y-%m-%d %H:%M')
                    })
            except Exception as e:
                logger.error(f"Failed to send time limit alert for booking {booking.id}: {e}")
        
        return jsonify({
            'success': True,
            'alerts_sent': alerts_sent,
            'time_limit_count': len(alerts_sent['time_limit']),
            'due_date_count': len(alerts_sent['due_date']),
            'total_alerts': len(alerts_sent['time_limit']) + len(alerts_sent['due_date'])
        })
        
    except Exception as e:
        logger.error(f"Error checking booking alerts: {e}")
        return jsonify({'error': str(e)}), 500
