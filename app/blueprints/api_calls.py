"""Call list/create/update/quick/user API routes."""
from datetime import datetime
from flask import jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models import CallLog, User, Tag
from app.utils.decorators import login_required_active, agent_required, manager_required
from app.utils.helpers import (
    log_activity, ensure_contact, notify_assignment, notify_watchers, notify_escalate,
)
from app.blueprints.api import (
    api_bp, VALID_STATUS, VALID_PRIORITY, VALID_CALL_TYPE,
    api_error, serialize_call, _page_args, _parse_follow_up,
)


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

    try:
        follow_up = _parse_follow_up(data.get('follow_up_date'))
    except ValueError:
        return api_error('Invalid follow_up_date format')

    notes = data.get('notes')
    if notes is not None:
        notes = str(notes)[:4000]

    call = CallLog(
        CallerName=str(data['caller_name']).strip()[:120],
        PhoneNumber=str(data['phone_number']).strip()[:30],
        Department=(str(data['department']).strip()[:50] if data.get('department') else None),
        CallType=call_type,
        ReasonForCall=str(data['reason_for_call']).strip()[:2000],
        Priority=priority,
        Status='Open',
        AssignedTo=assigned,
        Notes=notes,
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
        c.Resolution = str(data['resolution'])[:4000] if data['resolution'] is not None else None
    if 'notes' in data:
        c.Notes = str(data['notes'])[:4000] if data['notes'] is not None else None
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
                c.FollowUpDate = _parse_follow_up(val)
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
            c.Resolution = res[:4000]
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
