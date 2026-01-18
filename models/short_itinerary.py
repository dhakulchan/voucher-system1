"""
Short Itinerary Model
Stores reusable itinerary templates with pricing for quick booking creation
"""

from app import db
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DECIMAL, DateTime

class ShortItinerary(db.Model):
    """Short itinerary template for quick selection during booking creation"""
    
    __tablename__ = 'short_itinerary'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    program_name = Column(String(255), nullable=False, index=True)
    tour_code = Column(String(100), nullable=True, index=True)
    product_link = Column(String(500), nullable=True, index=True)
    description = Column(Text, nullable=True)
    adult_twin_sharing = Column(DECIMAL(10, 2), default=0.00)
    adult_single = Column(DECIMAL(10, 2), default=0.00)
    child_extra_bed = Column(DECIMAL(10, 2), default=0.00)
    child_no_bed = Column(DECIMAL(10, 2), default=0.00)
    infant = Column(DECIMAL(10, 2), default=0.00)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<ShortItinerary {self.id}: {self.program_name}>"
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'program_name': self.program_name,
            'tour_code': self.tour_code,
            'product_link': self.product_link,
            'description': self.description,
            'adult_twin_sharing': float(self.adult_twin_sharing) if self.adult_twin_sharing else 0.00,
            'adult_single': float(self.adult_single) if self.adult_single else 0.00,
            'child_extra_bed': float(self.child_extra_bed) if self.child_extra_bed else 0.00,
            'child_no_bed': float(self.child_no_bed) if self.child_no_bed else 0.00,
            'infant': float(self.infant) if self.infant else 0.00,
            'notes': self.notes,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }
    
    def format_for_booking(self):
        """
        Format itinerary data for insertion into Service Detail field
        Returns formatted text with program name, prices, and notes
        """
        lines = []
        # Program name with tour code in parentheses
        if self.tour_code:
            lines.append(f"{self.program_name} ({self.tour_code})")
        else:
            lines.append(f"{self.program_name}")
        
        if self.description:
            lines.append(f"   {self.description}")
        
        # Add pricing information
        prices = []
        if self.adult_twin_sharing and float(self.adult_twin_sharing) > 0:
            prices.append(f"Adult Twin: {float(self.adult_twin_sharing):,.2f} THB")
        if self.adult_single and float(self.adult_single) > 0:
            prices.append(f"Adult Single: {float(self.adult_single):,.2f} THB")
        if self.child_extra_bed and float(self.child_extra_bed) > 0:
            prices.append(f"Child w/Bed: {float(self.child_extra_bed):,.2f} THB")
        if self.child_no_bed and float(self.child_no_bed) > 0:
            prices.append(f"Child No Bed: {float(self.child_no_bed):,.2f} THB")
        if self.infant and float(self.infant) > 0:
            prices.append(f"Infant: {float(self.infant):,.2f} THB")
        
        if prices:
            lines.append("Price: " + " | ".join(prices))
        
        if self.notes:
            lines.append(f"Note: {self.notes}")
        
        if self.product_link:
            lines.append(f"<a href='{self.product_link}' target='_blank'>คลิกดูเพิ่ม</a>")
        
        return "\n".join(lines)
    
    @staticmethod
    def search(query, page=1, per_page=20):
        """
        Search short itineraries by program name or description
        Returns paginated results
        """
        search_filter = ShortItinerary.program_name.like(f'%{query}%')
        if query:
            search_filter = db.or_(
                ShortItinerary.program_name.like(f'%{query}%'),
                ShortItinerary.description.like(f'%{query}%')
            )
        
        return ShortItinerary.query.filter(search_filter)\
            .order_by(ShortItinerary.program_name)\
            .paginate(page=page, per_page=per_page, error_out=False)
