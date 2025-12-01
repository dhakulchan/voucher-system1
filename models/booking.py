from extensions import db
from utils.datetime_utils import naive_utc_now
import json

class Booking(db.Model):
    __tablename__ = 'bookings'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    booking_reference = db.Column(db.String(100), unique=True, nullable=False)
    
    # Quote and Invoice fields
    quote_id = db.Column(db.Integer)  # Missing field from database
    quote_number = db.Column(db.String(100))
    quote_status = db.Column(db.String(50))  # Missing field from database
    invoice_id = db.Column(db.Integer)  # Missing field from database
    invoice_number = db.Column(db.String(100))
    invoice_status = db.Column(db.String(20))  # paid, sent, draft, cancelled
    invoice_amount = db.Column(db.Numeric(10, 2))  # invoice amount
    is_paid = db.Column(db.Boolean, default=False)  # payment status
    invoice_paid_date = db.Column(db.DateTime)  # payment date
    
    # Booking Details
    booking_type = db.Column(db.String(50), nullable=False)  # 'tour', 'hotel', 'transport'
    status = db.Column(db.String(50), default='draft')  # Enhanced workflow status
    
    # Enhanced Workflow Status Management  
    STATUS_DRAFT = 'draft'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_QUOTED = 'quoted'
    STATUS_INVOICED = 'invoiced'
    STATUS_PAID = 'paid'
    STATUS_VOUCHERED = 'vouchered'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'
    
    # Workflow Timestamps
    confirmed_at = db.Column(db.DateTime)
    quoted_at = db.Column(db.DateTime) 
    invoiced_at = db.Column(db.DateTime)
    paid_at = db.Column(db.DateTime)
    vouchered_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    # Travel Information
    arrival_date = db.Column(db.Date)
    departure_date = db.Column(db.Date)
    traveling_period_start = db.Column(db.Date)
    traveling_period_end = db.Column(db.Date)
    
    # Guest Information
    adults = db.Column(db.Integer, default=1)  # Number of adults
    children = db.Column(db.Integer, default=0)  # Number of children
    total_pax = db.Column(db.Integer, default=1)
    infants = db.Column(db.Integer, default=0)  # Number of infants (under 2 years)
    guest_list = db.Column(db.Text)  # JSON string of guest names
    
    # Additional Booking Information
    party_name = db.Column(db.String(255))  # Party or group name
    party_code = db.Column(db.String(100))  # Party or group code
    description = db.Column(db.Text)  # Booking description
    
    # Admin & Management Fields
    admin_notes = db.Column(db.Text)  # Internal admin notes
    manager_memos = db.Column(db.Text)  # Manager memos
    # created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # Who created this booking - Temporarily commented
    
    # Hotel RO Specific Fields
    agency_reference = db.Column(db.String(100))
    hotel_name = db.Column(db.String(255))
    room_type = db.Column(db.String(100))
    special_request = db.Column(db.Text)
    
    # MPV Booking Specific Fields
    pickup_point = db.Column(db.String(255))
    destination = db.Column(db.String(255))
    pickup_time = db.Column(db.Time)
    vehicle_type = db.Column(db.String(100))
    
    # Tour Voucher Specific Fields
    internal_note = db.Column(db.Text)
    flight_info = db.Column(db.Text)
    daily_services = db.Column(db.Text)  # JSON string of daily services (reused for voucher rows)
    voucher_image_path = db.Column(db.String(255))  # relative path to uploaded voucher image
    voucher_images = db.Column(db.Text)  # JSON string of multiple voucher images
    voucher_album_ids = db.Column(db.Text)  # JSON string of selected voucher album IDs from library
    
    # Admin and Management Fields
    admin_notes = db.Column(db.Text)  # Admin notes - visible to admin users only
    manager_memos = db.Column(db.Text)  # Manager memos - important management notes
    
    # Payment Information Fields
    bank_received = db.Column(db.Text)  # Bank that received payment
    received_date = db.Column(db.Date)  # Date payment was received
    received_amount = db.Column(db.Numeric(10, 2))  # Amount received
    product_type = db.Column(db.Text)  # Type of product/service
    notes = db.Column(db.Text)  # Additional notes
    
    # Products & Calculation
    products = db.Column(db.Text)  # JSON string of products & calculation data
    
    # Financial
    total_amount = db.Column(db.Numeric(10, 2))
    currency = db.Column(db.String(10), default='THB')
    
    # Time and Deadline Management
    time_limit = db.Column(db.DateTime, nullable=False)  # Time limit for booking confirmation (Required)
    due_date = db.Column(db.Date)  # Due date for payment or action
    
    # Metadata
    created_at = db.Column(db.DateTime, default=naive_utc_now)
    updated_at = db.Column(db.DateTime, default=naive_utc_now, onupdate=naive_utc_now)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendors.id'))  # legacy usage
    supplier_id = db.Column(db.Integer, db.ForeignKey('vendors.id'))  # new Supplier FK (soft rename)
    supplier = db.relationship('Supplier', foreign_keys=[supplier_id], backref='bookings', lazy='joined')
    
    # Enhanced Relationships
    # quotes = db.relationship('Quote', back_populates='booking', cascade='all, delete-orphan')  # Temporarily disabled
    # customer relationship comes from Customer model's backref='customer'
    
    # Security - ใช้แบบง่ายๆ ก่อน โดยไม่เพิ่ม column ใหม่
    # share_token = db.Column(db.String(64), unique=True, nullable=True)  # Secure sharing token
    
    def __repr__(self):
        return f'<Booking {self.booking_reference}>'
    
    def get_guest_list(self):
        """Return guest list as Python list"""
        if self.guest_list:
            try:
                # Try JSON format first
                return json.loads(self.guest_list)
            except json.JSONDecodeError:
                # Handle legacy HTML format
                import re
                # First convert <br> tags to newlines
                text_with_breaks = self.guest_list.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
                # Remove all HTML tags
                clean_text = re.sub(r'<[^>]+>', '', text_with_breaks)
                # Split by newlines and filter empty lines
                lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
                return lines
        return []
    
    def set_guest_list(self, guests):
        """Set guest list from Python list"""
        if isinstance(guests, list):
            self.guest_list = json.dumps(guests)
        else:
            self.guest_list = guests
    
    def get_guest_list_for_edit(self):
        """Return guest list formatted for textarea editing"""
        guests = self.get_guest_list()
        if guests:
            # Handle both dictionary and string formats
            formatted_guests = []
            for guest in guests:
                if isinstance(guest, dict):
                    # Format dict as readable string
                    guest_str = f"{guest.get('name', 'Unknown')}"
                    if guest.get('nationality'):
                        guest_str += f" ({guest.get('nationality')})"
                    if guest.get('type'):
                        guest_str += f" - {guest.get('type')}"
                    if guest.get('special_needs'):
                        guest_str += f" - Special needs: {guest.get('special_needs')}"
                    formatted_guests.append(guest_str)
                else:
                    # Already a string
                    formatted_guests.append(str(guest))
            return '\n'.join(formatted_guests)
        return ''
    
    def generate_secure_token(self, expires_days=None):
        """Generate secure share token with expiration based on departure_date + 120 days"""
        import hashlib
        import hmac
        import base64
        from datetime import datetime, timedelta
        from flask import current_app
        
        # Calculate expiration based on departure_date + 120 days, or fallback to custom days
        if expires_days is None:
            # Use departure_date + 120 days if available
            if self.departure_date:
                departure_dt = self.departure_date
                # If departure_date is date object, convert to datetime
                if hasattr(departure_dt, 'date'):
                    departure_dt = departure_dt.date()
                # Calculate expiry as departure + 120 days
                expiry_date = datetime.combine(departure_dt, datetime.min.time()) + timedelta(days=120)
                exp = int(expiry_date.timestamp())
            else:
                # Fallback: 120 days from now if no departure_date
                exp = int((datetime.utcnow() + timedelta(days=120)).timestamp())
        else:
            # Use custom expires_days from parameter
            exp = int((datetime.utcnow() + timedelta(days=expires_days)).timestamp())
        
        ts_base = int((self.updated_at or self.created_at or datetime.utcnow()).timestamp())
        
        # สร้าง base data - use pipe separator to avoid confusion with timestamp numbers
        base_data = f"{self.id}|{ts_base}|{exp}"
        
        # สร้าง signature ด้วย HMAC - Use same secret key access as verification
        secret_key = current_app.config['SECRET_KEY'].encode('utf-8')
        full_signature = hmac.new(secret_key, base_data.encode(), hashlib.sha256).digest()
        signature = full_signature[:26]  # Use first 26 bytes to match verification
        
        # รวม base + signature แล้ว encode เป็น URL-safe base64
        combined = base_data.encode() + b"." + signature
        token = base64.urlsafe_b64encode(combined).decode().rstrip('=')
        return token
    
    def get_secure_share_url(self, base_url=""):
        """Get secure public share URL with departure_date + 120 days expiration"""
        token = self.generate_secure_token()  # Use departure_date + 120 days logic
        return f"{base_url}/public/booking/{token}"
    
    @staticmethod
    def verify_share_token(token):
        """Verify share token and return booking if valid"""
        import hmac
        import hashlib
        import base64
        from datetime import datetime
        from config import Config
        import logging
        
        logger = logging.getLogger(__name__)
        logger.info(f"Verifying token: {token[:20]}...")
        
        try:
            # Try URL-safe base64 first (used by generate_secure_token method)
            try:
                pad = '=' * (-len(token) % 4)
                decoded_data = base64.urlsafe_b64decode(token + pad)
            except Exception:
                # Fallback to regular base64 (used by booking_share_manager)
                decoded_data = base64.b64decode(token.encode('utf-8'))
            
            logger.info(f"Token decoded successfully, total length: {len(decoded_data)}")
            
            # Check for dot separator first (URL-safe format)
            if b'.' in decoded_data:
                base_data, signature = decoded_data.rsplit(b'.', 1)
                logger.info(f"URL-safe format: base length: {len(base_data)}, signature length: {len(signature)}")
            else:
                # Direct concatenation format (booking_share_manager format)
                if len(decoded_data) < 32:
                    logger.error("Token too short for direct format")
                    return None
                # Find where timestamp ends (after second colon + 10 digits)
                colon_positions = []
                for i, byte in enumerate(decoded_data):
                    if byte == ord(':'):
                        colon_positions.append(i)
                
                if len(colon_positions) < 2:
                    logger.error("Invalid token format - not enough colons")
                    return None
                
                second_colon = colon_positions[1]
                timestamp_end = second_colon + 11  # colon + 10 digit timestamp
                
                base_data = decoded_data[:timestamp_end]
                signature = decoded_data[timestamp_end:]
                logger.info(f"Direct format: base length: {len(base_data)}, signature length: {len(signature)}")
            
            # Support multiple signature lengths (15, 20, 21, 23, 24, 26, 28, 32 bytes)
            if len(signature) not in [15, 20, 21, 23, 24, 26, 28, 32]:
                logger.error(f"Invalid signature length: {len(signature)}, expected 15, 20, 21, 23, 24, 26, 28, or 32")
                return None
            
            # Parse base data
            try:
                # For URL-safe format, the base_data might contain binary data
                # We need to extract only the text part (booking_id:timestamp:expiry)
                if b'.' in decoded_data:
                    # Find printable ASCII part of base_data
                    text_end = len(base_data)
                    for i, byte in enumerate(base_data):
                        if byte < 32 or byte > 126:  # Non-printable ASCII
                            text_end = i
                            break
                    text_part = base_data[:text_end].decode('utf-8')
                    
                    # Remove trailing dot if present
                    if text_part.endswith('.'):
                        text_part = text_part[:-1]
                    
                    logger.info(f"Extracted text part: {text_part}")
                    
                    # Try pipe separator first (new format), then colon separator (old format)
                    if '|' in text_part:
                        parts = text_part.split('|')
                        logger.info(f"Using pipe separator, parts: {parts}")
                    else:
                        parts = text_part.split(':')
                        logger.info(f"Using colon separator, parts: {parts}")
                    
                    # If only 2 parts (booking_id:timestamp), add default expiry
                    if len(parts) == 2:
                        booking_id, ts_base = parts
                        # Add 30 days from timestamp as expiry
                        import time
                        expiry = int(ts_base) + (30 * 24 * 60 * 60)  # 30 days
                        parts = [booking_id, ts_base, str(expiry)]
                        logger.info(f"Added default expiry: {expiry}")
                else:
                    # For non-URL-safe format, try pipe separator first
                    text_data = base_data.decode('utf-8')
                    if '|' in text_data:
                        parts = text_data.split('|')
                        logger.info(f"Non-URL-safe using pipe separator, parts: {parts}")
                    else:
                        parts = text_data.split(':')
                        logger.info(f"Non-URL-safe using colon separator, parts: {parts}")
            except UnicodeDecodeError:
                # If decode fails, this might be a different format
                logger.error("Could not decode base data as UTF-8")
                return None
            
            if len(parts) != 3:
                logger.error(f"Invalid parts count: {len(parts)}, expected 3")
                return None
                
            booking_id, ts_base, exp = parts
            booking_id = int(booking_id)
            exp = int(exp)
            
            # Check expiration
            current_time = datetime.utcnow().timestamp()
            logger.info(f"Token expiry: {exp}, Current time: {current_time}")
            if current_time > exp:
                logger.warning("Token expired")
                return None  # Token expired
            
            # Get booking and verify signature - Handle datetime issues
            try:
                # Try using Session.get() instead of Query.get()
                from extensions import db
                booking = db.session.get(Booking, booking_id)
                if not booking:
                    logger.warning(f"Booking {booking_id} not found")
                    return None
                logger.info(f"Found booking {booking_id}")
            except Exception as e:
                logger.error(f"Database query error: {e}")
                # Fallback to direct SQL query
                try:
                    from sqlalchemy import text
                    result = db.session.execute(text('SELECT * FROM bookings WHERE id = :id'), {'id': booking_id}).fetchone()
                    if not result:
                        logger.warning(f"Booking {booking_id} not found via fallback")
                        return None
                    
                    # Create a minimal booking object for verification
                    booking = Booking()
                    booking.id = booking_id
                    logger.info(f"Found booking {booking_id} via direct SQL fallback")
                except Exception as e2:
                    logger.error(f"Fallback query also failed: {e2}")
                    return None
                
            # Verify signature - use Flask app's actual secret key
            from flask import current_app
            secret_key = current_app.config['SECRET_KEY'].encode('utf-8')
            
            # For URL-safe format, use the original text part for verification, not base_data which contains signature
            if b'.' in decoded_data:
                # Extract only the text part for signature verification
                if '|' in text_part:
                    parts_for_verification = text_part.split('|')
                else:
                    parts_for_verification = text_part.split(':')
                verification_text = '|'.join(parts_for_verification[:3])  # booking_id|timestamp|expiry
                verification_data = verification_text.encode('utf-8')
                logger.info(f"Using verification text: {verification_text}")
            else:
                verification_data = base_data
                logger.info(f"Using base_data for verification")
            
            # Try different signature algorithms based on signature length
            signature_verified = False
            
            if len(signature) == 32:
                # Standard SHA256 signature
                expected_sig = hmac.new(secret_key, verification_data, hashlib.sha256).digest()
                signature_verified = hmac.compare_digest(signature, expected_sig)
                logger.info(f"SHA256 verification: {signature_verified}")
                
            elif len(signature) == 24:
                # Truncated signature (first 24 bytes of SHA256)
                expected_sig_full = hmac.new(secret_key, verification_data, hashlib.sha256).digest()
                expected_sig = expected_sig_full[:24]
                signature_verified = hmac.compare_digest(signature, expected_sig)
                logger.info(f"Truncated SHA256 (24 bytes) verification: {signature_verified}")
                
            elif len(signature) == 26:
                # Truncated signature (first 26 bytes of SHA256)
                expected_sig_full = hmac.new(secret_key, verification_data, hashlib.sha256).digest()
                expected_sig = expected_sig_full[:26]
                signature_verified = hmac.compare_digest(signature, expected_sig)
                logger.info(f"Truncated SHA256 (26 bytes) verification: {signature_verified}")
                
            elif len(signature) == 23:
                # Truncated signature (first 23 bytes of SHA256)
                expected_sig_full = hmac.new(secret_key, verification_data, hashlib.sha256).digest()
                expected_sig = expected_sig_full[:23]
                signature_verified = hmac.compare_digest(signature, expected_sig)
                logger.info(f"Truncated SHA256 (23 bytes) verification: {signature_verified}")
                
            elif len(signature) == 15:
                # Truncated signature (first 15 bytes of SHA256)
                expected_sig_full = hmac.new(secret_key, verification_data, hashlib.sha256).digest()
                expected_sig = expected_sig_full[:15]
                signature_verified = hmac.compare_digest(signature, expected_sig)
                logger.info(f"Truncated SHA256 (15 bytes) verification: {signature_verified}")
                
            elif len(signature) == 28:
                # Alternative signature method
                expected_sig = hmac.new(secret_key, verification_data, hashlib.sha224).digest()
                signature_verified = hmac.compare_digest(signature, expected_sig)
                logger.info(f"SHA224 verification: {signature_verified}")
            
            logger.info(f"Secret key length: {len(secret_key)}")
            logger.info(f"Verification data: {verification_data}")
            logger.info(f"Signature length: {len(signature)}")
            logger.info(f"Signature verified: {signature_verified}")
            
            if signature_verified:
                logger.info("Token signature verified successfully")
                return booking
            else:
                logger.warning("Token signature verification failed")
                return None
                
        except Exception as e:
            logger.error(f"Token verification error: {str(e)}")
            return None
    
    def get_daily_services(self):
        """Return daily services as Python list"""
        if self.daily_services:
            try:
                return json.loads(self.daily_services)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_daily_services(self, services):
        """Set daily services from Python list"""
        if isinstance(services, list):
            self.daily_services = json.dumps(services)
        else:
            self.daily_services = services
    
    def get_products(self):
        """Return products list as Python list"""
        if self.products:
            try:
                return json.loads(self.products)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_products(self, products):
        """Set products list from Python list"""
        if isinstance(products, list):
            self.products = json.dumps(products)
        else:
            self.products = products
    
    def get_voucher_rows(self):
        """Return voucher rows (map from daily_services). Each row dict keys:
        arrival, departure, service_by, description, type
        Backward compatibility: if legacy keys (date, description) exist.
        """
        rows = self.get_daily_services()
        normalized = []
        for r in rows:
            if isinstance(r, dict):
                normalized.append({
                    'arrival': r.get('arrival') or r.get('date') or '',
                    'departure': r.get('departure') or r.get('departure_date') or '',
                    'service_by': r.get('service_by') or r.get('description') or '',
                    'description': r.get('description') or r.get('service_by') or '',
                    'type': r.get('type') or r.get('type_class') or r.get('type_class_pax') or ''
                })
        return normalized

    def set_voucher_rows(self, rows):
        """Persist voucher rows into daily_services JSON. Accept only list of dicts."""
        if isinstance(rows, list):
            safe = []
            for r in rows:
                if isinstance(r, dict):
                    safe.append({
                        'arrival': r.get('arrival',''),
                        'departure': r.get('departure',''),
                        'service_by': r.get('service_by',''),
                        'type': r.get('type','')
                    })
            self.daily_services = json.dumps(safe)

    def get_voucher_images(self):
        """Return voucher images as Python list"""
        if self.voucher_images:
            try:
                return json.loads(self.voucher_images)
            except json.JSONDecodeError:
                return []
        return []

    def set_voucher_images(self, images):
        """Set voucher images from Python list"""
        if isinstance(images, list):
            self.voucher_images = json.dumps(images)
        else:
            self.voucher_images = images

    def add_voucher_image(self, image_data):
        """Add a single voucher image to the list"""
        images = self.get_voucher_images()
        images.append(image_data)
        self.set_voucher_images(images)

    def remove_voucher_image(self, image_id):
        """Remove voucher image by ID"""
        images = self.get_voucher_images()
        images = [img for img in images if img.get('id') != image_id]
        self.set_voucher_images(images)
    
    def get_voucher_album_ids(self):
        """Get list of selected voucher album IDs"""
        if self.voucher_album_ids:
            try:
                return json.loads(self.voucher_album_ids)
            except:
                return []
        return []
    
    def set_voucher_album_ids(self, album_ids):
        """Set voucher album IDs"""
        if isinstance(album_ids, list):
            self.voucher_album_ids = json.dumps(album_ids)
        elif isinstance(album_ids, str):
            self.voucher_album_ids = album_ids
        else:
            self.voucher_album_ids = json.dumps([])
    
    def get_voucher_library_images(self):
        """Get voucher library images from selected album IDs"""
        import logging
        logger = logging.getLogger(__name__)
        
        album_ids = self.get_voucher_album_ids()
        logger.info(f"🔍 Booking {self.id}: voucher_album_ids = {album_ids}")
        
        if not album_ids:
            logger.warning(f"⚠️ Booking {self.id}: No album IDs selected")
            return []
        
        try:
            from models.voucher_album import VoucherAlbum
            import os
            
            # Fetch albums by IDs and create a dict for quick lookup
            albums = VoucherAlbum.query.filter(VoucherAlbum.id.in_(album_ids)).all()
            logger.info(f"📚 Found {len(albums)} albums in database for IDs: {album_ids}")
            
            # Create a dictionary mapping album_id -> album object
            album_dict = {album.id: album for album in albums}
            
            # Process albums in the order specified by album_ids (to maintain user's sort order)
            processed_images = []
            for album_id in album_ids:
                album = album_dict.get(album_id)
                if not album:
                    logger.warning(f"  ⚠️ Album ID {album_id} not found in database")
                    continue
                    
                logger.info(f"  Processing album {album.id}: {album.title} - path: {album.image_path}")
                if album.image_path:
                    # Remove 'static/' prefix if it exists in the path
                    image_path = album.image_path
                    if image_path.startswith('static/'):
                        image_path = image_path[7:]  # Remove 'static/' prefix
                    
                    # Try different path combinations for production/development
                    possible_paths = [
                        os.path.join('/home/ubuntu/voucher-ro_v1.0/static', image_path),  # Production
                        os.path.join('/opt/bitnami/apache/htdocs/static', image_path),   # Bitnami
                        os.path.join(os.getcwd(), 'static', image_path)                   # Development
                    ]
                    
                    found = False
                    for abs_path in possible_paths:
                        if os.path.exists(abs_path):
                            file_url = f"file://{abs_path}"
                            processed_images.append({
                                'url': file_url,
                                'title': album.title,
                                'remarks': album.remarks,
                                'id': album.id
                            })
                            logger.info(f"  ✅ Found image at: {abs_path}")
                            found = True
                            break
                    
                    if not found:
                        logger.warning(f"  ⚠️ Image file not found for album {album.id}. Tried: {possible_paths}")
            
            logger.info(f"✅ Returning {len(processed_images)} processed library images")
            return processed_images
        except Exception as e:
            logger.error(f"❌ Error getting voucher library images: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []

    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'booking_reference': self.booking_reference,
            'quote_id': self.quote_id,
            'quote_number': self.quote_number,
            'quote_status': self.quote_status,
            'invoice_id': self.invoice_id,
            'invoice_number': self.invoice_number,
            'booking_type': self.booking_type,
            'status': self.status,
            'arrival_date': self.arrival_date.isoformat() if self.arrival_date else None,
            'departure_date': self.departure_date.isoformat() if self.departure_date else None,
            'traveling_period_start': self.traveling_period_start.isoformat() if self.traveling_period_start else None,
            'traveling_period_end': self.traveling_period_end.isoformat() if self.traveling_period_end else None,
            'adults': self.adults,
            'children': self.children,
            'total_pax': self.total_pax,
            'infants': self.infants,
            'party_name': self.party_name,
            'party_code': self.party_code,
            'description': self.description,
            'guest_list': self.get_guest_list(),
            'agency_reference': self.agency_reference,
            'hotel_name': self.hotel_name,
            'room_type': self.room_type,
            'special_request': self.special_request,
            'pickup_point': self.pickup_point,
            'destination': self.destination,
            'pickup_time': self.pickup_time.strftime('%H:%M') if self.pickup_time else None,
            'vehicle_type': self.vehicle_type,
            'internal_note': self.internal_note,
            'flight_info': self.flight_info,
            'admin_notes': self.admin_notes,
            'manager_memos': self.manager_memos,
            'daily_services': self.get_daily_services(),
            'products': self.get_products(),
            'voucher_image_path': self.voucher_image_path,
            'voucher_images': self.get_voucher_images(),
            'voucher_rows': self.get_voucher_rows(),
            'total_amount': float(self.total_amount) if self.total_amount else None,
            'currency': self.currency,
            'time_limit': self.time_limit.isoformat() if self.time_limit else None,
                        'due_date': self.due_date.isoformat() if self.due_date else None,
        }
    
    def is_invoice_paid(self):
        """Check if invoice is paid"""
        return self.invoice_status and self.invoice_status.lower() in ['paid', 'payment_complete']
    
    def can_create_voucher(self):
        """Check if voucher can be created (invoice paid + booking confirmed)"""
        return (self.status == 'confirmed' and 
                self.is_invoice_paid() and 
                self.invoice_number)
    
    def get_payment_status_display(self):
        """Get user-friendly payment status"""
        if self.is_invoice_paid():
            return 'PAID'
    
    # Role-based Permission Methods
    def can_edit_products(self, user):
        """Check if user can edit products/packages"""
        if not user:
            return False
        return user.role in ['Administrator', 'Operation']
    
    def can_view_admin_section(self, user):
        """Check if user can view admin notes and manager memos"""
        if not user:
            return False
        return user.role == 'Administrator'
    
    def can_edit_admin_notes(self, user):
        """Check if user can edit admin notes"""
        if not user:
            return False
        return user.role == 'Administrator'
    
    def can_edit_manager_memos(self, user):
        """Check if user can edit manager memos"""
        if not user:
            return False
        return user.role in ['Administrator', 'Operation']
    
    def can_create_booking(self, user):
        """Check if user can create new bookings"""
        if not user:
            return False
        return user.role in ['Administrator', 'Operation', 'Staff']
    
    def can_edit_booking(self, user):
        """Check if user can edit booking details"""
        if not user:
            return False
        if user.role == 'Administrator':
            return True
        if user.role == 'Operation':
            return True
        if user.role == 'Staff':
            # Staff can only edit their own created bookings and only if not confirmed
            return (self.created_by == user.id and 
                    self.status not in ['confirmed', 'invoiced', 'voucher_generated'])
        return False
    
    def can_delete_booking(self, user):
        """Check if user can delete bookings"""
        if not user:
            return False
        if user.role == 'Administrator':
            return True
        if user.role == 'Operation':
            # Operation can delete only if not invoiced or voucher generated
            return self.status not in ['invoiced', 'voucher_generated']
        return False
    
    def can_view_financial_info(self, user):
        """Check if user can view pricing and financial information"""
        if not user:
            return False
        return user.role in ['Administrator', 'Operation']

    # Enhanced Workflow Methods
    def can_create_quote(self):
        """Check if booking can create quote"""
        return self.status == self.STATUS_CONFIRMED
    
    def can_apply_to_invoice(self):
        """Check if quote can be applied to invoice"""
        return self.status == self.STATUS_QUOTED and self.quotes
    
    def can_generate_voucher(self):
        """Check if can generate voucher"""
        return self.status in [self.STATUS_PAID, 'vouchered']
    
    def confirm_booking(self):
        """Confirm booking - Step 1"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"🔧 Starting confirm_booking for booking {self.id}")
        
        try:
            self.status = self.STATUS_CONFIRMED
            logger.info(f"✅ Status set to {self.STATUS_CONFIRMED} for booking {self.id}")
        except Exception as status_error:
            logger.error(f"❌ Error setting status for booking {self.id}: {str(status_error)}")
            raise status_error
            
        try:
            # Try to set timestamp if column exists
            confirmed_at_value = naive_utc_now()
            logger.info(f"🕒 Setting confirmed_at to {confirmed_at_value} for booking {self.id}")
            self.confirmed_at = confirmed_at_value
            logger.info(f"✅ confirmed_at set successfully for booking {self.id}")
        except AttributeError as attr_error:
            # Column doesn't exist in database - skip timestamp
            logger.warning(f"⚠️ confirmed_at column doesn't exist for booking {self.id}: {str(attr_error)}")
            pass
        except Exception as timestamp_error:
            logger.error(f"❌ Error setting confirmed_at for booking {self.id}: {str(timestamp_error)}")
            raise timestamp_error
            
        logger.info(f"✅ confirm_booking completed for booking {self.id}")
        
    def mark_as_quoted(self):
        """Mark as quoted - Step 2"""
        self.status = self.STATUS_QUOTED
        try:
            # Try to set timestamp if column exists
            self.quoted_at = naive_utc_now()
        except AttributeError:
            # Column doesn't exist in database - skip timestamp
            pass
        
    def mark_as_invoiced(self):
        """Mark as invoiced - Step 3"""
        self.status = self.STATUS_INVOICED 
        try:
            # Try to set timestamp if column exists
            self.invoiced_at = naive_utc_now()
        except AttributeError:
            # Column doesn't exist in database - skip timestamp
            pass
        
    def mark_as_paid(self):
        """Mark as paid - Step 4"""
        self.status = self.STATUS_PAID
        try:
            # Try to set timestamp if column exists
            self.paid_at = naive_utc_now()
        except AttributeError:
            # Column doesn't exist in database - skip timestamp
            pass
        
    def mark_as_vouchered(self):
        """Mark as vouchered - Step 5"""
        self.status = self.STATUS_VOUCHERED
        try:
            # Try to set timestamp if column exists
            self.vouchered_at = naive_utc_now()
        except AttributeError:
            # Column doesn't exist in database - skip timestamp
            pass
        
    def get_payment_status_display(self):
        """Get human readable payment status"""
        if self.invoice_status:
            return self.invoice_status.upper()
        elif self.invoice_number:
            return 'PENDING'
        else:
            return 'NO INVOICE'
    
    def needs_invoice_sync(self):
        """Check if invoice sync is needed"""
        # Sync needed if:
        # 1. Has quote but no invoice data
        # 2. Has invoice but not paid
        # 3. Haven't synced recently
        return (self.quote_id and 
                (not self.invoice_number or not self.is_invoice_paid()))
