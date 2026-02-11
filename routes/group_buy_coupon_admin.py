"""
Group Buy Coupon Admin Routes
จัดการคูปองส่วนลด
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models.group_buy_coupon import GroupBuyCoupon, GroupBuyCouponUsage
from models.group_buy import GroupBuyCampaign
from services.coupon_service import CouponService
from extensions import db
from datetime import datetime
from utils.datetime_utils import naive_utc_now

coupon_bp = Blueprint('group_buy_coupon', __name__, url_prefix='/backoffice/group-buy/coupons')

@coupon_bp.route('/')
@login_required
def list_coupons():
    """แสดงรายการคูปอง"""
    from utils.datetime_utils import naive_utc_now
    
    coupons = GroupBuyCoupon.query.order_by(GroupBuyCoupon.created_at.desc()).all()
    
    # Get stats for each coupon
    coupon_stats = {}
    for coupon in coupons:
        stats = CouponService.get_usage_stats(coupon.id)
        coupon_stats[coupon.id] = stats
    
    return render_template('group_buy/admin/coupons/list.html', 
                         coupons=coupons,
                         coupon_stats=coupon_stats,
                         now=naive_utc_now())

@coupon_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_coupon():
    """สร้างคูปองใหม่"""
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        description = request.form.get('description', '').strip()
        discount_type = request.form.get('discount_type', 'fixed')
        discount_value = float(request.form.get('discount_value', 0))
        
        # Dates
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        start_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M')
        
        # Limits
        max_uses = request.form.get('max_uses', '').strip()
        max_uses = int(max_uses) if max_uses else None
        max_uses_per_user = int(request.form.get('max_uses_per_user', 1))
        
        # Conditions
        min_purchase_amount = float(request.form.get('min_purchase_amount', 0))
        campaign_id = request.form.get('campaign_id', '').strip()
        campaign_id = int(campaign_id) if campaign_id else None
        
        success, message, coupon = CouponService.create_coupon(
            code=code,
            description=description,
            discount_type=discount_type,
            discount_value=discount_value,
            start_date=start_date,
            end_date=end_date,
            created_by=current_user.id,
            max_uses=max_uses,
            max_uses_per_user=max_uses_per_user,
            min_purchase_amount=min_purchase_amount,
            campaign_id=campaign_id
        )
        
        if success:
            flash(message, 'success')
            return redirect(url_for('group_buy_coupon.list_coupons'))
        else:
            flash(message, 'danger')
    
    # Get campaigns for dropdown
    campaigns = GroupBuyCampaign.query.filter_by(is_active=True).order_by(GroupBuyCampaign.name).all()
    
    return render_template('group_buy/admin/coupons/create.html', campaigns=campaigns)

@coupon_bp.route('/<int:coupon_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_coupon(coupon_id):
    """แก้ไขคูปอง"""
    coupon = GroupBuyCoupon.query.get_or_404(coupon_id)
    
    if request.method == 'POST':
        # Update basic info
        coupon.description = request.form.get('description', '').strip()
        coupon.discount_type = request.form.get('discount_type', 'fixed')
        coupon.discount_value = float(request.form.get('discount_value', 0))
        
        # Update dates
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        coupon.start_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M')
        coupon.end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M')
        
        # Update limits
        max_uses = request.form.get('max_uses', '').strip()
        coupon.max_uses = int(max_uses) if max_uses else None
        coupon.max_uses_per_user = int(request.form.get('max_uses_per_user', 1))
        
        # Update conditions
        coupon.min_purchase_amount = float(request.form.get('min_purchase_amount', 0))
        campaign_id = request.form.get('campaign_id', '').strip()
        coupon.campaign_id = int(campaign_id) if campaign_id else None
        
        # Update status
        coupon.is_active = request.form.get('is_active') == 'on'
        
        try:
            db.session.commit()
            flash('อัพเดทคูปองสำเร็จ', 'success')
            return redirect(url_for('group_buy_coupon.list_coupons'))
        except Exception as e:
            db.session.rollback()
            flash(f'เกิดข้อผิดพลาด: {str(e)}', 'danger')
    
    # Get campaigns for dropdown
    campaigns = GroupBuyCampaign.query.filter_by(is_active=True).order_by(GroupBuyCampaign.name).all()
    
    # Get stats
    stats = CouponService.get_usage_stats(coupon_id)
    
    return render_template('group_buy/admin/coupons/edit.html', 
                         coupon=coupon, 
                         campaigns=campaigns,
                         stats=stats)

@coupon_bp.route('/<int:coupon_id>/delete', methods=['POST'])
@login_required
def delete_coupon(coupon_id):
    """ลบคูปอง"""
    coupon = GroupBuyCoupon.query.get_or_404(coupon_id)
    
    # Check if coupon has been used
    if coupon.used_count > 0:
        flash('ไม่สามารถลบคูปองที่มีการใช้งานแล้ว', 'danger')
        return redirect(url_for('group_buy_coupon.list_coupons'))
    
    try:
        db.session.delete(coupon)
        db.session.commit()
        flash('ลบคูปองสำเร็จ', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'เกิดข้อผิดพลาด: {str(e)}', 'danger')
    
    return redirect(url_for('group_buy_coupon.list_coupons'))

@coupon_bp.route('/<int:coupon_id>/toggle', methods=['POST'])
@login_required
def toggle_coupon(coupon_id):
    """เปิด/ปิดการใช้งานคูปอง"""
    coupon = GroupBuyCoupon.query.get_or_404(coupon_id)
    coupon.is_active = not coupon.is_active
    
    try:
        db.session.commit()
        status = 'เปิดใช้งาน' if coupon.is_active else 'ปิดใช้งาน'
        flash(f'{status}คูปองสำเร็จ', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'เกิดข้อผิดพลาด: {str(e)}', 'danger')
    
    return redirect(url_for('group_buy_coupon.list_coupons'))

@coupon_bp.route('/<int:coupon_id>/usage')
@login_required
def view_usage(coupon_id):
    """ดูรายละเอียดการใช้งานคูปอง"""
    coupon = GroupBuyCoupon.query.get_or_404(coupon_id)
    usage_logs = GroupBuyCouponUsage.query.filter_by(coupon_id=coupon_id)\
        .order_by(GroupBuyCouponUsage.used_at.desc()).all()
    
    stats = CouponService.get_usage_stats(coupon_id)
    
    return render_template('group_buy/admin/coupons/usage.html',
                         coupon=coupon,
                         usage_logs=usage_logs,
                         stats=stats)

# API endpoint for validating coupon (AJAX)
@coupon_bp.route('/validate', methods=['POST'])
def validate_coupon_api():
    """API สำหรับตรวจสอบคูปอง (ใช้งานในหน้า public)"""
    data = request.get_json()
    code = data.get('code', '').strip()
    campaign_id = data.get('campaign_id')
    amount = float(data.get('amount', 0))
    customer_email = data.get('customer_email')
    
    success, message, discount, coupon = CouponService.validate_and_apply_coupon(
        code=code,
        campaign_id=campaign_id,
        amount=amount,
        customer_email=customer_email
    )
    
    if success:
        return jsonify({
            'success': True,
            'message': message,
            'discount': float(discount),
            'final_amount': amount - discount,
            'discount_type': coupon.discount_type,
            'discount_value': float(coupon.discount_value)
        })
    else:
        return jsonify({
            'success': False,
            'message': message
        }), 400
