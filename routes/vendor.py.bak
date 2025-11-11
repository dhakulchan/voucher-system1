from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from extensions import db
from models.vendor import Vendor

vendor_bp = Blueprint('vendor', __name__, url_prefix='/vendor')

@vendor_bp.route('/')
@login_required
def list():
    vendors = Vendor.query.order_by(Vendor.name).all()
    return render_template('vendor/list.html', vendors=vendors)

@vendor_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        try:
            v = Vendor(
                name=request.form.get('name'),
                contact_name=request.form.get('contact_name'),
                phone=request.form.get('phone'),
                email=request.form.get('email'),
                address=request.form.get('address'),
                notes=request.form.get('notes'),
                active=bool(request.form.get('active'))
            )
            db.session.add(v)
            db.session.commit()
            flash('Vendor created', 'success')
            return redirect(url_for('vendor.list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {e}', 'error')
    return render_template('vendor/create.html')

@vendor_bp.route('/edit/<int:id>', methods=['GET','POST'])
@login_required
def edit(id):
    v = Vendor.query.get_or_404(id)
    if request.method == 'POST':
        try:
            v.name = request.form.get('name')
            v.contact_name = request.form.get('contact_name')
            v.phone = request.form.get('phone')
            v.email = request.form.get('email')
            v.address = request.form.get('address')
            v.notes = request.form.get('notes')
            v.active = bool(request.form.get('active'))
            db.session.commit()
            flash('Vendor updated', 'success')
            return redirect(url_for('vendor.list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {e}', 'error')
    return render_template('vendor/edit.html', vendor=v)

@vendor_bp.route('/toggle/<int:id>', methods=['POST'])
@login_required
def toggle(id):
    v = Vendor.query.get_or_404(id)
    v.active = not v.active
    db.session.commit()
    return redirect(url_for('vendor.list'))
