from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from utils.logging_config import get_logger
from flask_login import login_required
from extensions import db
from models.customer import Customer
from sqlalchemy import or_

customer_bp = Blueprint('customer', __name__)
logger = get_logger(__name__)

@customer_bp.route('/view/<int:id>')
@login_required
def view(id):
    customer = Customer.query.get_or_404(id)
    return render_template('customer/view.html', customer=customer)

@customer_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    customer = Customer.query.get_or_404(id)
    if request.method == 'POST':
        try:
            customer.first_name = request.form.get('first_name') or customer.first_name
            customer.last_name = request.form.get('last_name') or customer.last_name
            customer.email = request.form.get('email') or customer.email
            customer.phone = request.form.get('phone') or customer.phone
            customer.nationality = request.form.get('nationality') or customer.nationality
            customer.address = request.form.get('address') or customer.address
            customer.notes = request.form.get('notes') or customer.notes
            customer.sync_name()

            # Invoice Ninja integration removed - skip client linking

            db.session.commit()
            flash('อัปเดตข้อมูลลูกค้าเรียบร้อย', 'success')
            return redirect(url_for('customer.view', id=customer.id))
        except Exception as e:
            db.session.rollback()
            flash(f'เกิดข้อผิดพลาด: {e}', 'error')
    return render_template('customer/edit.html', customer=customer)

@customer_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        try:
            email = (request.form.get('email') or '').strip()
            # Check duplicate locally by email
            if email:
                exists_local = Customer.query.filter(Customer.email.ilike(email)).first()
                if exists_local:
                    flash('มีลูกค้าด้วยอีเมลนี้อยู่แล้ว เชื่อมโยงระเบียนเดิมแทน', 'warning')
                    return redirect(url_for('customer.view', id=exists_local.id))

            c = Customer(
                first_name=request.form.get('first_name'),
                last_name=request.form.get('last_name'),
                email=email,
                phone=request.form.get('phone'),
                nationality=request.form.get('nationality'),
                address=request.form.get('address'),
                notes=request.form.get('notes'),
                name=''  # set then sync
            )
            c.sync_name()

            # Invoice Ninja integration removed - skip client creation

            db.session.add(c)
            db.session.commit()
            flash('เพิ่มลูกค้าใหม่สำเร็จ', 'success')
            return redirect(url_for('customer.view', id=c.id))
        except Exception as e:
            db.session.rollback()
            flash(f'เกิดข้อผิดพลาด: {e}', 'error')
    return render_template('customer/create.html')

@customer_bp.route('/api/check_duplicate')
@login_required
def api_check_duplicate():
    """API endpoint to check for duplicate customers"""
    email = request.args.get('email', '').strip()
    if not email:
        return jsonify({'ok': False})
    
    # Check local database
    local_customer = Customer.query.filter(Customer.email.ilike(email)).first()
    
    # Invoice Ninja integration removed
    
    return jsonify({
        'ok': True,
        'local': {
            'id': local_customer.id,
            'name': local_customer.name
        } if local_customer else None,
        'invoice_ninja': None  # Integration removed
    })

@customer_bp.route('/list')
@login_required  
def list():
    """Customer list page"""
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    query = Customer.query
    
    if search:
        search_filter = or_(
            Customer.name.ilike(f'%{search}%'),
            Customer.email.ilike(f'%{search}%'),
            Customer.phone.ilike(f'%{search}%'),
            Customer.nationality.ilike(f'%{search}%')
        )
        query = query.filter(search_filter)
    
    # Use ID instead of created_at to avoid datetime conversion issues
    try:
        customers = query.order_by(Customer.id.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Error fetching customers: {e}")
        customers = query.order_by(Customer.id.desc()).paginate(
            page=1, per_page=per_page, error_out=False
        )
    
    return render_template('customer/list.html', customers=customers, search=search)

@customer_bp.route('/api/search')
@login_required
def api_search():
    """API endpoint for customer autocomplete (local first, fallback to Invoice Ninja)"""
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify([])
    
    # Local search
    local_customers = Customer.query.filter(
        or_(
            Customer.name.ilike(f'%{query}%'),
            Customer.email.ilike(f'%{query}%'),
            Customer.phone.ilike(f'%{query}%')
        )
    ).limit(10).all()
    
    results = []
    for customer in local_customers:
        results.append({
            'id': customer.id,
            'name': customer.name,
            'email': customer.email,
            'phone': customer.phone,
            'nationality': customer.nationality or '',
            'label': f"{customer.name} ({customer.email})" if customer.email else customer.name,
            'value': customer.name,
            'is_remote': False
        })

    # Invoice Ninja integration removed
    # Only showing local results
    
    return jsonify(results)

@customer_bp.route('/api/import-invoice-ninja-client', methods=['POST'])
@login_required
def api_import_invoice_ninja_client():
    """Import or link an Invoice Ninja client as a local Customer"""
    data = request.get_json(silent=True) or {}
    client_id = data.get('client_id') or request.form.get('client_id')
    if not client_id:
        return jsonify({'ok': False, 'error': 'missing_client_id'}), 400

    # Invoice Ninja integration removed
    return jsonify({'ok': False, 'error': 'invoice_ninja_removed'}), 400
