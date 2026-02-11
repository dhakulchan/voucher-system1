from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        from models.user import User
        
        username = request.form.get('username')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            # Check if 2FA is enabled
            if user.is_2fa_enabled:
                # Check if user has completed 2FA setup
                if not user.totp_secret:
                    # First time setup - redirect to setup page
                    session['pending_2fa_user_id'] = user.id
                    session['pending_2fa_remember'] = remember
                    session['pending_2fa_next'] = request.args.get('next')
                    flash('2FA is required for your account. Please complete the setup below.', 'info')
                    return redirect(url_for('two_factor.setup'))
                else:
                    # Already setup - go to verify page
                    session['pending_2fa_user_id'] = user.id
                    session['pending_2fa_remember'] = remember
                    session['pending_2fa_next'] = request.args.get('next')
                    flash('Please enter your 2FA verification code', 'info')
                    return redirect(url_for('two_factor.verify'))
            
            # Normal login without 2FA
            login_user(user, remember=remember)
            
            # Auto-create customer profile for Customer role users
            if user.role == 'Customer' and not user.customer_profile:
                from models.customer import Customer
                from extensions import db
                try:
                    # Create customer profile automatically
                    customer = Customer(
                        name=user.username,
                        email=user.email,
                        phone='',  # Can be updated later by user
                        customer_type='Visitor-Individual',
                        user_id=user.id,
                        created_by=user.id
                    )
                    db.session.add(customer)
                    db.session.commit()
                    flash('Welcome! Your customer profile has been created automatically.', 'info')
                except Exception as e:
                    db.session.rollback()
                    from utils.logging_config import get_logger
                    logger = get_logger(__name__)
                    logger.error(f"Failed to auto-create customer profile for user {user.id}: {e}")
            
            # Set session variables for role-based access control
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_role'] = user.role
            
            next_page = request.args.get('next')
            flash('Login successful!', 'success')
            return redirect(next_page or url_for('dashboard.index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    # Check if user is Customer before logout
    is_customer = current_user.role == 'Customer'
    
    logout_user()
    # Clear session variables
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('user_role', None)
    flash('You have been logged out.', 'info')
    
    # Redirect to appropriate login page
    if is_customer:
        return redirect(url_for('customer_points.customer_login'))
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        from models.user import User
        from extensions import db
        
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        # Auto-assign Customer role for all new registrations
        role = 'Customer'
        
        # Validation
        if not all([username, email, password, confirm_password]):
            flash('All fields are required', 'error')
            return render_template('auth/register.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('auth/register.html')
        
        # Check if user exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('auth/register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return render_template('auth/register.html')
        
        # Create new user with Customer role
        user = User.create_user(username, email, password, is_admin=False, role=role)
        db.session.add(user)
        db.session.commit()
        
        # Auto-create customer profile for new Customer registrations
        try:
            from models.customer import Customer
            customer = Customer(
                name=username,
                email=email,
                phone='',  # Can be updated later
                customer_type='Visitor-Individual',
                user_id=user.id,
                created_by=user.id
            )
            db.session.add(customer)
            db.session.commit()
        except Exception as e:
            # Don't fail registration if customer profile creation fails
            db.session.rollback()
            from utils.logging_config import get_logger
            logger = get_logger(__name__)
            logger.error(f"Failed to auto-create customer profile during registration for user {user.id}: {e}")
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('customer_points.customer_login'))
    
    return render_template('auth/register.html')

@auth_bp.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html', user=current_user)

@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    from models.user import User
    from extensions import db
    
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if not current_user.check_password(current_password):
        flash('Current password is incorrect', 'error')
        return redirect(url_for('auth.profile'))
    
    if new_password != confirm_password:
        flash('New passwords do not match', 'error')
        return redirect(url_for('auth.profile'))
    
    current_user.set_password(new_password)
    db.session.commit()
    
    flash('Password changed successfully!', 'success')
    return redirect(url_for('auth.profile'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Request password reset"""
    if request.method == 'POST':
        from models.user import User
        from extensions import db
        from datetime import datetime, timedelta
        from sqlalchemy import text
        import secrets
        
        email = request.form.get('email', '').strip().lower()
        
        if not email:
            flash('กรุณากรอกอีเมล', 'error')
            return render_template('auth/forgot_password.html')
        
        # Find user by email
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Generate reset token
            token = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(hours=1)  # Token valid for 1 hour
            
            try:
                # Save reset token
                db.session.execute(text("""
                    INSERT INTO password_reset_tokens (user_id, token, expires_at)
                    VALUES (:user_id, :token, :expires_at)
                """), {
                    'user_id': user.id,
                    'token': token,
                    'expires_at': expires_at
                })
                db.session.commit()
                
                # Send email with reset link
                reset_url = url_for('auth.reset_password', token=token, _external=True)
                
                # Send email
                try:
                    from extensions import mail
                    from flask_mail import Message
                    from flask import current_app
                    
                    msg = Message(
                        subject='รีเซ็ตรหัสผ่าน - ระบบจองทัวร์',
                        recipients=[user.email],
                        sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@dhakulchan.com')
                    )
                    
                    # Email body
                    msg.html = f"""
                    <!DOCTYPE html>
                    <html lang="th">
                    <head>
                        <meta charset="UTF-8">
                        <style>
                            body {{ font-family: 'Sarabun', Arial, sans-serif; background-color: #f4f4f4; margin: 0; padding: 0; }}
                            .container {{ max-width: 600px; margin: 40px auto; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }}
                            .header h1 {{ margin: 0; font-size: 24px; }}
                            .content {{ padding: 30px; }}
                            .button {{ display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; margin: 20px 0; font-weight: bold; }}
                            .button:hover {{ opacity: 0.9; }}
                            .footer {{ background: #f8f9fa; padding: 20px; text-align: center; color: #666; font-size: 14px; }}
                            .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; }}
                            .link-box {{ background: #f8f9fa; padding: 15px; border-radius: 5px; word-break: break-all; margin: 15px 0; }}
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <div class="header">
                                <h1>🔐 รีเซ็ตรหัสผ่าน</h1>
                            </div>
                            <div class="content">
                                <p>สวัสดี <strong>{user.username}</strong>,</p>
                                <p>คุณได้ขอรีเซ็ตรหัสผ่านสำหรับบัญชีของคุณ กรุณาคลิกปุ่มด้านล่างเพื่อตั้งรหัสผ่านใหม่:</p>
                                
                                <div style="text-align: center;">
                                    <a href="{reset_url}" class="button">รีเซ็ตรหัสผ่าน</a>
                                </div>
                                
                                <p>หรือคัดลอกลิงก์นี้ไปวางในเบราว์เซอร์:</p>
                                <div class="link-box">
                                    <a href="{reset_url}" style="color: #667eea;">{reset_url}</a>
                                </div>
                                
                                <div class="warning">
                                    <strong>⚠️ หมายเหตุ:</strong>
                                    <ul style="margin: 10px 0; padding-left: 20px;">
                                        <li>ลิงก์นี้จะหมดอายุใน <strong>1 ชั่วโมง</strong></li>
                                        <li>ใช้ได้เพียง <strong>1 ครั้ง</strong> เท่านั้น</li>
                                        <li>ถ้าคุณไม่ได้ขอรีเซ็ตรหัสผ่าน กรุณาเพิกเฉยอีเมลนี้</li>
                                    </ul>
                                </div>
                                
                                <p>หากคุณมีคำถามหรือต้องการความช่วยเหลือ กรุณาติดต่อทีมงานของเรา</p>
                            </div>
                            <div class="footer">
                                <p><strong>Dhakul Chan Travel Service</strong></p>
                                <p>710, 716, 704, 706 Prachautid Road, Samsennok, Huai Kwang, Bangkok 10310</p>
                                <p>Tel: +662 2744216 | Email: support@dhakulchan.com</p>
                                <p style="margin-top: 15px; color: #999;">
                                    © 2026 Dhakul Chan Group. All Rights Reserved.
                                </p>
                            </div>
                        </div>
                    </body>
                    </html>
                    """
                    
                    mail.send(msg)
                    flash('ลิงก์รีเซ็ตรหัสผ่านถูกส่งไปยังอีเมลของคุณแล้ว กรุณาตรวจสอบกล่องจดหมาย', 'success')
                    
                except Exception as e:
                    from utils.logging_config import get_logger
                    logger = get_logger(__name__)
                    logger.error(f"Failed to send password reset email: {e}")
                    # Fallback: Show link if email fails
                    flash(f'ไม่สามารถส่งอีเมลได้ กรุณาใช้ลิงก์นี้: {reset_url}', 'warning')
                    flash('ลิงก์มีอายุ 1 ชั่วโมง', 'info')
                
            except Exception as e:
                db.session.rollback()
                from utils.logging_config import get_logger
                logger = get_logger(__name__)
                logger.error(f"Error creating password reset token: {e}")
                flash('เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง', 'error')
        else:
            # Don't reveal if email exists or not (security best practice)
            flash('หากอีเมลนี้มีในระบบ คุณจะได้รับลิงก์สำหรับรีเซ็ตรหัสผ่าน', 'info')
        
        return render_template('auth/forgot_password.html')
    
    return render_template('auth/forgot_password.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password with token"""
    from models.user import User
    from extensions import db
    from datetime import datetime
    from sqlalchemy import text
    
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Validation
        if not new_password or not confirm_password:
            flash('กรุณากรอกรหัสผ่านใหม่และยืนยันรหัสผ่าน', 'error')
            return render_template('auth/reset_password.html', token=token)
        
        if new_password != confirm_password:
            flash('รหัสผ่านไม่ตรงกัน', 'error')
            return render_template('auth/reset_password.html', token=token)
        
        if len(new_password) < 6:
            flash('รหัสผ่านต้องมีความยาวอย่างน้อย 6 ตัวอักษร', 'error')
            return render_template('auth/reset_password.html', token=token)
        
        # Verify token
        result = db.session.execute(text("""
            SELECT user_id, expires_at, used
            FROM password_reset_tokens
            WHERE token = :token
        """), {'token': token}).fetchone()
        
        if not result:
            flash('ลิงก์รีเซ็ตรหัสผ่านไม่ถูกต้อง', 'error')
            return redirect(url_for('auth.login'))
        
        user_id, expires_at, used = result
        
        # Check if token is expired
        if datetime.now() > expires_at:
            flash('ลิงก์รีเซ็ตรหัสผ่านหมดอายุแล้ว กรุณาขอลิงก์ใหม่', 'error')
            return redirect(url_for('auth.forgot_password'))
        
        # Check if token already used
        if used:
            flash('ลิงก์นี้ถูกใช้งานไปแล้ว', 'error')
            return redirect(url_for('auth.forgot_password'))
        
        # Update password
        user = User.query.get(user_id)
        if not user:
            flash('ไม่พบผู้ใช้', 'error')
            return redirect(url_for('auth.login'))
        
        try:
            user.set_password(new_password)
            
            # Mark token as used
            db.session.execute(text("""
                UPDATE password_reset_tokens
                SET used = TRUE
                WHERE token = :token
            """), {'token': token})
            
            db.session.commit()
            
            flash('เปลี่ยนรหัสผ่านสำเร็จ! กรุณาเข้าสู่ระบบด้วยรหัสผ่านใหม่', 'success')
            
            # Redirect based on user role
            if user.role == 'Customer':
                return redirect(url_for('customer_points.customer_login'))
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            from utils.logging_config import get_logger
            logger = get_logger(__name__)
            logger.error(f"Error resetting password: {e}")
            flash('เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง', 'error')
    
    # GET request - verify token first
    result = db.session.execute(text("""
        SELECT user_id, expires_at, used
        FROM password_reset_tokens
        WHERE token = :token
    """), {'token': token}).fetchone()
    
    if not result:
        flash('ลิงก์รีเซ็ตรหัสผ่านไม่ถูกต้อง', 'error')
        return redirect(url_for('auth.login'))
    
    user_id, expires_at, used = result
    
    if datetime.now() > expires_at:
        flash('ลิงก์รีเซ็ตรหัสผ่านหมดอายุแล้ว กรุณาขอลิงก์ใหม่', 'error')
        return redirect(url_for('auth.forgot_password'))
    
    if used:
        flash('ลิงก์นี้ถูกใช้งานไปแล้ว', 'error')
        return redirect(url_for('auth.forgot_password'))
    
    return render_template('auth/reset_password.html', token=token)

@auth_bp.route('/update-email', methods=['POST'])
@login_required
def update_email():
    from models.user import User
    from extensions import db
    
    new_email = request.form.get('new_email', '').strip()
    password_confirm = request.form.get('password_confirm')
    
    # Validate password
    if not current_user.check_password(password_confirm):
        flash('Password is incorrect', 'error')
        return redirect(url_for('auth.profile'))
    
    # Validate email format
    import re
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', new_email):
        flash('Invalid email format', 'error')
        return redirect(url_for('auth.profile'))
    
    # Check if email already exists
    existing_user = User.query.filter_by(email=new_email).first()
    if existing_user and existing_user.id != current_user.id:
        flash('Email address is already in use by another account', 'error')
        return redirect(url_for('auth.profile'))
    
    # Check if email is the same
    if new_email == current_user.email:
        flash('New email is the same as current email', 'warning')
        return redirect(url_for('auth.profile'))
    
    try:
        old_email = current_user.email
        current_user.email = new_email
        db.session.commit()
        
        flash(f'Email updated successfully! Changed from {old_email} to {new_email}', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating email: {str(e)}', 'error')
    
    return redirect(url_for('auth.profile'))
