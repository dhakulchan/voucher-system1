from datetime import date
from utils.datetime_utils import naive_utc_now
from extensions import db

class QueueSession(db.Model):
    __tablename__ = 'queue_sessions'
    id = db.Column(db.Integer, primary_key=True)
    channel = db.Column(db.String(50), default='default', index=True)
    session_date = db.Column(db.Date, default=date.today, index=True)
    last_number = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=naive_utc_now)
    updated_at = db.Column(db.DateTime, default=naive_utc_now, onupdate=naive_utc_now)

    def next_number(self):
        self.last_number += 1
        return self.last_number

class QueueTicket(db.Model):
    __tablename__ = 'queue_tickets'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('queue_sessions.id'), nullable=False, index=True)
    number = db.Column(db.Integer, nullable=False)
    display_code = db.Column(db.String(20), index=True)
    status = db.Column(db.String(20), default='waiting', index=True)  # waiting|calling|serving|done|canceled
    service_type = db.Column(db.String(50))
    customer_name = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=naive_utc_now)
    updated_at = db.Column(db.DateTime, default=naive_utc_now, onupdate=naive_utc_now)
    called_at = db.Column(db.DateTime)
    started_at = db.Column(db.DateTime)
    finished_at = db.Column(db.DateTime)

    session = db.relationship('QueueSession', backref=db.backref('tickets', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'number': self.number,
            'display_code': self.display_code,
            'status': self.status,
            'service_type': self.service_type,
            'customer_name': self.customer_name,
            'phone': self.phone,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'called_at': self.called_at.isoformat() if self.called_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
        }
