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


def _parse_follow_up(raw):
    """Parse ISO datetime; raise ValueError on malformed non-empty input."""
    if raw in (None, ''):
        return None
    return datetime.fromisoformat(str(raw).replace('Z', '+00:00'))


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
            'title': f"{a['user']} \u00b7 {a['action']}",
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


from app.blueprints import api_calls  # noqa: E402,F401
