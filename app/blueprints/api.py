"""
REST API endpoints (session-authenticated).
"""
from datetime import datetime
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from sqlalchemy import or_
from app import db
from app.models import CallLog, User
from app.utils.decorators import login_required_active, agent_required
from app.utils.helpers import get_dashboard_stats, log_activity

api_bp = Blueprint('api', __name__)


@api_bp.route('/dashboard/stats')
@login_required
@login_required_active
def dashboard_stats():
    stats = get_dashboard_stats(user=current_user)
    # JSON-safe subset
    return jsonify({
        'total_calls': stats['total_calls'],
        'open_calls': stats['open_calls'],
        'resolved_today': stats['resolved_today'],
        'high_priority': stats['high_priority'],
        'unassigned': stats['unassigned'],
        'my_open': stats['my_open'],
        'sla_breach': stats['sla_breach'],
        'sla_warn': stats['sla_warn'],
        'status_counts': stats['status_counts'],
        'calls_per_day': stats['calls_per_day'],
        'dept_counts': stats['dept_counts'],
        'workload': stats['workload'],
    })


@api_bp.route('/search')
@login_required
@login_required_active
def global_search():
    """Command-palette / typeahead search across calls and agents."""
    q = (request.args.get('q') or '').strip()
    if len(q) < 1:
        return jsonify(calls=[], users=[])
    like = f'%{q}%'
    call_q = CallLog.query.filter(or_(
        CallLog.CallerName.ilike(like),
        CallLog.PhoneNumber.ilike(like),
        CallLog.ReasonForCall.ilike(like),
    ))
    try:
        cid = int(q)
        call_q = CallLog.query.filter(or_(
            CallLog.CallID == cid,
            CallLog.CallerName.ilike(like),
            CallLog.PhoneNumber.ilike(like),
        ))
    except ValueError:
        pass
    calls = call_q.order_by(CallLog.DateLogged.desc()).limit(8).all()
    users = User.query.filter(
        User.IsActive == True,
        or_(User.FullName.ilike(like), User.Username.ilike(like))
    ).limit(5).all()
    return jsonify({
        'calls': [
            {
                'id': c.CallID,
                'caller': c.CallerName,
                'phone': c.PhoneNumber,
                'status': c.Status,
                'priority': c.Priority,
                'url': f'/calls/{c.CallID}',
            }
            for c in calls
        ],
        'users': [
            {'id': u.UserID, 'name': u.FullName, 'role': u.Role}
            for u in users
        ],
    })


@api_bp.route('/calls')
@login_required
@login_required_active
def list_calls_api():
    status = request.args.get('status')
    q = CallLog.query.order_by(CallLog.DateLogged.desc())
    if status:
        q = q.filter(CallLog.Status == status)
    calls = q.limit(50).all()
    return jsonify([
        {
            'id': c.CallID,
            'caller': c.CallerName,
            'phone': c.PhoneNumber,
            'status': c.Status,
            'priority': c.Priority,
            'department': c.Department,
            'assigned_to': c.AssignedTo,
        }
        for c in calls
    ])


@api_bp.route('/calls', methods=['POST'])
@login_required
@login_required_active
@agent_required
def create_call_api():
    data = request.get_json(silent=True) or {}
    required = ['caller_name', 'phone_number', 'reason_for_call', 'call_type']
    for k in required:
        if not data.get(k):
            return jsonify(ok=False, error=f'Missing {k}'), 400
    call = CallLog(
        CallerName=str(data['caller_name']).strip(),
        PhoneNumber=str(data['phone_number']).strip(),
        Department=data.get('department') or None,
        CallType=data.get('call_type', 'Incoming'),
        ReasonForCall=str(data['reason_for_call']).strip(),
        Priority=data.get('priority') or 'Medium',
        Status='Open',
        AssignedTo=data.get('assigned_to') or None,
        Notes=data.get('notes'),
    )
    db.session.add(call)
    db.session.flush()
    log_activity(call.CallID, current_user.UserID, 'Created', 'Via API')
    db.session.commit()
    return jsonify(ok=True, id=call.CallID), 201


@api_bp.route('/calls/<int:call_id>')
@login_required
@login_required_active
def get_call_api(call_id):
    c = CallLog.query.get_or_404(call_id)
    return jsonify({
        'id': c.CallID,
        'caller': c.CallerName,
        'phone': c.PhoneNumber,
        'status': c.Status,
        'priority': c.Priority,
        'department': c.Department,
        'reason': c.ReasonForCall,
        'resolution': c.Resolution,
        'assigned_to': c.AssignedTo,
        'assignee': c.assignee.FullName if c.assignee else None,
        'date_logged': c.DateLogged.isoformat() if c.DateLogged else None,
    })


@api_bp.route('/calls/<int:call_id>', methods=['PUT', 'PATCH'])
@login_required
@login_required_active
@agent_required
def update_call_api(call_id):
    c = CallLog.query.get_or_404(call_id)
    data = request.get_json(silent=True) or {}
    if 'status' in data and data['status']:
        old = c.Status
        c.Status = data['status']
        log_activity(c.CallID, current_user.UserID, 'Updated', f'Status {old} → {c.Status} (API)')
    if 'priority' in data and data['priority']:
        c.Priority = data['priority']
    if 'resolution' in data:
        c.Resolution = data['resolution']
    if 'assigned_to' in data:
        c.AssignedTo = data['assigned_to'] or None
    c.LastUpdated = datetime.utcnow()
    db.session.commit()
    return jsonify(ok=True)


@api_bp.route('/users')
@login_required
@login_required_active
def list_users_api():
    users = User.query.filter(User.IsActive == True).order_by(User.FullName).all()
    return jsonify([
        {'id': u.UserID, 'name': u.FullName, 'role': u.Role, 'username': u.Username}
        for u in users
    ])


@api_bp.route('/reports/daily')
@login_required
@login_required_active
def daily_report_api():
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    count = CallLog.query.filter(CallLog.DateLogged >= today).count()
    return jsonify({'date': today.date().isoformat(), 'calls_logged': count})


@api_bp.route('/phone-lookup')
@login_required
@login_required_active
def phone_lookup():
    """Duplicate / history check when logging a call."""
    phone = (request.args.get('phone') or '').strip()
    if len(phone) < 5:
        return jsonify(matches=[])
    matches = (
        CallLog.query.filter(CallLog.PhoneNumber.ilike(f'%{phone}%'))
        .order_by(CallLog.DateLogged.desc())
        .limit(5)
        .all()
    )
    return jsonify({
        'matches': [
            {
                'id': c.CallID,
                'caller': c.CallerName,
                'status': c.Status,
                'date': c.DateLogged.strftime('%Y-%m-%d') if c.DateLogged else '',
                'reason': (c.ReasonForCall or '')[:80],
            }
            for c in matches
        ]
    })
