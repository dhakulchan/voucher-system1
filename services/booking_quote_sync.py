"""
Booking-Quote Sync Service
Ensures data consistency between booking updates and quote generation
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class BookingQuoteSyncService:
    """Service to sync booking data with quote data"""
    
    @staticmethod
    def on_booking_update(booking):
        """
        Called whenever a booking is updated to ensure quote data is synced
        
        Args:
            booking: Booking model instance that was updated
        """
        try:
            # Update quote-related fields when booking changes
            BookingQuoteSyncService._update_quote_metadata(booking)
            
            # If booking is in quoted status, regenerate quote number if needed
            if booking.status == 'quoted' and not booking.quote_number:
                BookingQuoteSyncService._generate_quote_number(booking)
            
            # Update quote status based on booking status
            BookingQuoteSyncService._sync_quote_status(booking)
            
            logger.info(f'Synced quote data for booking {booking.booking_reference}')
            
        except Exception as e:
            logger.error(f'Error syncing booking-quote data: {str(e)}')
            raise
    
    @staticmethod
    def _update_quote_metadata(booking):
        """Update quote metadata when booking changes"""
        
        # Update quoted_at timestamp if status changed to quoted
        if booking.status == 'quoted' and not booking.quoted_at:
            booking.quoted_at = datetime.now()
        
        # Update quote status based on booking status
        if booking.status == 'quoted':
            booking.quote_status = 'active'
        elif booking.status == 'confirmed':
            booking.quote_status = 'accepted'
        elif booking.status == 'cancelled':
            booking.quote_status = 'expired'
        else:
            booking.quote_status = 'draft'
    
    @staticmethod
    def _generate_quote_number(booking):
        """Generate a unique quote number for the booking"""
        
        if not booking.quote_number:
            # Generate quote number based on booking reference and timestamp
            timestamp = datetime.now().strftime('%m%d%H%M')
            booking.quote_number = f'QT{2509000 + booking.id:07d}({timestamp})'
    
    @staticmethod
    def _sync_quote_status(booking):
        """Sync quote status with booking status"""
        
        status_mapping = {
            'draft': 'draft',
            'quoted': 'active',
            'confirmed': 'accepted',
            'cancelled': 'expired',
            'completed': 'accepted'
        }
        
        booking.quote_status = status_mapping.get(booking.status, 'draft')
    
    @staticmethod
    def ensure_quote_data_fresh(booking):
        """
        Ensure quote data is fresh and up-to-date before PDF generation
        
        Args:
            booking: Booking model instance
        
        Returns:
            Booking: Updated booking instance with fresh quote data
        """
        try:            
            # Update quote metadata
            BookingQuoteSyncService._update_quote_metadata(booking)
            BookingQuoteSyncService._generate_quote_number(booking)
            BookingQuoteSyncService._sync_quote_status(booking)
            
            logger.info(f'Ensured fresh quote data for booking {booking.booking_reference}')
            return booking
            
        except Exception as e:
            logger.error(f'Error ensuring fresh quote data: {str(e)}')
            raise
    
    @staticmethod
    def validate_quote_data(booking):
        """
        Validate that booking has all required data for quote generation
        
        Args:
            booking: Booking model instance
            
        Returns:
            dict: Validation result with success flag and messages
        """
        validation_result = {
            'success': True,
            'warnings': [],
            'errors': []
        }
        
        # Check required fields
        if not booking.booking_reference:
            validation_result['errors'].append('Booking reference is required')
            validation_result['success'] = False
        
        if not booking.customer_id:
            validation_result['errors'].append('Customer is required')
            validation_result['success'] = False
        
        # Check passenger counts
        total_pax = (booking.adults or 0) + (booking.children or 0) + (booking.infants or 0)
        if total_pax == 0:
            validation_result['warnings'].append('No passengers specified')
        
        # Check pricing
        if not booking.total_amount or booking.total_amount <= 0:
            validation_result['warnings'].append('No total amount specified')
        
        # Check dates
        if not booking.traveling_period_start:
            validation_result['warnings'].append('Travel start date not specified')
        
        if not booking.traveling_period_end:
            validation_result['warnings'].append('Travel end date not specified')
        
        # Check description
        if not booking.description:
            validation_result['warnings'].append('No tour description provided')
        
        return validation_result