"""
Tour Voucher WeasyPrint Generator V2
Using HTML template with WeasyPrint for better Thai font support and modern styling
"""

import os
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS
from utils.logging_config import get_logger
from services.qr_generator import QRGenerator


class TourVoucherWeasyPrintV2:
    """Tour Voucher Generator V2 using WeasyPrint and HTML template"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.output_dir = self._ensure_output_dir()
        self.qr_generator = QRGenerator()
        
        # Setup Jinja2 environment
        template_dir = os.path.join(os.getcwd(), 'templates')
        self.jinja_env = Environment(loader=FileSystemLoader(template_dir))
        
        # Register custom filters
        self.jinja_env.filters['nl2br'] = self._nl2br_filter
    
    def _nl2br_filter(self, text):
        """Convert newlines to <br> tags for HTML"""
        if text is None:
            return ''
        import re
        text = str(text).replace('\r\n', '\n').replace('\r', '\n')
        return re.sub(r'\n', '<br>\n', text)
        
    def _ensure_output_dir(self):
        """Ensure output directory exists - support both dev and production"""
        # Priority order: check writable paths first
        possible_paths = [
            '/home/ubuntu/voucher-ro_v1.0/static/generated',  # Production (home)
            '/opt/bitnami/apache/htdocs/static/generated',     # Production (Bitnami)
            os.path.join(os.getcwd(), 'static', 'generated')   # Development
        ]
        
        output_dir = None
        for path in possible_paths:
            try:
                # Try to create directory
                os.makedirs(path, exist_ok=True)
                # Test if we can write to it
                test_file = os.path.join(path, '.write_test')
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                # If we got here, this path is writable
                output_dir = path
                os.chmod(path, 0o755)  # Ensure proper permissions
                break
            except (PermissionError, OSError):
                # This path is not writable, try next
                continue
        
        if not output_dir:
            # Fallback to current directory
            output_dir = os.path.join(os.getcwd(), 'static', 'generated')
            os.makedirs(output_dir, exist_ok=True)
        
        return output_dir
        
    def generate_tour_voucher_v2(self, booking) -> str:
        """Generate tour voucher PDF using HTML template V2 and return filename"""
        try:
            self.logger.info(f"🎨 Generating Tour Voucher V2 for booking {getattr(booking, 'booking_reference', 'UNKNOWN')}")
            
            # Generate QR code for booking
            qr_code_path = None
            try:
                booking_ref = getattr(booking, 'booking_reference', '')
                if booking_ref:
                    qr_url = f"https://dhakulchan.com/booking/{booking_ref}"
                    qr_code_path = self.qr_generator.generate_voucher_qr(booking)
                    if qr_code_path:
                        # Convert to relative path for template
                        qr_code_path = f"file://{os.path.abspath(qr_code_path)}"
            except Exception as e:
                self.logger.warning(f"Failed to generate QR code: {e}")
                
            # Create booking wrapper with proper methods for template
            class BookingWrapper:
                def __init__(self, booking):
                    self._booking = booking
                    # Copy all attributes
                    for attr in dir(booking):
                        if not attr.startswith('_') and hasattr(booking, attr):
                            try:
                                setattr(self, attr, getattr(booking, attr))
                            except:
                                pass
                
                def get_daily_services(self):
                    """Get daily services as list of dictionaries"""
                    self.logger.info(f"🔍 Daily services debug - hasattr get_daily_services: {hasattr(self._booking, 'get_daily_services')}")
                    self.logger.info(f"🔍 Daily services debug - hasattr daily_services: {hasattr(self._booking, 'daily_services')}")
                    
                    try:
                        if hasattr(self._booking, 'get_daily_services'):
                            services = self._booking.get_daily_services()
                            self.logger.info(f"🔍 Raw get_daily_services(): {repr(services)}")
                            if services:
                                return services
                    except Exception as e:
                        self.logger.error(f"❌ Error calling get_daily_services(): {e}")
                    
                    try:
                        if hasattr(self._booking, 'daily_services') and self._booking.daily_services:
                            self.logger.info(f"🔍 Raw daily_services: {repr(self._booking.daily_services)}")
                            import json
                            services = json.loads(self._booking.daily_services)
                            self.logger.info(f"✅ Parsed daily_services: {repr(services)}")
                            return services
                    except Exception as e:
                        self.logger.error(f"❌ Error parsing daily_services JSON: {e}")
                    
                    # Create fallback service data based on booking information
                    self.logger.info("⚠️ No daily services found, creating fallback data")
                    fallback_services = []
                    
                    # Try to create basic service entries
                    if hasattr(self._booking, 'traveling_period_start') and self._booking.traveling_period_start:
                        fallback_services.append({
                            'date': self._booking.traveling_period_start.strftime('%d/%m/%Y'),
                            'departure_date': self._booking.traveling_period_end.strftime('%d/%m/%Y') if hasattr(self._booking, 'traveling_period_end') and self._booking.traveling_period_end else 'DD/MM/YYYY',
                            'description': self._booking.description or self._booking.hotel_name or 'Hotel/Accommodation/Transfer',
                            'type': self._booking.room_type or 'Accommodation'
                        })
                    
                    return fallback_services
                
                def get_customer_name_with_id(self):
                    """Get customer name without reference ID"""
                    try:
                        # Try to access customer through relationship first
                        if hasattr(self._booking, 'customer') and self._booking.customer:
                            customer_name = getattr(self._booking.customer, 'name', None)
                            if customer_name:
                                return customer_name
                        
                        # Try to access customer data through customer_id
                        if hasattr(self._booking, 'customer_id') and self._booking.customer_id:
                            # Import here to avoid circular imports
                            from models.customer import Customer
                            from extensions import db
                            
                            # Query customer by ID
                            customer = db.session.query(Customer).filter_by(id=self._booking.customer_id).first()
                            if customer and customer.name:
                                return customer.name
                        
                        # Fall back to party_name
                        if hasattr(self._booking, 'party_name') and self._booking.party_name:
                            return self._booking.party_name
                        
                        # Final fallback
                        return "Customer"
                        
                    except Exception as e:
                        self.logger.error(f"❌ Error getting customer name: {e}")
                        return "Customer"
                
                def get_voucher_images(self):
                    """Get voucher images as list with file:// URLs for WeasyPrint (includes uploaded + library images)"""
                    try:
                        processed_images = []
                        
                        # 1. Get uploaded voucher images first
                        if hasattr(self._booking, 'get_voucher_images'):
                            images = self._booking.get_voucher_images()
                            if images:
                                # Convert Flask URLs to absolute file:// URLs for WeasyPrint
                                for image in images:
                                    if isinstance(image, dict):
                                        # Handle different data structures
                                        image_url = None
                                        
                                        # Try different URL/path fields
                                        if 'url' in image and image['url']:
                                            image_url = image['url']
                                        elif 'path' in image and image['path']:
                                            image_path = image['path']
                                        elif 'filename' in image and image['filename']:
                                            image_path = image['filename']
                                        else:
                                            continue
                                        
                                        # Process the URL/path
                                        if image_url:
                                            # Handle Flask static URLs like /static/uploads/...
                                            if image_url.startswith('/static/'):
                                                # Remove /static/ prefix and make absolute path
                                                relative_path = image_url[8:]  # Remove '/static/'
                                                import os
                                                abs_path = os.path.join(os.getcwd(), 'static', relative_path)
                                                if os.path.exists(abs_path):
                                                    file_url = f"file://{abs_path}"
                                                    processed_images.append({
                                                        'url': file_url,
                                                        'original': image
                                                    })
                                                    continue
                                            elif image_url.startswith(('http://', 'https://')):
                                                # External URL - use as is
                                                processed_images.append({
                                                    'url': image_url,
                                                    'title': image.get('title', 'Voucher Image'),
                                                    'original': image
                                                })
                                                continue
                                        
                                        # Fallback to path-based processing
                                        if 'path' in image:
                                            image_path = image['path']
                                        elif 'filename' in image:
                                            image_path = image['filename']
                                        else:
                                            continue
                                        
                                        if image_path and not image_path.startswith(('http://', 'https://', 'file://')):
                                            import os
                                            # Try different path combinations
                                            possible_paths = [
                                                os.path.join(os.getcwd(), 'static', image_path),
                                                os.path.join(os.getcwd(), 'static', 'uploads', 'voucher_images', image_path),
                                                os.path.join(os.getcwd(), image_path)
                                            ]
                                            
                                            for abs_path in possible_paths:
                                                if os.path.exists(abs_path):
                                                    file_url = f"file://{abs_path}"
                                                    processed_images.append({
                                                        'url': file_url,
                                                        'title': image.get('title', 'Voucher Image'),
                                                        'original': image
                                                    })
                                                    break
                                    else:
                                        # If it's just a string path
                                        image_path = str(image)
                                        if image_path and not image_path.startswith(('http://', 'https://', 'file://')):
                                            import os
                                            abs_path = os.path.join(os.getcwd(), 'static', 'uploads', 'voucher_images', image_path)
                                            if os.path.exists(abs_path):
                                                file_url = f"file://{abs_path}"
                                                processed_images.append({
                                                    'url': file_url,
                                                    'title': image if isinstance(image, str) else 'Voucher Image',
                                                    'original': image
                                                })
                                
                        self.logger.info(f"✅ Found {len(processed_images)} uploaded voucher images")
                        
                        # 2. Get Voucher Library images (appended after uploaded images)
                        if hasattr(self._booking, 'get_voucher_library_images'):
                            library_images = self._booking.get_voucher_library_images()
                            if library_images:
                                self.logger.info(f"📚 Found {len(library_images)} library images")
                                processed_images.extend(library_images)
                        
                        self.logger.info(f"✅ Total {len(processed_images)} voucher images (uploaded + library)")
                        return processed_images
                        
                        # Try direct attribute access (fallback)
                        if hasattr(self._booking, 'voucher_images') and self._booking.voucher_images:
                            import json
                            images = json.loads(self._booking.voucher_images)
                            if images:
                                # Process same as above but for direct access
                                for image in images:
                                    if isinstance(image, dict) and 'url' in image:
                                        image_url = image['url']
                                        if image_url.startswith('/static/'):
                                            relative_path = image_url[8:]
                                            import os
                                            abs_path = os.path.join(os.getcwd(), 'static', relative_path)
                                            if os.path.exists(abs_path):
                                                file_url = f"file://{abs_path}"
                                                processed_images.append({
                                                    'url': file_url,
                                                    'title': image.get('title', 'Voucher Image'),
                                                    'original': image
                                                })
                                
                                self.logger.info(f"✅ Found {len(processed_images)} voucher images via direct access")
                        
                        # Also add library images in fallback mode
                        if hasattr(self._booking, 'get_voucher_library_images'):
                            library_images = self._booking.get_voucher_library_images()
                            if library_images:
                                self.logger.info(f"📚 Found {len(library_images)} library images (fallback)")
                                processed_images.extend(library_images)
                        
                        return processed_images
                        
                    except Exception as e:
                        self.logger.error(f"❌ Error getting voucher images: {e}")
                        return []
                
                def get_voucher_library_images(self):
                    """Get voucher library images from selected album IDs"""
                    try:
                        self.logger.info(f"🔍 Checking for voucher library images...")
                        if hasattr(self._booking, 'get_voucher_library_images'):
                            self.logger.info(f"✅ Booking has get_voucher_library_images method")
                            images = self._booking.get_voucher_library_images()
                            self.logger.info(f"📸 Retrieved {len(images) if images else 0} library images")
                            if images:
                                for idx, img in enumerate(images):
                                    self.logger.info(f"  Image {idx+1}: {img.get('title', 'No title')} - {img.get('url', 'No URL')}")
                                return images
                            else:
                                self.logger.warning(f"⚠️ No library images found")
                        else:
                            self.logger.warning(f"⚠️ Booking doesn't have get_voucher_library_images method")
                        return []
                    except Exception as e:
                        self.logger.error(f"❌ Error getting voucher library images: {e}")
                        import traceback
                        self.logger.error(f"Traceback: {traceback.format_exc()}")
                        return []
                
                def get_guest_list(self):
                    """Get guest list properly with Thai character support and Unicode decoding"""
                    def decode_unicode_string(text):
                        """Decode Unicode escape sequences in string"""
                        if isinstance(text, str):
                            try:
                                # Handle Unicode escape sequences like \u0e23\u0e32\u0e22...
                                decoded = text.encode('utf-8').decode('unicode_escape').encode('latin1').decode('utf-8')
                                return decoded
                            except:
                                try:
                                    # Alternative method for Unicode decoding
                                    decoded = text.encode().decode('unicode_escape')
                                    return decoded
                                except:
                                    return text
                        return text
                    
                    def process_guest_list(guest_data):
                        """Process guest list to proper format"""
                        self.logger.info(f"🔍 Processing guest_data type: {type(guest_data)}, value: {repr(guest_data)}")
                        
                        if isinstance(guest_data, list):
                            # Handle list - decode each item and join with line breaks
                            decoded_guests = []
                            for item in guest_data:
                                decoded_item = decode_unicode_string(str(item))
                                if decoded_item and decoded_item.strip():  # Skip empty items
                                    decoded_guests.append(decoded_item)
                            result = '\n'.join(decoded_guests)
                            self.logger.info(f"✅ List processed to: {repr(result)}")
                            return result
                        elif isinstance(guest_data, str):
                            # Handle string - try to parse as JSON first
                            try:
                                import json
                                parsed = json.loads(guest_data)
                                self.logger.info(f"🔍 String parsed as JSON: {repr(parsed)}")
                                return process_guest_list(parsed)  # Recursive call for parsed data
                            except Exception as e:
                                # If not JSON, treat as plain text and decode
                                self.logger.info(f"🔍 String not JSON (error: {e}), treating as plain text")
                                result = decode_unicode_string(guest_data)
                                self.logger.info(f"✅ String processed to: {repr(result)}")
                                return result
                        else:
                            result = decode_unicode_string(str(guest_data))
                            self.logger.info(f"✅ Other type processed to: {repr(result)}")
                            return result
                    
                    # Debug logging
                    self.logger.info(f"🔍 Guest list debug - booking object: {repr(self._booking)}")
                    self.logger.info(f"🔍 Guest list debug - hasattr get_guest_list: {hasattr(self._booking, 'get_guest_list')}")
                    self.logger.info(f"🔍 Guest list debug - hasattr guest_list: {hasattr(self._booking, 'guest_list')}")
                    
                    try:
                        if hasattr(self._booking, 'get_guest_list'):
                            guest_list = self._booking.get_guest_list()
                            self.logger.info(f"🔍 Raw get_guest_list(): {repr(guest_list)}")
                            if guest_list:
                                if isinstance(guest_list, list):
                                    # Convert list to string with line breaks
                                    result = '\n'.join(str(guest) for guest in guest_list if guest and str(guest).strip())
                                    self.logger.info(f"✅ List converted to string: {repr(result)}")
                                    return result
                                else:
                                    result = process_guest_list(guest_list)
                                    self.logger.info(f"✅ Final result from get_guest_list(): {repr(result)}")
                                    return result
                    except Exception as e:
                        self.logger.error(f"❌ Error calling get_guest_list(): {e}")
                    
                    try:
                        if hasattr(self._booking, 'guest_list') and self._booking.guest_list:
                            guest_list = self._booking.guest_list
                            self.logger.info(f"🔍 Raw guest_list attribute: {repr(guest_list)}")
                            result = process_guest_list(guest_list)
                            self.logger.info(f"✅ Final result from guest_list: {repr(result)}")
                            return result
                    except Exception as e:
                        self.logger.error(f"❌ Error processing guest_list: {e}")
                    
                    self.logger.warning("⚠️ No guest list found, returning default")
                    return 'No guest information available'
            
            booking_wrapper = BookingWrapper(booking)
                
            # Prepare template data
            template_data = {
                'booking': booking_wrapper,
                'qr_code_path': qr_code_path,
                'now': datetime.now(),
                'config': {
                    'COMPANY_LICENSE': '11/12345',
                    'TAT_LICENSE': 'TAT-123456'
                },
                'is_completed': False  # ✅ ปิดการแสดงหน้า Thank You สำหรับทุก status
            }
            
            # Load and render template
            template = self.jinja_env.get_template('pdf/tour_voucher_template_v2_sample.html')
            html_content = template.render(**template_data)
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            booking_ref = getattr(booking, 'booking_reference', 'UNKNOWN')
            filename = f"Tour_voucher_v2_{booking_ref}_{timestamp}.pdf"
            filepath = os.path.join(self.output_dir, filename)
            
            # Generate PDF using WeasyPrint
            base_url = f"file://{os.getcwd()}/"
            html_doc = HTML(string=html_content, base_url=base_url)
            
            # Add CSS for better styling
            css_styles = CSS(string="""
                @page {
                    size: A4;
                    margin: 20mm 15mm 20mm 15mm;
                    @bottom-center {
                        content: "Page " counter(page) " of " counter(pages);
                        font-size: 10px;
                        color: #666;
                    }
                }
                
                body {
                    font-family: 'Noto Sans Thai', 'Segoe UI', Arial, sans-serif;
                }
            """)
            
            # Generate PDF with compatibility fix for pydyf 0.10.0
            pdf_bytes = html_doc.write_pdf(stylesheets=[css_styles])
            
            # Write bytes to file
            with open(filepath, 'wb') as f:
                f.write(pdf_bytes)
            
            self.logger.info(f"✅ Tour Voucher V2 PDF generated successfully: {filename}")
            return filename
            
        except Exception as e:
            self.logger.error(f"❌ Failed to generate Tour Voucher V2 PDF: {str(e)}")
            import traceback
            self.logger.error(f"❌ Traceback: {traceback.format_exc()}")
            raise e
            
    def generate_tour_voucher_v2_bytes(self, booking) -> bytes:
        """Generate tour voucher PDF using HTML template V2 and return bytes"""
        try:
            self.logger.info(f"🎨 Generating Tour Voucher V2 bytes for booking {getattr(booking, 'booking_reference', 'UNKNOWN')}")
            
            # Generate QR code for booking
            qr_code_path = None
            try:
                booking_ref = getattr(booking, 'booking_reference', '')
                if booking_ref:
                    qr_url = f"https://dhakulchan.com/booking/{booking_ref}"
                    qr_code_path = self.qr_generator.generate_voucher_qr(booking)
                    if qr_code_path:
                        # Convert to relative path for template
                        qr_code_path = f"file://{os.path.abspath(qr_code_path)}"
            except Exception as e:
                self.logger.warning(f"Failed to generate QR code: {e}")
                
            # Prepare template data
            template_data = {
                'booking': booking,
                'qr_code_path': qr_code_path,
                'now': datetime.now(),
                'is_completed': False,  # ✅ ปิดการแสดงหน้า Thank You สำหรับทุก status
                'config': {
                    'COMPANY_LICENSE': '11/12345',
                    'TAT_LICENSE': 'TAT-123456'
                }
            }
            
            # Load and render template
            template = self.jinja_env.get_template('pdf/tour_voucher_template_v2_sample.html')
            html_content = template.render(**template_data)
            
            # Generate PDF using WeasyPrint
            base_url = f"file://{os.getcwd()}/"
            html_doc = HTML(string=html_content, base_url=base_url)
            
            # Add CSS for better styling
            css_styles = CSS(string="""
                @page {
                    size: A4;
                    margin: 20mm 15mm 20mm 15mm;
                    @bottom-center {
                        content: "Page " counter(page) " of " counter(pages);
                        font-size: 10px;
                        color: #666;
                    }
                }
                
                body {
                    font-family: 'Noto Sans Thai', 'Segoe UI', Arial, sans-serif;
                }
            """)
            
            pdf_bytes = html_doc.write_pdf(stylesheets=[css_styles])
            
            self.logger.info(f"✅ Tour Voucher V2 PDF bytes generated successfully")
            return pdf_bytes
            
        except Exception as e:
            self.logger.error(f"❌ Failed to generate Tour Voucher V2 PDF bytes: {str(e)}")
            import traceback
            self.logger.error(f"❌ Traceback: {traceback.format_exc()}")
            raise e
            
    def generate_tour_voucher_png(self, booking) -> str:
        """Generate tour voucher PNG (currently returns PDF filename)"""
        # For now, return PDF filename
        # TODO: Implement PDF to PNG conversion if needed
        return self.generate_tour_voucher_v2(booking)