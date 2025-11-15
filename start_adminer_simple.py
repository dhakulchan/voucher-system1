#!/usr/bin/env python3
"""
Simple Adminer Launcher
Quick launcher for Adminer database management interface
"""

import os
import subprocess
import webbrowser
import time
import signal
import sys

def find_free_port():
    """Find if port 8080 is available"""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', 8080))
            return True
    except OSError:
        return False

def start_adminer():
    """Start Adminer using PHP built-in server"""
    print("🚀 Starting Adminer Database Management...")
    
    # Check if adminer.php exists
    if not os.path.exists('adminer.php'):
        print("❌ Adminer not found. Please run the full setup first.")
        return
    
    # Check port availability
    if not find_free_port():
        print("⚠️ Port 8080 is busy. Trying to stop existing server...")
        os.system("pkill -f 'php -S localhost:8080'")
        time.sleep(2)
    
    try:
        # Start PHP server
        print("📊 Starting PHP server for Adminer...")
        process = subprocess.Popen([
            'php', '-S', 'localhost:8080', 
            '-t', '/Applications/python/voucher-ro_v1.0'
        ])
        
        # Wait for server to start
        time.sleep(2)
        
        # Open browser
        adminer_url = "http://localhost:8080/adminer.php"
        print(f"🌐 Opening Adminer: {adminer_url}")
        webbrowser.open(adminer_url)
        
        print(f"""
✅ Adminer Running Successfully!

📊 Database Management: {adminer_url}
🔧 PHP Development Server: http://localhost:8080

💾 Database Connection for Enhanced System:
   Server: localhost:3306
   Username: voucher_user
   Password: voucher_secure_2024
   Database: voucher_enhanced

🔄 Press Ctrl+C to stop
""")
        
        # Handle graceful shutdown
        def signal_handler(sig, frame):
            print('\n🛑 Shutting down Adminer server...')
            process.terminate()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        # Keep running
        process.wait()
        
    except KeyboardInterrupt:
        print('\n🛑 Stopping Adminer server...')
        process.terminate()
    except Exception as e:
        print(f"❌ Error starting Adminer: {e}")

if __name__ == "__main__":
    os.chdir('/Applications/python/voucher-ro_v1.0')
    start_adminer()