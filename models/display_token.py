from app import db
from datetime import datetime
import secrets

class DisplayToken(db.Model):
    __tablename__ = 'display_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    expires_at = db.Column(db.DateTime)  # NULL = no expiration
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by = db.Column(db.String(100))
    last_accessed_at = db.Column(db.DateTime)
    access_count = db.Column(db.Integer, default=0)
    
    @staticmethod
    def generate_token():
        """Generate a secure random token"""
        return secrets.token_urlsafe(32)
    
    def is_valid(self):
        """Check if token is valid (active and not expired)"""
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at < datetime.utcnow():
            return False
        return True
    
    def record_access(self):
        """Record token access"""
        self.last_accessed_at = datetime.utcnow()
        self.access_count = (self.access_count or 0) + 1
        db.session.commit()
    
    def to_dict(self):
        return {
            'id': self.id,
            'token': self.token,
            'name': self.name,
            'description': self.description,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by,
            'last_accessed_at': self.last_accessed_at.isoformat() if self.last_accessed_at else None,
            'access_count': self.access_count or 0
        }
