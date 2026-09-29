"""
REST API endpoints (session-authenticated).
"""
from datetime import datetime
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from sqlalchemy import or_
from app import db
from app.models import CallLog, User, Tag, CannedResponse, DispositionCode
from app.utils.decorators import login_required_active, agent_required, manager_required
from app.utils.helpers import (
    get_dashboard_stats, log_activity, get_recent_activity, sla_risk,
    ensure_contact, notify_assignment, notify_escalate, notify_watchers,
)

api_bp = Blueprint('api', __name__)

VALID_STATUS = frozenset({'Open', 'In Progress', 'Pending', 'Resolved', 'Closed'})
VALID_PRIORITY = frozenset({'Low', 'Medium', 'High', 'Critical'})
VALID_CALL_TYPE = frozenset({'Incoming', 'Outgoing'})
VALID_PRESENCE = frozenset({'Available', 'Busy', 'Away', 'Offline'})
MAX_PAGE_SIZE = 100

# Map legacy UI presence values to server enum
PRESENCE_MAP = {
    'available': 'Available',
    'on_call': 'Busy',
    'break': 'Away',
    'busy': 'Busy',
    'away': 'Away',
    'offline': 'Offline',
    'Available': 'Available',
    'Busy': 'Busy',
    'Away': 'Away',
    'Offline': 'Offline',
}


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
        'is_overdue': bool(getattr(c, 'is_overdue', False)),
        'disposition': c.disposition.Code if getattr(c, 'disposition', None) else None,
        'tags': [
            {'id': t.TagID, 'name': t.Name, 'colour': t.Colour}
            for t in (c.tags or [])
        ],
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
            'follow_up_date': c.FollowUpDate.isoformat() if c.FollowUpDate else None,
            'time_spent': c.TimeSpent,
            'satisfaction': c.SatisfactionRating,
            'watching': c.is_watched_by(current_user) if current_user.is_authenticated else False,
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
        'my_overdue': stats.get('my_overdue', 0),
        'overdue_followups': stats.get('overdue_followups', 0),
        'sla_breach': stats['sla_breach'],
        'sla_warn': stats['sla_warn'],
        'avg_satisfaction': stats.get('avg_satisfaction'),
        'avg_handle_mins': stats.get('avg_handle_mins'),
        'status_counts': stats['status_counts'],
        'calls_per_day': stats['calls_per_day'],
        'dept_counts': stats['dept_counts'],
        'tag_counts': stats.get('tag_counts', []),
        'workload': stats['workload'],
        'unread_notifications': stats.get('unread_notifications', 0),
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


@api_bp.route('/presence', methods=['GET', 'POST'])
@login_required
@login_required_active
def presence():
    """Get or set current user desk presence."""
    if request.method == 'GET':
        return jsonify({
            'ok': True,
            'presence': getattr(current_user, 'Presence', 'Available') or 'Available',
            'user_id': current_user.UserID,
        })
    data = request.get_json(silent=True) or {}
    raw = (data.get('presence') or data.get('status') or '').strip()
    mapped = PRESENCE_MAP.get(raw) or PRESENCE_MAP.get(raw.lower())
    if not mapped or mapped not in VALID_PRESENCE:
        return api_error('Invalid presence', 400, allowed=sorted(VALID_PRESENCE))
    current_user.Presence = mapped
    db.session.commit()
    return jsonify(ok=True, presence=mapped)


@api_bp.route('/dispositions')
@login_required
@login_required_active
def list_dispositions_api():
    items = DispositionCode.query.filter_by(IsActive=True).order_by(DispositionCode.Label).all()
    return jsonify({
        'ok': True,
        'items': [
            {'id': d.DispositionID, 'code': d.Code, 'label': d.Label}
            for d in items
        ],
    })


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
            {'id': u.UserID, 'name': u.FullName, 'role': u.Role, 'presence': getattr(u, 'Presence', None)}
            for u in users
        ],
    })


@api_bp.route('/tags')
@login_required
@login_required_active
def list_tags_api():
    tags = Tag.query.filter_by(IsActive=True).order_by(Tag.Name).all()
    return jsonify({
        'ok': True,
        'tags': [
            {'id': t.TagID, 'name': t.Name, 'colour': t.Colour, 'description': t.Description}
            for t in tags
        ],
    })


@api_bp.route('/canned')
@login_required
@login_required_active
def list_canned_api():
    items = CannedResponse.query.filter_by(IsActive=True).order_by(CannedResponse.Category, CannedResponse.Title).all()
    return jsonify({
        'ok': True,
        'items': [
            {
                'id': r.ResponseID,
                'title': r.Title,
                'body': r.Body,
                'category': r.Category,
            }
            for r in items
        ],
    })


@api_bp.route('/calls')
@login_required
@login_required_active
def list_calls_api():
    status = request.args.get('status')
    if status and status not in VALID_STATUS:
        return api_error('Invalid status', 400, allowed=sorted(VALID_STATUS))
    tag_id = request.args.get('tag', type=int)
    overdue = request.args.get('overdue')
    q = CallLog.query.order_by(CallLog.DateLogged.desc())
    if status:
        q = q.filter(CallLog.Status == status)
    if tag_id:
        q = q.filter(CallLog.tags.any(Tag.TagID == tag_id))
    if overdue in ('1', 'true', 'yes'):
        q = q.filter(
            CallLog.FollowUpDate.isnot(None),
            CallLog.FollowUpDate < datetime.utcnow(),
            CallLog.Status.in_(['Open', 'In Progress', 'Pending'])
        )
    page, per_page = _page_args()
    pagination = q.paginate(page=page, per_page=per_page, error_out=False)
    items = [serialize_call(c) for c in pagination.items]
    resp = jsonify({
        'ok': True,
        'items': items,
        'page': page,
        'per_page': per_page,
        'total': pagination.total,
        'pages': pagination.pages,
    })
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

    follow_up = None
    if data.get('follow_up_date'):
        try:
            follow_up = datetime.fromisoformat(str(data['follow_up_date']).replace('Z', '+00:00'))
        except ValueError:
            pass

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
        FollowUpDate=follow_up,
    )
    db.session.add(call)
    db.session.flush()

    tag_ids = data.get('tag_ids') or data.get('tags') or []
    if tag_ids:
        try:
            tag_ids = [int(t) for t in tag_ids]
            tags = Tag.query.filter(Tag.TagID.in_(tag_ids), Tag.IsActive == True).all()
            call.tags = tags
        except (TypeError, ValueError):
            pass

    log_activity(call.CallID, current_user.UserID, 'Created', 'Via API')
    ensure_contact(call.PhoneNumber, display_name=call.CallerName)
    if call.AssignedTo:
        notify_assignment(call, actor=current_user)
    db.session.commit()
    return jsonify(ok=True, id=call.CallID, call=serialize_call(call, detail=True)), 201


@api_bp.route('/calls/round-robin', methods=['POST'])
@login_required
@login_required_active
@manager_required
def round_robin_assign():
    agents = (
        User.query.filter(
            User.IsActive == True,
            User.Role.in_(['Agent', 'Manager', 'Admin']),
            User.Presence.in_(['Available', 'Busy']),
        )
        .order_by(User.UserID)
        .all()
    )
    if not agents:
        agents = User.query.filter(
            User.IsActive == True,
            User.Role.in_(['Agent', 'Manager', 'Admin']),
        ).order_by(User.UserID).all()
    if not agents:
        return api_error('No active agents available', 400)

    unassigned = (
        CallLog.query.filter(
            CallLog.AssignedTo.is_(None),
            CallLog.Status.in_(['Open', 'In Progress', 'Pending'])
        )
        .order_by(CallLog.DateLogged.asc())
        .limit(200)
        .all()
    )
    if not unassigned:
        return jsonify(ok=True, assigned=0, message='Nothing to assign')

    assigned_count = 0
    for i, call in enumerate(unassigned):
        agent = agents[i % len(agents)]
        call.AssignedTo = agent.UserID
        if call.Status == 'Open':
            call.Status = 'In Progress'
        call.LastUpdated = datetime.utcnow()
        log_activity(
            call.CallID,
            current_user.UserID,
            'Assigned',
            f'Round-robin → {agent.FullName}'
        )
        notify_assignment(call, actor=current_user)
        assigned_count += 1

    db.session.commit()
    return jsonify(ok=True, assigned=assigned_count, agents=len(agents))


@api_bp.route('/calls/claim-next', methods=['POST'])
@login_required
@login_required_active
@agent_required
def claim_next():
    call = (
        CallLog.query.filter(
            CallLog.AssignedTo.is_(None),
            CallLog.Status.in_(['Open', 'Pending', 'In Progress'])
        )
        .order_by(
            db.case(
                (CallLog.Priority == 'Critical', 1),
                (CallLog.Priority == 'High', 2),
                (CallLog.Priority == 'Medium', 3),
                else_=4
            ),
            CallLog.DateLogged.asc()
        )
        .first()
    )
    if call is None:
        return jsonify(ok=False, message='No unassigned calls in the pool')

    call.AssignedTo = current_user.UserID
    if call.Status == 'Open':
        call.Status = 'In Progress'
    call.LastUpdated = datetime.utcnow()
    log_activity(
        call.CallID,
        current_user.UserID,
        'Claimed',
        f'Claim-next by {current_user.FullName}'
    )
    notify_watchers(call, title=f'Call #{call.CallID} claimed', body=f'Claim-next by {current_user.FullName}', category='claim', exclude_user_id=current_user.UserID)
    db.session.commit()
    return jsonify(ok=True, call_id=call.CallID, call=serialize_call(call))


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
        prev_assigned = c.AssignedTo
        c.AssignedTo = assigned
        if assigned and assigned != prev_assigned:
            notify_assignment(c, actor=current_user)
    if 'disposition_id' in data:
        did = data['disposition_id'] or None
        if did is not None:
            try:
                did = int(did)
            except (TypeError, ValueError):
                return api_error('disposition_id must be an integer')
        c.DispositionID = did
    if 'follow_up_date' in data:
        val = data['follow_up_date']
        if not val:
            c.FollowUpDate = None
        else:
            try:
                c.FollowUpDate = datetime.fromisoformat(str(val).replace('Z', '+00:00'))
            except ValueError:
                return api_error('Invalid follow_up_date format')
    if 'tag_ids' in data or 'tags' in data:
        tag_ids = data.get('tag_ids') or data.get('tags') or []
        try:
            tag_ids = [int(t) for t in tag_ids]
            tags = Tag.query.filter(Tag.TagID.in_(tag_ids), Tag.IsActive == True).all()
            c.tags = tags
        except (TypeError, ValueError):
            return api_error('Invalid tag_ids')
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
        notify_watchers(c, title=f'Call #{c.CallID} claimed', body=f'Claimed by {current_user.FullName}', category='claim', exclude_user_id=current_user.UserID)
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
        mins = data.get('time_spent')
        if mins is not None:
            try:
                mins_i = int(mins)
                if mins_i >= 0:
                    c.TimeSpent = mins_i
            except (TypeError, ValueError):
                pass
        log_activity(c.CallID, current_user.UserID, 'Updated', f'Status {old} → Resolved (quick)')
    elif action == 'escalate':
        c.Priority = 'Critical'
        log_activity(c.CallID, current_user.UserID, 'Escalated', 'Priority set to Critical')
        notify_escalate(c, actor=current_user)
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
    return jsonify({
        'ok': True,
        'items': [
            {
                'id': u.UserID,
                'name': u.FullName,
                'username': u.Username,
                'role': u.Role,
                'presence': getattr(u, 'Presence', None),
            }
            for u in users
        ],
    })
