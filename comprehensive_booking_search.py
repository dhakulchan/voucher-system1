#!/usr/bin/env python3
"""More comprehensive search for booking"""

from sqlalchemy import create_engine, text

# Database connection
engine = create_engine('mysql+mysqlconnector://voucher_user:voucher_secure_2024@localhost:3306/voucher_enhanced?charset=utf8mb4')

with engine.connect() as conn:
    # Search for any booking containing these patterns
    patterns = ['260122S5C2', 'S5C2', '2601', '0122', '5C2']
    
    for pattern in patterns:
        result = conn.execute(text("""
            SELECT id, booking_reference, status, created_at 
            FROM bookings 
            WHERE booking_reference LIKE :search
               OR quote_number LIKE :search
               OR guest_list LIKE :search
            LIMIT 5
        """), {'search': f'%{pattern}%'})
        
        rows = result.fetchall()
        if rows:
            print(f'\n=== Bookings matching "{pattern}" ===')
            for row in rows:
                print(f'ID: {row[0]}, Reference: {row[1]}, Status: {row[2]}, Created: {row[3]}')
    
    # Check booking ID 260122 or customer ID
    print('\n=== Checking if 260122 could be an ID ===')
    result = conn.execute(text("""
        SELECT id, booking_reference, status 
        FROM bookings 
        WHERE id = 260122
        LIMIT 1
    """))
    rows = result.fetchall()
    if rows:
        for row in rows:
            print(f'Found booking with ID 260122: Reference={row[1]}, Status={row[2]}')
    else:
        print('No booking with ID 260122')
