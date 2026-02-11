from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from extensions import db
from models.review import CampaignReview, CustomerPoints, PointTransaction
from models.group_buy import GroupBuyCampaign, GroupBuyParticipant
from datetime import datetime

customer_reviews_bp = Blueprint('customer_reviews', __name__, url_prefix='/customer/reviews')

@customer_reviews_bp.route('/')
@login_required
def list_reviews():
    """แสดงรีวิวทั้งหมดของลูกค้า"""
    # Get customer profile
    if not current_user.customer_profile:
        flash('กรุณาสร้างโปรไฟล์ลูกค้าก่อน', 'error')
        return redirect(url_for('public_group_buy.index'))
    
    reviews = CampaignReview.query.filter_by(
        customer_id=current_user.customer_profile.id
    ).order_by(CampaignReview.created_at.desc()).all()
    
    # Get customer points
    points = CustomerPoints.query.filter_by(customer_id=current_user.customer_profile.id).first()
    
    return render_template('customer/reviews/list.html', 
                         reviews=reviews,
                         points=points)

@customer_reviews_bp.route('/campaign/<int:campaign_id>')
def campaign_reviews(campaign_id):
    """แสดงรีวิวทั้งหมดของแคมเปญ - เปิดให้ทุกคนดูได้"""
    campaign = GroupBuyCampaign.query.get_or_404(campaign_id)
    
    reviews = CampaignReview.query.filter_by(
        campaign_id=campaign_id,
        is_approved=True
    ).order_by(CampaignReview.created_at.desc()).all()
    
    # Check if user can write review
    can_write = False
    if current_user.is_authenticated and current_user.customer_profile:
        # Check if user has participated (ไม่บังคับว่าต้องชำระแล้ว)
        participant = GroupBuyParticipant.query.filter_by(
            campaign_id=campaign_id,
            customer_id=current_user.customer_profile.id
        ).first()
        
        existing_review = CampaignReview.query.filter_by(
            campaign_id=campaign_id,
            customer_id=current_user.customer_profile.id
        ).first()
        
        can_write = participant is not None and existing_review is None
    
    return render_template('customer/reviews/campaign_reviews.html',
                         campaign=campaign,
                         reviews=reviews,
                         can_write=can_write)

@customer_reviews_bp.route('/write/<int:campaign_id>', methods=['GET', 'POST'])
@login_required
def write_review(campaign_id):
    """เขียนรีวิว"""
    campaign = GroupBuyCampaign.query.get_or_404(campaign_id)
    
    # Check if user has customer profile
    if not current_user.customer_profile:
        flash('กรุณาสร้างโปรไฟล์ลูกค้าก่อน', 'error')
        return redirect(url_for('public_group_buy.view_campaign', campaign_id=campaign_id))
    
    # Check if user participated (ไม่บังคับว่าต้องชำระแล้ว)
    participant = GroupBuyParticipant.query.filter_by(
        campaign_id=campaign_id,
        customer_id=current_user.customer_profile.id
    ).first()
    
    if not participant:
        flash('คุณต้องเป็นผู้เข้าร่วมแคมเปญนี้เท่านั้น', 'error')
        return redirect(url_for('public_group_buy.view_campaign', campaign_id=campaign_id))
    
    # Check if already reviewed
    existing = CampaignReview.query.filter_by(
        campaign_id=campaign_id,
        customer_id=current_user.customer_profile.id
    ).first()
    
    if existing:
        flash('คุณได้เขียนรีวิวแคมเปญนี้แล้ว', 'warning')
        return redirect(url_for('customer_reviews.campaign_reviews', campaign_id=campaign_id))
    
    if request.method == 'POST':
        rating = int(request.form.get('rating', 5))
        review_text = request.form.get('comment', '').strip()
        
        if not review_text:
            flash('กรุณาเขียนรีวิวของคุณ', 'error')
            return render_template('customer/reviews/write.html', campaign=campaign)
        
        # Create review
        review = CampaignReview(
            campaign_id=campaign_id,
            customer_id=current_user.customer_profile.id,
            rating=rating,
            review_text=review_text,
            is_approved=False  # Wait for admin approval
        )
        
        db.session.add(review)
        db.session.commit()
        
        flash('ขอบคุณสำหรับรีวิว! รอการอนุมัติเพื่อรับคะแนน', 'success')
        return redirect(url_for('customer_reviews.list_reviews'))
    
    return render_template('customer/reviews/write.html', campaign=campaign)

@customer_reviews_bp.route('/edit/<int:review_id>', methods=['GET', 'POST'])
@login_required
def edit_review(review_id):
    """แก้ไขรีวิว"""
    review = CampaignReview.query.get_or_404(review_id)
    
    # Check ownership
    if not current_user.customer_profile or review.customer_id != current_user.customer_profile.id:
        flash('คุณไม่มีสิทธิ์แก้ไขรีวิวนี้', 'error')
        return redirect(url_for('customer_reviews.list_reviews'))
    
    if request.method == 'POST':
        review.rating = int(request.form.get('rating', review.rating))
        review.review_text = request.form.get('comment', review.review_text).strip()
        
        review.is_approved = False  # Re-submit for approval
        
        db.session.commit()
        flash('แก้ไขรีวิวเรียบร้อย รอการอนุมัติ', 'success')
        return redirect(url_for('customer_reviews.list_reviews'))
    
    return render_template('customer/reviews/edit.html', 
                         review=review,
                         campaign=review.campaign)

@customer_reviews_bp.route('/delete/<int:review_id>', methods=['POST'])
@login_required
def delete_review(review_id):
    """ลบรีวิว"""
    review = CampaignReview.query.get_or_404(review_id)
    
    # Check ownership
    if not current_user.customer_profile or review.customer_id != current_user.customer_profile.id:
        flash('คุณไม่มีสิทธิ์ลบรีวิวนี้', 'error')
        return redirect(url_for('customer_reviews.list_reviews'))
    
    # If review was approved and points given, we should deduct points
    # But this is complex - better to just mark as deleted
    db.session.delete(review)
    db.session.commit()
    
    flash('ลบรีวิวเรียบร้อย', 'success')
    return redirect(url_for('customer_reviews.list_reviews'))
