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
    if raw in (None, ''):
        return None
    return datetime.fromisoformat(str(raw).replace('Z', '+00:00'))
