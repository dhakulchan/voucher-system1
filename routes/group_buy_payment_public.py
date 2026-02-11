"""
Group Buy Payment Public Routes
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session, current_app
from extensions import db
from models.group_buy import GroupBuyCampaign
from models.group_buy_payment import GroupBuyBankAccount, GroupBuyPayment
from services.coupon_service import CouponService
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from decimal import Decimal
from utils.timezone_helper import now_thailand, get_thailand_timestamp

bp = Blueprint('group_buy_payment', __name__, url_prefix='/group-buy/payment')

def calculate_fee(amount, fee_type, fee_value):
    """คำนวณค่าธรรมเนียม"""
    if fee_type == 'percentage':
        return Decimal(str(amount)) * Decimal(str(fee_value)) / Decimal('100')
    elif fee_type == 'fixed':
        return Decimal(str(fee_value))
    return Decimal('0')

@bp.route('/select/<int:campaign_id>')
def select_method(campaign_id):
    """เลือกวิธีการชำระเงิน"""
    campaign = GroupBuyCampaign.query.get_or_404(campaign_id)
    
    # Get active bank accounts
    bank_accounts = []
    if campaign.payment_bank_enabled:
        bank_accounts = GroupBuyBankAccount.query.filter_by(is_active=True).order_by(
            GroupBuyBankAccount.display_order
        ).all()
    
    # ดึงข้อมูล pax_count จาก session
    pax_count = 1  # default
    if 'participant_id' in session:
        from models.group_buy import GroupBuyParticipant
        participant = GroupBuyParticipant.query.get(session['participant_id'])
        if participant:
            pax_count = participant.pax_count or 1
    elif 'pax_count' in session:
        pax_count = session['pax_count']
    
    # คำนวณราคา
    price_per_person = campaign.group_price
    total_price = price_per_person * pax_count
    
    # คำนวณจำนวนมัดจำ (ถ้ามี)
    deposit_per_person = None
    total_deposit = None
    if campaign.allow_partial_payment and campaign.partial_payment_value:
        # คำนวณตาม type
        if campaign.partial_payment_type == 'fixed':
            deposit_per_person = float(campaign.partial_payment_value)
        elif campaign.partial_payment_type == 'percentage':
            deposit_per_person = float(campaign.group_price * campaign.partial_payment_value / 100)
        else:
            deposit_per_person = float(campaign.group_price)
        
        total_deposit = deposit_per_person * pax_count
    
    return render_template(
        'group_buy/public/payment_select.html',
        campaign=campaign,
        bank_accounts=bank_accounts,
        pax_count=pax_count,
        price_per_person=price_per_person,
        total_price=total_price,
        deposit_per_person=deposit_per_person,
        total_deposit=total_deposit
    )

@bp.route('/bank/<int:campaign_id>', methods=['GET', 'POST'])
def bank_transfer(campaign_id):
    """ชำระเงินผ่านธนาคาร"""
    campaign = GroupBuyCampaign.query.get_or_404(campaign_id)
    
    if not campaign.payment_bank_enabled:
        flash('ไม่สามารถชำระเงินผ่านธนาคารได้', 'error')
        return redirect(url_for('group_buy_payment.select_method', campaign_id=campaign_id))
    
    bank_accounts = GroupBuyBankAccount.query.filter_by(is_active=True).order_by(
        GroupBuyBankAccount.display_order
    ).all()
    
    # ดึง pax_count และข้อมูลลูกค้าจาก session หรือ participant ที่เพิ่งสร้าง/join
    pax_count = 1  # default
    customer_name = ''
    customer_email = ''
    customer_phone = ''
    
    if 'participant_id' in session:
        from models.group_buy import GroupBuyParticipant
        participant = GroupBuyParticipant.query.get(session['participant_id'])
        if participant:
            pax_count = participant.pax_count or 1
            # ดึงข้อมูลลูกค้าจาก participant
            customer_name = participant.participant_name or ''
            customer_email = participant.participant_email or ''
            customer_phone = participant.participant_phone or ''
    
    # คำนวณยอดมัดจำ
    payment_amount = campaign.calculate_partial_payment(pax_count)
    
    # Debug logging
    print("=" * 80)
    print(f"🌐 GET /bank/{campaign_id}")
    print(f"Campaign: {campaign.name}")
    print(f"allow_partial_payment: {campaign.allow_partial_payment}")
    print(f"partial_payment_type: {campaign.partial_payment_type}")
    print(f"partial_payment_value: {campaign.partial_payment_value}")
    print(f"group_price: {campaign.group_price}")
    print(f"pax_count: {pax_count}")
    print(f"payment_amount (calculated): ฿{payment_amount:,.2f}")
    print("=" * 80)
    
    if request.method == 'POST':
        print("=" * 80)
        print("🏦 BANK TRANSFER - POST REQUEST RECEIVED")
        print(f"Campaign: {campaign.name} (ID: {campaign_id})")
        print(f"Payment Amount: ฿{payment_amount:,.2f}")
        print(f"Form Keys: {list(request.form.keys())}")
        print("=" * 80)
        
        try:
            # ตรวจสอบว่ามี participant_id ใน session หรือไม่
            participant_id = session.get('participant_id')
            participant = None
            if participant_id:
                from models.group_buy import GroupBuyParticipant
                participant = GroupBuyParticipant.query.get(participant_id)
                print(f"✅ Found participant ID: {participant_id}")
            
            # Handle slip upload
            slip_image = None
            if 'slip_image' in request.files:
                file = request.files['slip_image']
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    timestamp = get_thailand_timestamp()
                    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'png'
                    new_filename = f"slip_{timestamp}.{ext}"
                    
                    upload_folder = os.path.join('static', 'uploads', 'payment_slips')
                    os.makedirs(upload_folder, exist_ok=True)
                    filepath = os.path.join(upload_folder, new_filename)
                    
                    file.save(filepath)
                    slip_image = filepath
                    print(f"📎 Attached slip file: {new_filename}")
            
            # ใช้ payment_amount ที่คำนวณไว้แล้ว (ไม่ใช้จาก form)
            amount = Decimal(str(payment_amount))
            original_amount = amount  # เก็บยอดเดิมไว้
            
            # Handle coupon discount
            coupon_code = request.form.get('coupon_code', '').strip()
            discount_amount = Decimal('0')
            coupon_obj = None
            
            if coupon_code:
                success, message, discount, coupon = CouponService.validate_and_apply_coupon(
                    code=coupon_code,
                    campaign_id=campaign_id,
                    amount=float(amount),
                    customer_email=request.form.get('customer_email')
                )
                
                if success:
                    discount_amount = Decimal(str(discount))
                    amount = amount - discount_amount
                    coupon_obj = coupon
                    print(f"🎟️ Coupon {coupon_code} applied: -฿{discount_amount}")
                else:
                    print(f"❌ Coupon validation failed: {message}")
                    flash(f'ไม่สามารถใช้คูปองได้: {message}', 'warning')
            
            # Parse transfer datetime - support DD/MM/YYYY, HH:MM format
            transfer_datetime_str = request.form.get('transfer_datetime')
            print(f"📅 Received transfer_datetime: '{transfer_datetime_str}'")
            
            if not transfer_datetime_str:
                flash('กรุณาระบุวันที่-เวลาที่โอนเงิน', 'error')
                return render_template(
                    'group_buy/public/payment_bank.html',
                    campaign=campaign,
                    bank_accounts=bank_accounts,
                    pax_count=pax_count,
                    payment_amount=payment_amount,
                    customer_name=customer_name,
                    customer_email=customer_email,
                    customer_phone=customer_phone
                )
            
            try:
                # Try parsing DD/MM/YYYY, HH:MM format first
                transfer_dt = datetime.strptime(transfer_datetime_str, '%d/%m/%Y, %H:%M')
                print(f"✅ Parsed datetime (DD/MM/YYYY format): {transfer_dt}")
            except ValueError:
                try:
                    # Fallback to ISO format
                    transfer_dt = datetime.fromisoformat(transfer_datetime_str)
                    print(f"✅ Parsed datetime (ISO format): {transfer_dt}")
                except ValueError as e:
                    print(f"❌ Failed to parse datetime: {e}")
                    flash(f'รูปแบบวันที่-เวลาไม่ถูกต้อง: {transfer_datetime_str}', 'error')
                    return render_template(
                        'group_buy/public/payment_bank.html',
                        campaign=campaign,
                        bank_accounts=bank_accounts,
                        pax_count=pax_count,
                        payment_amount=payment_amount,
                        customer_name=customer_name,
                        customer_email=customer_email,
                        customer_phone=customer_phone
                    )
            
            # Get bank account ID with validation
            bank_account_id_str = request.form.get('bank_account_id', '').strip()
            if not bank_account_id_str:
                flash('กรุณาเลือกบัญชีธนาคารที่ต้องการโอนเข้า', 'error')
                return redirect(url_for('group_buy_payment.bank_transfer', campaign_id=campaign_id))
            
            bank_account_id = int(bank_account_id_str)
            
            # Create payment record
            payment = GroupBuyPayment(
                booking_id=0,  # Placeholder
                campaign_id=campaign_id,
                customer_name=request.form.get('customer_name'),
                customer_email=request.form.get('customer_email'),
                customer_phone=request.form.get('customer_phone'),
                payment_method='bank',
                payment_status='pending',
                amount=amount,
                fee_amount=Decimal('0'),
                total_amount=amount,
                bank_account_id=bank_account_id,
                transfer_date=transfer_dt.date(),
                transfer_time=transfer_dt.time(),
                slip_image=slip_image,
                coupon_id=coupon_obj.id if coupon_obj else None,
                coupon_code=coupon_code if coupon_obj else None,
                discount_amount=discount_amount,
                original_amount=original_amount
            )
            
            db.session.add(payment)
            db.session.flush()  # เพื่อให้ได้ payment.id
            print(f"💾 Payment created: ID={payment.id}, Amount={payment.total_amount}, Coupon={payment.coupon_code}")
            
            # Record coupon usage if applied
            if coupon_obj:
                print(f"🎟️ Recording coupon usage: {coupon_code} (ID={coupon_obj.id}) for payment #{payment.id}")
                usage = CouponService.record_usage(
                    coupon=coupon_obj,
                    participant_id=participant.id if participant else None,
                    campaign_id=campaign_id,
                    original_amount=float(original_amount),
                    discount_amount=float(discount_amount),
                    customer_email=request.form.get('customer_email'),
                    payment_id=payment.id
                )
                print(f"✅ Coupon usage recorded: ID={usage.id if usage else 'None'}")
            else:
                print("ℹ️ No coupon applied to this payment")
            
            # อัปเดต participant ถ้ามี
            if participant:
                participant.payment_id = payment.id
                participant.payment_status = 'pending'
                participant.payment_amount = amount
                participant.payment_reference = f"BANK-{payment.id}"
                payment.booking_id = participant.booking_id if participant.booking_id else 0
                print(f"✅ Updated participant #{participant.id} with payment #{payment.id}")
            
            db.session.commit()
            print(f"✅ Payment #{payment.id} created successfully")
            
            # ส่งอีเมล์ยืนยัน
            try:
                send_booking_confirmation_email(payment, campaign)
                print(f"✅ Email sent to {payment.customer_email}")
            except Exception as e:
                print(f"❌ Failed to send email: {e}")
            
            flash('บันทึกข้อมูลการโอนเงินเรียบร้อย รอการตรวจสอบจากเจ้าหน้าที่', 'success')
            return redirect(url_for('public_group_buy.view_campaign', campaign_id=campaign.id))
            
        except Exception as e:
            import traceback
            print("=" * 80)
            print("❌ BANK TRANSFER ERROR:")
            print(f"Error: {str(e)}")
            print(f"Traceback:\n{traceback.format_exc()}")
            print("=" * 80)
            db.session.rollback()
            flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
    
    # GET request - แสดงฟอร์มพร้อมข้อมูลที่ pre-fill
    return render_template(
        'group_buy/public/payment_bank.html',
        campaign=campaign,
        bank_accounts=bank_accounts,
        pax_count=pax_count,
        payment_amount=payment_amount,
        customer_name=customer_name,
        customer_email=customer_email,
        customer_phone=customer_phone
    )

@bp.route('/qr/<int:campaign_id>', methods=['GET', 'POST'])
def qr_payment(campaign_id):
    """ชำระเงินผ่าน QR Code"""
    campaign = GroupBuyCampaign.query.get_or_404(campaign_id)
    
    if not campaign.payment_qr_enabled:
        flash('ไม่สามารถชำระเงินผ่าน QR Code ได้', 'error')
        return redirect(url_for('group_buy_payment.select_method', campaign_id=campaign_id))
    
    # ดึง pax_count จาก session
    pax_count = 1
    if 'participant_id' in session:
        from models.group_buy import GroupBuyParticipant
        participant = GroupBuyParticipant.query.get(session['participant_id'])
        if participant:
            pax_count = participant.pax_count or 1
    
    # คำนวณยอดมัดจำ
    payment_amount = campaign.calculate_partial_payment(pax_count)
    
    if request.method == 'POST':
        try:
            # Handle slip upload
            slip_image = None
            if 'slip_image' in request.files:
                file = request.files['slip_image']
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'png'
                    new_filename = f"slip_{timestamp}.{ext}"
                    
                    upload_folder = os.path.join('static', 'uploads', 'payment_slips')
                    os.makedirs(upload_folder, exist_ok=True)
                    filepath = os.path.join(upload_folder, new_filename)
                    
                    file.save(filepath)
                    slip_image = filepath
            
            # ใช้ payment_amount ที่คำนวณไว้แล้ว
            amount = Decimal(str(payment_amount))
            
            # Create payment record
            payment = GroupBuyPayment(
                booking_id=0,  # Placeholder
                campaign_id=campaign_id,
                customer_name=request.form.get('customer_name'),
                customer_email=request.form.get('customer_email'),
                customer_phone=request.form.get('customer_phone'),
                payment_method='qr',
                payment_status='pending',
                amount=amount,
                fee_amount=Decimal('0'),
                total_amount=amount,
                slip_image=slip_image
            )
            
            db.session.add(payment)
            db.session.commit()
            
            # ส่งอีเมล์ยืนยัน
            try:
                send_booking_confirmation_email(payment, campaign)
            except Exception as e:
                print(f"Failed to send email: {e}")
            
            return redirect(url_for('group_buy_payment.payment_status', payment_id=payment.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
    
    return render_template(
        'group_buy/public/payment_qr.html',
        campaign=campaign,
        pax_count=pax_count,
        payment_amount=payment_amount
    )

@bp.route('/stripe/<int:campaign_id>', methods=['GET', 'POST'])
def stripe_payment(campaign_id):
    """ชำระเงินผ่าน Stripe"""
    campaign = GroupBuyCampaign.query.get_or_404(campaign_id)
    
    if not campaign.payment_stripe_enabled:
        flash('ไม่สามารถชำระเงินผ่าน Stripe ได้', 'error')
        return redirect(url_for('group_buy_payment.select_method', campaign_id=campaign_id))
    
    # ดึง pax_count จาก session
    pax_count = 1
    if 'participant_id' in session:
        from models.group_buy import GroupBuyParticipant
        participant = GroupBuyParticipant.query.get(session['participant_id'])
        if participant:
            pax_count = participant.pax_count or 1
    
    # คำนวณยอดมัดจำ
    payment_amount = campaign.calculate_partial_payment(pax_count)
    
    # Calculate fee
    amount = Decimal(str(payment_amount))
    fee_amount = calculate_fee(
        amount,
        campaign.payment_stripe_fee_type,
        campaign.payment_stripe_fee_value
    )
    total_amount = amount + fee_amount
    
    if request.method == 'POST':
        try:
            payment_method_id = request.form.get('payment_method_id')
            
            if not payment_method_id:
                return jsonify({'error': 'Missing payment method'}), 400
            
            # Create payment record (booking_id = 0 as placeholder, update later when linked to actual booking)
            payment = GroupBuyPayment(
                booking_id=0,  # Placeholder - will be updated when booking is created
                campaign_id=campaign_id,
                customer_name=request.form.get('customer_name'),
                customer_email=request.form.get('customer_email'),
                customer_phone=request.form.get('customer_phone'),
                payment_method='stripe',
                payment_status='success',  # Assume success for now
                amount=amount,
                fee_amount=fee_amount,
                total_amount=total_amount,
                stripe_payment_intent_id=payment_method_id
            )
            
            db.session.add(payment)
            db.session.commit()
            
            # ส่งอีเมล์ยืนยัน
            try:
                send_booking_confirmation_email(payment, campaign)
            except Exception as e:
                print(f"Failed to send email: {e}")
            
            return redirect(url_for('group_buy_payment.payment_success', payment_id=payment.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
            return redirect(url_for('group_buy_payment.stripe_payment', campaign_id=campaign_id))
    
    return render_template(
        'group_buy/public/payment_stripe.html',
        campaign=campaign,
        pax_count=pax_count,
        payment_amount=payment_amount,
        amount=amount,
        fee_amount=fee_amount,
        total_amount=total_amount,
        config=current_app.config
    )

@bp.route('/status/<int:payment_id>')
def payment_status(payment_id):
    """ตรวจสอบสถานะการชำระเงิน"""
    payment = GroupBuyPayment.query.get_or_404(payment_id)
    campaign = GroupBuyCampaign.query.get(payment.campaign_id)
    
    return render_template(
        'group_buy/public/payment_status.html',
        payment=payment,
        campaign=campaign
    )

@bp.route('/success/<int:payment_id>')
def payment_success(payment_id):
    """หน้าชำระเงินสำเร็จ"""
    try:
        payment = GroupBuyPayment.query.get_or_404(payment_id)
        campaign = GroupBuyCampaign.query.get(payment.campaign_id)
        
        if not campaign:
            flash('ไม่พบข้อมูลแคมเปญ', 'error')
            return redirect(url_for('public_group_buy.index'))
        
        print(f"Payment success page - Payment ID: {payment_id}, Campaign: {campaign.name}")
        
        return render_template(
            'group_buy/public/payment_success.html',
            payment=payment,
            campaign=campaign
        )
    except Exception as e:
        import traceback
        print(f"Error in payment_success: {e}")
        print(traceback.format_exc())
        flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
        return redirect(url_for('public_group_buy.index'))

def send_booking_confirmation_email(payment, campaign):
    """ส่งอีเมล์ยืนยันการจอง"""
    from flask_mail import Message
    from extensions import mail
    
    try:
        # Prepare email content
        subject = f'ยืนยันการจอง Group Buy - {campaign.name}'
        
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Sarabun', Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; }}
                .section {{ background: white; padding: 20px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .section h3 {{ color: #1e3c72; margin-top: 0; border-bottom: 2px solid #1e3c72; padding-bottom: 10px; }}
                .info-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee; }}
                .info-label {{ font-weight: bold; color: #555; }}
                .info-value {{ color: #333; }}
                .amount {{ font-size: 1.5em; color: #28a745; font-weight: bold; text-align: center; padding: 15px; background: #e8f5e9; border-radius: 8px; }}
                .footer {{ text-align: center; padding: 20px; color: #777; font-size: 0.9em; }}
                .btn {{ display: inline-block; padding: 12px 30px; background: #1e3c72; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 ยืนยันการจอง Group Buy</h1>
                    <p>ขอบคุณที่ใช้บริการของเรา</p>
                </div>
                
                <div class="content">
                    <div class="section">
                        <h3>📋 รายละเอียดการจอง</h3>
                        <div class="info-row">
                            <span class="info-label">แคมเปญ:</span>
                            <span class="info-value">{campaign.name}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">ประเภท:</span>
                            <span class="info-value">{campaign.product_type}</span>
                        </div>
                        {f'<div class="info-row"><span class="info-label">วันเดินทาง:</span><span class="info-value">{campaign.travel_date_from.strftime("%d/%m/%Y")} - {campaign.travel_date_to.strftime("%d/%m/%Y")}</span></div>' if campaign.travel_date_from and campaign.travel_date_to else ''}
                    </div>
                    
                    <div class="section">
                        <h3>✈️ Flights & Hotels (เที่ยวบิน / โรงแรม)</h3>
                        <p style="white-space: pre-line;">{campaign.product_details.replace('<br>', chr(10)).replace('<br/>', chr(10)).replace('<br />', chr(10)) if campaign.product_details else 'ไม่มีข้อมูล'}</p>
                    </div>
                    
                    <div class="section">
                        <h3>📝 Description - รายละเอียด</h3>
                        <p style="white-space: pre-line;">{campaign.description.replace('<br>', chr(10)).replace('<br/>', chr(10)).replace('<br />', chr(10)) if campaign.description else 'ไม่มีข้อมูล'}</p>
                    </div>
                    
                    <div class="section">
                        <h3>💰 ข้อมูลการชำระเงิน</h3>
                        <div class="info-row">
                            <span class="info-label">ชื่อผู้จอง:</span>
                            <span class="info-value">{payment.customer_name}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">อีเมล:</span>
                            <span class="info-value">{payment.customer_email}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">เบอร์โทร:</span>
                            <span class="info-value">{payment.customer_phone}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">วิธีชำระเงิน:</span>
                            <span class="info-value">{payment.payment_method.upper()}</span>
                        </div>
                        <div class="amount">
                            ยอดชำระ: ฿{payment.total_amount:,.2f}
                        </div>
                    </div>
                    
                    <div class="section">
                        <h3>📌 เงื่อนไขและหมายเหตุ</h3>
                        <p style="white-space: pre-line;">{campaign.terms_conditions or 'ไม่มีข้อมูล'}</p>
                    </div>
                    
                    <div style="text-align: center;">
                        <a href="http://localhost:5001/group-buy/campaign/{campaign.id}" class="btn">ดูรายละเอียดเพิ่มเติม</a>
                    </div>
                </div>
                
                <div class="footer">
                    <p>© 2025 Dhakul Chan Nice Holidays. All Rights Reserved.</p>
                    <p>หากมีคำถาม กรุณาติดต่อ: support@dhakulchan.com</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg = Message(
            subject=subject,
            recipients=[payment.customer_email],
            bcc=['support@dhakulchan.com'],
            html=html_body
        )
        
        # แนบไฟล์ slip (ถ้ามี)
        if payment.slip_image:
            try:
                import os
                from flask import current_app
                
                # ตรวจสอบว่าไฟล์มีอยู่จริง
                slip_path = payment.slip_image
                if not slip_path.startswith('/'):
                    # ถ้าเป็น relative path ให้แปลงเป็น absolute
                    slip_path = os.path.join(current_app.root_path, slip_path)
                
                if os.path.exists(slip_path):
                    # อ่านไฟล์
                    with open(slip_path, 'rb') as fp:
                        file_data = fp.read()
                    
                    # กำหนด MIME type ตามนามสกุลไฟล์
                    filename = os.path.basename(slip_path)
                    ext = filename.rsplit('.', 1)[-1].lower()
                    mime_types = {
                        'pdf': 'application/pdf',
                        'png': 'image/png',
                        'jpg': 'image/jpeg',
                        'jpeg': 'image/jpeg'
                    }
                    mime_type = mime_types.get(ext, 'application/octet-stream')
                    
                    # แนบไฟล์
                    msg.attach(
                        filename=f"หลักฐานการโอนเงิน.{ext}",
                        content_type=mime_type,
                        data=file_data
                    )
                    print(f"📎 Attached slip file: {filename}")
                else:
                    print(f"⚠️ Slip file not found: {slip_path}")
            except Exception as e:
                print(f"⚠️ Failed to attach slip file: {e}")
        
        mail.send(msg)
        print(f"✅ Email sent to {payment.customer_email} (BCC: support@dhakulchan.com)")
        
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        raise
