"""
Flight Template Admin Routes
Manage flight templates for quick booking creation
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models.flight_template import FlightTemplate
from app import db
from functools import wraps
from flask_login import current_user, login_required

flight_template_admin = Blueprint('flight_template_admin', __name__, url_prefix='/admin/flight-template')

def admin_required(f):
    """Decorator to require admin access (Admin, Manager, Operation)"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.has_role('Administrator', 'Manager', 'Operation'):
            flash('⛔ Access denied. Administrator, Manager, or Operation privileges required.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function

def view_required(f):
    """Decorator for view access (all authenticated users)"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function

@flight_template_admin.route('/')
@view_required
def list_templates():
    """List all flight templates with pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '', type=str)
    
    if search:
        pagination = FlightTemplate.search(search, page=page, per_page=per_page)
    else:
        pagination = FlightTemplate.query.order_by(FlightTemplate.template_name)\
            .paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('flight_template/list.html', 
                         pagination=pagination, 
                         search=search)

@flight_template_admin.route('/create', methods=['GET', 'POST'])
@admin_required
def create_template():
    """Create new flight template"""
    if request.method == 'POST':
        try:
            template = FlightTemplate(
                template_name=request.form.get('template_name', '').strip(),
                date=request.form.get('date', '').strip() or None,
                flight_no=request.form.get('flight_no', '').strip() or None,
                from_to=request.form.get('from_to', '').strip() or None,
                time=request.form.get('time', '').strip() or None,
                note=request.form.get('note', '').strip() or None
            )
            
            if not template.template_name:
                flash('⚠️ Template Name is required', 'warning')
                return render_template('flight_template/create.html')
            
            db.session.add(template)
            db.session.commit()
            
            flash(f'✅ Flight template "{template.template_name}" created successfully!', 'success')
            return redirect(url_for('flight_template_admin.list_templates'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Error creating template: {str(e)}', 'danger')
            return render_template('flight_template/create.html')
    
    return render_template('flight_template/create.html')

@flight_template_admin.route('/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_template(id):
    """Edit existing flight template"""
    template = FlightTemplate.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            template.template_name = request.form.get('template_name', '').strip()
            template.date = request.form.get('date', '').strip() or None
            template.flight_no = request.form.get('flight_no', '').strip() or None
            template.from_to = request.form.get('from_to', '').strip() or None
            template.time = request.form.get('time', '').strip() or None
            template.note = request.form.get('note', '').strip() or None
            
            if not template.template_name:
                flash('⚠️ Template Name is required', 'warning')
                return render_template('flight_template/edit.html', template=template)
            
            db.session.commit()
            
            flash(f'✅ Flight template "{template.template_name}" updated successfully!', 'success')
            return redirect(url_for('flight_template_admin.list_templates'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Error updating template: {str(e)}', 'danger')
            return render_template('flight_template/edit.html', template=template)
    
    return render_template('flight_template/edit.html', template=template)

@flight_template_admin.route('/delete/<int:id>', methods=['POST'])
@admin_required
def delete_template(id):
    """Delete flight template"""
    template = FlightTemplate.query.get_or_404(id)
    
    try:
        template_name = template.template_name
        db.session.delete(template)
        db.session.commit()
        flash(f'✅ Flight template "{template_name}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Error deleting template: {str(e)}', 'danger')
    
    return redirect(url_for('flight_template_admin.list_templates'))

@flight_template_admin.route('/api/search')
@view_required
def api_search():
    """API endpoint for searching flight templates"""
    query = request.args.get('q', '', type=str)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    if query:
        pagination = FlightTemplate.search(query, page=page, per_page=per_page)
    else:
        pagination = FlightTemplate.query.order_by(FlightTemplate.template_name)\
            .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'items': [item.to_dict() for item in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': pagination.page
    })
