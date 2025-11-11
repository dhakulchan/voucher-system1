from flask import Blueprint, render_template, jsonify
from flask_login import login_required
from models.customer import Customer
from extensions import db
from services.booking_invoice import BookingInvoiceService
from sqlalchemy.exc import IntegrityError

sync_bp = Blueprint('sync', __name__, url_prefix='/sync')

@sync_bp.route('/')
@login_required
def index():
    """Sync dashboard: show counts and quick actions"""
    total = Customer.query.count()
    synced = Customer.query.filter(Customer.invoice_ninja_client_id.isnot(None)).count()
    pending = total - synced
    return render_template('sync/index.html', total=total, synced=synced, pending=pending)

@sync_bp.route('/api/stats')
@login_required
def api_stats():
    total = Customer.query.count()
    synced = Customer.query.filter(Customer.invoice_ninja_client_id.isnot(None)).count()
    pending = total - synced
    return jsonify({'total': total, 'synced': synced, 'pending': pending})

@sync_bp.route('/api/sync-customers')
@login_required
def api_sync_customers():
    """Invoice Ninja integration removed - sync no longer available."""
    return jsonify({'ok': False, 'error': 'invoice_ninja_removed', 'synced_count': 0, 'results': []})
