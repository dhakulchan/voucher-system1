from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from extensions import db
from models.vendor import Supplier

supplier_bp = Blueprint('supplier', __name__, url_prefix='/supplier')

@supplier_bp.route('/list')
@login_required
def list_():
    q = (request.args.get('q') or '').strip()
    base = Supplier.query
    if q:
        like = f"%{q}%"
        base = base.filter(db.or_(Supplier.name.ilike(like), Supplier.contact_name.ilike(like), Supplier.phone.ilike(like)))
    suppliers = base.order_by(Supplier.active.desc(), Supplier.name.asc()).all()
    return render_template('supplier/list.html', suppliers=suppliers, q=q)

@supplier_bp.route('/new', methods=['GET','POST'])
@login_required
def new():
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        contact = (request.form.get('contact_name') or '').strip()
        phone = (request.form.get('phone') or '').strip()
        email = (request.form.get('email') or '').strip()
        if not name:
            flash('Name is required', 'warning')
        else:
            s = Supplier(name=name, contact_name=contact, phone=phone, email=email, active=True)
            # Optional extended real_* fields
            s.real_name = (request.form.get('real_name') or '').strip()
            s.real_tel = (request.form.get('real_tel') or '').strip()
            s.real_fax = (request.form.get('real_fax') or '').strip()
            s.real_email = (request.form.get('real_email') or '').strip()
            s.real_group_email = (request.form.get('real_group_email') or '').strip()
            s.address = (request.form.get('address') or '').strip()
            s.notes = (request.form.get('notes') or '').strip()
            s.memos = (request.form.get('memos') or '').strip()
            s.remarks = (request.form.get('remarks') or '').strip()
            db.session.add(s)
            db.session.commit()
            flash('Supplier created', 'success')
            return redirect(url_for('supplier.list_'))
    return render_template('supplier/new.html')

@supplier_bp.route('/<int:id>/edit', methods=['GET','POST'])
@login_required
def edit(id):
    s = Supplier.query.get_or_404(id)
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        if not name:
            flash('Name is required', 'warning')
        else:
            s.name = name
            s.contact_name = (request.form.get('contact_name') or '').strip()
            s.phone = (request.form.get('phone') or '').strip()
            s.email = (request.form.get('email') or '').strip()
            s.real_name = (request.form.get('real_name') or '').strip()
            s.real_tel = (request.form.get('real_tel') or '').strip()
            s.real_fax = (request.form.get('real_fax') or '').strip()
            s.real_email = (request.form.get('real_email') or '').strip()
            s.real_group_email = (request.form.get('real_group_email') or '').strip()
            s.address = (request.form.get('address') or '').strip()
            s.notes = (request.form.get('notes') or '').strip()
            s.memos = (request.form.get('memos') or '').strip()
            s.remarks = (request.form.get('remarks') or '').strip()
            db.session.commit()
            flash('Supplier updated', 'success')
            return redirect(url_for('supplier.list_'))
    return render_template('supplier/edit.html', s=s)

@supplier_bp.route('/<int:id>/toggle', methods=['POST'])
@login_required
def toggle(id):
    s = Supplier.query.get_or_404(id)
    s.active = not s.active
    db.session.commit()
    return jsonify({'success': True, 'active': s.active})

@supplier_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def soft_delete(id):
    s = Supplier.query.get_or_404(id)
    s.active = False
    if s.notes:
        if '[DELETED]' not in s.notes:
            s.notes = '[DELETED] ' + s.notes
    else:
        s.notes = '[DELETED]'
    db.session.commit()
    return jsonify({'success': True})

@supplier_bp.route('/api/list')
@login_required
def api_list():
    """Return active suppliers with full details (id, name, address, phone, notes). Optional q filter."""
    q = (request.args.get('q') or '').strip()
    query = Supplier.query.filter_by(active=True)
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Supplier.name.ilike(like), Supplier.contact_name.ilike(like)))
    suppliers = query.order_by(Supplier.name.asc()).limit(500).all()
    
    supplier_list = []
    for s in suppliers:
        supplier_list.append({
            'id': s.id, 
            'name': s.name,
            'address': s.address or '',
            'phone': s.phone or '',
            'notes': s.notes or ''
        })
    
    return jsonify({'suppliers': supplier_list})

@supplier_bp.route('/api/create', methods=['POST'])
@login_required
def api_create():
    """Create a supplier (inline JSON). Returns new supplier id & name."""
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'success': False, 'message': 'Name is required'}), 400
    s = Supplier(
        name=name,
        contact_name=(data.get('contact_name') or '').strip(),
        phone=(data.get('phone') or '').strip(),
        email=(data.get('email') or '').strip(),
        real_group_email=(data.get('real_group_email') or '').strip(),
        active=True
    )
    db.session.add(s)
    db.session.commit()
    return jsonify({'success': True, 'supplier': {'id': s.id, 'name': s.name}})
