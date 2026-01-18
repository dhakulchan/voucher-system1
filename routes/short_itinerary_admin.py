"""
Short Itinerary Admin Routes
CRUD operations for managing short itinerary templates
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app import db
from models.short_itinerary import ShortItinerary
from functools import wraps
from flask_login import current_user, login_required

short_itinerary_admin = Blueprint('short_itinerary_admin', __name__, url_prefix='/admin/short-itinerary')

def admin_required(f):
    """Decorator to require admin access (Admin, Manager, Operation)"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.has_role('Administrator', 'Manager', 'Operation'):
            flash('⛔ Access denied. Administrator, Manager, or Operation privileges required.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def view_required(f):
    """Decorator for view access (all authenticated users)"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function

@short_itinerary_admin.route('/')
@view_required
def list_itineraries():
    """List all short itineraries with search and pagination"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    per_page = 20
    
    if search:
        pagination = ShortItinerary.search(search, page=page, per_page=per_page)
    else:
        pagination = ShortItinerary.query.order_by(ShortItinerary.program_name)\
            .paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('short_itinerary/list.html', 
                         pagination=pagination,
                         search=search)

@short_itinerary_admin.route('/create', methods=['GET', 'POST'])
@admin_required
def create_itinerary():
    """Create new short itinerary"""
    if request.method == 'POST':
        try:
            itinerary = ShortItinerary(
                program_name=request.form.get('program_name', '').strip(),
                tour_code=request.form.get('tour_code', '').strip() or None,
                description=request.form.get('description', '').strip() or None,
                adult_twin_sharing=float(request.form.get('adult_twin_sharing', 0) or 0),
                adult_single=float(request.form.get('adult_single', 0) or 0),
                child_extra_bed=float(request.form.get('child_extra_bed', 0) or 0),
                child_no_bed=float(request.form.get('child_no_bed', 0) or 0),
                infant=float(request.form.get('infant', 0) or 0),
                notes=request.form.get('notes', '').strip() or None
            )
            
            if not itinerary.program_name:
                flash('⚠️ Program Name is required', 'warning')
                return render_template('short_itinerary/create.html')
            
            db.session.add(itinerary)
            db.session.commit()
            
            flash(f'✅ Short itinerary "{itinerary.program_name}" created successfully!', 'success')
            return redirect(url_for('short_itinerary_admin.list_itineraries'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Error creating itinerary: {str(e)}', 'danger')
            return render_template('short_itinerary/create.html')
    
    return render_template('short_itinerary/create.html')

@short_itinerary_admin.route('/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_itinerary(id):
    """Edit existing short itinerary"""
    itinerary = ShortItinerary.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            itinerary.program_name = request.form.get('program_name', '').strip()
            itinerary.tour_code = request.form.get('tour_code', '').strip() or None
            itinerary.product_link = request.form.get('product_link', '').strip() or None
            itinerary.description = request.form.get('description', '').strip() or None
            itinerary.adult_twin_sharing = float(request.form.get('adult_twin_sharing', 0) or 0)
            itinerary.adult_single = float(request.form.get('adult_single', 0) or 0)
            itinerary.child_extra_bed = float(request.form.get('child_extra_bed', 0) or 0)
            itinerary.child_no_bed = float(request.form.get('child_no_bed', 0) or 0)
            itinerary.infant = float(request.form.get('infant', 0) or 0)
            itinerary.notes = request.form.get('notes', '').strip() or None
            
            if not itinerary.program_name:
                flash('⚠️ Program Name is required', 'warning')
                return render_template('short_itinerary/edit.html', itinerary=itinerary)
            
            db.session.commit()
            
            flash(f'✅ Short itinerary "{itinerary.program_name}" updated successfully!', 'success')
            return redirect(url_for('short_itinerary_admin.list_itineraries'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Error updating itinerary: {str(e)}', 'danger')
            return render_template('short_itinerary/edit.html', itinerary=itinerary)
    
    return render_template('short_itinerary/edit.html', itinerary=itinerary)

@short_itinerary_admin.route('/delete/<int:id>', methods=['POST'])
@admin_required
def delete_itinerary(id):
    """Delete short itinerary"""
    try:
        itinerary = ShortItinerary.query.get_or_404(id)
        program_name = itinerary.program_name
        
        db.session.delete(itinerary)
        db.session.commit()
        
        flash(f'✅ Short itinerary "{program_name}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Error deleting itinerary: {str(e)}', 'danger')
    
    return redirect(url_for('short_itinerary_admin.list_itineraries'))

@short_itinerary_admin.route('/api/search', methods=['GET'])
@login_required
def api_search():
    """API endpoint for searching itineraries (for modal selection)"""
    query = request.args.get('q', '', type=str)
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    if query:
        pagination = ShortItinerary.search(query, page=page, per_page=per_page)
    else:
        pagination = ShortItinerary.query.order_by(ShortItinerary.program_name)\
            .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'items': [item.to_dict() for item in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev
    })

@short_itinerary_admin.route('/api/format/<int:id>', methods=['GET'])
@login_required
def api_format(id):
    """API endpoint to get formatted itinerary text"""
    itinerary = ShortItinerary.query.get_or_404(id)
    return jsonify({
        'formatted_text': itinerary.format_for_booking()
    })
