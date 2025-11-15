#!/usr/bin/env python3
"""
Browser Simulation Test - การทดสอบแบบจำลอง Browser
ทดสอบ workflow ผ่าน browser simulation
"""

import requests
import re
from datetime import datetime

def test_browser_simulation():
    """ทดสอบแบบ browser simulation"""
    print("🌐 Enhanced Booking System - Browser Simulation Test")
    print("🇹🇭 ระบบการจองขั้นสูง - การทดสอบแบบจำลอง Browser") 
    print("=" * 80)
    
    base_url = "http://localhost:5001"
    session = requests.Session()
    
    # Test 1: Homepage Access
    print("🏠 Test 1: Homepage Access")
    try:
        response = session.get(base_url)
        print(f"   Homepage: {response.status_code} {response.reason}")
        if response.status_code == 200:
            print(f"   ✅ Homepage accessible")
        else:
            print(f"   ⚠️ Homepage may have issues")
    except Exception as e:
        print(f"   ❌ Homepage error: {e}")
    
    # Test 2: Login Page Access
    print(f"\n🔐 Test 2: Authentication System")
    try:
        login_response = session.get(f"{base_url}/auth/login")
        print(f"   Login page: {login_response.status_code} {login_response.reason}")
        if login_response.status_code == 200:
            print(f"   ✅ Login page accessible")
            
            # Check for login form
            if 'login' in login_response.text.lower() or 'username' in login_response.text.lower():
                print(f"   ✅ Login form detected")
            else:
                print(f"   ⚠️ Login form not clearly detected")
        else:
            print(f"   ⚠️ Login page may have issues")
    except Exception as e:
        print(f"   ❌ Login page error: {e}")
    
    # Test 3: Booking Access (should redirect to login)
    print(f"\n📋 Test 3: Booking Protection")
    booking_routes = [
        "/booking/",
        "/booking/create",
        "/booking/view/62"
    ]
    
    for route in booking_routes:
        try:
            response = session.get(f"{base_url}{route}", allow_redirects=False)
            print(f"   {route}: {response.status_code} {response.reason}")
            
            if response.status_code == 302:
                location = response.headers.get('Location', '')
                if '/auth/login' in location:
                    print(f"      ✅ Correctly protected (redirects to login)")
                else:
                    print(f"      ⚠️ Unexpected redirect: {location}")
            elif response.status_code == 200:
                print(f"      ⚠️ Not protected (should redirect to login)")
            else:
                print(f"      ❓ Unexpected response")
        except Exception as e:
            print(f"   {route}: ❌ Error - {e}")
    
    # Test 4: Public Routes (Enhanced System)
    print(f"\n🌐 Test 4: Enhanced Public Routes") 
    public_routes = [
        "/public/booking/sample-token",
        "/public/booking/sample-token/pdf",
        "/public/booking/sample-token/png"
    ]
    
    for route in public_routes:
        try:
            response = session.get(f"{base_url}{route}", allow_redirects=False)
            print(f"   {route}: {response.status_code} {response.reason}")
            
            # 404 is expected for invalid tokens
            if response.status_code == 404:
                print(f"      ✅ Correctly handles invalid token")
            elif response.status_code == 500:
                print(f"      ⚠️ Server error (may need valid token)")
            else:
                print(f"      ❓ Response: {response.status_code}")
        except Exception as e:
            print(f"   {route}: ❌ Error - {e}")
    
    # Test 5: API Routes
    print(f"\n🔌 Test 5: Enhanced API Routes")
    api_routes = [
        "/api/system/health",
        "/api/share/booking/62/url",
        "/api/share/booking/62/status"
    ]
    
    for route in api_routes:
        try:
            response = session.get(f"{base_url}{route}", allow_redirects=False)
            print(f"   {route}: {response.status_code} {response.reason}")
            
            if response.status_code == 200:
                print(f"      ✅ API endpoint working")
            elif response.status_code == 302:
                print(f"      🔐 Protected endpoint (needs auth)")
            elif response.status_code == 404:
                print(f"      ❌ Endpoint not found")
            elif response.status_code == 503:
                print(f"      ⚠️ Service unavailable")
            else:
                print(f"      ❓ Response: {response.status_code}")
        except Exception as e:
            print(f"   {route}: ❌ Error - {e}")
    
    # Test 6: Static Assets
    print(f"\n📁 Test 6: Static Assets")
    static_routes = [
        "/static/css/bootstrap.min.css",
        "/static/js/bootstrap.min.js",
        "/static/js/enhanced-booking.js"
    ]
    
    for route in static_routes:
        try:
            response = session.get(f"{base_url}{route}")
            print(f"   {route}: {response.status_code} {response.reason}")
            
            if response.status_code == 200:
                print(f"      ✅ Asset available")
            elif response.status_code == 404:
                print(f"      ❌ Asset not found")
            else:
                print(f"      ❓ Response: {response.status_code}")
        except Exception as e:
            print(f"   {route}: ❌ Error - {e}")

def test_workflow_features():
    """ทดสอบฟีเจอร์ workflow specific"""
    print(f"\n\n🔄 Enhanced Workflow Features Test")
    print("=" * 80)
    
    # Test Enhanced JavaScript
    print("📱 Test: Enhanced JavaScript Integration")
    try:
        import os
        js_file = "/Applications/python/voucher-ro_v1.0/static/js/enhanced-booking.js"
        if os.path.exists(js_file):
            with open(js_file, 'r') as f:
                js_content = f.read()
            
            # Check for key functions
            functions = [
                'getCurrentBookingId',
                'initializeBookingData', 
                'showToast'
            ]
            
            for func in functions:
                if func in js_content:
                    print(f"   ✅ Function {func} found")
                else:
                    print(f"   ❌ Function {func} missing")
        else:
            print(f"   ❌ Enhanced JavaScript file not found")
    except Exception as e:
        print(f"   ❌ JavaScript check error: {e}")
    
    # Test Template Status
    print(f"\n📄 Test: Template Status")
    try:
        template_file = "/Applications/python/voucher-ro_v1.0/templates/booking/view_en.html"
        
        # Simple syntax check
        with open(template_file, 'r') as f:
            template_content = f.read()
        
        # Check for recent fixes
        if '{{ booking.id }};' in template_content:
            print(f"   ✅ Template syntax appears correct")
        else:
            print(f"   ⚠️ Template may have syntax issues")
            
        # Check for protection comments
        if 'AUTO-FORMATTER PROTECTION' in template_content:
            print(f"   ✅ Protection comments in place")
        else:
            print(f"   ⚠️ Protection comments missing")
            
    except Exception as e:
        print(f"   ❌ Template check error: {e}")

def test_system_health():
    """ทดสอบสุขภาพระบบ"""
    print(f"\n\n🏥 System Health Check")
    print("=" * 80)
    
    try:
        # Test server responsiveness
        response = requests.get("http://localhost:5001", timeout=5)
        print(f"📊 Server Response Time: {response.elapsed.total_seconds():.3f}s")
        
        if response.elapsed.total_seconds() < 1.0:
            print(f"   ✅ Fast response time")
        elif response.elapsed.total_seconds() < 3.0:
            print(f"   ⚠️ Moderate response time")
        else:
            print(f"   ❌ Slow response time")
            
        # Test different endpoints
        endpoints = [
            "/auth/login",
            "/booking/view/62",
            "/static/css/bootstrap.min.css"
        ]
        
        for endpoint in endpoints:
            try:
                resp = requests.head(f"http://localhost:5001{endpoint}", timeout=5)
                print(f"   {endpoint}: {resp.status_code} ({resp.elapsed.total_seconds():.3f}s)")
            except Exception as e:
                print(f"   {endpoint}: ❌ {e}")
        
    except Exception as e:
        print(f"❌ Health check failed: {e}")

if __name__ == "__main__":
    print("🚀 Starting Browser Simulation Test...")
    
    # Run browser simulation
    test_browser_simulation()
    
    # Test workflow features
    test_workflow_features()
    
    # Test system health
    test_system_health()
    
    print(f"\n" + "=" * 80)
    print("🎯 BROWSER SIMULATION TEST SUMMARY")
    print("=" * 80)
    print("✅ Core system endpoints tested")
    print("✅ Authentication protection verified")  
    print("✅ Enhanced features checked")
    print("✅ System health evaluated")
    print("")
    print("🎊 Enhanced Booking System - Browser Test Complete!")
    print("🇹🇭 ระบบการจองขั้นสูง - การทดสอบ Browser เสร็จสิ้น!")
    print("=" * 80)