# utils/thai_utils.py - ฟังก์ชันสำหรับภาษาไทย
import calendar
from datetime import datetime

# Thai month names
THAI_MONTHS = [
    '', 'มกราคม', 'กุมภาพันธ์', 'มีนาคม', 'เมษายน', 'พฤษภาคม', 'มิถุนายน',
    'กรกฎาคม', 'สิงหาคม', 'กันยายน', 'ตุลาคม', 'พฤศจิกายน', 'ธันวาคม'
]

THAI_MONTHS_SHORT = [
    '', 'ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.',
    'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.'
]

# Thai day names
THAI_DAYS = [
    'จันทร์', 'อังคาร', 'พุธ', 'พฤหัสบดี', 'ศุกร์', 'เสาร์', 'อาทิตย์'
]

THAI_DAYS_SHORT = [
    'จ.', 'อ.', 'พ.', 'พฤ.', 'ศ.', 'ส.', 'อา.'
]

def thai_date_format(date_obj, format_type='full'):
    """แปลงวันที่เป็นรูปแบบภาษาไทย"""
    if not date_obj:
        return ''
    
    day = date_obj.day
    month = date_obj.month
    year = date_obj.year + 543  # แปลงเป็น พ.ศ.
    
    if format_type == 'full':
        return f"{day} {THAI_MONTHS[month]} พ.ศ. {year}"
    elif format_type == 'short':
        return f"{day} {THAI_MONTHS_SHORT[month]} {year}"
    elif format_type == 'numeric':
        return f"{day:02d}/{month:02d}/{year}"
    else:
        return f"{day}/{month}/{year}"

def thai_time_format(time_obj):
    """แปลงเวลาเป็นรูปแบบภาษาไทย"""
    if not time_obj:
        return ''
    return f"{time_obj.strftime('%H:%M')} น."

def thai_datetime_format(datetime_obj, format_type='full'):
    """แปลงวันที่และเวลาเป็นรูปแบบภาษาไทย"""
    if not datetime_obj:
        return ''
    
    date_part = thai_date_format(datetime_obj.date(), format_type)
    time_part = thai_time_format(datetime_obj.time())
    
    return f"{date_part} เวลา {time_part}"

def thai_number_to_text(number):
    """แปลงตัวเลขเป็นคำไทย"""
    ones = ['', 'หนึ่ง', 'สอง', 'สาม', 'สี่', 'ห้า', 'หก', 'เจ็ด', 'แปด', 'เก้า']
    tens = ['', '', 'ยี่', 'สาม', 'สี่', 'ห้า', 'หก', 'เจ็ด', 'แปด', 'เก้า']
    
    if number == 0:
        return 'ศูนย์'
    
    result = ''
    
    # Handle millions
    if number >= 1000000:
        millions = number // 1000000
        result += thai_number_to_text(millions) + 'ล้าน'
        number %= 1000000
    
    # Handle hundred thousands
    if number >= 100000:
        hundred_thousands = number // 100000
        result += thai_number_to_text(hundred_thousands) + 'แสน'
        number %= 100000
    
    # Handle ten thousands
    if number >= 10000:
        ten_thousands = number // 10000
        result += thai_number_to_text(ten_thousands) + 'หมื่น'
        number %= 10000
    
    # Handle thousands
    if number >= 1000:
        thousands = number // 1000
        result += thai_number_to_text(thousands) + 'พัน'
        number %= 1000
    
    # Handle hundreds
    if number >= 100:
        hundreds = number // 100
        result += ones[hundreds] + 'ร้อย'
        number %= 100
    
    # Handle tens
    if number >= 20:
        ten = number // 10
        result += tens[ten] + 'สิบ'
        number %= 10
    elif number >= 10:
        result += 'สิบ'
        number %= 10
    
    # Handle ones
    if number > 0:
        if number == 1 and len(result) > 0:
            result += 'เอ็ด'
        else:
            result += ones[number]
    
    return result

def format_thai_currency(amount, currency='THB'):
    """จัดรูปแบบเงินตราไทย"""
    if currency == 'THB':
        return f"฿{amount:,.2f}"
    elif currency == 'USD':
        return f"${amount:,.2f}"
    elif currency == 'EUR':
        return f"€{amount:,.2f}"
    else:
        return f"{currency} {amount:,.2f}"

def thai_currency_to_text(amount):
    """แปลงจำนวนเงินเป็นตัวหนังสือไทย"""
    baht = int(amount)
    satang = int((amount - baht) * 100)
    
    result = ''
    
    if baht > 0:
        result += thai_number_to_text(baht) + 'บาท'
    
    if satang > 0:
        if baht > 0:
            result += ''
        result += thai_number_to_text(satang) + 'สตางค์'
    elif baht > 0:
        result += 'ถ้วน'
    
    return result or 'ศูนย์บาท'

def thai_booking_status(status):
    """แปลงสถานะการจองเป็นภาษาไทย"""
    status_map = {
        'pending': 'รอดำเนินการ',
        'confirmed': 'ยืนยันแล้ว',
        'cancelled': 'ยกเลิก',
        'completed': 'เสร็จสิ้น',
        'paid': 'ชำระแล้ว',
        'unpaid': 'ยังไม่ชำระ'
    }
    return status_map.get(status, status)

def thai_booking_type(booking_type):
    """แปลงประเภทการจองเป็นภาษาไทย"""
    type_map = {
        'tour': 'ทัวร์',
        'hotel': 'โรงแรม',
        'transport': 'รถรับส่ง',
        'flight': 'เที่ยวบิน',
        'package': 'แพ็คเกจ'
    }
    return type_map.get(booking_type, booking_type)

def validate_thai_id_card(id_card):
    """ตรวจสอบเลขบัตรประชาชนไทย"""
    if not id_card or len(id_card) != 13 or not id_card.isdigit():
        return False
    
    # คำนวณหลักตรวจสอบ
    check_sum = 0
    for i in range(12):
        check_sum += int(id_card[i]) * (13 - i)
    
    check_digit = (11 - (check_sum % 11)) % 10
    
    return int(id_card[12]) == check_digit

def format_thai_phone(phone):
    """จัดรูปแบบเบอร์โทรศัพท์ไทย"""
    # ลบอักขระที่ไม่ใช่ตัวเลข
    numbers = ''.join(filter(str.isdigit, phone))
    
    if numbers.startswith('66'):
        numbers = '0' + numbers[2:]
    
    if len(numbers) == 10 and numbers.startswith('0'):
        return f"{numbers[:3]}-{numbers[3:6]}-{numbers[6:]}"
    elif len(numbers) == 9:
        return f"0{numbers[:2]}-{numbers[2:5]}-{numbers[5:]}"
    
    return phone

def thai_address_format(address_dict):
    """จัดรูปแบบที่อยู่ไทย"""
    parts = []
    
    if address_dict.get('number'):
        parts.append(f"เลขที่ {address_dict['number']}")
    
    if address_dict.get('village'):
        parts.append(f"หมู่บ้าน {address_dict['village']}")
    
    if address_dict.get('lane'):
        parts.append(f"ซอย {address_dict['lane']}")
    
    if address_dict.get('road'):
        parts.append(f"ถนน {address_dict['road']}")
    
    if address_dict.get('subdistrict'):
        parts.append(f"แขวง/ตำบล {address_dict['subdistrict']}")
    
    if address_dict.get('district'):
        parts.append(f"เขต/อำเภอ {address_dict['district']}")
    
    if address_dict.get('province'):
        parts.append(f"จังหวัด {address_dict['province']}")
    
    if address_dict.get('postal_code'):
        parts.append(address_dict['postal_code'])
    
    return ' '.join(parts)
