"""
MariaDB Safe Query Helper
Provides safe database queries that avoid datetime conversion issues
"""

from extensions import db
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

class SafeQueryHelper:
    """Helper class for raw SQL queries to avoid MariaDB datetime conversion issues"""
    
    @staticmethod
    def _convert_numeric_fields(bookings):
        """Convert numeric fields from strings to proper types"""
        converted_bookings = []
        
        for booking in bookings:
            # Convert to dict and then back to object-like structure
            booking_dict = dict(booking._mapping) if hasattr(booking, '_mapping') else dict(booking)
            
            # Convert numeric fields
            if 'total_amount' in booking_dict and booking_dict['total_amount']:
                try:
                    booking_dict['total_amount'] = float(booking_dict['total_amount'])
                except (ValueError, TypeError):
                    booking_dict['total_amount'] = 0.0
            
            if 'adults' in booking_dict and booking_dict['adults']:
                try:
                    booking_dict['adults'] = int(booking_dict['adults'])
                except (ValueError, TypeError):
                    booking_dict['adults'] = 0
                    
            if 'children' in booking_dict and booking_dict['children']:
                try:
                    booking_dict['children'] = int(booking_dict['children'])
                except (ValueError, TypeError):
                    booking_dict['children'] = 0
                    
            if 'total_pax' in booking_dict and booking_dict['total_pax']:
                try:
                    booking_dict['total_pax'] = int(booking_dict['total_pax'])
                except (ValueError, TypeError):
                    booking_dict['total_pax'] = 0
            
            # Create a simple object that allows attribute access
            class BookingResult:
                def __init__(self, data):
                    for key, value in data.items():
                        setattr(self, key, value)
            
            converted_bookings.append(BookingResult(booking_dict))
        
        return converted_bookings
    
    @staticmethod
    def get_recent_bookings(limit=10):
        """Get recent bookings using raw SQL to avoid datetime issues"""
        try:
            # Use raw SQL to avoid datetime conversion issues
            query = text("""
                SELECT id, customer_id, booking_reference, booking_type, status,
                       adults, children, total_pax, total_amount, currency,
                       DATE_FORMAT(created_at, '%Y-%m-%d %H:%i:%s') as created_at_str
                FROM bookings 
                ORDER BY id DESC 
                LIMIT :limit
            """)
            
            result = db.session.execute(query, {'limit': limit})
            bookings = result.fetchall()
            return SafeQueryHelper._convert_numeric_fields(bookings)
            
        except Exception as e:
            logger.error(f"Failed to get recent bookings: {e}")
            # Fallback to simple query
            try:
                from models.booking import Booking
                return Booking.query.order_by(Booking.id.desc()).limit(limit).all()
            except:
                return []
    
    @staticmethod
    def get_bookings_by_status(status, limit=50):
        """Get bookings by status using raw SQL"""
        try:
            query = text("""
                SELECT id, customer_id, booking_reference, booking_type, status,
                       adults, children, total_pax, total_amount, currency,
                       DATE_FORMAT(created_at, '%Y-%m-%d %H:%i:%s') as created_at_str
                FROM bookings 
                WHERE status = :status
                ORDER BY id DESC 
                LIMIT :limit
            """)
            
            result = db.session.execute(query, {'status': status, 'limit': limit})
            return result.fetchall()
            
        except Exception as e:
            logger.error(f"Failed to get bookings by status: {e}")
            return []
    
    @staticmethod
    def count_bookings_by_status(status):
        """Count bookings by status"""
        try:
            query = text("SELECT COUNT(*) as count FROM bookings WHERE status = :status")
            result = db.session.execute(query, {'status': status})
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Failed to count bookings by status: {e}")
            return 0
    
    @staticmethod
    def get_recent_customers(limit=10):
        """Get recent customers using raw SQL"""
        try:
            query = text("""
                SELECT id, name, first_name, last_name, email, phone, nationality,
                       DATE_FORMAT(created_at, '%Y-%m-%d %H:%i:%s') as created_at_str
                FROM customers 
                ORDER BY id DESC 
                LIMIT :limit
            """)
            
            result = db.session.execute(query, {'limit': limit})
            return result.fetchall()
            
        except Exception as e:
            logger.error(f"Failed to get recent customers: {e}")
            # Fallback to simple query
            try:
                from models.customer import Customer
                return Customer.query.order_by(Customer.id.desc()).limit(limit).all()
            except:
                return []
    
    @staticmethod
    def search_bookings(search_term, limit=20):
        """Search bookings by reference using raw SQL"""
        try:
            query = text("""
                SELECT id, customer_id, booking_reference, booking_type, status,
                       adults, children, total_pax, total_amount, currency,
                       DATE_FORMAT(created_at, '%Y-%m-%d %H:%i:%s') as created_at_str
                FROM bookings 
                WHERE booking_reference LIKE :search
                ORDER BY id DESC 
                LIMIT :limit
            """)
            
            result = db.session.execute(query, {
                'search': f'%{search_term}%',
                'limit': limit
            })
            bookings = result.fetchall()
            return SafeQueryHelper._convert_numeric_fields(bookings)
            
        except Exception as e:
            logger.error(f"Failed to search bookings: {e}")
            return []
    
    @staticmethod
    def get_booking_details(booking_id):
        """Get complete booking details using raw SQL"""
        try:
            query = text("""
                SELECT b.*, c.name as customer_name, c.email as customer_email,
                       DATE_FORMAT(b.created_at, '%Y-%m-%d %H:%i:%s') as created_at_str,
                       DATE_FORMAT(b.updated_at, '%Y-%m-%d %H:%i:%s') as updated_at_str
                FROM bookings b
                LEFT JOIN customers c ON b.customer_id = c.id
                WHERE b.id = :booking_id
            """)
            
            result = db.session.execute(query, {'booking_id': booking_id})
            return result.fetchone()
            
        except Exception as e:
            logger.error(f"Failed to get booking details: {e}")
            return None
    
    @staticmethod
    def get_booking_by_id(booking_id):
        """Get a single booking by ID using raw SQL to avoid datetime issues"""
        try:
            query = text("""
                SELECT * FROM bookings WHERE id = :booking_id
            """)
            
            result = db.session.execute(query, {'booking_id': booking_id})
            booking_data = result.fetchone()
            
            if booking_data:
                # Convert to dict and create object-like structure
                booking_dict = dict(booking_data._mapping) if hasattr(booking_data, '_mapping') else dict(booking_data)
                
                # Convert numeric fields
                if 'total_amount' in booking_dict and booking_dict['total_amount']:
                    try:
                        booking_dict['total_amount'] = float(booking_dict['total_amount'])
                    except (ValueError, TypeError):
                        booking_dict['total_amount'] = 0.0
                
                # Create a simple object that mimics the Booking model
                class BookingResult:
                    def __init__(self, data):
                        for key, value in data.items():
                            setattr(self, key, value)
                
                return BookingResult(booking_dict)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get booking by ID: {e}")
            return None