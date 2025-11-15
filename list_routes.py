#!/usr/bin/env python3
"""
Test script to check available routes
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app

def list_routes():
    """List all available routes"""
    with app.app_context():
        print("📋 Available routes:")
        for rule in app.url_map.iter_rules():
            methods = ','.join(rule.methods - {'HEAD', 'OPTIONS'})
            print(f"{methods:10} {rule.rule}")

if __name__ == "__main__":
    list_routes()