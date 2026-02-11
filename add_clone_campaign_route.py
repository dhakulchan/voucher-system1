"""
Add clone campaign route to group_buy_admin.py
Insert this after the edit_campaign route
"""

CLONE_ROUTE = '''
@bp.route('/campaigns/<int:campaign_id>/clone', methods=['GET'])
@login_required
@group_buy_permission_required('create_campaign')
def clone_campaign(campaign_id):
    """คัดลอกแคมเปญ"""
    try:
        # Get original campaign
        original = GroupBuyCampaign.query.get_or_404(campaign_id)
        
        # Create new campaign with copied data
        new_campaign = GroupBuyCampaign(
            name=f"{original.name} (Copy)",
            product_type=original.product_type,
            product_details=original.product_details,
            description=original.description,
            terms_conditions=original.terms_conditions,
            admin_notes=original.admin_notes,
            
            # Pricing
            regular_price=original.regular_price,
            group_price=original.group_price,
            
            # Requirements
            min_participants=original.min_participants,
            max_participants=original.max_participants,
            duration_hours=original.duration_hours,
            
            # Dates - set new dates (1 month from now)
            campaign_start_date=datetime.now() + timedelta(days=30),
            campaign_end_date=datetime.now() + timedelta(days=60),
            travel_date_from=original.travel_date_from + timedelta(days=30) if original.travel_date_from else None,
            travel_date_to=original.travel_date_to + timedelta(days=30) if original.travel_date_to else None,
            
            # Pax
            max_pax=original.max_pax,
            
            # Inventory
            total_slots=original.total_slots,
            available_slots=original.total_slots,  # Reset to full
            
            # Status - set as draft
            status='draft',
            is_active=False,
            is_public=False,
            featured=False,
            
            # Images
            product_image=original.product_image,
            image_title=original.image_title,
            image_position=original.image_position,
            
            # Special codes
            special_booker_codes=original.special_booker_codes,
            
            # Timestamps
            created_at=naive_utc_now(),
            updated_at=naive_utc_now()
        )
        
        db.session.add(new_campaign)
        db.session.commit()
        
        flash(f'คัดลอกแคมเปญสำเร็จ! กรุณาตรวจสอบและแก้ไขข้อมูลก่อนเปิดใช้งาน', 'success')
        return redirect(url_for('group_buy_admin.edit_campaign', campaign_id=new_campaign.id))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error cloning campaign: {e}")
        flash(f'เกิดข้อผิดพลาดในการคัดลอกแคมเปญ: {str(e)}', 'danger')
        return redirect(url_for('group_buy_admin.campaigns'))
'''

print(CLONE_ROUTE)
