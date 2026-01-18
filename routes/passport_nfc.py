"""
Passport NFC API Routes
Handles QR Code + Mobile NFC passport reading workflow
"""
from flask import Blueprint, request, jsonify
import secrets
import time
from datetime import datetime, timedelta

passport_nfc_bp = Blueprint('passport_nfc', __name__)

# In-memory session storage (use Redis in production)
nfc_sessions = {}

# Session expiry time (5 minutes)
SESSION_EXPIRY_SECONDS = 300


def cleanup_expired_sessions():
    """Remove expired sessions"""
    now = datetime.now()
    expired = [token for token, data in nfc_sessions.items() 
               if data['expires_at'] < now]
    for token in expired:
        del nfc_sessions[token]


@passport_nfc_bp.route('/api/passport/nfc/session', methods=['POST'])
def create_nfc_session():
    """
    Create a new NFC scanning session and return QR code token
    
    Returns:
        {
            "session_token": "abc123...",
            "expires_in": 300,
            "qr_url": "https://domain.com/mobile/nfc-scan?token=abc123"
        }
    """
    try:
        # Clean up old sessions
        cleanup_expired_sessions()
        
        # Generate secure token
        token = secrets.token_urlsafe(32)
        
        # Calculate expiry
        expires_at = datetime.now() + timedelta(seconds=SESSION_EXPIRY_SECONDS)
        
        # Store session
        nfc_sessions[token] = {
            'status': 'waiting',  # waiting, scanning, completed, expired, error
            'data': None,
            'created_at': datetime.now(),
            'expires_at': expires_at,
            'last_check': datetime.now()
        }
        
        return jsonify({
            'success': True,
            'session_token': token,
            'expires_in': SESSION_EXPIRY_SECONDS,
            'qr_url': f'/mobile/nfc-scan?token={token}'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@passport_nfc_bp.route('/api/passport/nfc/check/<token>', methods=['GET'])
def check_nfc_status(token):
    """
    Check the status of an NFC scanning session (polling endpoint)
    
    Args:
        token: Session token from QR code
        
    Returns:
        {
            "status": "waiting|scanning|completed|expired|error",
            "data": {...} (only if completed),
            "message": "..." (if error)
        }
    """
    try:
        cleanup_expired_sessions()
        
        if token not in nfc_sessions:
            return jsonify({
                'status': 'expired',
                'message': 'Session not found or expired'
            })
        
        session = nfc_sessions[token]
        
        # Check if expired
        if session['expires_at'] < datetime.now():
            session['status'] = 'expired'
            return jsonify({
                'status': 'expired',
                'message': 'Session has expired'
            })
        
        # Update last check time
        session['last_check'] = datetime.now()
        
        # Return current status
        response = {
            'status': session['status']
        }
        
        if session['status'] == 'completed' and session['data']:
            response['data'] = session['data']
            # Clean up completed session after retrieval
            del nfc_sessions[token]
        elif session['status'] == 'error':
            response['message'] = session.get('error_message', 'Unknown error')
            
        return jsonify(response)
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@passport_nfc_bp.route('/api/passport/nfc/scanning/<token>', methods=['POST'])
def update_scanning_status(token):
    """
    Mobile app calls this when user starts NFC scan
    
    Args:
        token: Session token
        
    Returns:
        {"success": true}
    """
    try:
        if token not in nfc_sessions:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        session = nfc_sessions[token]
        
        if session['expires_at'] < datetime.now():
            return jsonify({
                'success': False,
                'error': 'Session expired'
            }), 410
        
        # Update status to scanning
        session['status'] = 'scanning'
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@passport_nfc_bp.route('/api/passport/nfc/submit', methods=['POST'])
def submit_nfc_data():
    """
    Mobile app submits extracted NFC passport data
    
    Expected JSON body:
    {
        "token": "session_token",
        "data": {
            "full_name": "SURNAME, GIVEN NAMES",
            "passport_number": "AA1234567",
            "nationality": "THA",
            "date_of_birth": "1990-01-15",
            "expiry_date": "2030-12-31",
            "sex": "M",
            "issuing_country": "THA",
            "personal_number": "...",
            "mrz_line1": "...",
            "mrz_line2": "...",
            "photo_base64": "data:image/jpeg;base64,..."  (optional)
        }
    }
    
    Returns:
        {"success": true}
    """
    try:
        json_data = request.get_json()
        
        if not json_data or 'token' not in json_data:
            return jsonify({
                'success': False,
                'error': 'Missing token'
            }), 400
        
        token = json_data['token']
        
        if token not in nfc_sessions:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        session = nfc_sessions[token]
        
        if session['expires_at'] < datetime.now():
            return jsonify({
                'success': False,
                'error': 'Session expired'
            }), 410
        
        # Validate data
        if 'data' not in json_data:
            session['status'] = 'error'
            session['error_message'] = 'No passport data provided'
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        passport_data = json_data['data']
        
        # Required fields validation
        required_fields = ['full_name', 'passport_number', 'nationality', 
                          'date_of_birth', 'expiry_date', 'sex']
        
        missing_fields = [f for f in required_fields if not passport_data.get(f)]
        
        if missing_fields:
            session['status'] = 'error'
            session['error_message'] = f'Missing fields: {", ".join(missing_fields)}'
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # Store the data
        session['status'] = 'completed'
        session['data'] = passport_data
        
        return jsonify({
            'success': True,
            'message': 'Passport data received successfully'
        })
        
    except Exception as e:
        # Update session with error if token is available
        try:
            if 'token' in json_data and json_data['token'] in nfc_sessions:
                nfc_sessions[json_data['token']]['status'] = 'error'
                nfc_sessions[json_data['token']]['error_message'] = str(e)
        except:
            pass
            
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@passport_nfc_bp.route('/mobile/nfc-scan', methods=['GET'])
def mobile_nfc_scan_page():
    """
    Landing page for mobile app (opened when QR code is scanned)
    This should redirect to deep link or show app download options
    
    Query params:
        token: Session token
    """
    token = request.args.get('token')
    
    if not token:
        return jsonify({'error': 'Missing token'}), 400
    
    # Check if session exists
    if token not in nfc_sessions:
        return """
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Session Expired</title>
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 20px; text-align: center;">
            <h2>⏱️ Session Expired</h2>
            <p>This QR code has expired. Please generate a new one.</p>
        </body>
        </html>
        """, 410
    
    # Try to open deep link, fallback to app store
    return f"""
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta charset="UTF-8">
        <title>Open Passport Scanner</title>
        <script>
            // Try to open app deep link
            const deepLink = 'passportscanner://scan?token={token}';
            const appStoreUrl = 'https://apps.apple.com/app/passport-scanner/id000000000'; // TODO: Update
            const playStoreUrl = 'https://play.google.com/store/apps/details?id=com.example.passportscanner'; // TODO: Update
            
            let appOpened = false;
            
            // Try deep link
            window.location.href = deepLink;
            
            // Fallback to app store after 2 seconds
            setTimeout(function() {{
                if (!appOpened) {{
                    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
                    const isAndroid = /Android/.test(navigator.userAgent);
                    
                    if (isIOS) {{
                        document.getElementById('appLink').href = appStoreUrl;
                        document.getElementById('storeName').textContent = 'App Store';
                    }} else if (isAndroid) {{
                        document.getElementById('appLink').href = playStoreUrl;
                        document.getElementById('storeName').textContent = 'Google Play';
                    }}
                    
                    document.getElementById('fallback').style.display = 'block';
                }}
            }}, 2000);
            
            // Detect if app opened
            document.addEventListener('visibilitychange', function() {{
                if (document.hidden) {{
                    appOpened = true;
                }}
            }});
        </script>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                padding: 20px;
                text-align: center;
                max-width: 500px;
                margin: 0 auto;
            }}
            .spinner {{
                border: 4px solid #f3f3f3;
                border-top: 4px solid #4f46e5;
                border-radius: 50%;
                width: 50px;
                height: 50px;
                animation: spin 1s linear infinite;
                margin: 20px auto;
            }}
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
            #fallback {{
                display: none;
                margin-top: 30px;
            }}
            .btn {{
                display: inline-block;
                padding: 12px 24px;
                background: #4f46e5;
                color: white;
                text-decoration: none;
                border-radius: 8px;
                font-weight: 500;
                margin-top: 15px;
            }}
        </style>
    </head>
    <body>
        <h2>📱 Opening Passport Scanner...</h2>
        <div class="spinner"></div>
        <p>กำลังเปิดแอปพลิเคชัน...</p>
        
        <div id="fallback">
            <p>⚠️ ไม่พบแอปพลิเคชัน</p>
            <p>กรุณาดาวน์โหลดแอป Passport Scanner ก่อนใช้งาน</p>
            <a id="appLink" href="#" class="btn">
                ดาวน์โหลดจาก <span id="storeName">App Store</span>
            </a>
            <p style="margin-top: 20px; font-size: 12px; color: #666;">
                Session Token: {token[:8]}...
            </p>
        </div>
    </body>
    </html>
    """
