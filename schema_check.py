#!/usr/bin/env python3

import sys
import os
sys.path.append('/Applications/python/voucher-ro_v1.0')

from app import app, db
from models.booking import Booking

with app.app_context():
    print("🔍 Checking SQLAlchemy schema vs Database schema")
    
    # Get SQLAlchemy model columns
    model_columns = []
    for column in Booking.__table__.columns:
        model_columns.append((column.name, str(column.type)))
    
    print("\n📋 SQLAlchemy Model columns:")
    for name, col_type in model_columns:
        if 'quote' in name.lower():
            print(f"   {name}: {col_type}")
    
    # Get database schema
    inspector = db.inspect(db.engine)
    db_columns = inspector.get_columns('bookings')
    
    print("\n💾 Database columns:")
    for col in db_columns:
        if 'quote' in col['name'].lower():
            print(f"   {col['name']}: {col['type']} (nullable: {col['nullable']})")
    
    # Check if there's a mismatch
    model_quote_cols = [name for name, _ in model_columns if 'quote' in name.lower()]
    db_quote_cols = [col['name'] for col in db_columns if 'quote' in col['name'].lower()]
    
    print(f"\n🔍 Quote columns comparison:")
    print(f"   Model: {sorted(model_quote_cols)}")
    print(f"   Database: {sorted(db_quote_cols)}")
    
    if set(model_quote_cols) != set(db_quote_cols):
        print("   ❌ MISMATCH DETECTED!")
    else:
        print("   ✅ Columns match")
    
    # Test direct query
    print(f"\n🧪 Testing direct query:")
    result = db.session.execute(db.text("SELECT id, quote_number, quote_id FROM bookings WHERE id = 8")).fetchone()
    if result:
        print(f"   Direct SQL: ID={result[0]}, quote_number='{result[1]}', quote_id={result[2]}")
    
    # Test ORM query
    booking = Booking.query.get(8)
    if booking:
        print(f"   ORM query: ID={booking.id}, quote_number='{booking.quote_number}', quote_id={booking.quote_id}")
        
    print("✅ Schema check complete")