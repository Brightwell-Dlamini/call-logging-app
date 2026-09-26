"""
Helper utilities for activity logging, stats, SLA, notifications, and common operations.
"""
from datetime import datetime, timedelta, date
from sqlalchemy import func, or_, and_, case
from sqlalchemy.orm import joinedload
from app import db
from app.models import CallLog, CallActivity, User, Tag, Notification, Contact


# ---------------------------------------------------------------------------
# Configurable SLA thresholds (hours). Can later be moved to DB settings.
# ---------------------------------------------------------------------------
SLA_THRESHOLDS = {
    'Critical': {'warn': 2, 'breach': 4},
    'High':     {'warn': 8, 'breach': 24},
    'Medium':   {'warn': 24, 'breach': 48},
    'Low':      {'warn': 48, 'breach': 72},
}

OPEN_STATUSES = ('Open', 'In Progress', 'Pending')
RESOLVED_STATUSES = ('Resolved', 'Closed')


def _str_key_counts(rows):
    """Convert group_by rows to {str_key: int_count} for JSON-safe charts."""
    out = {}
    for key, cnt in rows:
        if key is None:
            continue
        # Enum members, dates, etc. → plain string labels
        label = getattr(key, 'value', None) or getattr(key, 'name', None) or str(key)
        out[str(label)] = int(cnt or 0)
    return out


def log_activity(call_id: int, user_id: int, action: str, details: str = None) -> CallActivity:
    activity = CallActivity(
        CallID=call_id,
        UserID=user_id,
        Action=action,
        Details=details
    )
    db.session.add(activity)
    return activity


def create_notification(
    user_id: int,
    title: str,
    body: str = None,
    category: str = 'system',
    link_url: str = None,
    call_id: int = None,
) -> Notification:
    """Create an in-app notification for a user."""
    if not user_id:
        return None
    n = Notification(
        UserID=user_id,
        Title=(title or '')[:160],
        Body=body,
        Category=category or 'system',
        LinkUrl=link_url,
        CallID=call_id,
    )
    db.session.add(n)
    return n


def notify_assignment(call: CallLog, actor: User = None) -> None:
    """Notify the newly assigned agent (skip self-assign)."""
    if not call or not call.AssignedTo:
        return
    actor_id = getattr(actor, 'UserID', None)
    if actor_id and call.AssignedTo == actor_id:
        return
    create_notification(
        user_id=call.AssignedTo,
        title=f'Call #{call.CallID} assigned to you',
        body=f'{call.CallerName} · {call.Priority} · {(call.ReasonForCall or "")[:120]}',
        category='assignment',
        link_url=f'/calls/{call.CallID}',
        call_id=call.CallID,
    )


def notify_watchers(call: CallLog, title: str, body: str = None, category: str = 'system', exclude_user_id: int = None) -> None:
    """Notify users watching this call."""
    if not call:
        return
    for w in (call.watchers or []):
        if exclude_user_id and w.UserID == exclude_user_id:
            continue
        create_notification(
            user_id=w.UserID,
            title=title,
            body=body,
            category=category,
            link_url=f'/calls/{call.CallID}',
            call_id=call.CallID,
        )


def notify_escalate(call: CallLog, actor: User = None) -> None:
    """Notify assignee and managers on escalation."""
    if not call:
        return
    actor_id = getattr(actor, 'UserID', None)
    title = f'Call #{call.CallID} escalated to Critical'
    body = f'{call.CallerName} · escalated by {getattr(actor, "FullName", "system")}'
    if call.AssignedTo and call.AssignedTo != actor_id:
        create_notification(
            user_id=call.AssignedTo,
            title=title,
            body=body,
            category='sla_warn',
            link_url=f'/calls/{call.CallID}',
            call_id=call.CallID,
        )
    managers = (
        User.query.filter(
            User.IsActive == True,
            User.Role.in_(['Manager', 'Admin']),
        )
        .limit(10)
        .all()
    )
    for m in managers:
        if m.UserID == actor_id or m.UserID == call.AssignedTo:
            continue
        create_notification(
            user_id=m.UserID,
            title=title,
            body=body,
            category='sla_warn',
            link_url=f'/calls/{call.CallID}',
            call_id=call.CallID,
        )


def age_hours(dt):
    if not dt:
        return None
    delta = datetime.utcnow() - dt
    return round(delta.total_seconds() / 3600, 1)


def sla_risk(call):
    """Return 'ok' | 'warn' | 'breach' based on priority and age."""
    if call.Status in RESOLVED_STATUSES:
        return 'ok'
    hours = age_hours(call.DateLogged) or 0
    thresholds = SLA_THRESHOLDS.get(call.Priority) or SLA_THRESHOLDS['Medium']
    if hours >= thresholds['breach']:
        return 'breach'
    if hours >= thresholds['warn']:
        return 'warn'
    return 'ok'


def sla_hours_remaining(call):
    """Approximate hours until breach (negative if already breached)."""
    if call.Status in RESOLVED_STATUSES:
        return None
    hours = age_hours(call.DateLogged) or 0
    thresholds = SLA_THRESHOLDS.get(call.Priority) or SLA_THRESHOLDS['Medium']
    return round(thresholds['breach'] - hours, 1)


def _sla_age_clauses(now, bucket):
    """Build portable DateLogged predicates for warn or breach buckets."""
    clauses = []
    for priority, thresholds in SLA_THRESHOLDS.items():
        warn_cut = now - timedelta(hours=thresholds['warn'])
        breach_cut = now - timedelta(hours=thresholds['breach'])
        if bucket == 'breach':
            clauses.append(and_(
                CallLog.Priority == priority,
                CallLog.DateLogged <= breach_cut,
            ))
        elif bucket == 'warn':
            clauses.append(and_(
                CallLog.Priority == priority,
                CallLog.DateLogged <= warn_cut,
                CallLog.DateLogged > breach_cut,
            ))
    return or_(*clauses) if clauses else False


def count_open_sla(bucket, now=None):
    """Count open calls in an SLA bucket without loading rows."""
    now = now or datetime.utcnow()
    return (
        CallLog.query.filter(
            CallLog.Status.in_(OPEN_STATUSES),
            _sla_age_clauses(now, bucket),
        )
        .count()
    )


def get_recent_activity(limit=12):
    rows = (
        CallActivity.query
        .options(joinedload(CallActivity.user), joinedload(CallActivity.call))
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


def get_contact_timeline(phone: str, limit: int = 20):
    """Return contact profile + recent calls for a phone number."""
    if not phone:
        return None
    phone = phone.strip()
    contact = Contact.query.filter_by(PhoneNumber=phone).first()
    calls = (
        CallLog.query
        .filter(CallLog.PhoneNumber == phone)
        .order_by(CallLog.DateLogged.desc())
        .limit(limit)
        .all()
    )
    return {
        'contact': {
            'id': contact.ContactID if contact else None,
            'phone': phone,
            'display_name': contact.DisplayName if contact else None,
            'email': contact.Email if contact else None,
            'company': contact.Company if contact else None,
            'notes': contact.Notes if contact else None,
            'is_vip': bool(contact.IsVIP) if contact else False,
        } if (contact or calls) else None,
        'calls': [
            {
                'id': c.CallID,
                'caller': c.CallerName,
                'status': c.Status,
                'priority': c.Priority,
                'reason': (c.ReasonForCall or '')[:160],
                'date_logged': c.DateLogged.isoformat() if c.DateLogged else None,
                'resolution': (c.Resolution or '')[:120] if c.Resolution else None,
            }
            for c in calls
        ],
        'total_calls': CallLog.query.filter(CallLog.PhoneNumber == phone).count(),
    }


def ensure_contact(phone: str, display_name: str = None) -> Contact:
    """Get or create a contact record for the phone number."""
    if not phone:
        return None
    phone = phone.strip()[:30]
    contact = Contact.query.filter_by(PhoneNumber=phone).first()
    if contact is None:
        contact = Contact(
            PhoneNumber=phone,
            DisplayName=(display_name or '')[:120] or None,
        )
        db.session.add(contact)
    elif display_name and not contact.DisplayName:
        contact.DisplayName = display_name[:120]
    return contact


def get_dashboard_stats(user=None):
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    now = datetime.utcnow()

    total_calls = CallLog.query.count()
    open_calls = CallLog.query.filter(
        CallLog.Status.in_(OPEN_STATUSES)
    ).count()

    resolved_ts = func.coalesce(CallLog.LastUpdated, CallLog.DateLogged)
    resolved_today = CallLog.query.filter(
        CallLog.Status.in_(RESOLVED_STATUSES),
        resolved_ts >= today_start,
    ).count()

    high_priority = CallLog.query.filter(
        CallLog.Priority.in_(['High', 'Critical']),
        CallLog.Status.in_(OPEN_STATUSES)
    ).count()
    unassigned = CallLog.query.filter(
        CallLog.AssignedTo.is_(None),
        CallLog.Status.in_(OPEN_STATUSES)
    ).count()

    sla_breach = count_open_sla('breach', now=now)
    sla_warn = count_open_sla('warn', now=now)

    overdue_followups = CallLog.query.filter(
        CallLog.FollowUpDate.isnot(None),
        CallLog.FollowUpDate < now,
        CallLog.Status.in_(OPEN_STATUSES)
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
    unread_notifications = 0
    if user is not None and getattr(user, 'UserID', None):
        my_open = CallLog.query.filter(
            CallLog.AssignedTo == user.UserID,
            CallLog.Status.in_(OPEN_STATUSES)
        ).count()
        my_overdue = CallLog.query.filter(
            CallLog.AssignedTo == user.UserID,
            CallLog.FollowUpDate.isnot(None),
            CallLog.FollowUpDate < now,
            CallLog.Status.in_(OPEN_STATUSES)
        ).count()
        try:
            unread_notifications = Notification.query.filter_by(
                UserID=user.UserID, IsRead=False
            ).count()
        except Exception:
            unread_notifications = 0

    status_rows = (
        db.session.query(CallLog.Status, func.count(CallLog.CallID))
        .group_by(CallLog.Status)
        .all()
    )
    status_counts = _str_key_counts(status_rows)

    priority_rows = (
        db.session.query(CallLog.Priority, func.count(CallLog.CallID))
        .group_by(CallLog.Priority)
        .all()
    )
    priority_counts = _str_key_counts(priority_rows)
    for p in ('Low', 'Medium', 'High', 'Critical'):
        priority_counts.setdefault(p, 0)

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
    calls_per_day = {}
    for i in range(7):
        d = (seven_days_ago + timedelta(days=i)).date()
        calls_per_day[d.isoformat()] = 0
    for d, c in daily:
        if d is None:
            continue
        if isinstance(d, datetime):
            key = d.date().isoformat()
        elif isinstance(d, date):
            key = d.isoformat()
        else:
            key = str(d)[:10]
        calls_per_day[key] = int(c)

    dept_rows = (
        db.session.query(CallLog.Department, func.count(CallLog.CallID))
        .filter(CallLog.Department.isnot(None), CallLog.Department != '')
        .group_by(CallLog.Department)
        .all()
    )
    dept_counts = _str_key_counts(dept_rows)

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
            {'id': tid, 'name': str(name), 'colour': str(colour or '#6366f1'), 'count': int(cnt)}
            for tid, name, colour, cnt in tag_rows
        ]
    except Exception:
        tag_counts = []

    workload_rows = (
        db.session.query(User.UserID, User.FullName, func.count(CallLog.CallID))
        .outerjoin(
            CallLog,
            (CallLog.AssignedTo == User.UserID) &
            (CallLog.Status.in_(OPEN_STATUSES))
        )
        .filter(User.IsActive == True, User.Role.in_(['Agent', 'Manager', 'Admin']))
        .group_by(User.UserID, User.FullName)
        .order_by(func.count(CallLog.CallID).desc())
        .all()
    )
    workload = [
        {'user_id': uid, 'name': name, 'open_count': int(cnt or 0)}
        for uid, name, cnt in workload_rows
    ]

    recent_calls = (
        CallLog.query
        .options(joinedload(CallLog.assignee))
        .order_by(CallLog.DateLogged.desc())
        .limit(8)
        .all()
    )

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
        'priority_counts': priority_counts,
        'calls_per_day': calls_per_day,
        'dept_counts': dept_counts,
        'tag_counts': tag_counts,
        'workload': workload,
        'recent_calls': recent_calls,
        'recent_activity': get_recent_activity(10),
        'unread_notifications': unread_notifications,
        'sla_thresholds': SLA_THRESHOLDS,
    }
