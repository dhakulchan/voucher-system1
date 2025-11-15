#!/usr/bin/env python3
"""
🛡️ Template Corruption Monitor - Advanced Version
GOAL: Monitor view_en.html for corruption and auto-fix
"""
import os
import time
import hashlib
import subprocess
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

class TemplateCorruptionMonitor:
    def __init__(self):
        self.template_path = "/Applications/python/voucher-ro_v1.0/templates/booking/view_en.html"
        self.backup_dir = "/Applications/python/voucher-ro_v1.0/template_backups"
        self.corruption_count = 0
        self.last_good_hash = None
        
        # Ensure backup directory exists
        os.makedirs(self.backup_dir, exist_ok=True)
        
    def check_template_syntax(self):
        """ตรวจสอบ syntax ของ template"""
        try:
            env = Environment(loader=FileSystemLoader('templates'))
            template = env.get_template('booking/view_en.html')
            return True, "Template syntax OK"
        except Exception as e:
            return False, str(e)
            
    def get_file_hash(self):
        """คำนวณ hash ของไฟล์"""
        with open(self.template_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
            
    def create_backup(self):
        """สร้าง backup ของไฟล์"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_path = f"{self.backup_dir}/view_en.html.backup_{timestamp}"
        subprocess.run(['cp', self.template_path, backup_path])
        return backup_path
        
    def auto_fix_common_issues(self):
        """แก้ไขปัญหาทั่วไปอัตโนมัติ"""
        with open(self.template_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Common fixes
        fixes_applied = []
        
        # Fix 1: Missing } in return statement
        if "return bookingData ? bookingData.dataset.bookingId : {{ booking.id }" in content:
            content = content.replace(
                "return bookingData ? bookingData.dataset.bookingId : {{ booking.id }",
                "return bookingData ? bookingData.dataset.bookingId : {{ booking.id }};"
            )
            fixes_applied.append("Fixed missing } in return statement")
            
        # Fix 2: Extra } after function
        content = content.replace("    };\n    }", "    };")
        
        # Fix 3: Spacing in object literal
        if "    reference: '{{ booking.booking_reference }}'," in content:
            content = content.replace(
                "    reference: '{{ booking.booking_reference }}',",
                "        reference: '{{ booking.booking_reference }}',"
            )
            fixes_applied.append("Fixed object literal spacing")
            
        # Write back
        with open(self.template_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        return fixes_applied
        
    def monitor_and_fix(self, interval=30):
        """ตรวจสอบและแก้ไขอัตโนมัติ"""
        print("🛡️ Template Corruption Monitor Started")
        print(f"📁 Monitoring: {self.template_path}")
        print(f"⏰ Check interval: {interval} seconds")
        print("🚨 Press Ctrl+C to stop")
        
        try:
            while True:
                # Check syntax
                is_valid, error_msg = self.check_template_syntax()
                current_hash = self.get_file_hash()
                
                if not is_valid:
                    self.corruption_count += 1
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                    
                    print(f"\n🚨 CORRUPTION DETECTED #{self.corruption_count}")
                    print(f"⏰ Time: {timestamp}")
                    print(f"❌ Error: {error_msg}")
                    
                    # Create backup before fixing
                    backup_path = self.create_backup()
                    print(f"📦 Backup created: {backup_path}")
                    
                    # Apply auto-fixes
                    fixes = self.auto_fix_common_issues()
                    
                    # Test fix
                    is_fixed, _ = self.check_template_syntax()
                    
                    if is_fixed:
                        print("✅ AUTO-FIX SUCCESSFUL!")
                        for fix in fixes:
                            print(f"   🔧 {fix}")
                        self.last_good_hash = self.get_file_hash()
                    else:
                        print("❌ AUTO-FIX FAILED - Manual intervention required")
                        
                elif current_hash != self.last_good_hash:
                    print(f"📝 File changed (hash: {current_hash[:8]}...)")
                    self.last_good_hash = current_hash
                    
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n🛑 Monitor stopped by user")
            
if __name__ == "__main__":
    monitor = TemplateCorruptionMonitor()
    monitor.monitor_and_fix(interval=30)  # Check every 30 seconds