"""
Queue Management Model
สำหรับระบบจัดการคิวลูกค้า
"""
from datetime import datetime
import pytz
from extensions import db

# Bangkok timezone
BANGKOK_TZ = pytz.timezone('Asia/Bangkok')


class Queue(db.Model):
    """Model สำหรับจัดการคิวลูกค้า"""
    __tablename__ = 'queues'
    
    id = db.Column(db.Integer, primary_key=True)
    queue_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(20), nullable=False)
    customer_email = db.Column(db.String(100))
    service_type = db.Column(db.String(50), nullable=False)  # booking, inquiry, payment, document, change, cancel
    status = db.Column(db.String(20), default='waiting', index=True)  # waiting, serving, completed, cancelled
    priority = db.Column(db.Integer, default=0)  # 0=normal, 1=high priority/VIP
    counter = db.Column(db.String(10))  # Counter/Booth number
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    called_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    
    def __repr__(self):
        return f'<Queue {self.queue_number} - {self.customer_name}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON responses"""
        def format_bangkok_time(dt):
            """Convert UTC datetime to Bangkok time string"""
            if not dt:
                return None
            # If datetime is naive, assume it's UTC
            if dt.tzinfo is None:
                dt = pytz.utc.localize(dt)
            # Convert to Bangkok time
            bangkok_time = dt.astimezone(BANGKOK_TZ)
            return bangkok_time.strftime('%Y-%m-%d %H:%M:%S')
        
        return {
            'id': self.id,
            'queue_number': self.queue_number,
            'customer_name': self.customer_name,
            'customer_phone': self.customer_phone,
            'customer_email': self.customer_email,
            'service_type': self.service_type,
            'status': self.status,
            'priority': self.priority,
            'counter': self.counter,
            'created_at': format_bangkok_time(self.created_at),
            'called_at': format_bangkok_time(self.called_at),
            'completed_at': format_bangkok_time(self.completed_at),
            'notes': self.notes,
            'waiting_time_minutes': self.waiting_time,
            'service_time_minutes': self.service_time,
            'total_time_minutes': self.total_time
        }
    
    @property
    def waiting_time(self):
        """Calculate waiting time in minutes"""
        if self.called_at and self.created_at:
            delta = self.called_at - self.created_at
            return int(delta.total_seconds() / 60)
        return None
    
    @property
    def service_time(self):
        """Calculate service time in minutes"""
        if self.completed_at and self.called_at:
            delta = self.completed_at - self.called_at
            return int(delta.total_seconds() / 60)
        return None
    
    @property
    def total_time(self):
        """Calculate total time from creation to completion"""
        if self.completed_at and self.created_at:
            delta = self.completed_at - self.created_at
            return int(delta.total_seconds() / 60)
        return None
