"""
Booking Auto Completion Service
Automatically updates booking status to "Completed" when today = departure_date + 3 days
"""

from datetime import datetime, date, timedelta
from sqlalchemy import and_
from models.booking import Booking
from extensions import db
import logging

class BookingAutoCompletionService:
    """Service for automatically completing bookings after their departure date"""
    
    @staticmethod
    def get_eligible_bookings():
        """
        Get bookings that are eligible for auto-completion
        Criteria: 
        - departure_date + 3 days = today
        - status is 'paid' or 'vouchered' (only these statuses can be auto-completed)
        """
        today = date.today()
        target_departure_date = today - timedelta(days=3)
        
        try:
            eligible_bookings = Booking.query.filter(
                and_(
                    Booking.departure_date == target_departure_date,
                    Booking.status.in_(['paid', 'vouchered'])
                )
            ).all()
            
            return eligible_bookings
            
        except Exception as e:
            logging.error(f"Error getting eligible bookings: {str(e)}")
            return []
    
    @staticmethod
    def auto_complete_booking(booking):
        """
        Auto complete a single booking
        """
        try:
            old_status = booking.status
            booking.status = 'completed'
            
            # Add completion timestamp (if not already exists in the model)
            if hasattr(booking, 'completed_at'):
                booking.completed_at = datetime.utcnow()
            
            db.session.commit()
            
            logging.info(f"Booking {booking.booking_reference} auto-completed: {old_status} -> completed")
            
            return True, f"Successfully updated booking {booking.booking_reference}"
            
        except Exception as e:
            db.session.rollback()
            error_msg = f"Error auto-completing booking {booking.booking_reference}: {str(e)}"
            logging.error(error_msg)
            return False, error_msg
    
    @staticmethod
    def process_auto_completion():
        """
        Main method to process all eligible bookings for auto-completion
        """
        eligible_bookings = BookingAutoCompletionService.get_eligible_bookings()
        
        if not eligible_bookings:
            logging.info("No bookings eligible for auto-completion")
            return {
                'total_processed': 0,
                'successful': 0,
                'failed': 0,
                'results': []
            }
        
        results = {
            'total_processed': len(eligible_bookings),
            'successful': 0,
            'failed': 0,
            'results': []
        }
        
        logging.info(f"Processing {len(eligible_bookings)} bookings for auto-completion")
        
        for booking in eligible_bookings:
            success, message = BookingAutoCompletionService.auto_complete_booking(booking)
            
            result_entry = {
                'booking_id': booking.id,
                'booking_reference': booking.booking_reference,
                'departure_date': booking.departure_date.strftime('%Y-%m-%d') if booking.departure_date else None,
                'old_status': booking.status if not success else 'completed',
                'success': success,
                'message': message
            }
            
            results['results'].append(result_entry)
            
            if success:
                results['successful'] += 1
            else:
                results['failed'] += 1
        
        # Log summary
        logging.info(f"Auto-completion completed: {results['successful']} successful, {results['failed']} failed")
        
        return results
    
    @staticmethod
    def get_completion_candidates(days_ahead=7):
        """
        Get bookings that will be eligible for completion in the next N days
        Useful for preview/monitoring purposes
        """
        today = date.today()
        candidates = []
        
        for i in range(days_ahead):
            check_date = today + timedelta(days=i)
            target_departure = check_date - timedelta(days=3)
            
            bookings = Booking.query.filter(
                and_(
                    Booking.departure_date == target_departure,
                    Booking.status.in_(['paid', 'vouchered'])
                )
            ).all()
            
            if bookings:
                candidates.append({
                    'completion_date': check_date.strftime('%Y-%m-%d'),
                    'departure_date': target_departure.strftime('%Y-%m-%d'),
                    'bookings': [{
                        'id': b.id,
                        'reference': b.booking_reference,
                        'status': b.status,
                        'customer_id': b.customer_id
                    } for b in bookings]
                })
        
        return candidates

# Convenience function for easy import
def run_auto_completion():
    """Convenience function to run auto-completion process"""
    return BookingAutoCompletionService.process_auto_completion()

def get_eligible_bookings():
    """Convenience function to get eligible bookings"""
    return BookingAutoCompletionService.get_eligible_bookings()

def preview_upcoming_completions(days=7):
    """Convenience function to preview upcoming completions"""
    return BookingAutoCompletionService.get_completion_candidates(days)