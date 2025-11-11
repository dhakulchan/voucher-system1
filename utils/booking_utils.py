import random
import string
from datetime import datetime

def generate_booking_reference():
    """Generate a unique booking reference"""
    today = datetime.now()
    date_part = today.strftime('%Y%m%d')
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"BK{date_part}{random_part}"

def generate_invoice_reference():
    """Generate a unique invoice reference"""
    today = datetime.now()
    date_part = today.strftime('%Y%m%d')
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"INV{date_part}{random_part}"

def generate_quote_reference():
    """Generate a unique quote reference"""
    today = datetime.now()
    date_part = today.strftime('%Y%m%d')
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"QT{date_part}{random_part}"

def format_currency(amount, currency='THB'):
    """Format currency amount"""
    if currency == 'THB':
        return f"฿{amount:,.2f}"
    elif currency == 'USD':
        return f"${amount:,.2f}"
    elif currency == 'EUR':
        return f"€{amount:,.2f}"
    else:
        return f"{currency} {amount:,.2f}"

def calculate_nights(checkin_date, checkout_date):
    """Calculate number of nights between two dates"""
    if checkin_date and checkout_date:
        delta = checkout_date - checkin_date
        return delta.days
    return 0

def validate_email(email):
    """Basic email validation"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone):
    """Basic phone validation"""
    import re
    # Remove all non-digit characters
    cleaned = re.sub(r'\D', '', phone)
    # Check if it's between 8-15 digits
    return 8 <= len(cleaned) <= 15

def slugify(text):
    """Convert text to URL-friendly slug"""
    import re
    # Convert to lowercase and replace spaces with hyphens
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text

def truncate_text(text, length=50, suffix='...'):
    """Truncate text to specified length"""
    if text and len(text) > length:
        return text[:length].strip() + suffix
    return text or ''

def get_file_extension(filename):
    """Get file extension from filename"""
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

def is_allowed_file(filename, allowed_extensions):
    """Check if file extension is allowed"""
    return get_file_extension(filename) in allowed_extensions
