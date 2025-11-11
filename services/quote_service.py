"""
Quote Service for enhanced booking workflow
"""
from models.quote import Quote
from models.booking import Booking
from extensions import db
from services.booking_invoice import BookingInvoiceService
from decimal import Decimal
import os
import logging
from utils.logging_config import get_logger
from sqlalchemy.exc import IntegrityError

class QuoteService:
    """Service for quote management and generation"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.output_dir = 'static/generated'
        os.makedirs(self.output_dir, exist_ok=True)
        
    def create_quote_from_booking(self, booking):
        """Create quote from booking with pricing calculation"""
        try:
            self.logger.info(f"🎯 Creating quote from booking {booking.booking_reference}")
            
            # Calculate quote amounts from booking
            subtotal = self._calculate_subtotal(booking)
            tax_amount = self._calculate_tax(subtotal)
            total_amount = subtotal + tax_amount
            
            # Generate unique quote number starting from QT2509008 (updated)
            # Use raw SQL to avoid SQLAlchemy cache issues
            min_number = 2509008
            max_attempts = 10  # Prevent infinite loop
            
            for attempt in range(max_attempts):
                try:
                    # Find the highest existing quote number using raw SQL
                    result = db.session.execute(
                        db.text("SELECT quote_number FROM quotes WHERE quote_number LIKE 'QT%' ORDER BY CAST(SUBSTR(quote_number, 3) AS INTEGER) DESC LIMIT 1")
                    ).fetchone()
                    
                    if result and result.quote_number.startswith('QT'):
                        try:
                            # Extract numeric part from quote number
                            numeric_part = result.quote_number[2:]  # Remove 'QT' prefix
                            last_number = int(numeric_part)
                            # Use the higher value between last_number+1 and min_number
                            new_number = max(last_number + 1, min_number)
                        except (ValueError, IndexError):
                            # If parsing fails, start from QT5449112
                            new_number = min_number
                    else:
                        # No existing quote, start from QT5449112
                        new_number = min_number
                    
                    quote_number = f"QT{new_number}"
                    
                    # Check if this quote number already exists
                    exists_check = db.session.execute(
                        db.text("SELECT COUNT(*) as count FROM quotes WHERE quote_number = :quote_number"),
                        {"quote_number": quote_number}
                    ).fetchone()
                    
                    if exists_check.count == 0:
                        # Quote number is unique, break the loop
                        break
                    else:
                        # Quote number exists, increment and try again
                        min_number = new_number + 1
                        self.logger.warning(f"Quote number {quote_number} exists, trying next number")
                        
                except Exception as e:
                    self.logger.error(f"Error generating quote number (attempt {attempt + 1}): {e}")
                    if attempt == max_attempts - 1:
                        # Last attempt, use timestamp-based fallback
                        import time
                        timestamp = int(time.time())
                        quote_number = f"QT{timestamp}"
                        break
                    continue
            
            self.logger.info(f"Generated unique quote number: {quote_number}")
            
            # Use raw SQL to create quote (bypass SQLAlchemy ORM)
            insert_sql = """
            INSERT INTO quotes (
                quote_number, booking_id, quote_date, valid_until, status,
                subtotal, tax_rate, tax_amount, discount_amount, total_amount, 
                terms_conditions, notes, converted_to_invoice, share_token,
                is_public, currency, created_at, updated_at,
                title, description
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s
            )
            """
            
            from datetime import datetime, timedelta
            now = datetime.utcnow()
            
            # Generate share token
            import secrets
            share_token = secrets.token_urlsafe(16)
            
            params = (
                quote_number,
                booking.id,
                now,
                now + timedelta(days=30),
                'draft',
                float(subtotal),
                7.0,
                float(tax_amount),
                0.0,  # discount_amount
                float(total_amount),
                self._get_default_terms(),
                f"Quote for booking {booking.booking_reference}",
                False,
                share_token,
                True,  # is_public
                booking.currency or 'THB',
                now,
                now,
                f'Quote for {booking.party_name or booking.booking_reference}',
                'Tour package quote'
            )
            
            # Use raw MariaDB connection with UNIQUE constraint handling
            import mysql.connector
            
            mariadb_config = {
                'user': 'voucher_user',
                'password': 'voucher_secure_2024',
                'host': 'localhost',
                'port': 3306,
                'database': 'voucher_enhanced',
                'charset': 'utf8mb4'
            }
            
            conn = mysql.connector.connect(**mariadb_config)
            cursor = conn.cursor()
            
            try:
                cursor.execute(insert_sql, params)
                quote_id = cursor.lastrowid
                conn.commit()
                self.logger.info(f"✅ Quote {quote_number} created successfully with ID {quote_id}")
                
            except IntegrityError as e:
                conn.rollback()
                error_msg = str(e)
                if 'UNIQUE constraint failed: quotes.quote_number' in error_msg or 'Duplicate entry' in error_msg:
                    self.logger.error(f"❌ Quote number {quote_number} already exists - this should not happen with our generation logic")
                    # Generate a timestamp-based fallback quote number
                    import time
                    fallback_quote_number = f"QT{int(time.time())}"
                    fallback_params = list(params)
                    fallback_params[0] = fallback_quote_number  # Replace quote_number
                    
                    try:
                        cursor.execute(insert_sql, tuple(fallback_params))
                        quote_id = cursor.lastrowid
                        conn.commit()
                        self.logger.info(f"✅ Fallback quote {fallback_quote_number} created with ID {quote_id}")
                        quote_number = fallback_quote_number  # Update for return
                    except Exception as fallback_error:
                        conn.close()
                        raise Exception(f"Failed to create quote even with fallback: {fallback_error}")
                else:
                    conn.close()
                    raise e
            finally:
                conn.close()
            
            self.logger.info(f"✅ Quote {quote_number} created with ID {quote_id} for booking {booking.id}")
            
            # Return quote_id instead of MockQuote object
            return quote_id
            
        except Exception as e:
            self.logger.error(f"❌ Error creating quote from booking {booking.id}: {str(e)}")
            # No need for db.session.rollback() with raw connection
            raise
    
    def _calculate_subtotal(self, booking):
        """Calculate subtotal from booking products"""
        try:
            # Use existing booking calculation logic
            total = Decimal('0.00')
            
            if booking.products:
                import json
                products = json.loads(booking.products)
                
                for product in products:
                    price = Decimal(str(product.get('price', 0)))
                    quantity = int(product.get('quantity', 1))
                    product_total = price * quantity
                    total += product_total
            
            # Fallback to total_amount if no products
            if total == 0 and booking.total_amount:
                total = Decimal(str(booking.total_amount))
                
            return total
            
        except Exception as e:
            self.logger.warning(f"Error calculating subtotal, using fallback: {e}")
            # Fallback calculation
            return Decimal(str(booking.total_amount or 0))
    
    def _calculate_tax(self, subtotal):
        """Calculate tax amount (7% VAT)"""
        tax_rate = Decimal('0.07')
        return subtotal * tax_rate
    
    def _get_default_terms(self):
        """Get default terms and conditions"""
        return """Terms and Conditions:
1. Quote valid for 30 days from issue date
2. Prices subject to availability
3. Payment required before service delivery
4. Cancellation policy applies
5. All services subject to third-party availability"""
    
    def _create_external_quote(self, quote):
        """External quote creation removed"""
        # External integration disabled
        pass
    
    def generate_quote_pdf(self, quote):
        """Generate quote PDF using existing PDF generation with REAL-TIME booking data sync"""
        try:
            self.logger.info(f"🎯 Generating PDF for quote {quote.quote_number}")
            self.logger.info(f"📋 Quote booking ID: {quote.booking_id}")
            
            # ✅ CRITICAL: ดึงข้อมูล booking ใหม่แบบ Real-time ก่อนสร้าง PDF
            from services.universal_booking_extractor import UniversalBookingExtractor
            from models.booking import Booking
            
            fresh_booking = UniversalBookingExtractor.get_fresh_booking_data(quote.booking_id)
            if not fresh_booking:
                self.logger.error(f"❌ Cannot fetch fresh booking data for quote {quote.quote_number}")
                # Fallback to direct booking query
                fresh_booking = Booking.query.get(quote.booking_id)
            
            self.logger.info(f"📋 Quote booking reference: {fresh_booking.booking_reference if fresh_booking else 'No booking'}")
                
            self.logger.info(f"✅ Using FRESH booking data: {fresh_booking.booking_reference}")
            self.logger.info(f"📊 Fresh booking status: {fresh_booking.status}")
            self.logger.info(f"💰 Fresh booking amount: {fresh_booking.total_amount}")
            
            # Use TourVoucherGeneratorV2 but customize for quotes
            from services.tour_voucher_generator_v2 import TourVoucherGeneratorV2
            
            generator = TourVoucherGeneratorV2()
            
            # ✅ Generate PDF with FRESH booking data instead of cached data
            # This returns tuple (pdf_bytes, filename)
            pdf_result = generator.generate_quote_pdf_v2(quote, fresh_booking)  # Pass fresh booking
            
            # Extract pdf_bytes and filename from tuple
            if isinstance(pdf_result, tuple) and len(pdf_result) == 2:
                pdf_bytes, filename = pdf_result
                self.logger.info(f"✅ Quote PDF generated with FRESH data: {filename} ({len(pdf_bytes)} bytes)")
                return pdf_result  # Return the full tuple
            else:
                # Fallback if not tuple
                self.logger.info(f"✅ Quote PDF generated: {pdf_result}")
                return pdf_result
            
        except Exception as e:
            self.logger.error(f"❌ Error generating quote PDF: {str(e)}")
            import traceback
            self.logger.error(f"🔍 Full traceback: {traceback.format_exc()}")
            raise
