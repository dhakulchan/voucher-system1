#!/usr/bin/env python3
"""
Send WeasyPrint generator update via HTTP to production server
"""

import requests
import json
import base64

# Read the modified WeasyPrint generator file
with open('services/weasyprint_quote_generator.py', 'r', encoding='utf-8') as f:
    updated_content = f.read()

# Create update payload
payload = {
    'action': 'update_weasyprint_generator',
    'file_content': base64.b64encode(updated_content.encode('utf-8')).decode('utf-8'),
    'backup_original': True
}

try:
    # Try to send update via debug route (if exists)
    update_url = 'https://service.dhakulchan.net/api/debug/update-generator'
    
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'WeasyPrint-Debug-Update/1.0'
    }
    
    print("🔄 Attempting to send WeasyPrint generator update to production...")
    print(f"📤 Content size: {len(updated_content)} characters")
    
    response = requests.post(update_url, data=json.dumps(payload), headers=headers, timeout=30)
    
    if response.status_code == 200:
        print("✅ WeasyPrint generator updated successfully!")
        print(f"📋 Response: {response.text}")
    else:
        print(f"❌ Update failed with status {response.status_code}")
        print(f"Response: {response.text}")
        
except requests.exceptions.RequestException as e:
    print(f"❌ Network error: {e}")
    print("\n📝 Manual update required - copy the following content:")
    print("=" * 50)
    print("File: services/weasyprint_quote_generator.py")
    print("=" * 50)
    print(f"Lines around 158-170 should contain the debug logging code...")
    
except Exception as e:
    print(f"❌ Error: {e}")

print("\n🔧 Alternative: Use Adminer file manager or SSH to update the file manually")
print("💡 Key changes: Added debug logging and forced data override before template.render()")