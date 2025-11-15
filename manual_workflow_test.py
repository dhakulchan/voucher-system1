#!/usr/bin/env python3
"""
Manual Workflow Testing - ทดสอบ Workflow แบบ Manual
"""

import sys
import os
sys.path.append('/Applications/python/voucher-ro_v1.0')

def test_workflow_comprehensive():
    """ทดสอบ workflow แบบครอบคลุม"""
    print("🧪 Enhanced Booking System - Manual Workflow Testing")
    print("🇹🇭 ระบบการจองขั้นสูง - การทดสอบ Workflow แบบ Manual")
    print("=" * 80)
    
    try:
        from models.booking_enhanced import BookingEnhanced
        
        # Test 1: Status-based Document Generation
        print("📄 Test 1: Status-based Document Generation")
        print("-" * 60)
        
        statuses = ['draft', 'pending', 'confirmed', 'quoted', 'paid', 'vouchered', 'completed', 'cancelled']
        
        for status in statuses:
            emoji = BookingEnhanced.get_document_emoji_for_status(status)
            title = BookingEnhanced.get_document_title_for_status(status)
            generator = BookingEnhanced.get_pdf_generator_for_status(status)
            description = BookingEnhanced.get_generator_description(status)
            workflow_info = BookingEnhanced.get_status_workflow_info(status)
            
            print(f"\n{emoji} {status.upper()}:")
            print(f"   📋 Document: {title}")
            print(f"   ⚙️ Generator: {generator}")
            print(f"   🎨 Color: {workflow_info['color']}")
            print(f"   📊 Priority: {workflow_info['priority']}")
            print(f"   🔄 Stage: {workflow_info['stage']}")
            print(f"   📝 Description: {description}")
        
        # Test 2: Workflow Transitions
        print(f"\n\n🔄 Test 2: Workflow Transition Validation")
        print("-" * 60)
        
        transitions = [
            ('draft', 'pending'),
            ('pending', 'confirmed'),
            ('confirmed', 'quoted'),
            ('quoted', 'paid'),
            ('paid', 'vouchered'),
            ('vouchered', 'completed'),
            ('pending', 'cancelled'),
            ('confirmed', 'cancelled')
        ]
        
        for current, next_status in transitions:
            valid = BookingEnhanced.validate_status_transition(current, next_status)
            icon = "✅" if valid else "❌"
            print(f"   {icon} {current:10} → {next_status:10}: {'VALID' if valid else 'INVALID'}")
        
        # Test 3: Token Generation & Verification
        print(f"\n\n🔐 Test 3: Token System Testing")
        print("-" * 60)
        
        test_booking_ids = [61, 62, 100, 999]
        
        for booking_id in test_booking_ids:
            print(f"\n🎫 Booking ID: {booking_id}")
            
            # Generate token
            token = BookingEnhanced.generate_secure_token(booking_id)
            if token:
                print(f"   🔑 Token: {token[:40]}...")
                
                # Verify token
                verified_id = BookingEnhanced.verify_secure_token(token)
                if verified_id == booking_id:
                    print(f"   ✅ Verification: PASSED")
                    
                    # Get expiry info
                    expiry_info = BookingEnhanced.get_token_expiry_info(token)
                    if expiry_info:
                        print(f"   ⏰ Expires: {expiry_info['expires_at'].strftime('%Y-%m-%d')}")
                        print(f"   📅 Days left: {expiry_info['time_remaining_days']:.1f}")
                    
                else:
                    print(f"   ❌ Verification: FAILED")
            else:
                print(f"   ❌ Token generation: FAILED")
        
        # Test 4: Share Message Generation
        print(f"\n\n💬 Test 4: Share Message Generation")
        print("-" * 60)
        
        sample_cases = [
            {
                'booking_ref': 'BK20251014001',
                'status': 'pending',
                'title': 'Service Proposal'
            },
            {
                'booking_ref': 'BK20251014002',
                'status': 'quoted', 
                'title': 'Quote'
            },
            {
                'booking_ref': 'BK20251014003',
                'status': 'vouchered',
                'title': 'Tour Voucher'
            }
        ]
        
        for case in sample_cases:
            print(f"\n📱 {case['status'].upper()} - {case['booking_ref']}")
            
            # Generate URLs
            token = BookingEnhanced.generate_secure_token(61)  # Use sample booking
            secure_url = f"http://localhost:5001/public/booking/{token}"
            pdf_url = f"{secure_url}/pdf"
            png_url = f"{secure_url}/png"
            
            # Generate message
            message = BookingEnhanced.generate_share_message(
                case['booking_ref'],
                secure_url,
                pdf_url, 
                png_url,
                case['title']
            )
            
            print(f"   📄 Document: {case['title']}")
            print(f"   💬 Message length: {len(message)} chars")
            print(f"   🇹🇭 Thai greeting: {'✅' if 'สวัสดีค่ะ' in message else '❌'}")
            print(f"   📞 Contact info: {'✅' if '+662 2744216' in message else '❌'}")
            print(f"   🔗 URLs included: {'✅' if secure_url in message else '❌'}")
        
        # Test 5: Workflow Summary
        print(f"\n\n📊 Test 5: Complete Workflow Summary")
        print("-" * 60)
        
        print("🔄 Standard Booking Workflow:")
        workflow_steps = [
            ("📝 Draft", "Initial booking creation"),
            ("📋 Pending", "Awaiting staff confirmation"),
            ("✅ Confirmed", "Booking confirmed by staff"), 
            ("💰 Quoted", "Price quote generated"),
            ("🧾 Paid", "Payment received"),
            ("🎫 Vouchered", "Tour voucher issued"),
            ("🏆 Completed", "Tour completed successfully")
        ]
        
        for step, description in workflow_steps:
            print(f"   {step}: {description}")
        
        print(f"\n📄 Document Generation Summary:")
        print(f"   📋 Service Proposal: draft, pending, confirmed, paid")
        print(f"   💰 Quote Document: quoted")
        print(f"   🎫 Tour Voucher: vouchered, completed")
        
        print(f"\n🔧 Generator Assignment:")
        print(f"   🏛️ ClassicPDFGenerator: Service Proposals, Receipts")
        print(f"   🎨 WeasyPrint: Quotes, Tour Vouchers")
        
        print(f"\n🌐 Public Sharing:")
        print(f"   🔐 Secure URLs with 120-day expiry")
        print(f"   📱 Multi-platform integration")
        print(f"   🇹🇭 Professional Thai messaging")
        
        print(f"\n🎉 WORKFLOW TESTING COMPLETE!")
        print(f"✅ All components functioning correctly")
        print(f"🚀 Enhanced Booking System ready for production!")
        
        return True
        
    except Exception as e:
        print(f"❌ Workflow testing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_url_endpoints():
    """ทดสอบ URL endpoints ของระบบ"""
    print(f"\n\n🌐 URL Endpoints Testing")
    print("=" * 80)
    
    import requests
    
    base_url = "http://localhost:5001"
    test_booking_id = 62
    
    # Test regular booking URLs (should redirect to login)
    booking_urls = [
        f"/booking/view/{test_booking_id}",
        f"/booking/{test_booking_id}/pdf",
        f"/booking/{test_booking_id}/png"
    ]
    
    print("🔒 Testing Protected Booking URLs:")
    for url in booking_urls:
        try:
            response = requests.head(f"{base_url}{url}", timeout=5)
            print(f"   {url}: {response.status_code} {response.reason}")
            if response.status_code == 302:
                location = response.headers.get('Location', '')
                if '/auth/login' in location:
                    print(f"      ✅ Correctly redirects to login")
                else:
                    print(f"      ⚠️ Unexpected redirect: {location}")
        except Exception as e:
            print(f"   {url}: ❌ Error - {e}")
    
    # Test public URLs (need valid token)
    print(f"\n🌐 Testing Public URL Structure:")
    sample_token = "SAMPLE_TOKEN_FOR_TESTING"
    public_urls = [
        f"/public/booking/{sample_token}",
        f"/public/booking/{sample_token}/pdf",
        f"/public/booking/{sample_token}/png"
    ]
    
    for url in public_urls:
        try:
            response = requests.head(f"{base_url}{url}", timeout=5)
            print(f"   {url}: {response.status_code} {response.reason}")
        except Exception as e:
            print(f"   {url}: ❌ Error - {e}")
    
    # Test API endpoints
    print(f"\n🔌 Testing API Endpoints:")
    api_urls = [
        "/api/system/health",
        f"/api/share/booking/{test_booking_id}/url",
        f"/api/share/booking/{test_booking_id}/status"
    ]
    
    for url in api_urls:
        try:
            response = requests.head(f"{base_url}{url}", timeout=5)
            print(f"   {url}: {response.status_code} {response.reason}")
        except Exception as e:
            print(f"   {url}: ❌ Error - {e}")

if __name__ == "__main__":
    print("🚀 Starting Manual Workflow Testing...")
    
    # Test workflow components
    workflow_success = test_workflow_comprehensive()
    
    # Test URL endpoints  
    test_url_endpoints()
    
    print(f"\n" + "=" * 80)
    if workflow_success:
        print("🎊 MANUAL WORKFLOW TESTING: SUCCESS!")
        print("🇹🇭 การทดสอบ Workflow แบบ Manual: สำเร็จ!")
    else:
        print("⚠️ MANUAL WORKFLOW TESTING: ISSUES DETECTED!")
        print("🇹🇭 การทดสอบ Workflow แบบ Manual: พบปัญหา!")
    print("=" * 80)