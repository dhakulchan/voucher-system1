"""
Booking #45 Edit Route Workaround
แก้ปัญหา datetime corruption เฉพาะกิจสำหรับ booking edit
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from mariadb_helper import get_mariadb_cursor, execute_mariadb_query
import logging

logger = logging.getLogger(__name__)

def get_booking_45_safe():
    """
    Safe method to get booking #45 data bypassing SQLAlchemy datetime issues
    """
    try:
        # Use raw MariaDB query
        query = """
            SELECT 
                b.*, 
                c.name as customer_name, 
                c.email as customer_email,
                c.phone as customer_phone
            FROM bookings b
            LEFT JOIN customers c ON b.customer_id = c.id
            WHERE b.id = 45
        """
        
        with get_mariadb_cursor() as (cursor, conn):
            cursor.execute(query)
            result = cursor.fetchone()
            
            if not result:
                return None
            
            # Convert to column names
            columns = [desc[0] for desc in cursor.description]
            booking_data = dict(zip(columns, result))
            
            # Convert datetime objects to strings for safe handling
            datetime_fields = [
                'created_at', 'updated_at', 'time_limit',
                'confirmed_at', 'quoted_at', 'invoiced_at',
                'paid_at', 'vouchered_at', 'invoice_paid_date',
                'arrival_date', 'departure_date',
                'traveling_period_start', 'traveling_period_end',
                'due_date', 'received_date'
            ]
            
            for field in datetime_fields:
                if field in booking_data and booking_data[field]:
                    booking_data[field] = str(booking_data[field])
            
            return booking_data
            
    except Exception as e:
        logger.error(f"Error getting booking #45: {e}")
        return None

def update_booking_45_safe(form_data):
    """
    Safe method to update booking #45 bypassing SQLAlchemy
    """
    try:
        # Extract form data
        updates = []
        values = []
        
        # Map form fields to database columns
        field_mapping = {
            'adults': 'adults',
            'children': 'children', 
            'infants': 'infants',
            'total_pax': 'total_pax',
            'pickup_point': 'pickup_point',
            'pickup_time': 'pickup_time',
            'total_amount': 'total_amount',
            'status': 'status',
            'currency': 'currency'
        }
        
        for form_field, db_field in field_mapping.items():
            if form_field in form_data:
                updates.append(f"{db_field} = %s")
                values.append(form_data[form_field])
        
        # Always update the updated_at field
        updates.append("updated_at = NOW()")
        
        # Add booking ID to values
        values.append(45)
        
        query = f"""
            UPDATE bookings 
            SET {', '.join(updates)}
            WHERE id = %s
        """
        
        with get_mariadb_cursor() as (cursor, conn):
            cursor.execute(query, values)
            conn.commit()
            
            if cursor.rowcount > 0:
                return True
            else:
                return False
                
    except Exception as e:
        logger.error(f"Error updating booking #45: {e}")
        return False

# Test the workaround functions
if __name__ == "__main__":
    print("🧪 Testing Booking #45 Safe Access Functions...")
    
    # Test getting booking data
    booking = get_booking_45_safe()
    if booking:
        print("✅ Successfully retrieved booking #45")
        print(f"   Reference: {booking['booking_reference']}")
        print(f"   Status: {booking['status']}")
        print(f"   Customer: {booking['customer_name']}")
    else:
        print("❌ Failed to retrieve booking #45")
    
    # Test updating booking data
    test_updates = {
        'total_amount': '21000',
        'status': 'pending'
    }
    
    success = update_booking_45_safe(test_updates)
    if success:
        print("✅ Successfully updated booking #45")
        
        # Verify update
        updated_booking = get_booking_45_safe()
        if updated_booking:
            print(f"   New Amount: {updated_booking['total_amount']}")
            print(f"   New Status: {updated_booking['status']}")
    else:
        print("❌ Failed to update booking #45")
    
    print("\n🎉 Booking #45 workaround functions ready!")