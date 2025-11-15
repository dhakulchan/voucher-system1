# Enhanced Quote PDF Generator Functions
# Helper functions for the improved quote template

import datetime
from decimal import Decimal
import re

def generate_quote_number():
    """สร้างเลขที่ใบเสนอราคาอัตโนมัติ"""
    now = datetime.datetime.now()
    return f"QT{now.strftime('%y%m%d')}{now.strftime('%H%M')}"

def format_thai_number(amount):
    """แปลงตัวเลขเป็นคำอ่านภาษาไทย"""
    try:
        amount = float(amount)
        if amount == 0:
            return "ศูนย์บาทถ้วน"
        
        # Basic Thai number words - can be expanded
        ones = ["", "หนึ่ง", "สอง", "สาม", "สี่", "ห้า", "หก", "เจ็ด", "แปด", "เก้า"]
        tens = ["", "", "ยี่", "สาม", "สี่", "ห้า", "หก", "เจ็ด", "แปด", "เก้า"]
        
        # Simplified conversion for demo
        if amount < 10:
            return f"{ones[int(amount)]}บาทถ้วน"
        elif amount < 100:
            tens_digit = int(amount // 10)
            ones_digit = int(amount % 10)
            if tens_digit == 1:
                result = "สิบ"
            elif tens_digit == 2:
                result = "ยี่สิบ"
            else:
                result = f"{tens[tens_digit]}สิบ"
            
            if ones_digit > 0:
                if ones_digit == 1 and tens_digit > 1:
                    result += "เอ็ด"
                else:
                    result += ones[ones_digit]
            
            return f"{result}บาทถ้วน"
        else:
            # For larger numbers, use a simplified approach
            return f"{int(amount):,}บาทถ้วน (ตัวหนังสือยังไม่รองรับ)"
            
    except (ValueError, TypeError):
        return "จำนวนเงินไม่ถูกต้อง"

def calculate_totals(products):
    """คำนวณยอดรวมทั้งหมด"""
    try:
        subtotal = Decimal('0')
        discount = Decimal('0')
        
        for product in products:
            amount = Decimal(str(product.get('amount', '0')))
            if product.get('is_negative', False):
                discount += abs(amount)  # Store discount as positive
            else:
                subtotal += amount
        
        total = subtotal - discount
        
        return {
            'subtotal': f"{subtotal:,.2f}",
            'discount': f"{discount:,.2f}",
            'total': f"{total:,.2f}",
            'total_words': format_thai_number(total)
        }
    except Exception as e:
        return {
            'subtotal': "0.00",
            'discount': "0.00", 
            'total': "0.00",
            'total_words': "ศูนย์บาทถ้วน"
        }

def validate_quote_data(booking_data):
    """ตรวจสอบข้อมูลก่อนสร้าง PDF"""
    errors = []
    
    if not booking_data.get('party_name'):
        errors.append('Party name is required')
    
    if not booking_data.get('products') or len(booking_data.get('products', [])) == 0:
        errors.append('At least one product is required')
    
    # Check for required dates
    if not booking_data.get('traveling_period_start'):
        errors.append('Travel start date is required')
        
    if not booking_data.get('traveling_period_end'):
        errors.append('Travel end date is required')
    
    return errors

def safe_format_date(date_obj, format_str='%d/%m/%Y'):
    """จัดการ format วันที่แบบปลอดภัย"""
    try:
        if isinstance(date_obj, str):
            # Try to parse string date
            try:
                date_obj = datetime.datetime.strptime(date_obj, '%Y-%m-%d')
            except ValueError:
                try:
                    date_obj = datetime.datetime.strptime(date_obj, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    return '-'
        
        if hasattr(date_obj, 'strftime'):
            return date_obj.strftime(format_str)
        else:
            return '-'
    except Exception:
        return '-'

def format_phone_number(phone):
    """จัดรูปแบบเบอร์โทรศัพท์"""
    if not phone:
        return ''
    
    # Remove all non-digit characters
    digits = re.sub(r'[^\d]', '', str(phone))
    
    # Format Thai mobile numbers
    if len(digits) == 10 and digits.startswith(('08', '09', '06', '07')):
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    elif len(digits) == 9 and digits.startswith(('8', '9', '6', '7')):
        return f"0{digits[:2]}-{digits[2:5]}-{digits[5:]}"
    else:
        return phone

def get_status_class(status):
    """ได้รับ CSS class สำหรับ status"""
    if not status:
        return 'status-draft'
    
    status_lower = str(status).lower()
    if status_lower in ['confirmed', 'active', 'paid']:
        return 'status-confirmed'
    elif status_lower in ['cancelled', 'expired']:
        return 'status-cancelled'
    else:
        return 'status-draft'

def prepare_template_context(booking, customer=None, products=None, **kwargs):
    """เตรียมข้อมูลสำหรับ template"""
    context = {}
    
    # Basic booking information
    context['booking'] = booking
    context['customer'] = customer
    context['products'] = products or []
    
    # Generate quote number if not provided
    context['quote_number'] = kwargs.get('quote_number', generate_quote_number())
    
    # Format dates
    context['generation_date'] = safe_format_date(datetime.datetime.now())
    
    if booking:
        context['due_date'] = safe_format_date(booking.get('due_date'))
        context['time_limit'] = safe_format_date(booking.get('time_limit'))
    
    # Calculate totals
    if products:
        totals = calculate_totals(products)
        context['total_amount'] = totals['total']
        context['total_amount_words'] = totals['total_words']
    else:
        context['total_amount'] = '0.00'
        context['total_amount_words'] = 'ศูนย์บาทถ้วน'
    
    # Format customer phone
    if customer and customer.get('phone'):
        context['customer_phone'] = format_phone_number(customer['phone'])
    
    # Add any additional context
    context.update(kwargs)
    
    return context

def enhance_product_data(products):
    """ปรับปรุงข้อมูล products สำหรับการแสดงผล"""
    if not products:
        return []
    
    enhanced_products = []
    
    for i, product in enumerate(products, 1):
        enhanced_product = product.copy()
        
        # Add sequence number if not present
        if 'no' not in enhanced_product:
            enhanced_product['no'] = i
        
        # Format amounts
        try:
            amount = float(product.get('amount', 0))
            price = float(product.get('price', 0))
            quantity = int(product.get('quantity', 1))
            
            enhanced_product['amount'] = f"{amount:,.2f}"
            enhanced_product['price'] = f"{price:,.2f}"
            enhanced_product['quantity'] = str(quantity)
            
            # Mark negative amounts (discounts)
            if amount < 0:
                enhanced_product['is_negative'] = True
                enhanced_product['amount'] = f"({abs(amount):,.2f})"
            
        except (ValueError, TypeError):
            enhanced_product['amount'] = product.get('amount', '0.00')
            enhanced_product['price'] = product.get('price', '0.00')
            enhanced_product['quantity'] = str(product.get('quantity', 1))
        
        enhanced_products.append(enhanced_product)
    
    return enhanced_products

# Example usage function
def generate_quote_pdf_context(booking_id=None, **override_data):
    """
    สร้าง context สำหรับ PDF template
    
    Args:
        booking_id: ID ของ booking
        **override_data: ข้อมูลที่ต้องการ override
    
    Returns:
        dict: Context สำหรับ template
    """
    # This would typically fetch data from database
    # For now, return sample data
    
    sample_booking = {
        'booking_reference': 'BK20250925DEMO',
        'party_name': 'ทดสอบ Package Tour',
        'status': 'confirmed',
        'adults': 2,
        'children': 1,
        'infants': 0,
        'traveling_period_start': datetime.datetime(2025, 10, 15),
        'traveling_period_end': datetime.datetime(2025, 10, 20),
        'due_date': datetime.datetime(2025, 10, 1),
        'time_limit': datetime.datetime(2025, 10, 1),
        'created_at': datetime.datetime.now(),
        'description': 'ทัวร์ญี่ปุ่น 5 วัน 4 คืน Tokyo - Osaka\n• เดินทางโดยสายการบิน ANA\n• โรงแรม 4 ดาว ใจกลางเมือง\n• รวมอาหาร 3 มื้อต่อวัน',
        'guest_list': '1. นาย สมชาย ใจดี\n2. นาง สมหญิง ใจดี\n3. เด็กชาย น้อมใส ใจดี',
        'flight_info': 'ANA 807 BKK-NRT 23:55-07:25+1\nANA 806 NRT-BKK 17:55-22:30'
    }
    
    sample_customer = {
        'name': 'นาย สมชาย ใจดี',
        'phone': '0812345678'
    }
    
    sample_products = [
        {
            'no': 1,
            'name': 'ทัวร์ญี่ปุ่น Tokyo-Osaka 5วัน4คืน',
            'quantity': 3,
            'price': '45000.00',
            'amount': '135000.00'
        },
        {
            'no': 2,
            'name': 'ประกันการเดินทาง (คุ้มครอง 1 ล้านบาท)',
            'quantity': 3,
            'price': '350.00',
            'amount': '1050.00'
        },
        {
            'no': 3,
            'name': 'ส่วนลด Early Bird',
            'quantity': 1,
            'price': '5000.00',
            'amount': '-5000.00',
            'is_negative': True
        }
    ]
    
    # Override with provided data
    booking = {**sample_booking, **override_data.get('booking', {})}
    customer = {**sample_customer, **override_data.get('customer', {})}
    products = enhance_product_data(override_data.get('products', sample_products))
    
    # Prepare final context
    context = prepare_template_context(
        booking=booking,
        customer=customer,
        products=products,
        **{k: v for k, v in override_data.items() if k not in ['booking', 'customer', 'products']}
    )
    
    return context

if __name__ == "__main__":
    # Test functions
    print("Testing quote helper functions...")
    
    # Test number formatting
    print(f"Format 50000: {format_thai_number(50000)}")
    print(f"Format 1250: {format_thai_number(1250)}")
    
    # Test totals calculation
    test_products = [
        {'amount': '45000.00', 'is_negative': False},
        {'amount': '1050.00', 'is_negative': False},
        {'amount': '-5000.00', 'is_negative': True}
    ]
    totals = calculate_totals(test_products)
    print(f"Totals: {totals}")
    
    # Test context generation
    context = generate_quote_pdf_context()
    print(f"Generated context keys: {list(context.keys())}")