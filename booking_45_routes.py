"""
Special Route Handler for Booking #45
แก้ปัญหา datetime corruption โดยใช้ raw MariaDB connection
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from mariadb_helper import get_mariadb_cursor
import logging

class SimpleBooking:
    """Wrapper class to make dictionary data compatible with template object expectations"""
    def __init__(self, booking_data):
        # Copy all data from dictionary to object attributes
        for key, value in booking_data.items():
            # Convert numeric fields to proper types for template compatibility
            if key in ['total_amount', 'adults', 'children', 'infants', 'total_pax'] and value:
                try:
                    if key == 'total_amount':
                        setattr(self, key, float(value))
                    else:
                        setattr(self, key, int(value))
                except (ValueError, TypeError):
                    setattr(self, key, value)
            else:
                setattr(self, key, value)
    
    def get_products(self):
        """Return products list for template compatibility"""
        print(f"🔍 DEBUG: get_products called")
        print(f"🔍 DEBUG: self.products exists: {hasattr(self, 'products')}")
        if hasattr(self, 'products'):
            print(f"🔍 DEBUG: self.products value: {self.products}")
            print(f"🔍 DEBUG: self.products type: {type(self.products)}")
        
        if hasattr(self, 'products') and self.products:
            try:
                import json
                if isinstance(self.products, str):
                    parsed = json.loads(self.products)
                    print(f"🔍 DEBUG: Parsed {len(parsed)} products from JSON")
                    return parsed
                elif isinstance(self.products, list):
                    print(f"🔍 DEBUG: Returning {len(self.products)} products from list")
                    return self.products
            except Exception as e:
                print(f"🔍 DEBUG: Error parsing products: {e}")
                return []
        print(f"🔍 DEBUG: No products found, returning empty list")
        return []
    
    def get_guest_list(self):
        """Return guest list for template compatibility"""
        guest_list = getattr(self, 'guest_list', '')
        return guest_list if guest_list else ''
    
    def get_guest_list_for_edit(self):
        """Return guest list formatted for editing"""
        guest_list = getattr(self, 'guest_list', '')
        if guest_list:
            try:
                import json
                import html
                import re
                
                # Try to parse as JSON first
                parsed_list = json.loads(guest_list)
                if type(parsed_list).__name__ == 'list':
                    # Process each guest item to clean HTML
                    formatted_guests = []
                    for guest in parsed_list:
                        if type(guest).__name__ == 'dict':
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
                            # Clean HTML from string
                            guest_str = str(guest)
                            
                            # Decode HTML entities first
                            guest_str = html.unescape(guest_str)
                            
                            # Convert <br> tags to newlines before removing HTML
                            guest_str = re.sub(r'<br\s*/?>', '\n', guest_str, flags=re.IGNORECASE)
                            
                            # Remove all other HTML tags
                            guest_str = re.sub(r'<[^>]+>', '', guest_str)
                            
                            # Clean up extra whitespace and empty lines
                            lines = [line.strip() for line in guest_str.split('\n') if line.strip()]
                            
                            if lines:
                                formatted_guests.extend(lines)
                    
                    return '\n'.join(formatted_guests)
                else:
                    return str(guest_list)
            except Exception as e:
                # If JSON parsing fails, return as-is
                return str(guest_list)
        return ''
    
    def get_activity_logs(self):
        """Return activity logs for view template compatibility"""
        return getattr(self, 'activity_logs', [])
    
    def __getattr__(self, name):
        """Fallback for any missing attributes"""
        # Special handling for attributes that should be lists
        if name in ['activity_logs', 'products']:
            return []
        return None

class SimpleCustomer:
    """Simple customer object for template compatibility"""
    def __init__(self, name=None, email=None, phone=None):
        self.name = name
        self.email = email
        self.phone = phone

class SafeDatetime:
    """Wrapper class to make string datetime values compatible with template datetime operations"""
    def __init__(self, datetime_str):
        self.datetime_str = str(datetime_str) if datetime_str else ""
        self._parsed_datetime = None
        
    def __str__(self):
        return self.datetime_str
    
    def __repr__(self):
        return f"SafeDatetime('{self.datetime_str}')"
    
    def strftime(self, format_str):
        """Handle .strftime() calls from templates"""
        if not self.datetime_str:
            return ""
        
        # Try to parse the datetime string if not already parsed
        if not self._parsed_datetime:
            try:
                # Common datetime formats to try
                formats = [
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%d',
                    '%d/%m/%Y %H:%M:%S',
                    '%d/%m/%Y',
                    '%Y-%m-%d %H:%M',
                    '%d/%m/%Y %H:%M'
                ]
                
                for fmt in formats:
                    try:
                        from datetime import datetime
                        self._parsed_datetime = datetime.strptime(self.datetime_str, fmt)
                        break
                    except ValueError:
                        continue
                        
                # If parsing fails, return the original string
                if not self._parsed_datetime:
                    return self.datetime_str
                    
            except Exception:
                return self.datetime_str
        
        try:
            return self._parsed_datetime.strftime(format_str)
        except Exception:
            return self.datetime_str
    
    def __bool__(self):
        """For truthiness checks in templates"""
        return bool(self.datetime_str)
    
    def __eq__(self, other):
        """For comparison operations"""
        if isinstance(other, SafeDatetime):
            return self.datetime_str == other.datetime_str
        return self.datetime_str == str(other)
    
    # Make it behave like the original string in most contexts
    def __getattr__(self, name):
        return getattr(self.datetime_str, name)

logger = logging.getLogger(__name__)

# Create blueprint for booking #45 special handling
booking_45_bp = Blueprint('booking_45', __name__)

@booking_45_bp.route('/booking/view/45')
@login_required
def view_booking_45():
    """Special handler for viewing booking #45 to bypass datetime corruption"""
    try:
        print("🔍 Entering view_booking_45 function")
        
        # Get booking data using raw MariaDB
        with get_mariadb_cursor() as (cursor, conn):
            print("🔍 Connected to MariaDB for view")
            cursor.execute("""
                SELECT 
                    b.*,
                    c.name as customer_name,
                    c.email as customer_email,
                    c.phone as customer_phone,
                    c.first_name as customer_first_name,
                    c.last_name as customer_last_name
                FROM bookings b
                LEFT JOIN customers c ON b.customer_id = c.id
                WHERE b.id = 45
            """)
            
            result = cursor.fetchone()
            print(f"🔍 Query result: {result is not None}")
            
            if not result:
                flash('Booking #45 not found', 'error')
                print("🔍 No booking found - redirecting")
                return redirect(url_for('booking.list'))
            
            # Convert to dictionary
            columns = [desc[0] for desc in cursor.description]
            booking_data = dict(zip(columns, result))
            print(f"🔍 Booking data loaded: {len(booking_data)} fields")
            
        # Convert ALL date/time related fields to SafeDatetime objects for template compatibility
        # First pass: handle known datetime fields
        datetime_field_names = [
            'time_limit', 'created_at', 'updated_at', 'confirmed_at', 
            'quoted_at', 'invoiced_at', 'paid_at', 'vouchered_at', 
            'invoice_paid_date', 'date', 'datetime', 'timestamp',
            'arrival_date', 'departure_date', 'traveling_period_start',
            'traveling_period_end', 'due_date'
        ]
        
        print(f"📊 Original time_limit value: {booking_data.get('time_limit')} (type: {type(booking_data.get('time_limit'))})")
        
        for field_name in datetime_field_names:
            if field_name in booking_data and booking_data[field_name]:
                original_value = booking_data[field_name]
                booking_data[field_name] = SafeDatetime(booking_data[field_name])
                print(f"🔄 Converted {field_name}: {original_value} -> {booking_data[field_name]} (type: {type(booking_data[field_name])})")
        
        # Second pass: catch any remaining fields that might contain datetime data
        for key, value in booking_data.items():
            if value and isinstance(value, str):
                # Check if it looks like a date/time string pattern
                if any(x in key.lower() for x in ['date', 'time', 'created', 'updated', 'at']) and not isinstance(value, SafeDatetime):
                    original_value = value
                    booking_data[key] = SafeDatetime(value)
                    print(f"🔄 Second pass converted {key}: {original_value} -> {booking_data[key]} (type: {type(booking_data[key])})")
        
        print(f"📊 Final time_limit value: {booking_data.get('time_limit')} (type: {type(booking_data.get('time_limit'))})")
        
        # Debug products field from database - DON'T override with empty list!
        print(f"🔍 View - Original products from DB: {booking_data.get('products')} (type: {type(booking_data.get('products'))})")
            
        # Create customer object for template compatibility
        customer_obj = SimpleCustomer()
        if booking_data.get('customer_name'):
            customer_obj.name = booking_data['customer_name']
            customer_obj.email = booking_data.get('customer_email', '')
            customer_obj.phone = booking_data.get('customer_phone', '')
            customer_obj.first_name = booking_data.get('customer_first_name', '')
            customer_obj.last_name = booking_data.get('customer_last_name', '')
        
        booking_data['customer'] = customer_obj
        
        # Load activity logs for the booking
        activity_list = []
        try:
            with get_mariadb_cursor() as (cursor, conn):
                cursor.execute("""
                    SELECT al.id, al.action, al.description, al.created_at, al.user_id, u.username
                    FROM activity_logs al
                    LEFT JOIN users u ON al.user_id = u.id
                    WHERE al.description LIKE %s
                    ORDER BY al.created_at DESC
                    LIMIT 20
                """, (f'%BOOKING #45%',))
                
                activity_logs = cursor.fetchall()
                print(f"🔍 Found {len(activity_logs) if activity_logs else 0} activity logs for booking #45")
                
                # Convert tuples to simple objects for template compatibility
                if activity_logs:
                    for log in activity_logs:
                        log_obj = type('ActivityLog', (), {})()
                        log_obj.id = log[0] if log[0] is not None else 0
                        log_obj.action = log[1] if log[1] is not None else 'unknown'
                        log_obj.description = log[2] if log[2] is not None else ''
                        log_obj.created_at = log[3] if log[3] is not None else None
                        log_obj.user_id = log[4] if log[4] is not None else None
                        
                        # Add user object if available
                        if log[5]:  # username
                            user_obj = type('User', (), {})()
                            user_obj.username = log[5]
                            log_obj.user = user_obj
                        else:
                            log_obj.user = None
                            
                        activity_list.append(log_obj)
                        
                print(f"🔍 Converted {len(activity_list)} activity logs to objects")
                if activity_list:
                    print(f"🔍 First activity: {activity_list[0].action} - {activity_list[0].description[:50]}...")
        except Exception as e:
            print(f"🔍 Error loading activity logs: {e}")
            activity_list = []  # Ensure it's always a list
        
        # Create booking object wrapper for template compatibility
        booking_obj = SimpleBooking(booking_data)
        
        # Add activity logs to booking object using setattr to ensure it's properly set
        setattr(booking_obj, 'activity_logs', activity_list)
        print(f"🔍 Set booking_obj.activity_logs with {len(activity_list)} logs using setattr")
        print(f"🔍 booking_obj.activity_logs type: {type(booking_obj.activity_logs)}")
        print(f"🔍 booking_obj.activity_logs is None: {booking_obj.activity_logs is None}")
        print(f"🔍 booking_obj.__dict__: {booking_obj.__dict__.keys()}")
        
        # Test direct access
        print(f"🔍 Direct access test: {getattr(booking_obj, 'activity_logs', 'NOT_FOUND')}")
        
        # Ensure activity_logs is never None for template safety
        if not hasattr(booking_obj, 'activity_logs') or booking_obj.activity_logs is None:
            setattr(booking_obj, 'activity_logs', [])
            print(f"🔍 Set activity_logs to empty list as fallback using setattr")
        
        # Debug products for view
        test_products = booking_obj.get_products()
        print(f"🎯 VIEW - booking_obj.get_products() returns: {test_products}")
        
        # Debug total_amount issue
        print(f"🔍 Original total_amount: {booking_data.get('total_amount')} (type: {type(booking_data.get('total_amount'))})")
        print(f"🔍 booking_obj.total_amount: {booking_obj.total_amount} (type: {type(booking_obj.total_amount)})")
        
        print(f"🔍 About to render view template with booking object type: {type(booking_obj)}")
        logger.info(f"✅ Successfully loaded booking #45 for view: {booking_data.get('booking_reference', 'N/A')}")
        
        # Check current language
        from flask import session
        current_language = session.get('language', 'en')
        template_name = f'booking/view_{current_language}.html'
        
        # Try to render with language-specific template, fallback to English
        try:
            return render_template(template_name, booking=booking_obj, special_mode=True)
        except:
            return render_template('booking/view_en.html', booking=booking_obj, special_mode=True)
        
    except Exception as e:
        print(f"🔍 Exception in view_booking_45: {e}")
        logger.error(f"❌ Error loading booking #45 for view: {e}", exc_info=True)
        flash(f'Database error loading booking #45 view: {str(e)}', 'error')
        return redirect(url_for('booking.list'))

@booking_45_bp.route('/booking/edit/45')
@login_required
def edit_booking_45():
    """Special handler for booking #45 to bypass datetime corruption"""
    try:
        print("🔍 Entering edit_booking_45 function")
        
        # Get booking data using raw MariaDB
        with get_mariadb_cursor() as (cursor, conn):
            print("🔍 Connected to MariaDB")
            cursor.execute("""
                SELECT 
                    b.*,
                    c.name as customer_name,
                    c.email as customer_email,
                    c.phone as customer_phone
                FROM bookings b
                LEFT JOIN customers c ON b.customer_id = c.id
                WHERE b.id = 45
            """)
            
            result = cursor.fetchone()
            print(f"🔍 Query result: {result is not None}")
            
            if not result:
                flash('Booking #45 not found', 'error')
                print("🔍 No booking found - redirecting")
                return redirect(url_for('booking.list'))
            
            # Convert to dictionary
            columns = [desc[0] for desc in cursor.description]
            booking_data = dict(zip(columns, result))
            print(f"🔍 Booking data loaded: {len(booking_data)} fields")
            
        # Convert ALL date/time related fields to SafeDatetime objects for template compatibility
        # First pass: handle known datetime fields
        datetime_field_names = [
            'time_limit', 'created_at', 'updated_at', 'confirmed_at', 
            'quoted_at', 'invoiced_at', 'paid_at', 'vouchered_at', 
            'invoice_paid_date', 'date', 'datetime', 'timestamp'
        ]
        
        print(f"📊 Original time_limit value: {booking_data.get('time_limit')} (type: {type(booking_data.get('time_limit'))})")
        
        for field_name in datetime_field_names:
            if field_name in booking_data and booking_data[field_name]:
                original_value = booking_data[field_name]
                booking_data[field_name] = SafeDatetime(booking_data[field_name])
                print(f"🔄 Converted {field_name}: {original_value} -> {booking_data[field_name]} (type: {type(booking_data[field_name])})")
        
        # Second pass: catch any remaining fields that might contain datetime data
        for key, value in booking_data.items():
            if value and isinstance(value, str):
                # Check if it looks like a date/time string pattern
                if any(x in key.lower() for x in ['date', 'time', 'created', 'updated', 'at']) and not isinstance(value, SafeDatetime):
                    original_value = value
                    booking_data[key] = SafeDatetime(value)
                    print(f"🔄 Second pass converted {key}: {original_value} -> {booking_data[key]} (type: {type(booking_data[key])})")
        
        print(f"📊 Final time_limit value: {booking_data.get('time_limit')} (type: {type(booking_data.get('time_limit'))})")
        
        # Debug products field from database - DON'T override with empty list!
        print(f"🔍 Original products from DB: {booking_data.get('products')} (type: {type(booking_data.get('products'))})")
            
        # Create customer object for template compatibility
        customer_obj = SimpleCustomer()
        if booking_data.get('customer_name'):
            customer_obj.name = booking_data['customer_name']
            customer_obj.email = booking_data.get('customer_email', '')
            customer_obj.phone = booking_data.get('customer_phone', '')
        
        booking_data['customer'] = customer_obj
        
        # Create booking object wrapper for template compatibility
        booking_obj = SimpleBooking(booking_data)
        
        # Debug final products from booking object
        test_products = booking_obj.get_products()
        print(f"🎯 FINAL booking_obj.get_products() returns: {test_products}")
        
        print(f"🔍 About to render template with booking object type: {type(booking_obj)}")
        print(f"🔍 Booking has get_products method: {hasattr(booking_obj, 'get_products')}")
        print(f"🔍 Booking time_limit type: {type(booking_obj.time_limit)}")
        logger.info(f"✅ Successfully loaded booking #45 data: {booking_data.get('booking_reference', 'N/A')}")
        return render_template('booking/edit.html', booking=booking_obj, special_mode=True)
        
    except Exception as e:
        print(f"🔍 Exception in edit_booking_45: {e}")
        logger.error(f"❌ Error loading booking #45: {e}", exc_info=True)
        flash(f'Database error loading booking #45: {str(e)}', 'error')
        return redirect(url_for('booking.list'))

@booking_45_bp.route('/booking/edit/45', methods=['POST'])
@login_required  
def update_booking_45():
    """Special handler for updating booking #45"""
    try:
        # Get form data
        form_data = request.form.to_dict()
        
        # Debug products data from form
        print(f"🔍 Form data received for booking #45 update:")
        print(f"🔍 Raw form keys: {list(form_data.keys())}")
        print(f"🔍 Total amount in form: {form_data.get('total_amount', 'NOT FOUND')}")
        print(f"🚨 BOOKING #45 EDIT FORM DATA RECEIVED:")
        print(f"   admin_notes: '{form_data.get('admin_notes', 'NOT_FOUND')}'")
        print(f"   manager_memos: '{form_data.get('manager_memos', 'NOT_FOUND')}'")
        print(f"   internal_note: '{form_data.get('internal_note', 'NOT_FOUND')}'")
        print(f"   guest_list: '{form_data.get('guest_list', 'NOT_FOUND')}'")
        print(f"   special_request: '{form_data.get('special_request', 'NOT_FOUND')}'")
        print(f"   flight_info: '{form_data.get('flight_info', 'NOT_FOUND')}'")
        print(f"🔍 End debug form data")
        
        # Handle products array data
        products_data = []
        product_index = 0
        while True:
            name_key = f'products[{product_index}][name]'
            quantity_key = f'products[{product_index}][quantity]'
            price_key = f'products[{product_index}][price]'
            amount_key = f'products[{product_index}][amount]'
            
            if name_key not in form_data:
                break
                
            product = {
                'name': form_data.get(name_key, ''),
                'quantity': float(form_data.get(quantity_key, 1)),
                'price': float(form_data.get(price_key, 0)),
                'amount': float(form_data.get(amount_key, 0))
            }
            
            # Only add non-empty products
            if product['name'].strip():
                products_data.append(product)
            
            product_index += 1
        
        print(f"🔍 Parsed products data: {products_data}")
        
        # Convert products to JSON string for database storage
        import json
        products_json = json.dumps(products_data) if products_data else '[]'
        
        # Prepare update query
        updates = []
        values = []
        
        # Safe fields to update
        safe_fields = {
            'adults': 'adults',
            'children': 'children',
            'infants': 'infants', 
            'total_pax': 'total_pax',
            'pickup_point': 'pickup_point',
            'pickup_time': 'pickup_time',
            'total_amount': 'total_amount',
            'status': 'status',
            'currency': 'currency',
            'notes': 'notes',
            'party_name': 'party_name',
            'description': 'description',
            'admin_notes': 'admin_notes',
            'manager_memos': 'manager_memos',
            'internal_note': 'internal_note',
            'guest_list': 'guest_list',
            'special_request': 'special_request',
            'flight_info': 'flight_info'
        }
        
        for form_field, db_field in safe_fields.items():
            if form_field in form_data and form_data[form_field] is not None:
                updates.append(f"{db_field} = %s")
                values.append(form_data[form_field])
        
        # Add products data separately
        if products_data:
            updates.append("products = %s")
            values.append(products_json)
            print(f"🔍 Adding products to update: {products_json}")
        
        # Always update timestamp
        updates.append("updated_at = NOW()")
        values.append(45)  # booking_id
        
        if updates:
            query = f"""
                UPDATE bookings 
                SET {', '.join(updates)}
                WHERE id = %s
            """
            
            with get_mariadb_cursor() as (cursor, conn):
                cursor.execute(query, values)
                conn.commit()
                
                if cursor.rowcount > 0:
                    flash('Booking #45 updated successfully!', 'success')
                    
                    # Log the update
                    cursor.execute("""
                        INSERT INTO activity_logs (user_id, action, description, created_at)
                        VALUES (%s, %s, %s, NOW())
                    """, (
                        1,  # admin user
                        'booking_updated',
                        f'[BOOKING #45] Booking updated via special handler'
                    ))
                    conn.commit()
                    
                    # Redirect to view page after successful update
                    return redirect(url_for('booking_45.view_booking_45'))
                else:
                    flash('No changes were made to booking #45', 'info')
                    return redirect(url_for('booking_45.view_booking_45'))
        
        return redirect(url_for('booking_45.edit_booking_45'))
        
    except Exception as e:
        logger.error(f"Error updating booking #45: {e}")
        flash(f'Error updating booking #45: {str(e)}', 'error')
        return redirect(url_for('booking_45.edit_booking_45'))

@booking_45_bp.route('/booking/test/45/products')
def test_products_45():
    """Test route to check products data for booking #45"""
    try:
        with get_mariadb_cursor() as (cursor, conn):
            cursor.execute("SELECT * FROM bookings WHERE id = %s", (45,))
            booking_row = cursor.fetchone()
            
            if not booking_row:
                return "Booking #45 not found"
            
            # Convert to dict
            column_names = [desc[0] for desc in cursor.description]
            booking_data = dict(zip(column_names, booking_row))
            
            # Create booking object
            booking_obj = SimpleBooking(booking_data)
            
            # Test get_products method
            products = booking_obj.get_products()
            
            result = f"""
            <h2>Booking #45 Products Test</h2>
            <p><strong>Raw products field:</strong> {booking_data.get('products', 'NULL')}</p>
            <p><strong>Products count:</strong> {len(products)}</p>
            <p><strong>Products data:</strong></p>
            <ul>
            """
            
            for i, product in enumerate(products):
                result += f"<li>Product {i+1}: {product}</li>"
            
            result += f"""
            </ul>
            <h3>Template Test</h3>
            <p>If products are working in template, they should appear below:</p>
            """
            
            # Test template variables
            existing_products = booking_obj.get_products()
            if existing_products and len(existing_products) > 0:
                result += f"<p>✅ Template should show {len(existing_products)} products</p>"
                for i, product in enumerate(existing_products):
                    result += f"""
                    <div style="border: 1px solid #ccc; margin: 5px; padding: 10px;">
                        <strong>Product {i+1}:</strong><br>
                        Name: {product.get('name', '')}<br>
                        Quantity: {product.get('quantity', 1)}<br>
                        Price: {product.get('price', 0)}<br>
                        Amount: {product.get('amount', 0)}
                    </div>
                    """
            else:
                result += "<p>❌ No products found for template</p>"
            
            result += f"""
            <h3>Actual Template Test</h3>
            <p><a href="/booking/test/45/edit-template" target="_blank">Click here to test actual edit template</a></p>
            """
            
            return result
            
    except Exception as e:
        return f"Error: {str(e)}"

@booking_45_bp.route('/booking/test/45/edit-template')
def test_edit_template_45():
    """Test route to render actual edit template without login requirement"""
    try:
        with get_mariadb_cursor() as (cursor, conn):
            cursor.execute("SELECT * FROM bookings WHERE id = %s", (45,))
            booking_row = cursor.fetchone()
            
            if not booking_row:
                flash('Booking #45 not found', 'error')
                return "Booking not found"
            
            # Convert to dict - handle both tuple and dict results
            if hasattr(booking_row, 'keys'):
                booking_data = dict(booking_row)
            else:
                column_names = [desc[0] for desc in cursor.description]
                booking_data = dict(zip(column_names, booking_row))
            
            # Apply datetime conversions
            datetime_fields = [
                'created_at', 'updated_at', 'confirmed_at', 'quoted_at', 
                'invoiced_at', 'paid_at', 'vouchered_at', 'time_limit',
                'arrival_date', 'departure_date', 'due_date', 'invoice_paid_date'
            ]
            
            for field in datetime_fields:
                if booking_data.get(field):
                    booking_data[field] = SafeDatetime(booking_data[field])
            
            # Create customer object
            customer_obj = SimpleCustomer()
            booking_data['customer'] = customer_obj
            
            # Create booking object
            booking_obj = SimpleBooking(booking_data)
            
            # Render template
            return render_template('booking/edit.html', booking=booking_obj, test_mode=True)
            
    except Exception as e:
        return f"Error rendering template: {str(e)}"

def register_booking_45_routes(app):
    """Register booking #45 special routes with the app"""
    app.register_blueprint(booking_45_bp)
    logger.info("✅ Booking #45 special routes registered")

if __name__ == "__main__":
    print("🧪 Testing Booking #45 Special Routes...")
    print("✅ Routes defined and ready to register")
    print("📋 Available routes:")
    print("   GET  /booking/edit/45 - Special edit form")
    print("   POST /booking/edit/45 - Special update handler (redirects to view)")
    print("   GET  /booking/view/45 - Special view page")