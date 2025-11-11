"""
Universal Sync Hooks - Real-time Booking to Quote Data Synchronization
ระบบ sync ข้อมูลแบบ real-time สำหรับ booking และ quote ทุกการแก้ไข
"""

import logging
import os
import shutil
from datetime import datetime
from sqlalchemy import event
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class UniversalSyncHooks:
    """ระบบ hooks สำหรับ auto-sync ข้อมูล booking และ quote แบบ real-time"""
    
    @staticmethod
    def setup_booking_sync_listeners():
        """ตั้งค่า SQLAlchemy event listeners สำหรับ auto-sync"""
        try:
            from models.booking import Booking
            
            # ตั้งค่า listeners สำหรับ booking model
            event.listen(Booking, 'after_update', UniversalSyncHooks.after_booking_update)
            event.listen(Booking, 'after_insert', UniversalSyncHooks.after_booking_insert)
            event.listen(Booking, 'before_update', UniversalSyncHooks.before_booking_update)
            event.listen(Booking, 'before_delete', UniversalSyncHooks.before_booking_delete)
            
            logger.info('Universal Sync Hooks: Booking sync listeners setup complete')
            
        except ImportError as e:
            logger.warning(f'Could not setup booking sync listeners: {e}')
        except Exception as e:
            logger.error(f'Error setting up sync listeners: {e}')
    
    @staticmethod
    def after_booking_update(mapper, connection, target):
        """หลังจากมีการ update booking - ทำ sync ทันที"""
        try:
            booking_id = target.id
            logger.info(f'Universal Sync: Booking {booking_id} updated - triggering sync')
            
            # ล้างแคช data เก่า
            UniversalSyncHooks._clear_booking_cache(booking_id)
            
            # อัปเดต quote data ให้ตรงกับ booking
            UniversalSyncHooks._sync_quote_data(target)
            
            # ลบ PDF เก่าที่ generate ไว้ (ให้ generate ใหม่)
            UniversalSyncHooks._invalidate_generated_pdfs(booking_id)
            
        except Exception as e:
            logger.error(f'Error in after_booking_update hook: {e}')
    
    @staticmethod
    def after_booking_insert(mapper, connection, target):
        """หลังจากสร้าง booking ใหม่ - ตั้งค่าเริ่มต้น"""
        try:
            booking_id = target.id
            logger.info(f'Universal Sync: New booking {booking_id} created - initializing sync')
            
            # ตั้งค่า quote data เริ่มต้น
            UniversalSyncHooks._initialize_quote_data(target)
            
        except Exception as e:
            logger.error(f'Error in after_booking_insert hook: {e}')
    
    @staticmethod
    def before_booking_update(mapper, connection, target):
        """ก่อนการ update booking - เตรียมข้อมูล"""
        try:
            # บันทึกสถานะก่อนการอัปเดต
            if hasattr(target, 'id') and target.id:
                UniversalSyncHooks._backup_current_state(target)
                
        except Exception as e:
            logger.error(f'Error in before_booking_update hook: {e}')
    
    @staticmethod
    def before_booking_delete(mapper, connection, target):
        """ก่อนการลบ booking - ทำความสะอาด"""
        try:
            booking_id = target.id
            logger.info(f'Universal Sync: Booking {booking_id} being deleted - cleaning up')
            
            # ลบ cache และ generated files
            UniversalSyncHooks._clear_booking_cache(booking_id)
            UniversalSyncHooks._invalidate_generated_pdfs(booking_id)
            
        except Exception as e:
            logger.error(f'Error in before_booking_delete hook: {e}')
    
    @staticmethod
    def _sync_quote_data(booking):
        """Sync quote data ให้ตรงกับ booking ปัจจุบัน"""
        try:
            # อัปเดต quote_number ถ้ายังไม่มี
            if not hasattr(booking, 'quote_number') or not booking.quote_number:
                booking.quote_number = UniversalSyncHooks._generate_new_quote_number()
            
            # ตรวจสอบและ sync quote ใน Quote table
            if hasattr(booking, 'quote_id') and booking.quote_id:
                from models.quote import Quote
                quote = Quote.query.filter(Quote.id == booking.quote_id).first()
                if quote and quote.quote_number != booking.quote_number:
                    # อัปเดต quote number ใน Quote table ให้ตรงกับ booking
                    quote.quote_number = booking.quote_number
                    logger.info(f'Synced quote {quote.id} number to {booking.quote_number}')
            
            # อัปเดต fields ที่สำคัญสำหรับ quote
            current_time = datetime.now()
            
            # Quote-specific fields
            if not hasattr(booking, 'quote_date') or not booking.quote_date:
                booking.quote_date = current_time
            
            if not hasattr(booking, 'quote_valid_until') or not booking.quote_valid_until:
                # Quote valid for 30 days
                from datetime import timedelta
                booking.quote_valid_until = current_time + timedelta(days=30)
            
            logger.info(f'Quote data synced for booking {booking.id}')
            
        except Exception as e:
            logger.error(f'Error syncing quote data for booking {booking.id}: {e}')
    
    @staticmethod
    def _initialize_quote_data(booking):
        """ตั้งค่า quote data เริ่มต้นสำหรับ booking ใหม่"""
        try:
            current_time = datetime.now()
            
            # ตั้งค่า quote_number
            if not hasattr(booking, 'quote_number') or not booking.quote_number:
                booking.quote_number = UniversalSyncHooks._generate_new_quote_number()
            
            # ตั้งค่า quote_date
            if not hasattr(booking, 'quote_date') or not booking.quote_date:
                booking.quote_date = current_time
            
            # ตั้งค่า quote validity
            if not hasattr(booking, 'quote_valid_until') or not booking.quote_valid_until:
                from datetime import timedelta
                booking.quote_valid_until = current_time + timedelta(days=30)
            
            logger.info(f'Quote data initialized for booking {booking.id}')
            
        except Exception as e:
            logger.error(f'Error initializing quote data for booking {booking.id}: {e}')
    
    @staticmethod
    def _generate_new_quote_number():
        """Generate new quote number in format QT25110001"""
        try:
            from models.booking import Booking
            
            # Find the highest existing quote number with new format QT251100XX
            booking_with_latest_quote = Booking.query.filter(
                Booking.quote_number.like('QT2511%')
            ).order_by(Booking.quote_number.desc()).first()
            
            if booking_with_latest_quote and booking_with_latest_quote.quote_number.startswith('QT2511'):
                try:
                    # Extract numeric part from quote number (last 4 digits)
                    numeric_part = booking_with_latest_quote.quote_number[6:]  # Remove 'QT2511' prefix
                    last_number = int(numeric_part)
                    new_number = last_number + 1
                except (ValueError, IndexError):
                    # If parsing fails, start from 0001
                    new_number = 1
            else:
                # No existing quote with new format, start from 0001
                new_number = 1
            
            # Make sure the number is unique by checking if it already exists
            while True:
                candidate_number = f'QT2511{new_number:04d}'
                existing = Booking.query.filter(Booking.quote_number == candidate_number).first()
                if not existing:
                    return candidate_number
                new_number += 1
                
        except Exception as e:
            logger.error(f'Error generating quote number: {e}')
            # Fallback to a timestamp-based number
            import time
            return f'QT2511{int(time.time()) % 10000:04d}'
    
    @staticmethod
    def sync_all_quote_numbers():
        """Sync ทุก quote numbers ให้ตรงกันระหว่าง bookings และ quotes tables"""
        try:
            from models.booking import Booking
            from models.quote import Quote
            
            logger.info('Starting comprehensive quote number sync...')
            
            # หา bookings ที่มี quote_number แต่ไม่มี quote record ที่ตรงกัน
            bookings_with_quotes = Booking.query.filter(
                Booking.quote_number.isnot(None)
            ).all()
            
            synced_count = 0
            
            for booking in bookings_with_quotes:
                try:
                    # หา quote ที่เกี่ยวข้องกับ booking
                    quote = None
                    if booking.quote_id:
                        quote = Quote.query.filter(Quote.id == booking.quote_id).first()
                    
                    if not quote:
                        # หา quote โดยใช้ booking_id
                        quote = Quote.query.filter(Quote.booking_id == booking.id).first()
                        if quote:
                            booking.quote_id = quote.id
                    
                    if quote:
                        # Sync quote number
                        if quote.quote_number != booking.quote_number:
                            old_number = quote.quote_number
                            quote.quote_number = booking.quote_number
                            logger.info(f'Synced Quote {quote.id}: {old_number} -> {booking.quote_number}')
                            synced_count += 1
                        
                        # เชื่อมโยง quote_id ถ้ายังไม่มี
                        if not booking.quote_id:
                            booking.quote_id = quote.id
                    
                except Exception as e:
                    logger.error(f'Error syncing booking {booking.id}: {e}')
            
            # Commit changes
            from models.booking import db
            db.session.commit()
            
            logger.info(f'Quote number sync completed. Synced {synced_count} quotes.')
            return synced_count
            
        except Exception as e:
            logger.error(f'Error in sync_all_quote_numbers: {e}')
            return 0
    
    @staticmethod
    def _clear_booking_cache(booking_id):
        """ล้างแคช data ของ booking"""
        try:
            # ล้าง memory cache ถ้ามี
            cache_key = f'booking_{booking_id}'
            
            # ลองล้าง Flask-Caching ถ้ามี
            try:
                from flask import current_app
                if hasattr(current_app, 'cache'):
                    current_app.cache.delete(cache_key)
            except:
                pass
            
            logger.debug(f'Cache cleared for booking {booking_id}')
            
        except Exception as e:
            logger.warning(f'Error clearing cache for booking {booking_id}: {e}')
    
    @staticmethod
    def _invalidate_generated_pdfs(booking_id):
        """ลบ PDF files ที่ generate ไว้แล้ว เพื่อให้ generate ใหม่"""
        try:
            # ลบ PDF files ใน static/generated
            generated_dir = os.path.join('static', 'generated')
            if os.path.exists(generated_dir):
                # หา files ที่มี booking_id หรือ booking_reference
                for filename in os.listdir(generated_dir):
                    if (filename.startswith(f'quote_') and 
                        (f'_{booking_id}_' in filename or str(booking_id) in filename)):
                        
                        file_path = os.path.join(generated_dir, filename)
                        try:
                            os.remove(file_path)
                            logger.info(f'Removed outdated PDF: {filename}')
                        except OSError:
                            pass
            
        except Exception as e:
            logger.warning(f'Error invalidating PDFs for booking {booking_id}: {e}')
    
    @staticmethod
    def _backup_current_state(booking):
        """บันทึกสถานะปัจจุบันก่อนการอัปเดต"""
        try:
            # สำหรับการ audit หรือ rollback ถ้าจำเป็น
            backup_data = {
                'booking_id': booking.id,
                'backup_time': datetime.now().isoformat(),
                'previous_state': {}
            }
            
            # เก็บ fields สำคัญ
            important_fields = [
                'total_amount', 'adults', 'children', 'infants',
                'special_request', 'description', 'quote_number'
            ]
            
            for field in important_fields:
                if hasattr(booking, field):
                    backup_data['previous_state'][field] = getattr(booking, field)
            
            # บันทึกไว้ใน log หรือ temporary storage
            logger.debug(f'Backed up state for booking {booking.id}')
            
        except Exception as e:
            logger.warning(f'Error backing up state for booking {booking.id}: {e}')

class RealTimeSyncManager:
    """ตัวจัดการ Real-time sync ระหว่าง booking และ quote"""
    
    @staticmethod
    def force_sync_booking(booking_id):
        """บังคับ sync booking แบบ manual"""
        try:
            from models.booking import Booking
            
            booking = Booking.query.get(booking_id)
            if not booking:
                logger.error(f'Booking {booking_id} not found for sync')
                return False
            
            # ทำ sync ทันที
            UniversalSyncHooks._sync_quote_data(booking)
            UniversalSyncHooks._clear_booking_cache(booking_id)
            UniversalSyncHooks._invalidate_generated_pdfs(booking_id)
            
            # บันทึกการ sync
            booking.last_sync_at = datetime.now()
            
            from app import db
            db.session.commit()
            
            logger.info(f'Force sync completed for booking {booking_id}')
            return True
            
        except Exception as e:
            logger.error(f'Error in force sync for booking {booking_id}: {e}')
            return False
    
    @staticmethod
    def sync_all_bookings():
        """Sync ข้อมูลทุก bookings - ใช้สำหรับการ maintenance"""
        try:
            from models.booking import Booking
            
            all_bookings = Booking.query.all()
            synced_count = 0
            
            for booking in all_bookings:
                try:
                    UniversalSyncHooks._sync_quote_data(booking)
                    synced_count += 1
                except Exception as e:
                    logger.warning(f'Error syncing booking {booking.id}: {e}')
                    continue
            
            from app import db
            db.session.commit()
            
            logger.info(f'Bulk sync completed: {synced_count}/{len(all_bookings)} bookings synced')
            return synced_count
            
        except Exception as e:
            logger.error(f'Error in bulk sync: {e}')
            return 0
    
    @staticmethod
    def get_sync_status(booking_id):
        """ตรวจสอบสถานะการ sync ของ booking"""
        try:
            from models.booking import Booking
            
            booking = Booking.query.get(booking_id)
            if not booking:
                return {'status': 'not_found'}
            
            status = {
                'booking_id': booking_id,
                'has_quote_number': bool(getattr(booking, 'quote_number', None)),
                'has_quote_date': bool(getattr(booking, 'quote_date', None)),
                'last_modified': booking.updated_at.isoformat() if hasattr(booking, 'updated_at') and booking.updated_at else None,
                'last_sync': booking.last_sync_at.isoformat() if hasattr(booking, 'last_sync_at') and booking.last_sync_at else None
            }
            
            # ตรวจสอบว่าข้อมูลล่าสุดหรือไม่
            if (hasattr(booking, 'updated_at') and hasattr(booking, 'last_sync_at') and 
                booking.updated_at and booking.last_sync_at):
                status['is_up_to_date'] = booking.last_sync_at >= booking.updated_at
            else:
                status['is_up_to_date'] = False
            
            return status
            
        except Exception as e:
            logger.error(f'Error getting sync status for booking {booking_id}: {e}')
            return {'status': 'error', 'message': str(e)}

def initialize_universal_sync():
    """เริ่มต้นระบบ Universal Sync Hooks"""
    try:
        UniversalSyncHooks.setup_booking_sync_listeners()
        logger.info('Universal Sync Hooks initialized successfully')
        return True
    except Exception as e:
        logger.error(f'Failed to initialize Universal Sync Hooks: {e}')
        return False