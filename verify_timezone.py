#!/usr/bin/env python3
"""
ตรวจสอบการตั้งค่า Timezone เป็น Asia/Bangkok
Verify Timezone Configuration for Asia/Bangkok
"""
import os
import sys
from datetime import datetime
import pytz

# Set timezone
os.environ['TZ'] = 'Asia/Bangkok'
try:
    import time
    time.tzset()
except AttributeError:
    print("⚠️  Windows ไม่รองรับ time.tzset()")

def verify_timezone():
    """ตรวจสอบการตั้งค่า timezone"""
    print("=" * 60)
    print("🌏 ตรวจสอบการตั้งค่า Timezone - Asia/Bangkok")
    print("=" * 60)
    
    # 1. Check OS environment
    tz_env = os.environ.get('TZ', 'Not Set')
    print(f"\n1️⃣  OS Environment TZ: {tz_env}")
    
    # 2. Check Python datetime
    now_local = datetime.now()
    print(f"2️⃣  Python datetime.now(): {now_local}")
    print(f"    Format: {now_local.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    # 3. Check pytz
    bangkok_tz = pytz.timezone('Asia/Bangkok')
    now_bangkok = datetime.now(bangkok_tz)
    print(f"3️⃣  pytz Asia/Bangkok: {now_bangkok}")
    print(f"    Format: {now_bangkok.strftime('%Y-%m-%d %H:%M:%S %Z%z')}")
    print(f"    UTC Offset: {now_bangkok.strftime('%z')}")
    
    # 4. Check UTC time
    now_utc = datetime.now(pytz.UTC)
    print(f"4️⃣  UTC Time: {now_utc}")
    print(f"    Format: {now_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    # 5. Time difference
    diff_hours = (now_bangkok.hour - now_utc.hour) % 24
    print(f"5️⃣  Time Difference: UTC+{diff_hours}")
    
    # 6. Check Flask Config
    try:
        from config import Config
        print(f"6️⃣  Flask Config TIMEZONE: {Config.TIMEZONE}")
    except Exception as e:
        print(f"⚠️  Cannot load Flask config: {e}")
    
    # 7. Check utils/timezone_helper
    try:
        from utils.timezone_helper import now_thailand, format_thai_datetime
        now_th = now_thailand()
        print(f"7️⃣  utils.timezone_helper.now_thailand(): {now_th}")
        print(f"    Formatted: {format_thai_datetime(now_th, '%d/%m/%Y %H:%M:%S')}")
    except Exception as e:
        print(f"⚠️  Cannot load timezone_helper: {e}")
    
    # 8. Check if timezone is correct
    print("\n" + "=" * 60)
    expected_offset = "+0700"
    actual_offset = now_bangkok.strftime('%z')
    
    if actual_offset == expected_offset:
        print("✅ SUCCESS: Timezone is correctly set to Asia/Bangkok (UTC+7)")
    else:
        print(f"❌ ERROR: Expected {expected_offset}, got {actual_offset}")
    
    print("=" * 60)
    
    # Thai datetime display
    print("\n🇹🇭 การแสดงผลวันที่และเวลาภาษาไทย:")
    print(f"   วันที่: {now_bangkok.strftime('%d/%m/%Y')}")
    print(f"   เวลา: {now_bangkok.strftime('%H:%M:%S')}")
    print(f"   วันที่และเวลา: {now_bangkok.strftime('%d/%m/%Y %H:%M:%S')}")
    
    return actual_offset == expected_offset

if __name__ == '__main__':
    success = verify_timezone()
    sys.exit(0 if success else 1)
