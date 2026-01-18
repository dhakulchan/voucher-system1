#!/usr/bin/env python3
"""
Force clear all user sessions to reload roles
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from flask import session
import redis

def clear_sessions():
    """Clear all sessions to force role reload"""
    app = create_app()
    
    print("\n" + "="*80)
    print("SESSION CACHE CLEARING")
    print("="*80)
    
    # Check if using Redis for sessions
    try:
        if hasattr(app, 'session_interface'):
            print(f"\nSession interface: {type(app.session_interface).__name__}")
        
        # Try to clear Redis cache if configured
        if 'SESSION_REDIS' in app.config:
            print("\n✅ Redis session storage detected")
            try:
                r = redis.from_url(app.config['SESSION_REDIS'])
                keys = r.keys('session:*')
                if keys:
                    r.delete(*keys)
                    print(f"✅ Cleared {len(keys)} session(s) from Redis")
                else:
                    print("✅ No active sessions found in Redis")
            except Exception as e:
                print(f"⚠️  Could not clear Redis sessions: {e}")
        else:
            print("\n⚠️  Not using Redis sessions (filesystem sessions)")
            print("   Users must log out and log in again to reload roles")
    
    except Exception as e:
        print(f"\n⚠️  Session check error: {e}")
    
    print("\n" + "="*80)
    print("RECOMMENDATIONS:")
    print("="*80)
    print("1. Ask all users to LOG OUT and LOG IN again")
    print("2. Or RESTART the application server (Gunicorn/Flask)")
    print("3. Clear browser cache (Ctrl+Shift+R or Cmd+Shift+R)")
    print("="*80)
    print()

if __name__ == '__main__':
    clear_sessions()
