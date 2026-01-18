"""
Two-Factor Authentication Routes
Handles 2FA setup, verification, and management
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user
from models.user import User
from extensions import db
import qrcode
import io
import base64

two_factor_bp = Blueprint('two_factor', __name__, url_prefix='/auth/2fa')

@two_factor_bp.route('/setup')
def setup():
    """Setup 2FA for current user or pending login user"""
    # Check if this is from a pending login (admin enabled 2FA but user hasn't setup)
    user = None
    is_pending_login = False
    
    if 'pending_2fa_user_id' in session:
        user = User.query.get(session['pending_2fa_user_id'])
        is_pending_login = True
    elif current_user.is_authenticated:
        user = current_user
    else:
        flash('Please login first', 'error')
        return redirect(url_for('auth.login'))
    
    # If already setup and not pending login, redirect
    if user.totp_secret and user.is_2fa_enabled and not is_pending_login:
        flash('2FA is already enabled for your account', 'info')
        return redirect(url_for('auth.profile'))
    
    # Generate TOTP secret
    if not user.totp_secret:
        user.generate_totp_secret()
        db.session.commit()
    
    # Generate QR code
    totp_uri = user.get_totp_uri()
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(totp_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    return render_template('auth/2fa_setup.html', 
                         qr_code=qr_code_base64,
                         secret=user.totp_secret,
                         is_pending_login=is_pending_login)

@two_factor_bp.route('/verify-setup', methods=['POST'])
def verify_setup():
    """Verify 2FA setup with a token"""
    token = request.form.get('token', '').strip()
    
    if not token:
        flash('Please enter the verification code', 'error')
        return redirect(url_for('two_factor.setup'))
    
    # Get user (either authenticated or pending login)
    user = None
    is_pending_login = False
    
    if 'pending_2fa_user_id' in session:
        user = User.query.get(session['pending_2fa_user_id'])
        is_pending_login = True
    elif current_user.is_authenticated:
        user = current_user
    else:
        flash('Session expired. Please login again.', 'error')
        return redirect(url_for('auth.login'))
    
    # Verify the token
    if user.verify_totp(token):
        # Generate backup codes
        backup_codes = user.generate_backup_codes()
        
        # Enable 2FA
        user.is_2fa_enabled = True
        db.session.commit()
        
        # If this was from pending login, complete the login now
        if is_pending_login:
            from flask_login import login_user
            login_user(user, remember=session.get('pending_2fa_remember', False))
            
            # Set session variables
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_role'] = user.role
            
            next_page = session.pop('pending_2fa_next', None)
            session.pop('pending_2fa_user_id', None)
            session.pop('pending_2fa_remember', None)
            
            flash('2FA has been successfully enabled!', 'success')
            return render_template('auth/2fa_backup_codes.html', 
                                 backup_codes=backup_codes,
                                 is_pending_login=True,
                                 next_page=next_page)
        else:
            flash('2FA has been successfully enabled!', 'success')
            return render_template('auth/2fa_backup_codes.html', 
                                 backup_codes=backup_codes,
                                 is_pending_login=False)
    else:
        flash('Invalid verification code. Please try again.', 'error')
        return redirect(url_for('two_factor.setup'))

@two_factor_bp.route('/verify', methods=['GET', 'POST'])
def verify():
    """Verify 2FA token during login"""
    # Check if user is in 2FA verification stage
    if 'pending_2fa_user_id' not in session:
        flash('Invalid access', 'error')
        return redirect(url_for('auth.login'))
    
    # Get user and check if they have setup 2FA
    user = User.query.get(session['pending_2fa_user_id'])
    if not user or not user.totp_secret:
        # User hasn't setup 2FA yet, redirect to setup
        flash('Please complete 2FA setup first', 'info')
        return redirect(url_for('two_factor.setup'))
    
    if request.method == 'POST':
        token = request.form.get('token', '').strip()
        use_backup = request.form.get('use_backup') == 'true'
        
        if not token:
            flash('Please enter the verification code', 'error')
            return render_template('auth/2fa_verify.html')
        
        # Get the user
        user = User.query.get(session['pending_2fa_user_id'])
        if not user:
            flash('Invalid session', 'error')
            return redirect(url_for('auth.login'))
        
        # Verify token or backup code
        verified = False
        if use_backup:
            verified = user.verify_backup_code(token)
            if verified:
                flash(f'Backup code used. You have {user.get_remaining_backup_codes()} codes remaining.', 'warning')
        else:
            verified = user.verify_totp(token)
        
        if verified:
            # Complete login
            from flask_login import login_user
            login_user(user, remember=session.get('pending_2fa_remember', False))
            
            # Set session variables
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_role'] = user.role
            
            # Clear pending 2FA session
            session.pop('pending_2fa_user_id', None)
            session.pop('pending_2fa_remember', None)
            
            next_page = session.pop('pending_2fa_next', None)
            flash('Login successful!', 'success')
            return redirect(next_page or url_for('dashboard.index'))
        else:
            flash('Invalid verification code. Please try again.', 'error')
    
    return render_template('auth/2fa_verify.html')

@two_factor_bp.route('/disable', methods=['POST'])
@login_required
def disable():
    """Disable 2FA for current user"""
    password = request.form.get('password')
    
    if not password or not current_user.check_password(password):
        flash('Invalid password', 'error')
        return redirect(url_for('auth.profile'))
    
    current_user.disable_2fa()
    db.session.commit()
    
    flash('2FA has been disabled', 'success')
    return redirect(url_for('auth.profile'))

@two_factor_bp.route('/regenerate-backup-codes', methods=['POST'])
@login_required
def regenerate_backup_codes():
    """Regenerate backup codes"""
    if not current_user.is_2fa_enabled:
        flash('2FA is not enabled', 'error')
        return redirect(url_for('auth.profile'))
    
    password = request.form.get('password')
    if not password or not current_user.check_password(password):
        flash('Invalid password', 'error')
        return redirect(url_for('auth.profile'))
    
    backup_codes = current_user.generate_backup_codes()
    db.session.commit()
    
    return render_template('auth/2fa_backup_codes.html', 
                         backup_codes=backup_codes,
                         regenerated=True)
