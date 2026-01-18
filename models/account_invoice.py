from extensions import db
from utils.datetime_utils import naive_utc_now

class InvoiceHongKong(db.Model):
    """Hong Kong Invoice Model"""
    __tablename__ = 'invoice_hongkong'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    cust_name = db.Column(db.String(255))
    company_name = db.Column(db.String(255))
    company_address = db.Column(db.Text)
    company_tel = db.Column(db.String(50))
    company_taxid = db.Column(db.String(50))
    company_contact = db.Column(db.String(255))
    total_pax = db.Column(db.Integer, default=0)
    arrival_date = db.Column(db.Date)
    departure_date = db.Column(db.Date)
    guest_list = db.Column(db.Text)
    flight_info = db.Column(db.Text)
    air_ticket_cost = db.Column(db.Numeric(12, 2), default=0.00)
    transportation_fee = db.Column(db.Numeric(12, 2), default=0.00)
    advance_expense = db.Column(db.Numeric(12, 2), default=0.00)
    tour_fee = db.Column(db.Numeric(12, 2), default=0.00)
    vat = db.Column(db.Numeric(12, 2), default=0.00)
    withholding_tax = db.Column(db.Numeric(12, 2), default=0.00)
    total_tour_fee = db.Column(db.Numeric(12, 2), default=0.00)
    created_at = db.Column(db.DateTime, default=naive_utc_now)
    updated_at = db.Column(db.DateTime, default=naive_utc_now, onupdate=naive_utc_now)
    
    # Relationship
    customer = db.relationship('Customer', backref='hongkong_invoices')
    
    def __repr__(self):
        return f'<InvoiceHongKong {self.id} - {self.cust_name}>'
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'cust_name': self.cust_name,
            'company_name': self.company_name,
            'company_address': self.company_address,
            'company_tel': self.company_tel,
            'company_taxid': self.company_taxid,
            'company_contact': self.company_contact,
            'total_pax': self.total_pax,
            'arrival_date': self.arrival_date.isoformat() if self.arrival_date else None,
            'departure_date': self.departure_date.isoformat() if self.departure_date else None,
            'guest_list': self.guest_list,
            'flight_info': self.flight_info,
            'air_ticket_cost': float(self.air_ticket_cost) if self.air_ticket_cost else 0.00,
            'transportation_fee': float(self.transportation_fee) if self.transportation_fee else 0.00,
            'advance_expense': float(self.advance_expense) if self.advance_expense else 0.00,
            'tour_fee': float(self.tour_fee) if self.tour_fee else 0.00,
            'vat': float(self.vat) if self.vat else 0.00,
            'withholding_tax': float(self.withholding_tax) if self.withholding_tax else 0.00,
            'total_tour_fee': float(self.total_tour_fee) if self.total_tour_fee else 0.00,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class InvoiceThai(db.Model):
    """Thai Invoice Model"""
    __tablename__ = 'invoice_thai'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    cust_name = db.Column(db.String(255))
    company_name = db.Column(db.String(255))
    company_address = db.Column(db.Text)
    company_tel = db.Column(db.String(50))
    company_taxid = db.Column(db.String(50))
    company_contact = db.Column(db.String(255))
    total_pax = db.Column(db.Integer, default=0)
    arrival_date = db.Column(db.Date)
    departure_date = db.Column(db.Date)
    guest_list = db.Column(db.Text)
    flight_info = db.Column(db.Text)
    air_ticket_cost = db.Column(db.Numeric(12, 2), default=0.00)
    transportation_fee = db.Column(db.Numeric(12, 2), default=0.00)
    advance_expense = db.Column(db.Numeric(12, 2), default=0.00)
    tour_fee = db.Column(db.Numeric(12, 2), default=0.00)
    vat = db.Column(db.Numeric(12, 2), default=0.00)
    withholding_tax = db.Column(db.Numeric(12, 2), default=0.00)
    total_tour_fee = db.Column(db.Numeric(12, 2), default=0.00)
    created_at = db.Column(db.DateTime, default=naive_utc_now)
    updated_at = db.Column(db.DateTime, default=naive_utc_now, onupdate=naive_utc_now)
    
    # Relationship
    customer = db.relationship('Customer', backref='thai_invoices')
    
    def __repr__(self):
        return f'<InvoiceThai {self.id} - {self.cust_name}>'
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'cust_name': self.cust_name,
            'company_name': self.company_name,
            'company_address': self.company_address,
            'company_tel': self.company_tel,
            'company_taxid': self.company_taxid,
            'company_contact': self.company_contact,
            'total_pax': self.total_pax,
            'arrival_date': self.arrival_date.isoformat() if self.arrival_date else None,
            'departure_date': self.departure_date.isoformat() if self.departure_date else None,
            'guest_list': self.guest_list,
            'flight_info': self.flight_info,
            'air_ticket_cost': float(self.air_ticket_cost) if self.air_ticket_cost else 0.00,
            'transportation_fee': float(self.transportation_fee) if self.transportation_fee else 0.00,
            'advance_expense': float(self.advance_expense) if self.advance_expense else 0.00,
            'tour_fee': float(self.tour_fee) if self.tour_fee else 0.00,
            'vat': float(self.vat) if self.vat else 0.00,
            'withholding_tax': float(self.withholding_tax) if self.withholding_tax else 0.00,
            'total_tour_fee': float(self.total_tour_fee) if self.total_tour_fee else 0.00,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
