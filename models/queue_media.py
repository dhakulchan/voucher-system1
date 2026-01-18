"""
Queue Media Model
จัดเก็บข้อมูลภาพและวีดีโอที่แสดงในหน้า Queue Display
"""
from app import db
from datetime import datetime


class QueueMedia(db.Model):
    """Media content for Queue Display (Images/Videos)"""
    __tablename__ = 'queue_media'

    id = db.Column(db.Integer, primary_key=True)
    
    # Media Information
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # Media Type
    media_type = db.Column(db.String(20), nullable=False)  # 'image', 'video', 'youtube'
    
    # File/URL
    file_path = db.Column(db.String(500))  # For uploaded images/videos
    youtube_url = db.Column(db.String(500))  # For YouTube videos
    
    # Display Settings
    duration = db.Column(db.Integer, default=10)  # Display duration in seconds (for images)
    display_order = db.Column(db.Integer, default=0)  # Order of display
    is_active = db.Column(db.Boolean, default=True)  # Enable/Disable
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'media_type': self.media_type,
            'file_path': self.file_path,
            'youtube_url': self.youtube_url,
            'duration': self.duration,
            'display_order': self.display_order,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<QueueMedia {self.title} ({self.media_type})>'
