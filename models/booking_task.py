"""
Booking Task Model
Enhanced task management with sub-tasks for bookings
Replaces BookingTodo with advanced features
"""
from extensions import db
from datetime import datetime

class BookingTask(db.Model):
    __tablename__ = 'booking_tasks'
    
    # Task statuses
    STATUS_PENDING = 'pending'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_ON_HOLD = 'on_hold'
    
    # Priority levels
    PRIORITY_LOW = 'low'
    PRIORITY_NORMAL = 'normal'
    PRIORITY_HIGH = 'high'
    PRIORITY_URGENT = 'urgent'
    
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False)
    parent_task_id = db.Column(db.Integer, db.ForeignKey('booking_tasks.id'), nullable=True)
    
    # Task details
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    confirmation = db.Column(db.Text)  # Booking confirmation details
    reservation = db.Column(db.Text)  # Reservation message for email booking/order
    
    # Task management
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'))
    status = db.Column(db.String(50), default=STATUS_PENDING)
    priority = db.Column(db.String(20), default=PRIORITY_NORMAL)
    category = db.Column(db.String(50))  # flights, hotels, transfers, etc.
    
    # Deadline and completion
    deadline = db.Column(db.Date)
    is_completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    booking = db.relationship('Booking', backref=db.backref('tasks', lazy='dynamic', cascade='all, delete-orphan'))
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_tasks')
    assignee = db.relationship('User', foreign_keys=[assigned_to], backref='assigned_tasks')
    
    # Self-referential relationship for sub-tasks
    sub_tasks = db.relationship(
        'BookingTask',
        backref=db.backref('parent_task', remote_side=[id]),
        cascade='all, delete-orphan',
        foreign_keys=[parent_task_id]
    )
    
    def to_dict(self, include_subtasks=False):
        """Convert task to dictionary"""
        try:
            result = {
                'id': self.id,
                'booking_id': self.booking_id,
                'parent_task_id': self.parent_task_id,
                'title': self.title,
                'description': self.description,
                'confirmation': self.confirmation,
                'reservation': self.reservation,
                'assigned_to': self.assigned_to,
                'assigned_to_name': self.assignee.username if self.assignee else None,
                'status': self.status,
                'is_completed': self.is_completed,
                'priority': self.priority,
                'category': self.category,
                'deadline': self.deadline.isoformat() if self.deadline else None,
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'updated_at': self.updated_at.isoformat() if self.updated_at else None,
                'completed_at': self.completed_at.isoformat() if self.completed_at else None,
                'created_by': self.creator.username if self.creator else 'Unknown',
                'created_by_id': self.created_by
            }
            
            if include_subtasks:
                result['sub_tasks'] = [sub.to_dict(include_subtasks=False) for sub in self.sub_tasks]
                result['sub_tasks_count'] = len(self.sub_tasks)
                result['completed_subtasks_count'] = sum(1 for sub in self.sub_tasks if sub.is_completed)
            
            return result
        except Exception as e:
            # Fallback with minimal data if relationships fail
            return {
                'id': self.id,
                'booking_id': self.booking_id,
                'parent_task_id': self.parent_task_id,
                'title': self.title or 'Untitled Task',
                'description': self.description,
                'assigned_to': self.assigned_to,
                'assigned_to_name': None,
                'status': self.status,
                'is_completed': self.is_completed or False,
                'priority': self.priority or 'normal',
                'category': self.category,
                'deadline': None,
                'created_at': None,
                'updated_at': None,
                'completed_at': None,
                'created_by': 'Unknown',
                'created_by_id': self.created_by,
                'sub_tasks': [],
                'sub_tasks_count': 0,
                'completed_subtasks_count': 0,
                'error': str(e)
            }
    
    def mark_as_completed(self):
        """Mark task as completed"""
        self.is_completed = True
        self.status = self.STATUS_COMPLETED
        self.completed_at = datetime.utcnow()
    
    def mark_as_pending(self):
        """Mark task as pending"""
        self.is_completed = False
        self.status = self.STATUS_PENDING
        self.completed_at = None
    
    def is_overdue(self):
        """Check if task is overdue"""
        if not self.deadline or self.is_completed:
            return False
        return self.deadline < datetime.utcnow().date()
    
    def get_progress_percentage(self):
        """Calculate progress based on completed sub-tasks"""
        if not self.sub_tasks:
            return 100 if self.is_completed else 0
        
        completed_count = sum(1 for sub in self.sub_tasks if sub.is_completed)
        total_count = len(self.sub_tasks)
        
        return int((completed_count / total_count) * 100) if total_count > 0 else 0
    
    def __repr__(self):
        status_icon = '✓' if self.is_completed else '○'
        parent_info = f' (sub of #{self.parent_task_id})' if self.parent_task_id else ''
        return f'<BookingTask {self.id}: [{status_icon}] {self.title[:50]}{parent_info}>'
