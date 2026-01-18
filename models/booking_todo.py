"""
Booking Todo Model
For managing todo items and notes for each booking
"""
from extensions import db
from datetime import datetime

class BookingTodo(db.Model):
    __tablename__ = 'booking_todos'
    
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False)
    
    # Todo details
    text = db.Column(db.Text, nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    
    # Priority and categorization
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, urgent
    category = db.Column(db.String(50))  # optional: flights, hotels, transfers, etc.
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # User tracking
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationship
    booking = db.relationship('Booking', backref=db.backref('todos', lazy='dynamic', cascade='all, delete-orphan'))
    creator = db.relationship('User', foreign_keys=[created_by])
    
    def to_dict(self):
        """Convert todo to dictionary"""
        return {
            'id': self.id,
            'booking_id': self.booking_id,
            'text': self.text,
            'is_completed': self.is_completed,
            'priority': self.priority,
            'category': self.category,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_by': self.creator.username if self.creator else 'Unknown'
        }
    
    def __repr__(self):
        status = '✓' if self.is_completed else '○'
        return f'<BookingTodo {self.id}: [{status}] {self.text[:50]}>'
