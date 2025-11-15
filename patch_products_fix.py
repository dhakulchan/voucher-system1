#!/usr/bin/env python3
"""
Patch script to fix product loading in PDF generation routes
"""
import re

def patch_booking_routes():
    """Fix routes/booking.py to use products JSON field instead of product_bookings"""
    
    with open('/Applications/python/voucher-ro_v1.0/routes/booking.py', 'r') as f:
        content = f.read()
    
    # Pattern to find the old product loading code
    old_pattern = r'''        # Get products for this booking
        products = \[\]
        if hasattr\(booking, 'product_bookings'\):
            for product_booking in booking\.product_bookings:
                if product_booking\.product:
                    products\.append\(\{
                        'name': product_booking\.product\.name,
                        'quantity': product_booking\.quantity,
                        'price': float\(product_booking\.price\) if product_booking\.price else 0\.0
                    \}\)'''
    
    # New product loading code
    new_code = '''        # Get products for this booking from the products JSON field
        products = []
        booking_products = booking.get_products()
        if booking_products:
            for product_data in booking_products:
                products.append({
                    'name': product_data.get('name', 'Unknown Product'),
                    'quantity': product_data.get('quantity', 1),
                    'price': float(product_data.get('price', 0.0)),
                    'amount': float(product_data.get('amount', 0.0))
                })
        
        # Debug: Print products being used  
        print(f"🔍 PDF Products for {booking.booking_reference} ({len(products)} items):")
        for i, product in enumerate(products, 1):
            print(f"  {i}. {product['name']} x{product['quantity']} = {product['price']:,.2f} (Amount: {product['amount']:,.2f})")'''
    
    # Replace all occurrences
    updated_content = re.sub(old_pattern, new_code, content, flags=re.MULTILINE)
    
    if updated_content != content:
        with open('/Applications/python/voucher-ro_v1.0/routes/booking.py', 'w') as f:
            f.write(updated_content)
        print("✅ Successfully patched routes/booking.py")
        print("📦 Now uses booking.get_products() instead of product_bookings")
    else:
        print("❌ No changes made - pattern not found or already patched")

if __name__ == "__main__":
    patch_booking_routes()
