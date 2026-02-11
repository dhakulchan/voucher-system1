from werkzeug.security import generate_password_hash
import mysql.connector
from datetime import datetime

# Database connection
conn = mysql.connector.connect(
    host="localhost",
    user="voucher_user",
    password="VoucherSecure2026!",
    database="voucher_enhanced"
)

cursor = conn.cursor()

# Create user นักเที่ยว2
username = "นักเที่ยว2"
email = "tourist2@dhakulchan.com"
password = "123456"  # Simple password for demo
password_hash = generate_password_hash(password)

cursor.execute("""
    INSERT INTO users (username, email, password_hash, role, created_at)
    VALUES (%s, %s, %s, %s, %s)
""", (username, email, password_hash, 'Customer', datetime.utcnow()))

conn.commit()
user_id = cursor.lastrowid

print(f"✅ สร้าง User สำเร็จ!")
print(f"   Username: {username}")
print(f"   Email: {email}")
print(f"   Password: {password}")
print(f"   Role: Customer")
print(f"   User ID: {user_id}")
print(f"\n🔐 Login ที่: https://booking.dhakulchan.net/auth/login")

cursor.close()
conn.close()
