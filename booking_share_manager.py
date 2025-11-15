#!/usr/bin/env python3
"""
Booking Management Tool for Secure Share Links
Generate and manage secure sharing tokens for bookings
"""

import os
import sys
import hmac
import hashlib
import base64
import time
import sqlite3
from datetime import datetime, timedelta

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

class BookingShareManager:
    def __init__(self, db_path='app.db'):
        self.db_path = db_path
        # Use the same secret key as the main app
        self.secret_key = 'dcts-secure-production-key-2025-voucher-system-v1'
        
    def generate_secure_token(self, booking_id, expires_days=30):
        """Generate a secure token for booking sharing"""
        created_at = int(time.time())
        expires_at = created_at + (expires_days * 24 * 3600)
        
        base_data = f'{booking_id}:{created_at}:{expires_at}'
        encoded_key = self.secret_key.encode('utf-8')
        signature = hmac.new(encoded_key, base_data.encode('utf-8'), hashlib.sha256).digest()
        
        token_data = base_data.encode('utf-8') + signature
        token = base64.b64encode(token_data).decode('utf-8')
        
        return token
    
    def get_booking_info(self, booking_id):
        """Get booking information from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT b.id, b.booking_reference, b.party_name, b.arrival_date, 
                   b.customer_id, c.name as customer_name, c.phone, c.email,
                   b.description, b.guest_list, b.adults, b.children, b.infants
            FROM bookings b
            LEFT JOIN customers c ON b.customer_id = c.id
            WHERE b.id = ?
        ''', (booking_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'id': result[0],
                'booking_reference': result[1],
                'party_name': result[2],
                'arrival_date': result[3],
                'customer_id': result[4],
                'customer_name': result[5],
                'phone': result[6],
                'email': result[7],
                'description': result[8],
                'guest_list': result[9],
                'adults': result[10],
                'children': result[11],
                'infants': result[12]
            }
        return None
    
    def create_share_link(self, booking_id, base_url='http://localhost:5001', expires_days=30):
        """Create a complete share link for a booking"""
        # Check if booking exists
        booking = self.get_booking_info(booking_id)
        if not booking:
            return None, f"Booking {booking_id} not found"
        
        # Generate token
        token = self.generate_secure_token(booking_id, expires_days)
        
        # Create full URL
        share_url = f"{base_url}/public/booking/{token}"
        
        return share_url, None
    
    def list_bookings(self, limit=10):
        """List recent bookings"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT b.id, b.booking_reference, b.party_name, b.arrival_date, 
                   c.name as customer_name
            FROM bookings b
            LEFT JOIN customers c ON b.customer_id = c.id
            ORDER BY b.id DESC
            LIMIT ?
        ''', (limit,))
        
        results = cursor.fetchall()
        conn.close()
        
        return results

def main():
    """CLI interface for booking share management"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Manage secure booking share links')
    parser.add_argument('command', choices=['list', 'share', 'info'], help='Command to execute')
    parser.add_argument('--booking-id', type=int, help='Booking ID')
    parser.add_argument('--expires-days', type=int, default=30, help='Token expiration in days')
    parser.add_argument('--base-url', default='http://localhost:5001', help='Base URL for links')
    parser.add_argument('--limit', type=int, default=10, help='Limit for list command')
    
    args = parser.parse_args()
    
    manager = BookingShareManager()
    
    if args.command == 'list':
        print("📋 Recent Bookings:")
        print("=" * 80)
        bookings = manager.list_bookings(args.limit)
        for booking in bookings:
            print(f"ID: {booking[0]:3} | Ref: {booking[1] or 'N/A':15} | Party: {booking[2] or 'N/A':20} | Date: {booking[3] or 'N/A'} | Customer: {booking[4] or 'N/A'}")
    
    elif args.command == 'info':
        if not args.booking_id:
            print("❌ Error: --booking-id is required for info command")
            return
        
        booking = manager.get_booking_info(args.booking_id)
        if booking:
            print(f"📊 Booking {args.booking_id} Information:")
            print("=" * 50)
            print(f"Booking Reference: {booking['booking_reference']}")
            print(f"Party Name: {booking['party_name']}")
            print(f"Arrival Date: {booking['arrival_date']}")
            print(f"Customer: {booking['customer_name']} ({booking['email']}, {booking['phone']})")
            print(f"Guests: {booking['adults']} adults, {booking['children']} children, {booking['infants']} infants")
            if booking['description']:
                print(f"Description: {booking['description'][:100]}...")
        else:
            print(f"❌ Booking {args.booking_id} not found")
    
    elif args.command == 'share':
        if not args.booking_id:
            print("❌ Error: --booking-id is required for share command")
            return
        
        share_url, error = manager.create_share_link(
            args.booking_id, 
            args.base_url, 
            args.expires_days
        )
        
        if error:
            print(f"❌ Error: {error}")
        else:
            print(f"🔗 Secure Share Link for Booking {args.booking_id}:")
            print("=" * 60)
            print(f"URL: {share_url}")
            print(f"Expires: {args.expires_days} days from now")
            print("\n✅ Link is ready to share!")

if __name__ == "__main__":
    # If no arguments, show interactive mode
    if len(sys.argv) == 1:
        print("🎫 Booking Share Manager")
        print("=" * 30)
        
        manager = BookingShareManager()
        
        # Show recent bookings
        print("\n📋 Recent Bookings:")
        bookings = manager.list_bookings(5)
        for booking in bookings:
            print(f"  {booking[0]:2}: {booking[1]} - {booking[2]}")
        
        # Interactive booking selection
        try:
            booking_id = int(input("\n🔢 Enter Booking ID to create share link: "))
            share_url, error = manager.create_share_link(booking_id)
            
            if error:
                print(f"❌ {error}")
            else:
                print(f"\n🔗 Share Link: {share_url}")
                print("✅ Ready to share!")
                
        except (ValueError, KeyboardInterrupt):
            print("\n👋 Goodbye!")
    else:
        main()
