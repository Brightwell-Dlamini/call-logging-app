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
from app.utils.helpers import get_dashboard_stats, log_activity, get_recent_activity, sla_risk

api_bp = Blueprint('api', __name__)

VALID_STATUS = frozenset({'Open', 'In Progress', 'Pending', 'Resolved', 'Closed'})
VALID_PRIORITY = frozenset({'Low', 'Medium', 'High', 'Critical'})
VALID_CALL_TYPE = frozenset({'Incoming', 'Outgoing'})
MAX_PAGE_SIZE = 100


def api_error(message, status=400, **extra):
    payload = {'ok': False, 'error': message}
    payload.update(extra)
    return jsonify(payload), status


def serialize_call(c, detail=False):
    data = {
        'id': c.CallID,
        'caller': c.CallerName,
        'phone': c.PhoneNumber,
        'status': c.Status,
        'priority': c.Priority,
        'department': c.Department,
        'assigned_to': c.AssignedTo,
        'sla': sla_risk(c),
    }
    if detail:
        data.update({
            'reason': c.ReasonForCall,
            'resolution': c.Resolution,
            'notes': c.Notes,
            'call_type': c.CallType,
            'assignee': c.assignee.FullName if c.assignee else None,
            'date_logged': c.DateLogged.isoformat() if c.DateLogged else None,
            'last_updated': c.LastUpdated.isoformat() if c.LastUpdated else None,
            'time_spent': c.TimeSpent,
            'satisfaction': c.SatisfactionRating,
        })
    return data


def _page_args():
    try:
        page = max(int(request.args.get('page', 1)), 1)
    except (TypeError, ValueError):
        page = 1
    try:
        per_page = int(request.args.get('per_page', 50))
    except (TypeError, ValueError):
        per_page = 50
    per_page = min(max(per_page, 1), MAX_PAGE_SIZE)
    return page, per_page


@api_bp.route('/dashboard/stats')
@login_required
@login_required_active
def dashboard_stats():
    stats = get_dashboard_stats(user=current_user)
    return jsonify({
        'ok': True,
        'total_calls': stats['total_calls'],
        'open_calls': stats['open_calls'],
        'resolved_today': stats['resolved_today'],
        'high_priority': stats['high_priority'],
        'unassigned': stats['unassigned'],
        'my_open': stats['my_open'],
        'sla_breach': stats['sla_breach'],
        'sla_warn': stats['sla_warn'],
        'avg_satisfaction': stats.get('avg_satisfaction'),
        'avg_handle_mins': stats.get('avg_handle_mins'),
        'status_counts': stats['status_counts'],
        'calls_per_day': stats['calls_per_day'],
        'dept_counts': stats['dept_counts'],
        'workload': stats['workload'],
    })


@api_bp.route('/notifications')
@login_required
@login_required_active
def notifications():
    items = get_recent_activity(15)
    out = []
    for a in items:
        out.append({
            'id': a['id'],
            'title': f"{a['user']} · {a['action']}",
            'body': f"#{a['call_id']} {a['caller']}".strip(),
            'url': f"/calls/{a['call_id']}",
            'when': a['when'].isoformat() if a['when'] else None,
        })
    return jsonify({'ok': True, 'items': out, 'count': len(out)})


@api_bp.route('/search')
@login_required
@login_required_active
def global_search():
    q = (request.args.get('q') or '').strip()[:120]
    if len(q) < 1:
        return jsonify(ok=True, calls=[], users=[])
    like = f'%{q}%'
    filters = [
        CallLog.CallerName.ilike(like),
        CallLog.PhoneNumber.ilike(like),
        CallLog.ReasonForCall.ilike(like),
    ]
    try:
        filters.append(CallLog.CallID == int(q))
    except ValueError:
        pass
    calls = (
        CallLog.query.filter(or_(*filters))
        .order_by(CallLog.DateLogged.desc())
        .limit(8)
        .all()
    )
    users = User.query.filter(
        User.IsActive == True,
        or_(User.FullName.ilike(like), User.Username.ilike(like))
    ).limit(5).all()
    return jsonify({
        'ok': True,
        'calls': [serialize_call(c) | {'url': f'/calls/{c.CallID}'} for c in calls],
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
    if status and status not in VALID_STATUS:
        return api_error('Invalid status', 400, allowed=sorted(VALID_STATUS))
    q = CallLog.query.order_by(CallLog.DateLogged.desc())
    if status:
        q = q.filter(CallLog.Status == status)
    page, per_page = _page_args()
    pagination = q.paginate(page=page, per_page=per_page, error_out=False)
    items = [serialize_call(c) for c in pagination.items]
    resp = jsonify(items)
    resp.headers['X-Total-Count'] = str(pagination.total)
    resp.headers['X-Page'] = str(page)
    return resp


@api_bp.route('/calls', methods=['POST'])
@login_required
@login_required_active
@agent_required
def create_call_api():
    data = request.get_json(silent=True) or {}
    required = ['caller_name', 'phone_number', 'reason_for_call', 'call_type']
    missing = [k for k in required if not data.get(k)]
    if missing:
        return api_error('Missing required fields', 400, missing=missing)
    call_type = data.get('call_type', 'Incoming')
    priority = data.get('priority') or 'Medium'
    if call_type not in VALID_CALL_TYPE:
        return api_error('Invalid call_type', 400, allowed=sorted(VALID_CALL_TYPE))
    if priority not in VALID_PRIORITY:
        return api_error('Invalid priority', 400, allowed=sorted(VALID_PRIORITY))
    assigned = data.get('assigned_to') or None
    if assigned is not None:
        try:
            assigned = int(assigned)
        except (TypeError, ValueError):
            return api_error('assigned_to must be an integer user id')
    call = CallLog(
        CallerName=str(data['caller_name']).strip()[:120],
        PhoneNumber=str(data['phone_number']).strip()[:30],
        Department=(str(data['department']).strip()[:50] if data.get('department') else None),
        CallType=call_type,
        ReasonForCall=str(data['reason_for_call']).strip(),
        Priority=priority,
        Status='Open',
        AssignedTo=assigned,
        Notes=data.get('notes'),
    )
    db.session.add(call)
    db.session.flush()
    log_activity(call.CallID, current_user.UserID, 'Created', 'Via API')
    db.session.commit()
    return jsonify(ok=True, id=call.CallID, call=serialize_call(call, detail=True)), 201


@api_bp.route('/calls/<int:call_id>')
@login_required
@login_required_active
def get_call_api(call_id):
    c = CallLog.query.get(call_id)
    if c is None:
        return api_error('Call not found', 404)
    return jsonify({'ok': True, **serialize_call(c, detail=True)})


@api_bp.route('/calls/<int:call_id>', methods=['PUT', 'PATCH'])
@login_required
@login_required_active
@agent_required
def update_call_api(call_id):
    c = CallLog.query.get(call_id)
    if c is None:
        return api_error('Call not found', 404)
    data = request.get_json(silent=True) or {}
    if not data:
        return api_error('JSON body required')
    if 'status' in data and data['status']:
        if data['status'] not in VALID_STATUS:
            return api_error('Invalid status', 400, allowed=sorted(VALID_STATUS))
        old = c.Status
        c.Status = data['status']
        log_activity(c.CallID, current_user.UserID, 'Updated', f'Status {old} → {c.Status} (API)')
    if 'priority' in data and data['priority']:
        if data['priority'] not in VALID_PRIORITY:
            return api_error('Invalid priority', 400, allowed=sorted(VALID_PRIORITY))
        c.Priority = data['priority']
    if 'resolution' in data:
        c.Resolution = data['resolution']
    if 'notes' in data:
        c.Notes = data['notes']
    if 'assigned_to' in data:
        assigned = data['assigned_to'] or None
        if assigned is not None:
            try:
                assigned = int(assigned)
            except (TypeError, ValueError):
                return api_error('assigned_to must be an integer user id')
        c.AssignedTo = assigned
    c.LastUpdated = datetime.utcnow()
    db.session.commit()
    return jsonify(ok=True, call=serialize_call(c, detail=True))


@api_bp.route('/calls/<int:call_id>/quick', methods=['POST'])
@login_required
@login_required_active
@agent_required
def quick_action(call_id):
    """claim | resolve | escalate | pending | reopen."""
    c = CallLog.query.get(call_id)
    if c is None:
        return api_error('Call not found', 404)
    data = request.get_json(silent=True) or {}
    action = (data.get('action') or '').lower()
    if action == 'claim':
        c.AssignedTo = current_user.UserID
        if c.Status == 'Open':
            c.Status = 'In Progress'
        log_activity(c.CallID, current_user.UserID, 'Claimed', f'Claimed by {current_user.FullName}')
    elif action == 'resolve':
        old = c.Status
        c.Status = 'Resolved'
        res = (data.get('resolution') or '').strip()
        if res:
            c.Resolution = res
        elif not c.Resolution:
            c.Resolution = f'Resolved by {current_user.FullName}'
        sat = data.get('satisfaction') or data.get('satisfaction_rating')
        if sat is not None:
            try:
                sat_i = int(sat)
                if 1 <= sat_i <= 5:
                    c.SatisfactionRating = sat_i
            except (TypeError, ValueError):
                pass
        log_activity(c.CallID, current_user.UserID, 'Updated', f'Status {old} → Resolved (quick)')
    elif action == 'escalate':
        c.Priority = 'Critical'
        log_activity(c.CallID, current_user.UserID, 'Escalated', 'Priority set to Critical')
    elif action == 'pending':
        old = c.Status
        c.Status = 'Pending'
        reason = (data.get('resolution') or data.get('reason') or '').strip()
        if reason:
            note_line = f'[Pending] {reason}'
            c.Notes = (c.Notes + '\n' + note_line) if c.Notes else note_line
            log_activity(c.CallID, current_user.UserID, 'Pending', reason[:200])
        else:
            log_activity(c.CallID, current_user.UserID, 'Updated', f'Status {old} → Pending')
    elif action == 'reopen':
        old = c.Status
        c.Status = 'Open'
        log_activity(c.CallID, current_user.UserID, 'Reopened', f'Status {old} → Open')
    else:
        return api_error(
            'Unknown action', 400,
            allowed=['claim', 'resolve', 'escalate', 'pending', 'reopen']
        )
    c.LastUpdated = datetime.utcnow()
    db.session.commit()
    return jsonify(ok=True, status=c.Status, priority=c.Priority, call=serialize_call(c))


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
    return jsonify({'ok': True, 'date': today.date().isoformat(), 'calls_logged': count})


@api_bp.route('/phone-lookup')
@login_required
@login_required_active
def phone_lookup():
    phone = (request.args.get('phone') or '').strip()[:30]
    if len(phone) < 5:
        return jsonify(ok=True, matches=[])
    matches = (
        CallLog.query.filter(CallLog.PhoneNumber.ilike(f'%{phone}%'))
        .order_by(CallLog.DateLogged.desc())
        .limit(5)
        .all()
    )
    return jsonify({
        'ok': True,
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
