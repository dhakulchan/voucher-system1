#!/usr/bin/env python3
"""
Create token with same secret key as production
"""
import os
import hmac
import hashlib
import base64
import time
from datetime import datetime, timedelta

# Use same config as app
basedir = os.path.abspath(os.path.dirname(__file__))
import sys
sys.path.insert(0, basedir)

from config import Config

def create_token_with_correct_key():
    """Create token using actual secret key from config"""
    # Get the actual secret key from config
    config = Config()
    secret_key = config.SECRET_KEY
    
    print(f"🔑 Using secret key: '{secret_key}' (length: {len(secret_key)})")
    
    # Create token for booking 3
    booking_id = 3
    created_at = int(time.time())
    expires_at = created_at + (30 * 24 * 3600)  # 30 days
    
    # Create the base data
    base_data = f"{booking_id}:{created_at}:{expires_at}"
    print(f"📦 Base data: '{base_data}'")
    
    # Create the signature
    signature = hmac.new(
        secret_key.encode('utf-8'),
        base_data.encode('utf-8'),
        hashlib.sha256
    ).digest()
    
    print(f"🖊️ Signature bytes length: {len(signature)}")
    print(f"🖊️ Signature (first 10 hex): {signature[:10].hex()}")
    
    # Encode everything
    token_data = base_data.encode('utf-8') + signature
    token = base64.b64encode(token_data).decode('utf-8')
    
    print(f"\n✅ Generated token: {token}")
    print(f"🔗 URL: http://localhost:5001/public/booking/{token}")
    
    # Also test manual verification
    print("\n🧪 Manual verification test:")
    try:
        # Decode the token
        decoded_data = base64.b64decode(token.encode('utf-8'))
        
        # Extract components
        colon_positions = []
        for i, byte in enumerate(decoded_data):
            if byte == ord(':'):
                colon_positions.append(i)
        
        if len(colon_positions) >= 2:
            second_colon = colon_positions[1]
            base_part = decoded_data[:second_colon + 11]  # Include timestamp
            signature_part = decoded_data[len(base_part):]
            
            print(f"   Base part: {base_part.decode('utf-8')}")
            print(f"   Signature length: {len(signature_part)}")
            
            # Verify signature
            expected_signature = hmac.new(
                secret_key.encode('utf-8'),
                base_part,
                hashlib.sha256
            ).digest()
            
            print(f"   Expected sig (first 10 hex): {expected_signature[:10].hex()}")
            print(f"   Actual sig (first 10 hex): {signature_part[:10].hex()}")
            print(f"   Signatures match: {hmac.compare_digest(expected_signature, signature_part)}")
    except Exception as e:
        print(f"   Verification error: {e}")
    
    return token

if __name__ == "__main__":
    token = create_token_with_correct_key()
