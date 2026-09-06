"""
Kanban-style workload board and personal queue.
"""
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import CallLog, User
from app.utils.decorators import login_required_active, agent_required
from app.utils.helpers import log_activity, age_hours, sla_risk

board_bp = Blueprint('board', __name__, url_prefix='/board')

COLUMNS = ['Open', 'In Progress', 'Pending', 'Resolved', 'Closed']


def _card(c):
    return {
        'id': c.CallID,
        'caller': c.CallerName,
        'phone': c.PhoneNumber,
        'priority': c.Priority,
        'status': c.Status,
        'department': c.Department or '',
        'assignee': c.assignee.FullName if c.assignee else None,
        'assigned_to': c.AssignedTo,
        'age_hours': age_hours(c.DateLogged),
        'sla': sla_risk(c),
        'is_overdue': bool(getattr(c, 'is_overdue', False)),
        'tags': [
            {'name': t.Name, 'colour': t.Colour}
            for t in (c.tags or [])
        ],
        'reason': (c.ReasonForCall or '')[:120],
    }


@board_bp.route('/')
@login_required
@login_required_active
def kanban():
    """Status board for the whole org queue."""
    columns = {}
    for status in COLUMNS:
        q = (
            CallLog.query.filter(CallLog.Status == status)
            .order_by(
                db.case(
                    (CallLog.Priority == 'Critical', 1),
                    (CallLog.Priority == 'High', 2),
                    (CallLog.Priority == 'Medium', 3),
                    else_=4
                ),
                CallLog.DateLogged.asc()
            )
            .limit(40)
            .all()
        )
        columns[status] = q

    agents = User.query.filter(
        User.IsActive == True,
        User.Role.in_(['Agent', 'Manager', 'Admin'])
    ).order_by(User.FullName).all()

    return render_template(
        'board/kanban.html',
        columns=columns,
        agents=agents,
        title='Board'
    )


@board_bp.route('/mine')
@login_required
@login_required_active
def my_queue():
    """Calls assigned to the current user."""
    open_statuses = ['Open', 'In Progress', 'Pending']
    mine = (
        CallLog.query.filter(
            CallLog.AssignedTo == current_user.UserID,
            CallLog.Status.in_(open_statuses)
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
        .all()
    )
    unassigned = (
        CallLog.query.filter(
            CallLog.AssignedTo.is_(None),
            CallLog.Status.in_(open_statuses)
        )
        .order_by(CallLog.DateLogged.asc())
        .limit(30)
        .all()
    )
    return render_template(
        'board/mine.html',
        mine=mine,
        unassigned=unassigned,
        title='My queue'
    )


@board_bp.route('/workload')
@login_required
@login_required_active
def workload():
    """Agent capacity view."""
    from app.utils.helpers import get_dashboard_stats
    stats = get_dashboard_stats(user=current_user)
    return render_template(
        'board/workload.html',
        workload=stats['workload'],
        unassigned=stats['unassigned'],
        title='Workload'
    )


@board_bp.route('/move', methods=['POST'])
@login_required
@login_required_active
@agent_required
def move_card():
    """Move a call to a new status (and optional assignee)."""
    data = request.get_json(silent=True) or {}
    call_id = data.get('call_id')
    new_status = data.get('status')
    assign_to = data.get('assigned_to')

    if new_status not in COLUMNS:
        return jsonify(ok=False, error='Invalid status'), 400
    try:
        call_id = int(call_id)
    except (TypeError, ValueError):
        return jsonify(ok=False, error='Invalid call_id'), 400

    call = CallLog.query.get_or_404(call_id)
    old = call.Status
    call.Status = new_status
    call.LastUpdated = datetime.utcnow()
    if new_status in ('Resolved', 'Closed') and not call.Resolution:
        call.Resolution = f'Marked {new_status} from board by {current_user.FullName}'

    details = f'Status {old} → {new_status} (board)'
    if assign_to is not None:
        try:
            aid = int(assign_to) if assign_to else None
        except (TypeError, ValueError):
            aid = None
        call.AssignedTo = aid
        agent = User.query.get(aid) if aid else None
        details += f'; assigned to {agent.FullName if agent else "Unassigned"}'

    log_activity(call.CallID, current_user.UserID, 'Board Move', details)
    db.session.commit()
    return jsonify(ok=True, call=_card(call))


@board_bp.route('/claim/<int:call_id>', methods=['POST'])
@login_required
@login_required_active
@agent_required
def claim(call_id):
    """Assign call to current user and set In Progress."""
    call = CallLog.query.get_or_404(call_id)
    call.AssignedTo = current_user.UserID
    if call.Status == 'Open':
        call.Status = 'In Progress'
    call.LastUpdated = datetime.utcnow()
    log_activity(
        call.CallID,
        current_user.UserID,
        'Claimed',
        f'Claimed by {current_user.FullName}'
    )
    db.session.commit()
    return jsonify(ok=True, call=_card(call))
