from flask import Blueprint, request, jsonify, render_template, current_app
from flask_login import login_required
from datetime import date
from utils.datetime_utils import utc_now
from extensions import db
from models.queue import QueueSession, QueueTicket

queue_bp = Blueprint('queue', __name__, url_prefix='/queue')

_QUEUE_LIMIT_MAX = 30
_QUEUE_LIMIT_WINDOW = 60
_QUEUE_REDIS_PREFIX = 'queue_rate:'

def _get_redis():
    try:
        import redis  # type: ignore
        url = current_app.config.get('REDIS_URL') or 'redis://localhost:6379/0'
        return redis.Redis.from_url(url)
    except Exception:
        return None

_MEM_BUCKET = {}

def _rate_limit(ip: str) -> bool:
    import time
    r = _get_redis()
    if r:
        key = f"{_QUEUE_REDIS_PREFIX}{ip}"
        with r.pipeline() as pipe:
            try:
                pipe.zremrangebyscore(key, 0, time.time() - _QUEUE_LIMIT_WINDOW)
                pipe.zadd(key, {str(time.time()): time.time()})
                pipe.zcard(key)
                pipe.expire(key, _QUEUE_LIMIT_WINDOW)
                _, _, count, _ = pipe.execute()
                return count <= _QUEUE_LIMIT_MAX
            except Exception:
                pass
    # Fallback memory
    now = time.time()
    bucket = _MEM_BUCKET.setdefault(ip, [])
    cutoff = now - _QUEUE_LIMIT_WINDOW
    while bucket and bucket[0] < cutoff:
        bucket.pop(0)
    if len(bucket) >= _QUEUE_LIMIT_MAX:
        return False
    bucket.append(now)
    return True

def _get_or_create_session(channel: str) -> QueueSession:
    today = date.today()
    session = QueueSession.query.filter_by(channel=channel, session_date=today).with_for_update(of=QueueSession).first()
    if not session:
        session = QueueSession(channel=channel, session_date=today, last_number=0)
        db.session.add(session)
        db.session.flush()
    return session

@queue_bp.route('/new', methods=['POST'])
def new_ticket():
    data = request.get_json() or {}
    channel = data.get('channel', 'default')
    service_type = data.get('service_type')
    customer_name = data.get('customer_name')
    phone = data.get('phone')
    ip = request.headers.get('X-Forwarded-For', request.remote_addr or 'unknown').split(',')[0].strip()
    if not _rate_limit(ip):
        return jsonify({'success': False, 'message': 'Rate limit exceeded'}), 429
    session = _get_or_create_session(channel)
    number = session.next_number()
    display_code = f"{channel[:2].upper()}{number:03d}" if channel != 'default' else f"Q{number:03d}"
    ticket = QueueTicket(session_id=session.id, number=number, display_code=display_code, service_type=service_type, customer_name=customer_name, phone=phone)
    db.session.add(ticket)
    db.session.commit()
    return jsonify({'success': True, 'ticket': ticket.to_dict()})

@queue_bp.route('/next', methods=['POST'])
@login_required
def next_ticket():
    data = request.get_json() or {}
    channel = data.get('channel', 'default')
    ticket = QueueTicket.query.join(QueueSession).filter(QueueSession.channel==channel, QueueSession.session_date==date.today(), QueueTicket.status=='waiting').order_by(QueueTicket.number.asc()).first()
    if not ticket:
        return jsonify({'success': False, 'message': 'No waiting'}), 404
    ticket.status = 'calling'
    ticket.called_at = utc_now()
    db.session.commit()
    return jsonify({'success': True, 'ticket': ticket.to_dict()})

@queue_bp.route('/ticket/<int:tid>/status', methods=['POST'])
@login_required
def update_ticket_status(tid):
    ticket = QueueTicket.query.get_or_404(tid)
    data = request.get_json() or {}
    new_status = data.get('status')
    valid = {'waiting','calling','serving','done','canceled'}
    if new_status not in valid:
        return jsonify({'success': False, 'message': 'Invalid status'}), 400
    ticket.status = new_status
    now = utc_now()
    if new_status == 'serving' and not ticket.started_at:
        ticket.started_at = now
    if new_status in {'done','canceled'} and not ticket.finished_at:
        ticket.finished_at = now
    db.session.commit()
    return jsonify({'success': True, 'ticket': ticket.to_dict()})

@queue_bp.route('/status', methods=['GET'])
def queue_status():
    channel = request.args.get('channel','default')
    session = QueueSession.query.filter_by(channel=channel, session_date=date.today()).first()
    if not session:
        return jsonify({'success': True, 'tickets': [], 'last_number': 0})
    tickets = [t.to_dict() for t in session.tickets.order_by(QueueTicket.number.asc()).limit(200)]
    return jsonify({'success': True, 'last_number': session.last_number, 'tickets': tickets})

@queue_bp.route('/display')
def display_queue():
    """HTML view polling queue status."""
    channel = request.args.get('channel','default')
    return render_template('queue/display.html', channel=channel)
