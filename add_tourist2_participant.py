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

# Get campaign 1 details
cursor.execute("SELECT id, name, group_price FROM group_buy_campaigns WHERE id = 1")
campaign = cursor.fetchone()

if not campaign:
    print("❌ Campaign not found")
    exit(1)

campaign_id, campaign_name, price = campaign

# Get an active group for this campaign
cursor.execute("""
    SELECT id FROM group_buy_groups 
    WHERE campaign_id = 1 AND status IN ('active', 'pending', 'success')
    LIMIT 1
""")
group_result = cursor.fetchone()

if not group_result:
    print("❌ No active group found for campaign 1")
    exit(1)

group_id = group_result[0]

# Create participant for นักเที่ยว2 (user_id=9)
user_id = 9
participant_name = "นักเที่ยว2"
email = "tourist2@dhakulchan.com"
phone = "0812345678"

cursor.execute("""
    INSERT INTO group_buy_participants 
    (group_id, campaign_id, customer_id, participant_name, participant_email, participant_phone, 
     payment_status, payment_amount, created_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
""", (group_id, campaign_id, user_id, participant_name, email, phone, 
      'paid', price, datetime.utcnow()))

conn.commit()
participant_id = cursor.lastrowid

print(f"✅ เพิ่มผู้เข้าร่วมสำเร็จ!")
print(f"   Campaign: {campaign_name}")
print(f"   Group ID: {group_id}")
print(f"   Participant: {participant_name}")
print(f"   Status: paid")
print(f"   Price: {price} บาท")
print(f"\n🎉 ตอนนี้สามารถเขียนรีวิวได้แล้ว!")

cursor.close()
conn.close()
