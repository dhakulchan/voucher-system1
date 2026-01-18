"""
Flight Template Model
Stores reusable flight templates for quick booking creation
"""

from app import db
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime

class FlightTemplate(db.Model):
    """Flight template for quick selection during booking creation"""
    
    __tablename__ = 'flight_templates'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    template_name = Column(String(255), nullable=False, index=True)
    date = Column(String(50), nullable=True)
    flight_no = Column(String(50), nullable=True)
    from_to = Column(String(100), nullable=True)
    time = Column(String(50), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<FlightTemplate {self.id}: {self.template_name}>"
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'template_name': self.template_name,
            'date': self.date,
            'flight_no': self.flight_no,
            'from_to': self.from_to,
            'time': self.time,
            'note': self.note,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }
    
    def format_for_booking(self):
        """
        Format flight data for insertion into Flight Information field
        Returns formatted text
        Example: 20Dec25 BKKHKG 08:30-12:50 +1hrs
        """
        parts = []
        if self.date:
            parts.append(self.date)
        if self.flight_no:
            parts.append(self.flight_no)
        if self.from_to:
            parts.append(self.from_to)
        if self.time:
            parts.append(self.time)
        
        flight_line = " ".join(parts)
        
        if self.note:
            return f"{flight_line}\nRemarks: {self.note}"
        return flight_line
    
    @staticmethod
    def search(query, page=1, per_page=20):
        """
        Search flight templates by template name
        Returns paginated results
        """
        search_filter = FlightTemplate.template_name.like(f'%{query}%')
        if query:
            search_filter = db.or_(
                FlightTemplate.template_name.like(f'%{query}%'),
                FlightTemplate.from_to.like(f'%{query}%')
            )
        
        return FlightTemplate.query.filter(search_filter)\
            .order_by(FlightTemplate.template_name)\
            .paginate(page=page, per_page=per_page, error_out=False)
