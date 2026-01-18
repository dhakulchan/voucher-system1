"""
Simple Booking #46 Routes - Special handler for datetime corruption
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from mariadb_helper import get_mariadb_cursor
import json

booking_46_bp = Blueprint('booking_46', __name__)

class SafeDatetime:
    def __init__(self, dt_string):
        if dt_string is None:
            self.original_string = ''
        else:
            self.original_string = str(dt_string)
    
    def __str__(self):
        return self.original_string
    
    def strftime(self, format_str):
        # If we have a valid datetime string, return it as-is
        # Templates will display the raw string instead of formatted datetime
        return self.original_string
    
    def __bool__(self):
        return bool(self.original_string)
    
    def __repr__(self):
        return f"SafeDatetime('{self.original_string}')"

class SimpleCustomer:
    def __init__(self):
        self.name = ''
        self.email = ''
        self.phone = ''

class SimpleBooking:
    def __init__(self, booking_data):
        # List of datetime fields that need special handling
        datetime_fields = [
            'created_at', 'updated_at', 'confirmed_at', 'quoted_at', 
            'invoiced_at', 'paid_at', 'vouchered_at', 'time_limit',
            'arrival_date', 'departure_date', 'traveling_period_start',
            'traveling_period_end', 'due_date', 'received_date',
            'invoice_paid_date'
        ]
        
        for key, value in booking_data.items():
            if key in datetime_fields and value:
                setattr(self, key, SafeDatetime(value))
            else:
                setattr(self, key, value)
    
    def get_products(self):
        if hasattr(self, 'products') and self.products:
            try:
                if isinstance(self.products, str):
                    return json.loads(self.products)
                elif isinstance(self.products, list):
                    return self.products
            except:
                pass
        return []
    
    def get_guest_list(self):
        """Return guest list for template compatibility"""
        guest_list = getattr(self, 'guest_list', '')
        return guest_list if guest_list else ''
    
    def get_guest_list_for_edit(self):
        """Return guest list formatted for editing"""
        import html
        import re
        
        guest_list = getattr(self, 'guest_list', '')
        if guest_list:
            try:
                # Try to parse as JSON first
                parsed_list = json.loads(guest_list)
                if isinstance(parsed_list, list):
                    # Process each guest item to clean HTML
                    formatted_guests = []
                    for guest in parsed_list:
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

class ActivityLogDisplay:
    def __init__(self, log_data):
        for key, value in log_data.items():
            if 'created_at' in key and value:
                setattr(self, key, SafeDatetime(value))
            else:
                setattr(self, key, value)

@booking_46_bp.route('/booking/view/46')
@login_required
def view_booking_46():
    try:
        with get_mariadb_cursor() as (cursor, conn):
            cursor.execute("SELECT * FROM bookings WHERE id = %s", (46,))
            booking_row = cursor.fetchone()
            
            if not booking_row:
                flash('Booking #46 not found', 'error')
                return redirect(url_for('booking.list'))
            
            # Get column names and convert tuple to dictionary
            column_names = [desc[0] for desc in cursor.description]
            booking_data = dict(zip(column_names, booking_row))
            
            cursor.execute("""
                SELECT al.*, u.username
                FROM activity_logs al
                LEFT JOIN users u ON al.user_id = u.id
                WHERE al.description LIKE %s
                ORDER BY al.created_at DESC
                LIMIT 20
            """, (f'%[BOOKING #{46}]%',))
            
            activity_logs_rows = cursor.fetchall()
            if activity_logs_rows:
                log_column_names = [desc[0] for desc in cursor.description]
                activity_logs_data = [dict(zip(log_column_names, row)) for row in activity_logs_rows]
                booking_data['activity_logs'] = [ActivityLogDisplay(log_data) for log_data in activity_logs_data]
            else:
                booking_data['activity_logs'] = []
            
            customer_obj = SimpleCustomer()
            if booking_data.get('party_name'):
                customer_obj.name = booking_data['party_name']
                customer_obj.email = booking_data.get('customer_email', '')
                customer_obj.phone = booking_data.get('customer_phone', '')
            booking_data['customer'] = customer_obj
            
            booking_obj = SimpleBooking(booking_data)
            return render_template('booking/view_en.html', booking=booking_obj)
            
    except Exception as e:
        flash(f'Database error loading booking #46: {str(e)}', 'error')
        return redirect(url_for('booking.list'))

@booking_46_bp.route('/booking/edit/46')
@login_required
def edit_booking_46():
    try:
        with get_mariadb_cursor() as (cursor, conn):
            cursor.execute("SELECT * FROM bookings WHERE id = %s", (46,))
            booking_row = cursor.fetchone()
            
            if not booking_row:
                flash('Booking #46 not found', 'error')
                return redirect(url_for('booking.list'))
            
            # Get column names and convert tuple to dictionary
            column_names = [desc[0] for desc in cursor.description]
            booking_data = dict(zip(column_names, booking_row))
            
            customer_obj = SimpleCustomer()
            if booking_data.get('party_name'):
                customer_obj.name = booking_data['party_name']
                customer_obj.email = booking_data.get('customer_email', '')
                customer_obj.phone = booking_data.get('customer_phone', '')
            booking_data['customer'] = customer_obj
            
            booking_obj = SimpleBooking(booking_data)
            return render_template('booking/edit.html', booking=booking_obj)
            
    except Exception as e:
        flash(f'Database error loading booking #46: {str(e)}', 'error')
        return redirect(url_for('booking.list'))

@booking_46_bp.route('/booking/edit/46', methods=['POST'])
@login_required  
def update_booking_46():
    try:
        form_data = request.form.to_dict()
        form_dict = request.form.to_dict(flat=False)
        
        updates = []
        values = []
        
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
            'products': 'products'
        }
        
        for form_field, db_field in safe_fields.items():
            if form_field in form_data and form_data[form_field] is not None:
                if form_field == 'products':
                    products = []
                    i = 0
                    while True:
                        name_key = f'products[{i}][name]'
                        quantity_key = f'products[{i}][quantity]'
                        price_key = f'products[{i}][price]'
                        amount_key = f'products[{i}][amount]'
                        
                        if name_key not in form_dict:
                            break
                            
                        name = form_dict[name_key][0] if form_dict[name_key] else ''
                        quantity = form_dict[quantity_key][0] if quantity_key in form_dict and form_dict[quantity_key] else '1'
                        price = form_dict[price_key][0] if price_key in form_dict and form_dict[price_key] else '0'
                        amount = form_dict[amount_key][0] if amount_key in form_dict and form_dict[amount_key] else '0'
                        
                        if name.strip():
                            products.append({
                                'name': name.strip(),
                                'quantity': int(quantity) if quantity else 1,
                                'price': float(price) if price else 0.0,
                                'amount': float(amount) if amount else 0.0
                            })
                        
                        i += 1
                    
                    updates.append(f"{db_field} = %s")
                    values.append(json.dumps(products))
                    print(f"Saving {len(products)} products")
                else:
                    updates.append(f"{db_field} = %s")
                    values.append(form_data[form_field])
        
        updates.append("updated_at = NOW()")
        values.append(46)
        
        if updates:
            query = f"UPDATE bookings SET {', '.join(updates)} WHERE id = %s"
            
            with get_mariadb_cursor() as (cursor, conn):
                cursor.execute(query, values)
                conn.commit()
                
                if cursor.rowcount > 0:
                    flash('Booking #46 updated successfully!', 'success')
                    return redirect(url_for('booking_46.view_booking_46'))
                else:
                    flash('No changes were made to booking #46', 'info')
        
        return redirect(url_for('booking_46.edit_booking_46'))
        
    except Exception as e:
        flash(f'Error updating booking #46: {str(e)}', 'error')
        return redirect(url_for('booking_46.edit_booking_46'))

def register_booking_46_routes(app):
    app.register_blueprint(booking_46_bp)
    print("✅ Booking #46 special routes registered")
