#!/usr/bin/env python3
"""
Simple Activity Log Test
ทดสอบ Activity Log เฉพาะส่วน
"""
from app import create_app
from models.booking import Booking

def simple_test():
    """ทดสอบการเรียก Activity Logs ผ่าน ORM"""
    print("🔍 Testing Activity Logs via app context...")
    
    app = create_app()
    with app.app_context():
        booking = Booking.query.get(65)
        if not booking:
            print("❌ Booking 65 not found")
            return False
            
        print(f"✅ Found booking: {booking.booking_reference}")
        
        # ทดสอบการโหลดข้อมูลแบบเดียวกับ booking view
        try:
            # สิ่งที่เราต้องการคือให้ใช้ direct database connection
            import pymysql
            connection = pymysql.connect(
                host='localhost',
                user='root',
                password='',
                database='voucher_enhanced',
                charset='utf8mb4'
            )
            
            with connection.cursor() as cursor:
                # Get activity logs for this booking
                cursor.execute("""
                    SELECT al.id, al.user_id, al.action, al.description, al.ip_address, 
                           al.user_agent, al.created_at, u.username, u.full_name
                    FROM activity_logs al
                    LEFT JOIN users u ON al.user_id = u.id
                    WHERE al.description LIKE %s
                    ORDER BY al.created_at DESC
                    LIMIT 50
                """, (f'%[BOOKING #{65}]%',))
                
                activity_logs_data = cursor.fetchall()
                print(f"📋 Found {len(activity_logs_data)} activity logs for booking 65")
                
                if activity_logs_data:
                    # Test ActivityLogDisplay creation
                    class ActivityLogDisplay:
                        def __init__(self, log_data):
                            (self.id, self.user_id, self.action, self.description, self.ip_address, 
                             self.user_agent, self.created_at, username, full_name) = log_data
                            
                            class UserDisplay:
                                def __init__(self, username, full_name):
                                    self.username = username or 'System'
                                    self.full_name = full_name or ''
                                    self.name = full_name or username or 'System'
                                    
                            self.user = UserDisplay(username, full_name)
                    
                    activity_logs = [ActivityLogDisplay(log_data) for log_data in activity_logs_data]
                    print(f"✅ Created {len(activity_logs)} ActivityLogDisplay objects")
                    
                    for i, log in enumerate(activity_logs, 1):
                        print(f"  {i}. {log.action} - {log.description[:50]}...")
                        
                    return True
                else:
                    print("❌ No activity logs found")
                    return False
                    
            connection.close()
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = simple_test()
    if success:
        print("\n🎉 Activity Logs working correctly!")
    else:
        print("\n❌ Activity Logs have issues!")