#!/usr/bin/env python3
"""
Complete Booking Workflow Test
Tests: draft->pending->confirmed->quoted->paid->vouchered
"""

import requests
import json
import re
import time
from datetime import datetime, timedelta

# Configuration
BASE_URL = "http://localhost:5001"
session = requests.Session()

def login():
    """Login to get session"""
    print("🔑 Logging in...")
    
    # Get login page
    login_page = session.get(f"{BASE_URL}/auth/login")
    
    # Login with credentials
    login_data = {
        'username': 'admin',
        'password': 'admin123',
    }
    
    response = session.post(f"{BASE_URL}/auth/login", data=login_data, allow_redirects=True)
    
    # Check if we're logged in
    dashboard = session.get(f"{BASE_URL}/")
    if dashboard.status_code == 200:
        print("✅ Login successful")
        return True
    else:
        print("❌ Login failed")
        return False

def get_customer_id():
    """Get first available customer ID"""
    response = session.get(f"{BASE_URL}/booking/create")
    if response.status_code == 200:
        pattern = r'<option value="(\d+)"[^>]*>([^<]+)</option>'
        matches = re.findall(pattern, response.text)
        
        if matches:
            customer_id, customer_name = matches[0]
            print(f"Using customer: {customer_name} (ID: {customer_id})")
            return customer_id
    
    return None

def create_test_booking():
    """Step 1: Create a new booking"""
    print("\n📝 Step 1: Creating new booking...")
    
    customer_id = get_customer_id()
    if not customer_id:
        print("❌ No customer available")
        return None
    
    today = datetime.now()
    arrival_date = today + timedelta(days=30)
    departure_date = arrival_date + timedelta(days=5)
    time_limit = today + timedelta(hours=72)
    
    booking_data = {
        'customer_id': customer_id,
        'booking_type': 'individual',
        'party_name': 'Workflow Test Party',
        'arrival_date': arrival_date.strftime('%Y-%m-%d'),
        'departure_date': departure_date.strftime('%Y-%m-%d'),
        'time_limit': time_limit.strftime('%Y-%m-%dT%H:%M'),
        'adults': '2',
        'children': '1',
        'total_pax': '3',
        'infants': '0',
        'description': 'Bangkok City Tour Package - Workflow Test',
        'pickup_point': 'Hotel Lobby',
        'pickup_time': '09:00',
        'flight_info': 'Flight info will be provided later',
        'products[0][name]': 'Bangkok Tour Package',
        'products[0][quantity]': '1',
        'products[0][price]': '4500.00',
        'products[0][amount]': '4500.00',
        'total_amount': '4500.00',
        'special_requests': 'Complete workflow test booking',
        'admin_notes': 'Created for workflow testing',
        'manager_memos': '',
        'internal_note': 'Automated test booking'
    }
    
    response = session.post(f"{BASE_URL}/booking/create", data=booking_data, allow_redirects=False)
    print(f"Create booking status: {response.status_code}")
    
    if response.status_code == 302:
        location = response.headers.get('Location', '')
        if '/booking/view/' in location:
            booking_id = location.split('/booking/view/')[-1].split('/')[0]
            if booking_id.isdigit():
                print(f"✅ Booking created with ID: {booking_id}")
                return int(booking_id)
    
    print("❌ Failed to create booking")
    return None

def check_booking_status(booking_id):
    """Check current booking status"""
    print(f"\n🔍 Checking booking {booking_id} status...")
    
    response = session.get(f"{BASE_URL}/booking/{booking_id}")
    if response.status_code == 200:
        # Extract status from response
        text = response.text.lower()
        
        status_patterns = {
            'draft': r'status[^>]*draft|draft[^<]*status',
            'pending': r'status[^>]*pending|pending[^<]*status', 
            'confirmed': r'status[^>]*confirmed|confirmed[^<]*status',
            'quoted': r'status[^>]*quoted|quoted[^<]*status',
            'paid': r'status[^>]*paid|paid[^<]*status',
            'vouchered': r'status[^>]*vouchered|vouchered[^<]*status'
        }
        
        for status, pattern in status_patterns.items():
            if re.search(pattern, text):
                print(f"📊 Current status: {status.upper()}")
                return status
        
        print(f"📊 Booking {booking_id} exists (status unknown)")
        return 'unknown'
    
    print(f"❌ Could not access booking {booking_id}")
    return None

def confirm_booking(booking_id):
    """Step 2: Confirm booking (draft/pending -> confirmed)"""
    print(f"\n✅ Step 2: Confirming booking {booking_id}...")
    
    response = session.post(f"{BASE_URL}/booking/{booking_id}/confirm", 
                          headers={'Content-Type': 'application/json'},
                          allow_redirects=False)
    print(f"Confirm booking status: {response.status_code}")
    
    if response.status_code in [200, 302]:
        if response.status_code == 200:
            try:
                result = response.json()
                if result.get('success'):
                    print("✅ Booking confirmed successfully")
                    return True
            except:
                pass
        
        print("✅ Booking confirmation attempted")
        return True
    
    print("❌ Failed to confirm booking")
    return False

def create_quote(booking_id):
    """Step 3: Create quote (confirmed -> quoted)"""
    print(f"\n💰 Step 3: Creating quote for booking {booking_id}...")
    
    response = session.post(f"{BASE_URL}/booking/{booking_id}/create-quote",
                          headers={'Content-Type': 'application/json'},
                          allow_redirects=False)
    print(f"Create quote status: {response.status_code}")
    
    if response.status_code in [200, 302]:
        if response.status_code == 200:
            try:
                result = response.json()
                if result.get('success'):
                    print("✅ Quote created successfully")
                    return True
            except:
                pass
        
        print("✅ Quote creation attempted")
        return True
    
    print("❌ Failed to create quote")
    return False

def mark_as_paid(booking_id):
    """Step 4: Mark as paid (quoted -> paid)"""
    print(f"\n💳 Step 4: Marking booking {booking_id} as paid...")
    
    payment_data = {
        'received_amount': '4500',
        'received_date': datetime.now().strftime('%Y-%m-%d'),
        'bank_received': 'Bank Transfer Received',
        'payment_method': 'Bank Transfer',
        'payment_reference': 'TXN-WORKFLOW-TEST-001',
        'invoice_status': 'paid',
        'payment_password': 'pm250966'
    }
    
    response = session.post(f"{BASE_URL}/booking/{booking_id}/mark-paid", 
                          json=payment_data,
                          headers={'Content-Type': 'application/json'},
                          allow_redirects=False)
    print(f"Mark paid status: {response.status_code}")
    
    if response.status_code in [200, 302]:
        if response.status_code == 200:
            try:
                result = response.json()
                if result.get('success'):
                    print("✅ Booking marked as paid successfully")
                    return True
            except:
                pass
        
        print("✅ Booking marked as paid")
        return True
    
    print("❌ Failed to mark booking as paid")
    return False

def generate_voucher(booking_id):
    """Step 5: Generate voucher (paid -> vouchered)"""
    print(f"\n🎫 Step 5: Generating voucher for booking {booking_id}...")
    
    response = session.post(f"{BASE_URL}/booking/{booking_id}/generate-voucher",
                          headers={'Content-Type': 'application/json'},
                          allow_redirects=False)
    print(f"Generate voucher status: {response.status_code}")
    
    if response.status_code in [200, 302]:
        if response.status_code == 200:
            try:
                result = response.json()
                if result.get('success'):
                    print("✅ Voucher generated successfully")
                    return True
            except:
                pass
        
        print("✅ Voucher generation attempted")
        return True
    
    print("❌ Failed to generate voucher")
    return False

def main():
    """Run complete workflow test"""
    print("🚀 Starting Complete Booking Workflow Test")
    print("Flow: Create -> Confirm -> Quote -> Paid -> Voucher")
    print("=" * 60)
    
    # Step 0: Login
    if not login():
        print("❌ Cannot proceed without login")
        return
    
    # Step 1: Create booking
    booking_id = create_test_booking()
    if not booking_id:
        print("❌ Cannot proceed without booking")
        return
    
    time.sleep(2)  # Allow database to settle
    
    # Check initial status
    initial_status = check_booking_status(booking_id)
    print(f"📊 Initial booking status: {initial_status}")
    
    # Step 2: Confirm booking
    time.sleep(2)
    if confirm_booking(booking_id):
        time.sleep(2)
        status = check_booking_status(booking_id)
        print(f"📊 After confirmation: {status}")
    
    # Step 3: Create quote
    time.sleep(2)
    if create_quote(booking_id):
        time.sleep(2)
        status = check_booking_status(booking_id)
        print(f"📊 After quote creation: {status}")
    
    # Step 4: Mark as paid
    time.sleep(2)
    if mark_as_paid(booking_id):
        time.sleep(2)
        status = check_booking_status(booking_id)
        print(f"📊 After payment: {status}")
    
    # Step 5: Generate voucher
    time.sleep(2)
    if generate_voucher(booking_id):
        time.sleep(2)
        final_status = check_booking_status(booking_id)
        print(f"📊 Final status: {final_status}")
    
    print("\n" + "=" * 60)
    print(f"🏁 WORKFLOW TEST COMPLETED for booking {booking_id}")
    print(f"📋 Manual verification: {BASE_URL}/booking/{booking_id}")
    print(f"📋 Alternative URL: {BASE_URL}/booking/view/{booking_id}")
    
    # Final status check
    print("\n🔍 Final Status Verification:")
    final_check = check_booking_status(booking_id)
    
    if final_check == 'vouchered':
        print("🎉 SUCCESS: Complete workflow executed successfully!")
    else:
        print(f"⚠️ INCOMPLETE: Final status is '{final_check}', expected 'vouchered'")

if __name__ == "__main__":
    main()