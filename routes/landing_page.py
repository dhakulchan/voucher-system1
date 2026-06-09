"""Landing Page Routes - Public"""
from flask import Blueprint, render_template, abort, request, redirect, jsonify
from models.landing_product import LandingProduct
from models.landing_page_group import LandingPageGroup, DESTINATION_CHOICES
from sqlalchemy import or_
from datetime import datetime

bp = Blueprint('landing_page', __name__, url_prefix='/landing')

@bp.route('/l/<short_url>')
def short_url_redirect(short_url):
    """Redirect จาก Short URL ไปหน้า Landing Page Group"""
    group = LandingPageGroup.query.filter_by(short_url=short_url, is_active=True).first()
    if not group:
        abort(404)
    return redirect(f'/landing?group={group.slug}')

@bp.route('/')
def index():
    """หน้า Landing Page แสดง Groups และ Products"""
    group_slug = request.args.get('group')
    category = request.args.get('category')
    
    # ถ้าเลือก group
    if group_slug:
        group = LandingPageGroup.query.filter_by(slug=group_slug, is_active=True).first()
        if not group:
            abort(404)
        
        query = LandingProduct.query.filter_by(is_active=True, group_id=group.id)
        
        if category:
            query = query.filter_by(category=category)
        
        products = query.order_by(
            LandingProduct.is_featured.desc(),
            LandingProduct.display_order.asc(),
            LandingProduct.created_at.desc()
        ).all()
        
        # Categories ใน Group นี้
        categories = LandingProduct.query.with_entities(
            LandingProduct.category
        ).filter(
            LandingProduct.is_active == True,
            LandingProduct.group_id == group.id,
            LandingProduct.category.isnot(None)
        ).distinct().all()
        
        return render_template(
            'landing/index.html',
            products=products,
            categories=[c[0] for c in categories],
            current_category=category,
            current_group=group,
            groups=None
        )
    
    # ไม่ได้เลือก group = แสดง Groups ทั้งหมด
    groups = LandingPageGroup.query.filter_by(is_active=True).order_by(
        LandingPageGroup.display_order.asc(),
        LandingPageGroup.start_date.desc()
    ).all()
    
    return render_template(
        'landing/index.html',
        products=None,
        categories=None,
        current_category=None,
        current_group=None,
        groups=groups
    )

@bp.route('/product/<int:product_id>')
def product_detail(product_id):
    """หน้ารายละเอียด Product (redirect ไป external URL)"""
    product = LandingProduct.query.get_or_404(product_id)
    
    if not product.is_active:
        abort(404)
    
    # Redirect ไปยัง external URL
    return redirect(product.external_url)

@bp.route('/groups')
def groups_list():
    """แสดงหน้ารายการ Groups พร้อม Filter/Search"""
    try:
        # รับค่า filter parameters
        search = request.args.get('search', '').strip()
        sort_by = request.args.get('sort', 'display_order')  # display_order, name, date
        cat_filter = request.args.get('cat', '').strip()  # destination category filter
        
        # Base query - แสดงเฉพาะ Groups ที่ active
        now = datetime.now()
        query = LandingPageGroup.query.filter_by(is_active=True)
        
        # Filter: Only show groups within active date range
        query = query.filter(
            or_(
                LandingPageGroup.start_date.is_(None),
                LandingPageGroup.start_date <= now
            )
        ).filter(
            or_(
                LandingPageGroup.end_date.is_(None),
                LandingPageGroup.end_date >= now
            )
        )
        
        # Apply search filter
        if search:
            search_pattern = f'%{search}%'
            query = query.filter(
                or_(
                    LandingPageGroup.name.ilike(search_pattern),
                    LandingPageGroup.description.ilike(search_pattern),
                    LandingPageGroup.slug.ilike(search_pattern)
                )
            )
        
        # Apply destination category filter
        if cat_filter:
            query = query.filter(LandingPageGroup.destination_category == cat_filter)
        
        # Apply sorting
        if sort_by == 'name':
            query = query.order_by(LandingPageGroup.name.asc())
        elif sort_by == 'date':
            query = query.order_by(LandingPageGroup.start_date.desc().nullslast())
        else:  # display_order (default)
            query = query.order_by(
                LandingPageGroup.display_order.asc(),
                LandingPageGroup.created_at.desc()
            )
        
        groups = query.all()
        
        # Get product count for each group
        for group in groups:
            group.active_product_count = group.products.filter_by(is_active=True).count()
        
        # Get all destination categories in use (for filter tabs)
        
        return render_template(
            'landing/groups_list.html',
            groups=groups,
            destination_choices=DESTINATION_CHOICES,
            cat_filter=cat_filter,
            current_filters={
                'search': search,
                'sort': sort_by,
                'cat': cat_filter
            }
        )
    except Exception as e:
        print(f"Error loading groups: {str(e)}")
        import traceback
        traceback.print_exc()
        return render_template('landing/groups_list.html', groups=[], destination_choices=[], cat_filter='', current_filters={})

@bp.route('/groups/<slug>')
def group_detail(slug):
    """แสดงรายละเอียด Group และ Products ภายใน"""
    try:
        group = LandingPageGroup.query.filter_by(slug=slug, is_active=True).first_or_404()
        
        # Check if group is within active date range
        now = datetime.now()
        if group.start_date and now < group.start_date:
            return render_template('landing/group_not_available.html', 
                                   message='กรุ๊ปนี้ยังไม่เปิดให้บริการ')
        if group.end_date and now > group.end_date:
            return render_template('landing/group_not_available.html',
                                   message='กรุ๊ปนี้สิ้นสุดแล้ว')
        
        # Get active products
        products = group.products.filter_by(is_active=True).order_by(
            LandingProduct.display_order.asc()
        ).all()
        
        return render_template(
            'landing/group_detail.html',
            group=group,
            products=products
        )
    except Exception as e:
        print(f"Error loading group detail: {str(e)}")
        import traceback
        traceback.print_exc()
        return render_template('landing/group_not_available.html',
                               message='ไม่พบกรุ๊ปที่ต้องการ'), 404

@bp.route('/api/groups')
def api_groups_list():
    """API สำหรับดึงข้อมูล Groups (JSON) พร้อม Filter"""
    try:
        search = request.args.get('search', '').strip()
        sort_by = request.args.get('sort', 'display_order')
        
        now = datetime.now()
        query = LandingPageGroup.query.filter_by(is_active=True)
        
        # Filter by date range
        query = query.filter(
            or_(
                LandingPageGroup.start_date.is_(None),
                LandingPageGroup.start_date <= now
            )
        ).filter(
            or_(
                LandingPageGroup.end_date.is_(None),
                LandingPageGroup.end_date >= now
            )
        )
        
        # Apply search
        if search:
            search_pattern = f'%{search}%'
            query = query.filter(
                or_(
                    LandingPageGroup.name.ilike(search_pattern),
                    LandingPageGroup.description.ilike(search_pattern)
                )
            )
        
        # Apply sorting
        if sort_by == 'name':
            query = query.order_by(LandingPageGroup.name.asc())
        elif sort_by == 'date':
            query = query.order_by(LandingPageGroup.start_date.desc().nullslast())
        else:
            query = query.order_by(
                LandingPageGroup.display_order.asc(),
                LandingPageGroup.created_at.desc()
            )
        
        groups = query.all()
        
        # Build response
        data = []
        for group in groups:
            product_count = group.products.filter_by(is_active=True).count()
            data.append({
                'id': group.id,
                'name': group.name,
                'slug': group.slug,
                'short_url': group.short_url,
                'description': group.description,
                'banner_image': group.banner_image,
                'theme_color': group.theme_color,
                'product_count': product_count,
                'start_date': group.start_date.isoformat() if group.start_date else None,
                'end_date': group.end_date.isoformat() if group.end_date else None,
                'url': f'/landing/groups/{group.slug}'
            })
        
        return jsonify({
            'success': True,
            'count': len(data),
            'data': data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
