# routes/language.py - การจัดการภาษา
from flask import Blueprint, request, session, redirect, url_for

language_bp = Blueprint('language', __name__)

@language_bp.route('/set-language/<language>')
def set_language(language):
    """ตั้งค่าภาษาในเซสชัน"""
    
    # รองรับภาษาไทยและอังกฤษ
    supported_languages = ['th', 'en']
    
    if language in supported_languages:
        session['language'] = language
    else:
        session['language'] = 'en'  # ค่าเริ่มต้นเป็นภาษาอังกฤษ
    
    # กลับไปหน้าเดิมหรือหน้าแรก
    return redirect(request.referrer or url_for('dashboard.index'))

@language_bp.context_processor
def inject_language():
    """ส่งข้อมูลภาษาปัจจุบันให้ templates"""
    current_lang = session.get('language', 'en')
    return {
        'current_language': current_lang,
        'is_thai': current_lang == 'th'
    }

def get_current_language():
    """ดึงภาษาปัจจุบัน"""
    return session.get('language', 'en')

def translate(th_text, en_text=None):
    """แปลข้อความตามภาษาปัจจุบัน"""
    current_lang = get_current_language()
    
    if current_lang == 'en' and en_text:
        return en_text
    elif current_lang == 'th':
        return th_text
    
    # ถ้าเป็นภาษาอังกฤษแต่ไม่มี en_text ให้ใช้ th_text 
    # หรือถ้าเป็นภาษาอื่นที่ไม่รองรับ ให้ใช้ English เป็นค่าเริ่มต้น
    return en_text if en_text else th_text

# Dictionary สำหรับแปลข้อความทั่วไป
TRANSLATIONS = {
    'th': {
        'dashboard': 'แดชบอร์ด',
        'booking': 'การจอง',
        'voucher': 'ใบบัตร',
        'customer': 'ลูกค้า',
        'api_docs': 'API เอกสาร',
        'login': 'เข้าสู่ระบบ',
        'logout': 'ออกจากระบบ',
        'profile': 'โปรไฟล์',
        'create': 'สร้าง',
        'edit': 'แก้ไข',
        'delete': 'ลบ',
        'view': 'ดู',
        'save': 'บันทึก',
        'cancel': 'ยกเลิก',
        'search': 'ค้นหา',
        'filter': 'กรอง',
        'status': 'สถานะ',
        'pending': 'รอดำเนินการ',
        'confirmed': 'ยืนยันแล้ว',
        'completed': 'เสร็จสิ้น',
        'cancelled': 'ยกเลิก',
        'active': 'ใช้งานได้',
        'used': 'ใช้แล้ว',
        'expired': 'หมดอายุ',
        'total': 'รวม',
        'amount': 'จำนวนเงิน',
        'date': 'วันที่',
        'time': 'เวลา',
        'name': 'ชื่อ',
        'email': 'อีเมล',
        'phone': 'เบอร์โทรศัพท์',
        'address': 'ที่อยู่',
        'tour_type': 'ประเภททัวร์',
        'adults': 'ผู้ใหญ่',
        'children': 'เด็ก',
        'special_requests': 'ความต้องการพิเศษ',
        'voucher_number': 'หมายเลขใบบัตร',
        'booking_number': 'หมายเลขจอง',
        'generated_at': 'สร้างเมื่อ',
        'valid_until': 'ใช้ได้ถึง',
        'success': 'สำเร็จ',
        'error': 'ข้อผิดพลาด',
        'warning': 'คำเตือน',
        'info': 'ข้อมูล',
        'confirm': 'ยืนยัน',
        'download': 'ดาวน์โหลด',
        'print': 'พิมพ์',
        'send_email': 'ส่งอีเมล',
        'back': 'กลับ',
        'next': 'ถัดไป',
        'previous': 'ก่อนหน้า',
        'first': 'แรก',
        'last': 'สุดท้าย',
        'list': 'รายการ',
        'customers': 'ลูกค้า',
        'add_new_customer': 'เพิ่มลูกค้าใหม่',
        'tour_voucher_system': 'ระบบจัดการใบบัตรทัวร์',
        'search_customers': 'ค้นหาลูกค้า',
        'no_customers_found': 'ไม่พบข้อมูลลูกค้า',
        'no_customers_message': 'ยังไม่มีลูกค้าในระบบ หรือไม่มีข้อมูลที่ตรงกับเงื่อนไขการค้นหา',
        'name_email_phone_placeholder': 'ชื่อ, อีเมล, เบอร์โทรศัพท์...',
        'full_name': 'ชื่อ-นามสกุล',
        'nationality': 'สัญชาติ',
        'booking_count': 'จำนวนการจอง',
        'registration_date': 'วันที่สมัครสมาชิก',
        'actions': 'การดำเนินการ',
        'view_details': 'ดูรายละเอียด',
        'create_new_booking': 'สร้างการจองใหม่',
        'add_first_customer': 'เพิ่มลูกค้าคนแรก',
        'tour_voucher_management_system': 'Dhakul Chan Management System',
        'profile': 'โปรไฟล์',
        'login': 'เข้าสู่ระบบ',
        'language_label': 'ภาษา / Language',
        'invoice_ninja': 'Invoice Ninja',
        'create_quote': 'สร้าง Quote',
        'create_invoice': 'สร้าง Invoice', 
        'send_invoice': 'ส่ง Invoice',
        'mark_as_paid': 'ทำเครื่องหมายชำระแล้ว',
        'quote_status': 'สถานะ Quote',
        'invoice_status': 'สถานะ Invoice',
        'connected': 'เชื่อมต่อแล้ว',
        'disconnected': 'ไม่ได้เชื่อมต่อ',
        'connection_error': 'เกิดข้อผิดพลาดในการเชื่อมต่อ',
        'no_quote': 'ยังไม่มี Quote',
        'no_invoice': 'ยังไม่มี Invoice',
        'checking': 'กำลังตรวจสอบ...',
        'integration_statistics': 'สถิติการเชื่อมต่อ',
        'total_bookings_with_quotes': 'จำนวนการจองที่มี Quote',
        'total_bookings_with_invoices': 'จำนวนการจองที่มี Invoice',
        'bookings_with_invoice_ninja_integration': 'การจองที่เชื่อมต่อกับ Invoice Ninja',
        'no_invoice_ninja_integration_found': 'ไม่พบการเชื่อมต่อ Invoice Ninja',
        'no_bookings_integrated_message': 'ยังไม่มีการจองที่เชื่อมต่อกับ Invoice Ninja',
        'go_to_bookings': 'ไปที่การจอง'
    },
    'en': {
        'dashboard': 'Dashboard',
        'booking': 'Booking',
        'voucher': 'Voucher',
        'customer': 'Customer',
        'api_docs': 'API Docs',
        'login': 'Login',
        'logout': 'Logout',
        'profile': 'Profile',
        'create': 'Create',
        'edit': 'Edit',
        'delete': 'Delete',
        'view': 'View',
        'save': 'Save',
        'cancel': 'Cancel',
        'search': 'Search',
        'filter': 'Filter',
        'status': 'Status',
        'pending': 'Pending',
        'confirmed': 'Confirmed',
        'completed': 'Completed',
        'cancelled': 'Cancelled',
        'active': 'Active',
        'used': 'Used',
        'expired': 'Expired',
        'total': 'Total',
        'amount': 'Amount',
        'date': 'Date',
        'time': 'Time',
        'name': 'Name',
        'email': 'Email',
        'phone': 'Phone',
        'address': 'Address',
        'tour_type': 'Tour Type',
        'adults': 'Adults',
        'children': 'Children',
        'special_requests': 'Special Requests',
        'voucher_number': 'Voucher Number',
        'booking_number': 'Booking Number',
        'generated_at': 'Generated At',
        'valid_until': 'Valid Until',
        'success': 'Success',
        'error': 'Error',
        'warning': 'Warning',
        'info': 'Info',
        'confirm': 'Confirm',
        'download': 'Download',
        'print': 'Print',
        'send_email': 'Send Email',
        'back': 'Back',
        'next': 'Next',
        'previous': 'Previous',
        'first': 'First',
        'last': 'Last',
        'list': 'List',
        'customers': 'Customers',
        'add_new_customer': 'Add New Customer',
        'tour_voucher_system': 'Tour Voucher Management System',
        'search_customers': 'Search Customers',
        'no_customers_found': 'No Customers Found',
        'no_customers_message': 'There are no customers in the system or no data matches the search criteria',
        'name_email_phone_placeholder': 'Name, Email, Phone...',
        'full_name': 'Full Name',
        'nationality': 'Nationality',
        'booking_count': 'Bookings',
        'registration_date': 'Registration Date',
        'actions': 'Actions',
        'view_details': 'View Details',
        'create_new_booking': 'Create New Booking',
        'add_first_customer': 'Add First Customer',
        'tour_voucher_management_system': 'Dhakul Chan Management System',
        'profile': 'Profile',
        'login': 'Login',
        'language_label': 'Language / ภาษา',
        'invoice_ninja': 'Invoice Ninja',
        'create_quote': 'Create Quote',
        'create_invoice': 'Create Invoice',
        'send_invoice': 'Send Invoice',
        'mark_as_paid': 'Mark as Paid',
        'quote_status': 'Quote Status',
        'invoice_status': 'Invoice Status',
        'connected': 'Connected',
        'disconnected': 'Disconnected',
        'connection_error': 'Connection Error',
        'no_quote': 'No Quote',
        'no_invoice': 'No Invoice',
        'checking': 'Checking...',
        'integration_statistics': 'Integration Statistics',
        'total_bookings_with_quotes': 'Total Bookings with Quotes',
        'total_bookings_with_invoices': 'Total Bookings with Invoices',
        'bookings_with_invoice_ninja_integration': 'Bookings with Invoice Ninja Integration',
        'no_invoice_ninja_integration_found': 'No Invoice Ninja Integration Found',
        'no_bookings_integrated_message': 'No bookings have been integrated with Invoice Ninja yet.',
        'go_to_bookings': 'Go to Bookings',
        'language_label': 'Language'
    }
}

def t(key, **kwargs):
    """ฟังก์ชันแปลภาษา"""
    current_lang = get_current_language()
    text = TRANSLATIONS.get(current_lang, {}).get(key, key)
    
    # แทนที่ตัวแปรถ้ามี
    if kwargs:
        text = text.format(**kwargs)
    
    return text

def get_translations_json():
    """ส่งคืน translations ในรูปแบบ JSON สำหรับ JavaScript"""
    current_lang = get_current_language()
    return TRANSLATIONS.get(current_lang, {})
