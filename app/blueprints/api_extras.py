"""
Additional REST API endpoints: saved views, notifications, contact timeline, API tokens, change feed.
"""
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app import db, limiter
from app.models import SavedView, Notification, ApiToken, CallLog, CallActivity
from app.utils.decorators import login_required_active, agent_required
from app.utils.helpers import get_contact_timeline, ensure_contact
from app.utils.audit import log_audit

api_extras_bp = Blueprint('api_extras', __name__)


def api_error(message, status=400, **extra):
    payload = {'ok': False, 'error': message}
    payload.update(extra)
    return jsonify(payload), status


# ---------------------------------------------------------------------------
# Change feed (lightweight polling for board / inbox refresh)
# ---------------------------------------------------------------------------

@api_extras_bp.route('/feed/changes')
@login_required
@login_required_active
@limiter.limit('60 per minute')
def change_feed():
    """Return a revision stamp and counts of recent changes since a timestamp."""
    since_raw = (request.args.get('since') or '').strip()
    since = None
    if since_raw:
        try:
            since = datetime.fromisoformat(since_raw.replace('Z', '+00:00')).replace(tzinfo=None)
        except ValueError:
            since = None
    if since is None:
        since = datetime.utcnow() - timedelta(minutes=5)

    # Cap lookback
    floor = datetime.utcnow() - timedelta(hours=6)
    if since < floor:
        since = floor

    updated_calls = CallLog.query.filter(CallLog.LastUpdated >= since).count()
    new_activities = CallActivity.query.filter(CallActivity.ActivityDate >= since).count()
    open_count = CallLog.query.filter(
        CallLog.Status.in_(['Open', 'In Progress', 'Pending'])
    ).count()
    unassigned = CallLog.query.filter(
        CallLog.AssignedTo.is_(None),
        CallLog.Status.in_(['Open', 'In Progress', 'Pending'])
    ).count()

    server_now = datetime.utcnow()
    revision = f"{updated_calls}:{new_activities}:{open_count}:{unassigned}:{server_now.strftime('%Y%m%d%H%M%S')}"

    return jsonify({
        'ok': True,
        'since': since.isoformat(),
        'server_time': server_now.isoformat(),
        'updated_calls': updated_calls,
        'new_activities': new_activities,
        'open_count': open_count,
        'unassigned': unassigned,
        'revision': revision,
        'has_changes': (updated_calls + new_activities) > 0,
    })


# ---------------------------------------------------------------------------
# Saved Views
# ---------------------------------------------------------------------------

@api_extras_bp.route('/views', methods=['GET'])
@login_required
@login_required_active
def list_saved_views():
    views = (
        SavedView.query
        .filter_by(UserID=current_user.UserID)
        .order_by(SavedView.IsPinned.desc(), SavedView.SortOrder, SavedView.Name)
        .all()
    )
    return jsonify({'ok': True, 'views': [v.to_dict() for v in views]})


@api_extras_bp.route('/views', methods=['POST'])
@login_required
@login_required_active
def create_saved_view():
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()[:80]
    if not name:
        return api_error('name is required')
    filters = data.get('filters') or {}
    if not isinstance(filters, dict):
        return api_error('filters must be an object')

    view = SavedView(
        UserID=current_user.UserID,
        Name=name,
        IsPinned=bool(data.get('is_pinned', False)),
        SortOrder=int(data.get('sort_order') or 0),
    )
    view.set_filters(filters)
    db.session.add(view)
    db.session.commit()
    return jsonify({'ok': True, 'view': view.to_dict()}), 201


@api_extras_bp.route('/views/<int:view_id>', methods=['PUT', 'PATCH'])
@login_required
@login_required_active
def update_saved_view(view_id):
    view = SavedView.query.filter_by(ViewID=view_id, UserID=current_user.UserID).first()
    if not view:
        return api_error('View not found', 404)
    data = request.get_json(silent=True) or {}
    if 'name' in data:
        name = (data.get('name') or '').strip()[:80]
        if name:
            view.Name = name
    if 'filters' in data and isinstance(data['filters'], dict):
        view.set_filters(data['filters'])
    if 'is_pinned' in data:
        view.IsPinned = bool(data['is_pinned'])
    if 'sort_order' in data:
        try:
            view.SortOrder = int(data['sort_order'])
        except (TypeError, ValueError):
            pass
    view.UpdatedAt = datetime.utcnow()
    db.session.commit()
    return jsonify({'ok': True, 'view': view.to_dict()})


@api_extras_bp.route('/views/<int:view_id>', methods=['DELETE'])
@login_required
@login_required_active
def delete_saved_view(view_id):
    view = SavedView.query.filter_by(ViewID=view_id, UserID=current_user.UserID).first()
    if not view:
        return api_error('View not found', 404)
    db.session.delete(view)
    db.session.commit()
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# Notifications (real in-app)
# ---------------------------------------------------------------------------

@api_extras_bp.route('/inbox', methods=['GET'])
@login_required
@login_required_active
def list_notifications():
    """List current user's notifications (newest first)."""
    try:
        limit = min(max(int(request.args.get('limit', 30)), 1), 100)
    except (TypeError, ValueError):
        limit = 30
    unread_only = request.args.get('unread') in ('1', 'true', 'yes')

    q = Notification.query.filter_by(UserID=current_user.UserID)
    if unread_only:
        q = q.filter_by(IsRead=False)
    items = q.order_by(Notification.CreatedAt.desc()).limit(limit).all()
    unread_count = Notification.query.filter_by(
        UserID=current_user.UserID, IsRead=False
    ).count()
    return jsonify({
        'ok': True,
        'items': [n.to_dict() for n in items],
        'unread_count': unread_count,
    })


@api_extras_bp.route('/inbox/read', methods=['POST'])
@login_required
@login_required_active
def mark_notifications_read():
    data = request.get_json(silent=True) or {}
    ids = data.get('ids')  # list of notification ids, or omit to mark all
    q = Notification.query.filter_by(UserID=current_user.UserID, IsRead=False)
    if ids:
        try:
            ids = [int(i) for i in ids]
            q = q.filter(Notification.NotificationID.in_(ids))
        except (TypeError, ValueError):
            return api_error('ids must be a list of integers')
    updated = q.update({'IsRead': True}, synchronize_session=False)
    db.session.commit()
    return jsonify({'ok': True, 'marked': updated})


@api_extras_bp.route('/inbox/<int:notification_id>/read', methods=['POST'])
@login_required
@login_required_active
def mark_one_read(notification_id):
    n = Notification.query.filter_by(
        NotificationID=notification_id, UserID=current_user.UserID
    ).first()
    if not n:
        return api_error('Notification not found', 404)
    n.IsRead = True
    db.session.commit()
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# Contact timeline
# ---------------------------------------------------------------------------

@api_extras_bp.route('/contacts/timeline')
@login_required
@login_required_active
def contact_timeline():
    phone = (request.args.get('phone') or '').strip()
    if not phone:
        return api_error('phone query parameter is required')
    try:
        limit = min(max(int(request.args.get('limit', 20)), 1), 50)
    except (TypeError, ValueError):
        limit = 20
    data = get_contact_timeline(phone, limit=limit)
    return jsonify({'ok': True, **(data or {'contact': None, 'calls': [], 'total_calls': 0})})


@api_extras_bp.route('/contacts', methods=['POST', 'PUT', 'PATCH'])
@login_required
@login_required_active
@agent_required
def upsert_contact():
    data = request.get_json(silent=True) or {}
    phone = (data.get('phone') or data.get('phone_number') or '').strip()[:30]
    if not phone:
        return api_error('phone is required')
    contact = ensure_contact(phone, display_name=data.get('display_name') or data.get('name'))
    if data.get('email') is not None:
        contact.Email = (str(data['email']).strip()[:120] or None)
    if data.get('company') is not None:
        contact.Company = (str(data['company']).strip()[:120] or None)
    if data.get('notes') is not None:
        contact.Notes = data['notes']
    if 'is_vip' in data:
        contact.IsVIP = bool(data['is_vip'])
    if data.get('display_name') or data.get('name'):
        contact.DisplayName = (str(data.get('display_name') or data.get('name')).strip()[:120] or None)
    contact.UpdatedAt = datetime.utcnow()
    db.session.commit()
    return jsonify({
        'ok': True,
        'contact': {
            'id': contact.ContactID,
            'phone': contact.PhoneNumber,
            'display_name': contact.DisplayName,
            'email': contact.Email,
            'company': contact.Company,
            'notes': contact.Notes,
            'is_vip': contact.IsVIP,
        }
    })


# ---------------------------------------------------------------------------
# API Tokens (personal access tokens)
# ---------------------------------------------------------------------------

@api_extras_bp.route('/tokens', methods=['GET'])
@login_required
@login_required_active
def list_tokens():
    tokens = (
        ApiToken.query
        .filter_by(UserID=current_user.UserID)
        .order_by(ApiToken.CreatedAt.desc())
        .all()
    )
    return jsonify({'ok': True, 'tokens': [t.to_dict() for t in tokens]})


@api_extras_bp.route('/tokens', methods=['POST'])
@login_required
@login_required_active
@limiter.limit('10 per hour')
def create_token():
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()[:80]
    if not name:
        return api_error('name is required')
    scopes = data.get('scopes') or 'read'
    if isinstance(scopes, list):
        scopes = ','.join(str(s).strip() for s in scopes if s)
    scopes = str(scopes)[:255]

    expires_at = None
    if data.get('expires_days'):
        try:
            days = int(data['expires_days'])
            if days > 0:
                expires_at = datetime.utcnow() + timedelta(days=min(days, 3650))
        except (TypeError, ValueError):
            pass

    raw = ApiToken.generate_token()
    token = ApiToken(
        UserID=current_user.UserID,
        Name=name,
        Scopes=scopes,
        ExpiresAt=expires_at,
    )
    token.set_token(raw)
    db.session.add(token)
    db.session.flush()
    log_audit(
        'token.create',
        f'name={name} scopes={scopes}',
        target_type='api_token',
        target_id=token.TokenID,
    )
    db.session.commit()
    return jsonify({'ok': True, 'token': token.to_dict(include_token=raw)}), 201


@api_extras_bp.route('/tokens/<int:token_id>', methods=['DELETE'])
@login_required
@login_required_active
def revoke_token(token_id):
    token = ApiToken.query.filter_by(TokenID=token_id, UserID=current_user.UserID).first()
    if not token:
        return api_error('Token not found', 404)
    token.IsActive = False
    log_audit(
        'token.revoke',
        f'name={token.Name}',
        target_type='api_token',
        target_id=token.TokenID,
    )
    db.session.commit()
    return jsonify({'ok': True})
