#!/usr/bin/env python3
"""
Quick Diagnostic for Adminer PHP Issue
Identifies why adminer is downloading instead of executing
"""

import subprocess
import sys
import os

def run_remote_command(command, description=""):
    """Execute command on remote server"""
    if description:
        print(f"🔍 {description}")
    
    ssh_cmd = [
        'ssh', '-o', 'StrictHostKeyChecking=no',
        '-i', os.path.expanduser("~/.ssh/LightsailDefaultKey-ap-southeast-1.pem"),
        'bitnami@54.255.136.172',
        command
    ]
    
    try:
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=30)
        print(f"📄 Output: {result.stdout.strip()}")
        if result.stderr.strip():
            print(f"❌ Error: {result.stderr.strip()}")
        return result.returncode == 0
    except Exception as e:
        print(f"💥 Exception: {str(e)}")
        return False

def main():
    """Run diagnostics"""
    print("🔍 Adminer PHP Execution Diagnostics")
    print("=" * 50)
    
    diagnostics = [
        ("curl -s -I http://localhost/adminer/adminer.php | head -5", "Check HTTP headers for adminer.php"),
        ("curl -s -I http://localhost/adminer/ | head -5", "Check HTTP headers for adminer directory"),
        ("ls -la /opt/bitnami/apache/htdocs/adminer/", "Check adminer directory contents"),
        ("apache2ctl -M | grep php", "Check if PHP module is loaded"),
        ("php --version", "Check PHP version"),
        ("cat /etc/apache2/mods-available/mime.conf | grep php", "Check PHP MIME configuration"),
        ("sudo systemctl status apache2 | head -10", "Check Apache status"),
        ("sudo tail -5 /var/log/apache2/error.log", "Check recent Apache errors"),
    ]
    
    for cmd, desc in diagnostics:
        print(f"\n🔍 {desc}")
        print("-" * 40)
        run_remote_command(cmd)
    
    print("\n" + "=" * 50)
    print("🎯 Common Issues and Solutions:")
    print("1. If Content-Type is 'application/octet-stream' or 'text/plain': PHP module not configured")
    print("2. If 404 errors: File path or permissions issue")
    print("3. If 'No such file': Adminer not properly installed")
    print("4. If PHP module missing: Run 'sudo a2enmod php8.x' and restart Apache")
    print("\n💡 To fix the issue, run: python fix_php_execution.py")

if __name__ == "__main__":
    main()