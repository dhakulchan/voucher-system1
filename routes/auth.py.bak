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
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            flash('Login successful!', 'success')
            return redirect(next_page or url_for('dashboard.index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
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
        
        # Create new user
        user = User.create_user(username, email, password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    
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
