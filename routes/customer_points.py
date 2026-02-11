"""
Customer Points Routes - For customers to view their own points
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user, login_user
from models.review import CustomerPoints, PointTransaction
from models.user import User
from extensions import db

customer_points_bp = Blueprint('customer_points', __name__, url_prefix='/customer')

@customer_points_bp.route('/login', methods=['GET', 'POST'])
def customer_login():
    """Customer-specific login page"""
    if current_user.is_authenticated:
        if current_user.role == 'Customer':
            return redirect(url_for('customer_points.my_points'))
        else:
            return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('กรุณากรอกชื่อผู้ใช้และรหัสผ่าน', 'error')
            return render_template('customer/auth/login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            if user.role != 'Customer':
                flash('กรุณาใช้หน้า Login สำหรับเจ้าหน้าที่', 'warning')
                return redirect(url_for('auth.login'))
            
            login_user(user)
            flash(f'ยินดีต้อนรับ {user.username}!', 'success')
            
            # Redirect to requested page or points page
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('customer_points.my_points'))
        else:
            flash('ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง', 'error')
    
    return render_template('customer/auth/login.html')

@customer_points_bp.route('/points')
@login_required
def my_points():
    """Customer views their own points"""
    # Only allow Customer role
    if current_user.role != 'Customer':
        flash('คุณไม่มีสิทธิ์เข้าถึงหน้านี้', 'error')
        return redirect(url_for('dashboard.index'))
    
    # Check if user has customer profile
    if not current_user.customer_profile:
        flash('กรุณาสร้างโปรไฟล์ลูกค้าก่อน', 'error')
        return redirect(url_for('public_group_buy.index'))
    
    # Get customer points
    points_record = CustomerPoints.query.filter_by(customer_id=current_user.customer_profile.id).first()
    
    # Get recent transactions
    transactions = PointTransaction.query.filter_by(
        customer_id=current_user.customer_profile.id
    ).order_by(PointTransaction.created_at.desc()).limit(20).all()
    
    return render_template('customer/points/my_points.html',
                         points_record=points_record,
                         transactions=transactions)
