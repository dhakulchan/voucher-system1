#!/usr/bin/env python3

import sqlite3

# Connect to database
conn = sqlite3.connect('app.db')
cursor = conn.cursor()

print("=== Creating proper booking 8 ===")

# Create booking 8 with correct columns
cursor.execute("""
    INSERT INTO bookings (
        id, customer_id, booking_reference, 
        quote_id, quote_number, quote_status, quoted_at,
        booking_type, status, confirmed_at,
        adults, children, total_pax, infants,
        total_amount, currency, time_limit,
        created_at, updated_at, created_by
    ) VALUES (
        8, 1, 'BK20250913FF74',
        6, 'QT20250913631', 'sent', datetime('now'),
        'package_tour', 'confirmed', datetime('now'),
        2, 0, 2, 0,
        10000.00, 'THB', datetime('now', '+7 days'),
        datetime('now'), datetime('now'), 1
    )
""")
conn.commit()
print("✅ Booking 8 created successfully")

# Verify
cursor.execute("SELECT id, booking_reference, quote_number, quote_id, status FROM bookings WHERE id = 8")
booking = cursor.fetchone()
print(f"New booking 8: {booking}")

# Check synchronization again
print("\n=== Updated synchronization status ===")
cursor.execute("""
    SELECT 
        b.id as booking_id, 
        b.quote_number as booking_quote_number, 
        b.quote_id as booking_quote_id,
        q.id as actual_quote_id,
        q.quote_number as actual_quote_number
    FROM bookings b
    LEFT JOIN quotes q ON b.id = q.booking_id
    WHERE b.id = 8
""")
sync_status = cursor.fetchall()
for row in sync_status:
    booking_id, booking_quote_num, booking_quote_id, actual_quote_id, actual_quote_num = row
    if actual_quote_id and booking_quote_num:
        print(f"✅ SYNCED: Booking {booking_id} has quote {booking_quote_id} ({booking_quote_num})")

conn.close()
print("=== Done ===")