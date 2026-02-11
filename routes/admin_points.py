"""
Admin Customer Points Management Routes
จัดการแต้มสะสมลูกค้า - เพิ่ม/ลด/ตรวจสอบแต้ม
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from models.review import CustomerPoints, PointTransaction
from models.customer import Customer
from models.group_buy import GroupBuyParticipant
from services.points_service import PointsService
from extensions import db
from datetime import datetime, timedelta
import logging

bp = Blueprint('admin_points', __name__, url_prefix='/admin/points')
logger = logging.getLogger(__name__)

@bp.route('/')
@login_required
def list_customers():
    """แสดงรายการลูกค้าทั้งหมดพร้อมแต้มสะสม"""
    if not current_user.has_sidebar_menu('customer_points'):
        flash('คุณไม่มีสิทธิ์เข้าถึงหน้านี้', 'error')
        return redirect(url_for('dashboard.index'))
    
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    sort_by = request.args.get('sort', 'points')  # points, name, email
    per_page = 20
    
    # Query customers with points
    query = db.session.query(Customer, CustomerPoints).outerjoin(
        CustomerPoints, Customer.id == CustomerPoints.customer_id
    )
    
    # Apply search filter
    if search:
        query = query.filter(
            db.or_(
                Customer.name.ilike(f'%{search}%'),
                Customer.email.ilike(f'%{search}%'),
                Customer.phone.ilike(f'%{search}%')
            )
        )
    
    # Apply sorting (MariaDB doesn't support NULLS LAST, use CASE instead)
    if sort_by == 'points':
        from sqlalchemy import case
        query = query.order_by(
            case((CustomerPoints.total_points == None, 1), else_=0),
            CustomerPoints.total_points.desc()
        )
    elif sort_by == 'name':
        query = query.order_by(Customer.name)
    elif sort_by == 'email':
        query = query.order_by(Customer.email)
    
    results = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Calculate statistics
    total_customers = Customer.query.count()
    customers_with_points = CustomerPoints.query.filter(CustomerPoints.total_points > 0).count()
    total_points_issued = db.session.query(db.func.sum(CustomerPoints.total_points)).scalar() or 0
    
    return render_template('admin/points/list.html',
                         results=results,
                         search=search,
                         sort_by=sort_by,
                         total_customers=total_customers,
                         customers_with_points=customers_with_points,
                         total_points_issued=total_points_issued)

@bp.route('/customer/<int:customer_id>')
@login_required
def customer_detail(customer_id):
    """ดูรายละเอียดแต้มของลูกค้า"""
    if not current_user.has_sidebar_menu('customer_points'):
        flash('คุณไม่มีสิทธิ์เข้าถึงหน้านี้', 'error')
        return redirect(url_for('dashboard.index'))
    
    customer = Customer.query.get_or_404(customer_id)
    points_record = CustomerPoints.query.filter_by(customer_id=customer_id).first()
    
    # Get transaction history
    transactions = PointTransaction.query.filter_by(
        customer_id=customer_id
    ).order_by(PointTransaction.created_at.desc()).limit(50).all()
    
    # Get bookings (participants in group buy campaigns)
    bookings = GroupBuyParticipant.query.filter_by(customer_id=customer_id).order_by(
        GroupBuyParticipant.created_at.desc()
    ).limit(10).all()
    
    # Calculate statistics
    total_earned = db.session.query(
        db.func.sum(PointTransaction.points)
    ).filter(
        PointTransaction.customer_id == customer_id,
        PointTransaction.transaction_type == 'earned'
    ).scalar() or 0
    
    total_redeemed = db.session.query(
        db.func.sum(PointTransaction.points)
    ).filter(
        PointTransaction.customer_id == customer_id,
        PointTransaction.transaction_type == 'redeemed'
    ).scalar() or 0
    
    # Points expiring soon (within 30 days)
    expiring_soon = db.session.query(
        db.func.sum(PointTransaction.points)
    ).filter(
        PointTransaction.customer_id == customer_id,
        PointTransaction.transaction_type == 'earned',
        PointTransaction.expires_at <= datetime.now() + timedelta(days=30),
        PointTransaction.expires_at > datetime.now()
    ).scalar() or 0
    
    return render_template('admin/points/detail.html',
                         customer=customer,
                         points_record=points_record,
                         transactions=transactions,
                         bookings=bookings,
                         total_earned=abs(total_earned),
                         total_redeemed=abs(total_redeemed),
                         expiring_soon=abs(expiring_soon))

@bp.route('/customer/<int:customer_id>/adjust', methods=['POST'])
@login_required
def adjust_points(customer_id):
    """ปรับแต้มลูกค้า (เพิ่ม/ลด) โดย Admin"""
    if not current_user.has_sidebar_menu('customer_points'):
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        customer = Customer.query.get_or_404(customer_id)
        points = int(request.form.get('points', 0))
        reason = request.form.get('reason', '').strip()
        
        if not reason:
            flash('กรุณาระบุเหตุผลในการปรับแต้ม', 'warning')
            return redirect(url_for('admin_points.customer_detail', customer_id=customer_id))
        
        if points == 0:
            flash('กรุณาระบุจำนวนแต้มที่ต้องการปรับ', 'warning')
            return redirect(url_for('admin_points.customer_detail', customer_id=customer_id))
        
        # Add or deduct points
        points_service = PointsService()
        
        if points > 0:
            # เพิ่มแต้ม
            points_service.add_points(
                customer_id=customer_id,
                points=points,
                source_type='admin_adjustment',
                source_id=current_user.id,
                description=f"Admin adjustment: {reason}"
            )
            flash(f'เพิ่มแต้มให้ {customer.name} จำนวน {points} แต้มเรียบร้อยแล้ว', 'success')
            
        else:
            # ลดแต้ม
            points_record = CustomerPoints.query.filter_by(customer_id=customer_id).first()
            if not points_record or points_record.total_points < abs(points):
                flash('ลูกค้ามีแต้มไม่เพียงพอ', 'error')
                return redirect(url_for('admin_points.customer_detail', customer_id=customer_id))
            
            # Create deduction transaction
            transaction = PointTransaction(
                customer_id=customer_id,
                points=points,  # ติดลบ
                transaction_type='adjustment',
                balance_after=points_record.total_points + points,
                source_type='admin_adjustment',
                source_id=current_user.id,
                description=f"Admin adjustment: {reason}"
            )
            db.session.add(transaction)
            
            # Update total points
            points_record.total_points += points  # points เป็นลบอยู่แล้ว
            db.session.commit()
            
            flash(f'หักแต้มของ {customer.name} จำนวน {abs(points)} แต้มเรียบร้อยแล้ว', 'success')
        
        logger.info(f"Admin {current_user.username} adjusted {points} points for customer #{customer_id}: {reason}")
        
    except ValueError:
        flash('จำนวนแต้มไม่ถูกต้อง', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
        logger.error(f"Error adjusting points for customer #{customer_id}: {e}")
    
    return redirect(url_for('admin_points.customer_detail', customer_id=customer_id))

@bp.route('/transactions')
@login_required
def list_transactions():
    """แสดงรายการธุรกรรมแต้มทั้งหมด"""
    if not current_user.has_sidebar_menu('customer_points'):
        flash('คุณไม่มีสิทธิ์เข้าถึงหน้านี้', 'error')
        return redirect(url_for('dashboard.index'))
    
    page = request.args.get('page', 1, type=int)
    transaction_type = request.args.get('type', 'all')  # all, earned, redeemed, deducted
    per_page = 50
    
    query = PointTransaction.query
    
    if transaction_type != 'all':
        query = query.filter_by(transaction_type=transaction_type)
    
    transactions = query.order_by(
        PointTransaction.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    # Statistics
    total_earned = db.session.query(
        db.func.sum(PointTransaction.points)
    ).filter_by(transaction_type='earned').scalar() or 0
    
    total_redeemed = db.session.query(
        db.func.sum(PointTransaction.points)
    ).filter_by(transaction_type='redeemed').scalar() or 0
    
    return render_template('admin/points/transactions.html',
                         transactions=transactions,
                         transaction_type=transaction_type,
                         total_earned=abs(total_earned),
                         total_redeemed=abs(total_redeemed))

@bp.route('/export')
@login_required
def export_points():
    """Export ข้อมูลแต้มเป็น CSV"""
    if not current_user.has_sidebar_menu('customer_points'):
        flash('คุณไม่มีสิทธิ์เข้าถึงหน้านี้', 'error')
        return redirect(url_for('dashboard.index'))
    
    from io import StringIO
    import csv
    from flask import Response
    
    # Query all customers with points
    results = db.session.query(Customer, CustomerPoints).outerjoin(
        CustomerPoints, Customer.id == CustomerPoints.customer_id
    ).all()
    
    # Create CSV
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['Customer ID', 'Name', 'Email', 'Phone', 'Total Points', 'Last Updated'])
    
    for customer, points in results:
        writer.writerow([
            customer.id,
            customer.name,
            customer.email,
            customer.phone or '',
            points.total_points if points else 0,
            points.updated_at.strftime('%Y-%m-%d %H:%M:%S') if points else ''
        ])
    
    output = si.getvalue()
    si.close()
    
    return Response(
        output,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=customer_points_{datetime.now().strftime("%Y%m%d")}.csv'}
    )
