from extensions import db
from datetime import datetime

class VoucherImage(db.Model):
    __tablename__ = 'voucher_images'
    
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False)
    image_path = db.Column(db.Text, nullable=False)
    display_order = db.Column(db.Integer, default=0)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with Booking
    booking = db.relationship('Booking', backref=db.backref('voucher_images_rel', lazy=True))
    
    def __repr__(self):
        return f'<VoucherImage {self.id}: {self.image_path}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'booking_id': self.booking_id,
            'image_path': self.image_path,
            'display_order': self.display_order,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None
        }
