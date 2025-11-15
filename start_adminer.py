#!/usr/bin/env python3
"""
Adminer Setup for Local Development
Integrates Adminer database management into the local development environment
"""

import os
import socket
import webbrowser
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading

class AdminerHandler(SimpleHTTPRequestHandler):
    """Custom handler for serving Adminer and project files"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="/Applications/python/voucher-ro_v1.0", **kwargs)
    
    def do_GET(self):
        """Handle GET requests with special routing for Adminer"""
        if self.path == '/' or self.path == '/admin':
            # Redirect to Adminer
            self.send_response(302)
            self.send_header('Location', '/adminer.php')
            self.end_headers()
            return
        
        if self.path == '/adminer.php':
            # Serve Adminer
            self.serve_adminer()
            return
            
        # Default file serving
        super().do_GET()
    
    def serve_adminer(self):
        """Serve the Adminer PHP file"""
        try:
            with open('/Applications/python/voucher-ro_v1.0/adminer.php', 'rb') as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/x-httpd-php')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            
        except FileNotFoundError:
            self.send_error(404, "Adminer not found")

def find_free_port(start_port=8080):
    """Find a free port starting from start_port"""
    for port in range(start_port, start_port + 100):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    return None

def start_adminer_server():
    """Start Adminer server for local development"""
    print("=== Starting Adminer for Local Development ===")
    
    # Check if Adminer exists
    adminer_path = "/Applications/python/voucher-ro_v1.0/adminer.php"
    if not os.path.exists(adminer_path):
        print("❌ Adminer not found. Please download it first.")
        return False
    
    # Find free port
    port = find_free_port(8080)
    if not port:
        print("❌ No free ports available")
        return False
    
    print(f"🚀 Starting Adminer server on port {port}")
    
    # Create server
    server = HTTPServer(('localhost', port), AdminerHandler)
    
    # Start server in background thread
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    
    # Open in browser
    adminer_url = f"http://localhost:{port}/adminer.php"
    print(f"📊 Adminer URL: {adminer_url}")
    
    # Wait a moment then open browser
    time.sleep(1)
    try:
        webbrowser.open(adminer_url)
        print("🌐 Opening Adminer in browser...")
    except Exception as e:
        print(f"⚠️ Could not open browser: {e}")
    
    print(f"""
✅ Adminer Setup Complete!

📊 Database Management: {adminer_url}
🔧 Local Development Server: http://localhost:{port}

💾 Database Connection Settings:
   Server: localhost
   Username: root (or your MySQL user)
   Password: (your MySQL password)
   Database: (select your database)

🔄 Press Ctrl+C to stop the server
""")
    
    try:
        # Keep server running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping Adminer server...")
        server.shutdown()
        return True

if __name__ == "__main__":
    start_adminer_server()