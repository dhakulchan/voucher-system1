"""
Group Buy Payment Admin Routes
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from extensions import db
from models.group_buy_payment import GroupBuyBankAccount, GroupBuyPayment
from werkzeug.utils import secure_filename
import os
from datetime import datetime

bp = Blueprint('group_buy_payment_admin', __name__, url_prefix='/backoffice/group-buy')

@bp.route('/bank-accounts')
def bank_accounts():
    """จัดการบัญชีธนาคาร"""
    accounts = GroupBuyBankAccount.query.order_by(
        GroupBuyBankAccount.display_order,
        GroupBuyBankAccount.id
    ).all()
    return render_template('group_buy/admin/bank_accounts.html', accounts=accounts)

@bp.route('/bank-accounts/create', methods=['GET', 'POST'])
def create_bank_account():
    """สร้างบัญชีธนาคารใหม่"""
    if request.method == 'POST':
        try:
            # Handle logo upload
            bank_logo = None
            if 'bank_logo' in request.files:
                file = request.files['bank_logo']
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'png'
                    new_filename = f"bank_logo_{timestamp}.{ext}"
                    
                    upload_folder = os.path.join('static', 'uploads', 'bank_logos')
                    os.makedirs(upload_folder, exist_ok=True)
                    filepath = os.path.join(upload_folder, new_filename)
                    
                    file.save(filepath)
                    bank_logo = filepath
            
            account = GroupBuyBankAccount(
                bank_name=request.form.get('bank_name'),
                account_number=request.form.get('account_number'),
                account_name=request.form.get('account_name'),
                bank_logo=bank_logo,
                is_active=request.form.get('is_active') == 'on',
                display_order=int(request.form.get('display_order', 0))
            )
            
            db.session.add(account)
            db.session.commit()
            
            flash('เพิ่มบัญชีธนาคารสำเร็จ', 'success')
            return redirect(url_for('group_buy_payment_admin.bank_accounts'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
    
    return render_template('group_buy/admin/create_bank_account.html')

@bp.route('/bank-accounts/<int:id>/edit', methods=['GET', 'POST'])
def edit_bank_account(id):
    """แก้ไขบัญชีธนาคาร"""
    account = GroupBuyBankAccount.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            account.bank_name = request.form.get('bank_name')
            account.account_number = request.form.get('account_number')
            account.account_name = request.form.get('account_name')
            account.is_active = request.form.get('is_active') == 'on'
            account.display_order = int(request.form.get('display_order', 0))
            
            # Handle logo upload
            if 'bank_logo' in request.files:
                file = request.files['bank_logo']
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'png'
                    new_filename = f"bank_logo_{timestamp}.{ext}"
                    
                    upload_folder = os.path.join('static', 'uploads', 'bank_logos')
                    os.makedirs(upload_folder, exist_ok=True)
                    filepath = os.path.join(upload_folder, new_filename)
                    
                    file.save(filepath)
                    account.bank_logo = filepath
            
            db.session.commit()
            flash('อัปเดตบัญชีธนาคารสำเร็จ', 'success')
            return redirect(url_for('group_buy_payment_admin.bank_accounts'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
    
    return render_template('group_buy/admin/edit_bank_account.html', account=account)

@bp.route('/bank-accounts/<int:id>/delete', methods=['POST'])
def delete_bank_account(id):
    """ลบบัญชีธนาคาร"""
    try:
        account = GroupBuyBankAccount.query.get_or_404(id)
        db.session.delete(account)
        db.session.commit()
        flash('ลบบัญชีธนาคารสำเร็จ', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
    
    return redirect(url_for('group_buy_payment_admin.bank_accounts'))

@bp.route('/payments')
def payments():
    """จัดการการชำระเงิน"""
    status = request.args.get('status')
    method = request.args.get('method')
    
    query = GroupBuyPayment.query
    
    if status:
        query = query.filter_by(payment_status=status)
    if method:
        query = query.filter_by(payment_method=method)
    
    payments = query.order_by(GroupBuyPayment.created_at.desc()).all()
    
    return render_template('group_buy/admin/payments.html', payments=payments)

@bp.route('/payments/<int:id>/verify', methods=['POST'])
def verify_payment(id):
    """ยืนยันการชำระเงิน"""
    try:
        payment = GroupBuyPayment.query.get_or_404(id)
        
        payment.payment_status = 'paid'
        payment.admin_verified_at = datetime.utcnow()
        payment.admin_verified_by = 1  # TODO: Get from session
        payment.admin_notes = request.form.get('admin_notes', '')
        
        db.session.commit()
        
        flash('ยืนยันการชำระเงินสำเร็จ', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
    
    return redirect(url_for('group_buy_payment_admin.payments'))

@bp.route('/payments/<int:id>/refund', methods=['POST'])
def refund_payment(id):
    """คืนเงิน"""
    try:
        payment = GroupBuyPayment.query.get_or_404(id)
        
        refund_amount = float(request.form.get('refund_amount', payment.total_amount))
        
        payment.payment_status = 'refunded'
        payment.refund_amount = refund_amount
        payment.refund_reason = request.form.get('refund_reason', '')
        payment.refunded_at = datetime.utcnow()
        payment.refunded_by = 1  # TODO: Get from session
        
        db.session.commit()
        
        flash('คืนเงินสำเร็จ', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
    
    return redirect(url_for('group_buy_payment_admin.payments'))
