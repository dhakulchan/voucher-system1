#!/usr/bin/env python3
"""
Adminer Manager - Complete database management utility
Enhanced script for managing local development database access
"""

import os
import sys
import subprocess
import time
import webbrowser
import signal
from pathlib import Path

class AdminerManager:
    def __init__(self):
        self.project_dir = Path("/Applications/python/voucher-ro_v1.0")
        self.adminer_file = self.project_dir / "adminer.php"
        self.port = 8080
        self.process = None
        
    def check_requirements(self):
        """Check if all requirements are met"""
        errors = []
        
        # Check PHP
        try:
            result = subprocess.run(['php', '--version'], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                errors.append("PHP not found or not working")
            else:
                print(f"✅ PHP: {result.stdout.split()[1]}")
        except FileNotFoundError:
            errors.append("PHP not installed")
        
        # Check Adminer file
        if not self.adminer_file.exists():
            errors.append(f"Adminer file not found: {self.adminer_file}")
        else:
            size_mb = self.adminer_file.stat().st_size / (1024 * 1024)
            print(f"✅ Adminer: {size_mb:.1f}MB")
        
        return errors
    
    def find_process(self):
        """Find existing PHP server process"""
        try:
            result = subprocess.run(['pgrep', '-f', f'php -S localhost:{self.port}'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip().split('\n')
            return []
        except:
            return []
    
    def stop_existing(self):
        """Stop any existing PHP server"""
        pids = self.find_process()
        if pids:
            print(f"🛑 Stopping existing PHP server (PIDs: {', '.join(pids)})")
            for pid in pids:
                try:
                    subprocess.run(['kill', pid], check=True)
                except:
                    pass
            time.sleep(1)
    
    def start_server(self):
        """Start PHP development server"""
        print(f"🚀 Starting PHP development server on port {self.port}")
        
        # Change to project directory
        os.chdir(self.project_dir)
        
        # Start PHP server
        cmd = ['php', '-S', f'localhost:{self.port}', '-t', str(self.project_dir)]
        self.process = subprocess.Popen(cmd)
        
        # Wait for server to start
        time.sleep(2)
        
        return self.process
    
    def open_browser(self):
        """Open Adminer in browser"""
        url = f"http://localhost:{self.port}/adminer.php"
        print(f"🌐 Opening: {url}")
        try:
            webbrowser.open(url)
        except Exception as e:
            print(f"⚠️ Could not open browser: {e}")
            print(f"📊 Please open manually: {url}")
    
    def show_connection_info(self):
        """Display database connection information"""
        print(f"""
✅ Adminer Server Running Successfully!

📊 Adminer URL: http://localhost:{self.port}/adminer.php
🔧 Server Root: {self.project_dir}

💾 Enhanced System Database:
   System: MySQL/MariaDB
   Server: localhost:3306
   Username: voucher_user  
   Password: voucher_secure_2024
   Database: voucher_enhanced

💾 Local Development Database:
   System: MySQL/MariaDB
   Server: localhost
   Username: root
   Password: [your MySQL password]
   Database: [select available]

🔄 Press Ctrl+C to stop the server
        """)
    
    def setup_signal_handler(self):
        """Setup graceful shutdown"""
        def signal_handler(sig, frame):
            print('\n🛑 Shutting down Adminer server...')
            if self.process:
                self.process.terminate()
                self.process.wait()
            print('✅ Server stopped successfully')
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def run(self):
        """Main execution method"""
        print("🔧 Adminer Manager - Local Development Database Access")
        print("=" * 60)
        
        # Check requirements
        errors = self.check_requirements()
        if errors:
            print("❌ Requirements not met:")
            for error in errors:
                print(f"   - {error}")
            return False
        
        # Stop existing servers
        self.stop_existing()
        
        # Start new server
        try:
            self.start_server()
            self.show_connection_info()
            self.open_browser()
            self.setup_signal_handler()
            
            # Keep running
            self.process.wait()
            
        except KeyboardInterrupt:
            print('\n🛑 Stopping server...')
            if self.process:
                self.process.terminate()
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
        
        return True

def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        if sys.argv[1] in ['--help', '-h']:
            print("""
Adminer Manager - Database Management for Local Development

Usage:
    python3 adminer_manager.py        # Start Adminer server
    python3 adminer_manager.py -h     # Show this help
    
Features:
    - Automatic PHP server management
    - Browser integration
    - Connection information display
    - Graceful shutdown handling
    - Process management
    
Database Access:
    - Enhanced voucher system (MariaDB)
    - Local MySQL/MariaDB instances
    - Full schema management
    - Query execution interface
            """)
            return
    
    manager = AdminerManager()
    success = manager.run()
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()