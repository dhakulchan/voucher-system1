#!/usr/bin/env python3
"""
🕵️ Template Corruption Source Detective
GOAL: Identify the exact source of recurring corruption
"""
import os
import time
import psutil
import subprocess
from datetime import datetime

class CorruptionDetective:
    def __init__(self):
        self.template_path = "/Applications/python/voucher-ro_v1.0/templates/booking/view_en.html"
        self.suspicious_processes = []
        self.file_access_log = []
        
    def get_file_access_processes(self):
        """หา processes ที่เข้าถึงไฟล์"""
        try:
            # ใช้ lsof เพื่อหา processes ที่เปิดไฟล์
            result = subprocess.run(['lsof', self.template_path], 
                                  capture_output=True, text=True)
            
            if result.stdout:
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                processes = []
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 2:
                        processes.append({
                            'command': parts[0],
                            'pid': parts[1],
                            'user': parts[2] if len(parts) > 2 else 'unknown',
                            'time': datetime.now().strftime("%H:%M:%S")
                        })
                return processes
            return []
        except Exception as e:
            print(f"Error checking file access: {e}")
            return []
            
    def check_suspicious_editors(self):
        """ตรวจหา text editors / IDEs ที่เปิดอยู่"""
        suspicious_names = [
            'code',        # VS Code
            'vim', 'nvim', # Vim editors  
            'emacs',       # Emacs
            'sublime',     # Sublime Text
            'atom',        # Atom
            'nano',        # Nano
            'TextEdit',    # macOS TextEdit
            'prettier',    # Prettier formatter
            'eslint',      # ESLint
            'python'       # Python scripts
        ]
        
        running_editors = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                name = proc.info['name'].lower()
                cmdline = ' '.join(proc.info['cmdline'] or [])
                
                for suspicious in suspicious_names:
                    if suspicious in name or suspicious in cmdline:
                        running_editors.append({
                            'name': proc.info['name'],
                            'pid': proc.info['pid'],
                            'cmdline': cmdline[:100],  # Truncate long commands
                            'create_time': datetime.fromtimestamp(
                                proc.create_time()
                            ).strftime("%H:%M:%S")
                        })
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
        return running_editors
        
    def check_git_hooks(self):
        """ตรวจสอบ Git hooks ที่อาจแก้ไขไฟล์"""
        hooks_dir = "/Applications/python/voucher-ro_v1.0/.git/hooks"
        active_hooks = []
        
        if os.path.exists(hooks_dir):
            for hook_file in os.listdir(hooks_dir):
                hook_path = os.path.join(hooks_dir, hook_file)
                if os.path.isfile(hook_path) and os.access(hook_path, os.X_OK):
                    # Check if hook mentions template files
                    try:
                        with open(hook_path, 'r') as f:
                            content = f.read()
                            if 'template' in content.lower() or 'view_en.html' in content:
                                active_hooks.append({
                                    'name': hook_file,
                                    'path': hook_path,
                                    'mentions_templates': True
                                })
                    except:
                        pass
                        
        return active_hooks
        
    def investigate(self):
        """รัน investigation complete"""
        print("🕵️ Template Corruption Source Investigation")
        print("=" * 50)
        
        # 1. Check file access
        print("\n📁 Current File Access:")
        file_processes = self.get_file_access_processes()
        if file_processes:
            for proc in file_processes:
                print(f"  🔍 {proc['command']} (PID: {proc['pid']}) - {proc['time']}")
        else:
            print("  ✅ No active file access detected")
            
        # 2. Check running editors
        print("\n📝 Suspicious Editors/Tools:")
        editors = self.check_suspicious_editors()
        if editors:
            for editor in editors:
                print(f"  ⚠️  {editor['name']} (PID: {editor['pid']}) - Started: {editor['create_time']}")
                if len(editor['cmdline']) > 50:
                    print(f"     Command: {editor['cmdline']}")
        else:
            print("  ✅ No suspicious editors detected")
            
        # 3. Check Git hooks
        print("\n🔗 Git Hooks:")
        hooks = self.check_git_hooks()
        if hooks:
            for hook in hooks:
                print(f"  ⚠️  {hook['name']} - Mentions templates: {hook['mentions_templates']}")
        else:
            print("  ✅ No suspicious Git hooks found")
            
        # 4. Summary & Recommendations
        print("\n📊 Investigation Summary:")
        total_suspects = len(file_processes) + len(editors) + len(hooks)
        print(f"  🎯 Total suspects: {total_suspects}")
        
        if total_suspects > 0:
            print("\n🚨 RECOMMENDATIONS:")
            if editors:
                print("  1. Check VS Code auto-formatting settings")
                print("  2. Disable auto-save in editors")
                print("  3. Check for Prettier/ESLint configurations")
            if hooks:
                print("  4. Review Git hooks for template modifications")
            if file_processes:
                print("  5. Monitor identified file access processes")
        else:
            print("  ✅ No obvious corruption source identified")
            print("  🔄 Continue monitoring for pattern analysis")

if __name__ == "__main__":
    detective = CorruptionDetective()
    detective.investigate()