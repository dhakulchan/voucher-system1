#!/usr/bin/env python3
"""
CLI Script for Booking Auto Completion
Usage: python auto_complete_bookings.py [--preview] [--days N]
"""

import sys
import os
import argparse
import json
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import ultra-aggressive datetime fix FIRST
import ultra_aggressive_datetime_fix
ultra_aggressive_datetime_fix.ultra_aggressive_patch()
ultra_aggressive_datetime_fix.apply_engine_level_patch()

from flask import Flask
from config import Config
from extensions import db
from services.booking_auto_completion import BookingAutoCompletionService

def create_app():
    """Create Flask app for CLI usage"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize extensions
    db.init_app(app)
    
    return app

def run_auto_completion():
    """Run the auto completion process"""
    app = create_app()
    
    with app.app_context():
        print(f"🕐 Starting auto-completion process at {datetime.now()}")
        print("=" * 60)
        
        results = BookingAutoCompletionService.process_auto_completion()
        
        print(f"📊 Processing Summary:")
        print(f"   Total processed: {results['total_processed']}")
        print(f"   ✅ Successful: {results['successful']}")
        print(f"   ❌ Failed: {results['failed']}")
        print()
        
        if results['results']:
            print("📋 Detailed Results:")
            for result in results['results']:
                status_icon = "✅" if result['success'] else "❌"
                print(f"   {status_icon} {result['booking_reference']} (ID: {result['booking_id']})")
                print(f"      Departure: {result['departure_date']}")
                print(f"      Status: {result['old_status']} -> completed")
                print(f"      Message: {result['message']}")
                print()
        
        print("=" * 60)
        print(f"🏁 Auto-completion completed at {datetime.now()}")
        
        return results

def preview_upcoming_completions(days=7):
    """Preview upcoming completions"""
    app = create_app()
    
    with app.app_context():
        print(f"🔍 Preview: Bookings eligible for completion in next {days} days")
        print("=" * 60)
        
        candidates = BookingAutoCompletionService.get_completion_candidates(days)
        
        if not candidates:
            print("📭 No bookings eligible for completion in the specified period")
        else:
            for candidate in candidates:
                print(f"📅 Completion Date: {candidate['completion_date']}")
                print(f"   ✈️  Departure Date: {candidate['departure_date']}")
                print(f"   📚 Bookings ({len(candidate['bookings'])}):")
                
                for booking in candidate['bookings']:
                    print(f"      • {booking['reference']} (ID: {booking['id']}) - Status: {booking['status']}")
                print()
        
        print("=" * 60)
        
        return candidates

def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(description='Booking Auto Completion CLI')
    parser.add_argument('--preview', action='store_true', 
                       help='Preview upcoming completions instead of processing')
    parser.add_argument('--days', type=int, default=7,
                       help='Number of days to look ahead for preview (default: 7)')
    parser.add_argument('--json', action='store_true',
                       help='Output results in JSON format')
    
    args = parser.parse_args()
    
    try:
        if args.preview:
            results = preview_upcoming_completions(args.days)
        else:
            results = run_auto_completion()
        
        if args.json:
            print(json.dumps(results, indent=2, default=str))
        
        # Exit with appropriate code
        if not args.preview and results.get('failed', 0) > 0:
            sys.exit(1)  # Some failures occurred
        else:
            sys.exit(0)  # Success
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        if args.json:
            print(json.dumps({"error": str(e)}))
        sys.exit(1)

if __name__ == '__main__':
    main()