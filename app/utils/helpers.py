"""
Helper utilities for activity logging, stats, and common operations.
"""
from datetime import datetime, timedelta
from sqlalchemy import func
from app import db
from app.models import CallLog, CallActivity, User


def log_activity(call_id: int, user_id: int, action: str, details: str = None) -> CallActivity:
    """
    Record an activity entry for a call.
    """
    activity = CallActivity(
        CallID=call_id,
        UserID=user_id,
        Action=action,
        Details=details
    )
    db.session.add(activity)
    return activity


def get_dashboard_stats():
    """
    Compute key dashboard statistics.
    Returns a dict of counts and recent data.
    """
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

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

    # Calls by status
    status_counts = dict(
        db.session.query(CallLog.Status, func.count(CallLog.CallID))
        .group_by(CallLog.Status)
        .all()
    )

    # Calls per day (last 7 days)
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

    # Calls by department
    dept_counts = dict(
        db.session.query(CallLog.Department, func.count(CallLog.CallID))
        .filter(CallLog.Department.isnot(None))
        .group_by(CallLog.Department)
        .all()
    )

    # Recent calls
    recent_calls = (
        CallLog.query
        .order_by(CallLog.DateLogged.desc())
        .limit(5)
        .all()
    )

    return {
        'total_calls': total_calls,
        'open_calls': open_calls,
        'resolved_today': resolved_today,
        'high_priority': high_priority,
        'status_counts': status_counts,
        'calls_per_day': calls_per_day,
        'dept_counts': dept_counts,
        'recent_calls': recent_calls
    }
