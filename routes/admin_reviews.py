"""
Admin Reviews Management Routes
จัดการรีวิวจากลูกค้า - อนุมัติ/ปฏิเสธรีวิว
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from models.review import CampaignReview, ReviewImage
from models.customer import Customer
from models.group_buy import GroupBuyCampaign
from extensions import db
import logging

bp = Blueprint('admin_reviews', __name__, url_prefix='/admin/reviews')
logger = logging.getLogger(__name__)

@bp.route('/')
@login_required
def list_reviews():
    """แสดงรายการรีวิวทั้งหมด"""
    # ตรวจสอบสิทธิ์
    if not current_user.has_sidebar_menu('customer_reviews'):
        flash('คุณไม่มีสิทธิ์เข้าถึงหน้านี้', 'error')
        return redirect(url_for('dashboard.index'))
    
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', 'pending')
    per_page = 20
    
    # Query based on filter
    query = CampaignReview.query
    
    if status_filter == 'pending':
        query = query.filter_by(is_approved=False)
    elif status_filter == 'approved':
        query = query.filter_by(is_approved=True)
    
    reviews = query.order_by(
        CampaignReview.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    # Count statistics
    total_reviews = CampaignReview.query.count()
    pending_reviews = CampaignReview.query.filter_by(is_approved=False).count()
    approved_reviews = CampaignReview.query.filter_by(is_approved=True).count()
    
    return render_template('admin/reviews/list.html', 
                         reviews=reviews,
                         status_filter=status_filter,
                         total_reviews=total_reviews,
                         pending_reviews=pending_reviews,
                         approved_reviews=approved_reviews)

@bp.route('/<int:review_id>')
@login_required
def view_review(review_id):
    """ดูรายละเอียดรีวิว"""
    if not current_user.has_sidebar_menu('customer_reviews'):
        flash('คุณไม่มีสิทธิ์เข้าถึงหน้านี้', 'error')
        return redirect(url_for('dashboard.index'))
    
    review = CampaignReview.query.get_or_404(review_id)
    
    return render_template('admin/reviews/detail.html', review=review)

@bp.route('/<int:review_id>/approve', methods=['POST'])
@login_required
def approve_review(review_id):
    """อนุมัติรีวิว"""
    if not current_user.has_sidebar_menu('customer_reviews'):
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        review = CampaignReview.query.get_or_404(review_id)
        review.is_approved = True
        db.session.commit()
        
        flash(f'อนุมัติรีวิว #{review_id} เรียบร้อยแล้ว', 'success')
        logger.info(f"Review #{review_id} approved by {current_user.username}")
        
    except Exception as e:
        db.session.rollback()
        flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
        logger.error(f"Error approving review #{review_id}: {e}")
    
    return redirect(url_for('admin_reviews.list_reviews'))

@bp.route('/<int:review_id>/reject', methods=['POST'])
@login_required
def reject_review(review_id):
    """ปฏิเสธรีวิว"""
    if not current_user.has_sidebar_menu('customer_reviews'):
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        review = CampaignReview.query.get_or_404(review_id)
        review.is_approved = False
        db.session.commit()
        
        flash(f'ปฏิเสธรีวิว #{review_id} แล้ว', 'info')
        logger.info(f"Review #{review_id} rejected by {current_user.username}")
        
    except Exception as e:
        db.session.rollback()
        flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
        logger.error(f"Error rejecting review #{review_id}: {e}")
    
    return redirect(url_for('admin_reviews.list_reviews'))

@bp.route('/<int:review_id>/delete', methods=['POST'])
@login_required
def delete_review(review_id):
    """ลบรีวิว"""
    if not current_user.has_sidebar_menu('customer_reviews'):
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        review = CampaignReview.query.get_or_404(review_id)
        
        # ลบรูปภาพที่เกี่ยวข้อง
        ReviewImage.query.filter_by(review_id=review_id).delete()
        
        # ลบรีวิว
        db.session.delete(review)
        db.session.commit()
        
        flash(f'ลบรีวิว #{review_id} เรียบร้อยแล้ว', 'success')
        logger.info(f"Review #{review_id} deleted by {current_user.username}")
        
    except Exception as e:
        db.session.rollback()
        flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
        logger.error(f"Error deleting review #{review_id}: {e}")
    
    return redirect(url_for('admin_reviews.list_reviews'))

@bp.route('/bulk-action', methods=['POST'])
@login_required
def bulk_action():
    """จัดการรีวิวแบบหลายรายการพร้อมกัน"""
    if not current_user.has_sidebar_menu('customer_reviews'):
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        action = request.form.get('action')
        review_ids = request.form.getlist('review_ids[]')
        
        if not review_ids:
            flash('กรุณาเลือกรีวิวอย่างน้อย 1 รายการ', 'warning')
            return redirect(url_for('admin_reviews.list_reviews'))
        
        review_ids = [int(id) for id in review_ids]
        
        if action == 'approve':
            CampaignReview.query.filter(CampaignReview.id.in_(review_ids)).update(
                {CampaignReview.is_approved: True}, synchronize_session=False
            )
            flash(f'อนุมัติรีวิว {len(review_ids)} รายการเรียบร้อยแล้ว', 'success')
            
        elif action == 'reject':
            CampaignReview.query.filter(CampaignReview.id.in_(review_ids)).update(
                {CampaignReview.is_approved: False}, synchronize_session=False
            )
            flash(f'ปฏิเสธรีวิว {len(review_ids)} รายการแล้ว', 'info')
            
        elif action == 'delete':
            ReviewImage.query.filter(ReviewImage.review_id.in_(review_ids)).delete(synchronize_session=False)
            CampaignReview.query.filter(CampaignReview.id.in_(review_ids)).delete(synchronize_session=False)
            flash(f'ลบรีวิว {len(review_ids)} รายการเรียบร้อยแล้ว', 'success')
        
        db.session.commit()
        logger.info(f"Bulk action '{action}' performed on {len(review_ids)} reviews by {current_user.username}")
        
    except Exception as e:
        db.session.rollback()
        flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
        logger.error(f"Error in bulk action: {e}")
    
    return redirect(url_for('admin_reviews.list_reviews'))
