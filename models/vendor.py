from extensions import db
from utils.datetime_utils import naive_utc_now

class Supplier(db.Model):
    """Supplier (soft-renamed from Vendor) keeping the same table name 'vendors'."""
    __tablename__ = 'vendors'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    contact_name = db.Column(db.String(255))
    phone = db.Column(db.String(255))  # Increased from 50 to 255 to accommodate longer phone numbers
    email = db.Column(db.String(255))
    address = db.Column(db.Text)
    active = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text)

    # Newly added supplier detail fields
    real_name = db.Column(db.String(200))
    real_tel = db.Column(db.String(60))
    real_fax = db.Column(db.String(60))
    real_email = db.Column(db.String(180))
    fax = db.Column(db.String(60))
    mobile_phone = db.Column(db.String(60))
    real_group_email = db.Column(db.String(180))  # new group email field
    memos = db.Column(db.Text)      # internal memos
    remarks = db.Column(db.Text)    # external/general remarks

    created_at = db.Column(db.DateTime, default=naive_utc_now)
    updated_at = db.Column(db.DateTime, default=naive_utc_now, onupdate=naive_utc_now)

    def __repr__(self):
        return f'<Supplier {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'contact_name': self.contact_name,
            'phone': self.phone,
            'email': self.email,
            'address': self.address,
            'active': self.active,
            'notes': self.notes,
            'real_name': self.real_name,
            'real_tel': self.real_tel,
            'real_fax': self.real_fax,
            'real_email': self.real_email,
            'fax': self.fax,
            'mobile_phone': self.mobile_phone,
            'real_group_email': self.real_group_email,
            'memos': self.memos,
            'remarks': self.remarks,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

# Backward compatibility alias
Vendor = Supplier
