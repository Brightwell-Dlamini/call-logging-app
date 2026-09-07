"""
Helper utilities for activity logging, stats, and common operations.
"""
from datetime import datetime, timedelta
from sqlalchemy import func
from app import db
from app.models import CallLog, CallActivity, User, Tag


def log_activity(call_id: int, user_id: int, action: str, details: str = None) -> CallActivity:
    activity = CallActivity(
        CallID=call_id,
        UserID=user_id,
        Action=action,
        Details=details
    )
    db.session.add(activity)
    return activity


def age_hours(dt):
    if not dt:
        return None
    delta = datetime.utcnow() - dt
    return round(delta.total_seconds() / 3600, 1)


def sla_risk(call):
    if call.Status in ('Resolved', 'Closed'):
        return 'ok'
    hours = age_hours(call.DateLogged) or 0
    if call.Priority == 'Critical' and hours >= 4:
        return 'breach'
    if call.Priority == 'Critical' and hours >= 2:
        return 'warn'
    if call.Priority == 'High' and hours >= 24:
        return 'breach'
    if call.Priority == 'High' and hours >= 8:
        return 'warn'
    if hours >= 48:
        return 'warn'
    return 'ok'


def get_recent_activity(limit=12):
    rows = (
        CallActivity.query
        .order_by(CallActivity.ActivityDate.desc())
        .limit(limit)
        .all()
    )
    out = []
    for a in rows:
        out.append({
            'id': a.ActivityID,
            'action': a.Action,
            'details': a.Details or '',
            'when': a.ActivityDate,
            'user': a.user.FullName if a.user else '—',
            'call_id': a.CallID,
            'caller': a.call.CallerName if a.call else '',
        })
    return out


def get_dashboard_stats(user=None):
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    now = datetime.utcnow()

    total_calls = CallLog.query.count()
    open_calls = CallLog.query.filter(
        CallLog.Status.in_(['Open', 'In Progress', 'Pending'])
    ).count()
    resolved_today = CallLog.query.filter(
        CallLog.Status.in_(['Resolved', 'Closed']),
        CallLog.LastUpdated >= today_start
    ).count()
    high_priority = CallLog.query.filter(
        CallLog.Priority.in_(['High', 'Critical']),
        CallLog.Status.in_(['Open', 'In Progress', 'Pending'])
    ).count()
    unassigned = CallLog.query.filter(
        CallLog.AssignedTo.is_(None),
        CallLog.Status.in_(['Open', 'In Progress', 'Pending'])
    ).count()

    open_q = CallLog.query.filter(
        CallLog.Status.in_(['Open', 'In Progress', 'Pending'])
    ).all()
    sla_breach = sum(1 for c in open_q if sla_risk(c) == 'breach')
    sla_warn = sum(1 for c in open_q if sla_risk(c) == 'warn')

    # Overdue follow-ups
    overdue_followups = CallLog.query.filter(
        CallLog.FollowUpDate.isnot(None),
        CallLog.FollowUpDate < now,
        CallLog.Status.in_(['Open', 'In Progress', 'Pending'])
    ).count()

    avg_sat = db.session.query(func.avg(CallLog.SatisfactionRating)).filter(
        CallLog.SatisfactionRating.isnot(None)
    ).scalar()
    avg_satisfaction = round(float(avg_sat), 1) if avg_sat is not None else None

    avg_time = db.session.query(func.avg(CallLog.TimeSpent)).filter(
        CallLog.TimeSpent.isnot(None)
    ).scalar()
    avg_handle_mins = round(float(avg_time), 0) if avg_time is not None else None

    my_open = 0
    my_overdue = 0
    if user is not None and getattr(user, 'UserID', None):
        my_open = CallLog.query.filter(
            CallLog.AssignedTo == user.UserID,
            CallLog.Status.in_(['Open', 'In Progress', 'Pending'])
        ).count()
        my_overdue = CallLog.query.filter(
            CallLog.AssignedTo == user.UserID,
            CallLog.FollowUpDate.isnot(None),
            CallLog.FollowUpDate < now,
            CallLog.Status.in_(['Open', 'In Progress', 'Pending'])
        ).count()

    status_counts = dict(
        db.session.query(CallLog.Status, func.count(CallLog.CallID))
        .group_by(CallLog.Status)
        .all()
    )

    seven_days_ago = today_start - timedelta(days=6)
    daily = (
        db.session.query(
            func.date(CallLog.DateLogged).label('day'),
            func.count(CallLog.CallID)
        )
        .filter(CallLog.DateLogged >= seven_days_ago)
        .group_by(func.date(CallLog.DateLogged))
        .order_by('day')
        .all()
    )
    calls_per_day = {str(d): c for d, c in daily}

    dept_counts = dict(
        db.session.query(CallLog.Department, func.count(CallLog.CallID))
        .filter(CallLog.Department.isnot(None))
        .group_by(CallLog.Department)
        .all()
    )

    # Tag usage (top 8)
    try:
        tag_rows = (
            db.session.query(Tag.TagID, Tag.Name, Tag.Colour, func.count(CallLog.CallID))
            .join(CallLog.tags)
            .group_by(Tag.TagID, Tag.Name, Tag.Colour)
            .order_by(func.count(CallLog.CallID).desc())
            .limit(8)
            .all()
        )
        tag_counts = [
            {'id': tid, 'name': name, 'colour': colour, 'count': cnt}
            for tid, name, colour, cnt in tag_rows
        ]
    except Exception:
        tag_counts = []

    workload_rows = (
        db.session.query(User.UserID, User.FullName, func.count(CallLog.CallID))
        .outerjoin(
            CallLog,
            (CallLog.AssignedTo == User.UserID) &
            (CallLog.Status.in_(['Open', 'In Progress', 'Pending']))
        )
        .filter(User.IsActive == True, User.Role.in_(['Agent', 'Manager', 'Admin']))
        .group_by(User.UserID, User.FullName)
        .order_by(func.count(CallLog.CallID).desc())
        .all()
    )
    workload = [
        {'user_id': uid, 'name': name, 'open_count': cnt}
        for uid, name, cnt in workload_rows
    ]

    recent_calls = CallLog.query.order_by(CallLog.DateLogged.desc()).limit(8).all()

    return {
        'total_calls': total_calls,
        'open_calls': open_calls,
        'resolved_today': resolved_today,
        'high_priority': high_priority,
        'unassigned': unassigned,
        'my_open': my_open,
        'my_overdue': my_overdue,
        'overdue_followups': overdue_followups,
        'sla_breach': sla_breach,
        'sla_warn': sla_warn,
        'avg_satisfaction': avg_satisfaction,
        'avg_handle_mins': avg_handle_mins,
        'status_counts': status_counts,
        'calls_per_day': calls_per_day,
        'dept_counts': dept_counts,
        'tag_counts': tag_counts,
        'workload': workload,
        'recent_calls': recent_calls,
        'recent_activity': get_recent_activity(10),
    }
