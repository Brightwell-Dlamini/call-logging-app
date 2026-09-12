"""Shared demo-data bootstrap used by the factory and /seed."""
from datetime import datetime, timedelta

DEMO_USERS = [
    ('admin', 'admin@calllog.local', 'System Administrator', 'Admin', 'admin123'),
    ('agent1', 'agent1@calllog.local', 'Thabo Molefe', 'Agent', 'agent123'),
    ('manager1', 'manager1@calllog.local', 'Lerato Nkosi', 'Manager', 'manager123'),
]

DEMO_DEPARTMENTS = ['IT', 'HR', 'Sales', 'Support', 'Billing']

DEMO_TAGS = [
    ('billing', '#ef4444', 'Billing and payment related'),
    ('technical', '#3b82f6', 'Technical support'),
    ('vip', '#f59e0b', 'VIP or priority customer'),
    ('follow-up', '#8b5cf6', 'Requires scheduled follow-up'),
    ('escalated', '#dc2626', 'Escalated issue'),
    ('onboarding', '#10b981', 'New customer onboarding'),
]

DEMO_CANNED = [
    ('Greeting', 'Thank you for contacting support. How may I assist you today?', 'Greeting'),
    ('Password Reset', 'I have initiated a password reset. Please check your email for further instructions.', 'Resolution'),
    ('Follow-up Scheduled', 'A follow-up has been scheduled. We will contact you on the agreed date.', 'Follow-up'),
    ('Escalation Notice', 'Your case has been escalated to a senior agent. You will receive an update shortly.', 'Escalation'),
    ('Resolution Confirmation', 'The issue has been resolved. Please let us know if you require any further assistance.', 'Resolution'),
    ('Awaiting Information', 'We are currently awaiting additional information from your side to proceed.', 'Pending'),
]

DEMO_DISPOSITIONS = [
    ('RESOLVED', 'Resolved – customer confirmed', 'Issue fixed and confirmed by caller'),
    ('INFO_PROVIDED', 'Information provided', 'Caller received the information requested'),
    ('CALLBACK', 'Callback scheduled', 'Outbound callback arranged'),
    ('ESCALATED', 'Escalated', 'Handed to another team or tier'),
    ('DUPLICATE', 'Duplicate', 'Duplicate of an existing ticket'),
    ('NO_RESPONSE', 'No response', 'Could not reach customer'),
    ('SPAM', 'Spam / invalid', 'Spam or invalid contact'),
]

DEMO_CALLS = [
    ('Sipho Dlamini', '+27821234567', 'Support', 'Incoming', 'Password reset not working', 'High', 'Open'),
    ('Nomsa Khumalo', '+27829876543', 'Billing', 'Incoming', 'Invoice discrepancy for March', 'Medium', 'In Progress'),
    ('Johan van der Berg', '+27831112233', 'IT', 'Incoming', 'VPN connection drops every hour', 'Critical', 'Open'),
    ('Aisha Patel', '+27824445566', 'HR', 'Outgoing', 'Follow-up on leave request', 'Low', 'Resolved'),
    ('Michael Chen', '+27827778899', 'Sales', 'Incoming', 'Quote for enterprise plan', 'Medium', 'Pending'),
    ('Fatima Abrahams', '+27820001122', 'Support', 'Incoming', 'App crashes on login', 'High', 'In Progress'),
    ('David Mokoena', '+27823334455', 'Billing', 'Incoming', 'Refund not received', 'High', 'Open'),
    ('Sarah Jacobs', '+27826667788', 'IT', 'Outgoing', 'Scheduled maintenance notification', 'Low', 'Closed'),
    ('Pieter Botha', '+27829990011', 'Sales', 'Incoming', 'Demo request for next week', 'Medium', 'Resolved'),
    ('Zanele Mthembu', '+27822223344', 'Support', 'Incoming', '2FA setup assistance', 'Medium', 'Open'),
    ('Ryan Smith', '+27825556677', 'HR', 'Incoming', 'Payslip access issue', 'Low', 'Pending'),
    ('Grace Ndlovu', '+27828889900', 'IT', 'Incoming', 'Email not syncing on mobile', 'High', 'In Progress'),
]


def _enrich_existing_calls():
    """Attach tags, activity, satisfaction to existing calls missing them."""
    from app import db
    from app.models import CallLog, Tag, User, CallActivity

    notes = []
    tags = Tag.query.order_by(Tag.TagID).all()
    users = User.query.limit(3).all()
    actor_id = users[0].UserID if users else None
    calls = CallLog.query.order_by(CallLog.CallID).limit(50).all()

    tagged = 0
    activities = 0
    filled = 0
    for i, call in enumerate(calls):
        if tags and not (call.tags or []):
            call.tags = [tags[i % len(tags)], tags[(i + 2) % len(tags)]]
            tagged += 1
        if call.Status in ('Resolved', 'Closed'):
            if call.TimeSpent is None:
                call.TimeSpent = 30
                filled += 1
            if call.SatisfactionRating is None:
                call.SatisfactionRating = 4 + (i % 2)
                filled += 1
            if not call.Resolution:
                call.Resolution = 'Issue resolved'
                filled += 1
        if actor_id and CallActivity.query.filter_by(CallID=call.CallID).count() == 0:
            db.session.add(CallActivity(
                CallID=call.CallID,
                UserID=actor_id,
                Action='Created',
                Details='Demo enrich',
                ActivityDate=call.DateLogged or datetime.utcnow(),
            ))
            activities += 1

    if tagged:
        notes.append(f'tagged {tagged} calls')
    if activities:
        notes.append(f'{activities} activities')
    if filled:
        notes.append(f'filled {filled} metrics')
    return notes


def bootstrap_demo_data(include_sample_calls=True):
    """Create demo users, departments, tags, canned responses, dispositions, and optional sample calls.

    Returns a list of created labels. Does not commit.
    """
    from app import db
    from app.models import (
        User, Department, CallLog, Tag, CannedResponse,
        DispositionCode, Contact, CallActivity,
    )

    created = []

    if User.query.count() == 0:
        for username, email, full, role, pwd in DEMO_USERS:
            u = User(
                Username=username,
                Email=email,
                FullName=full,
                Role=role,
                IsActive=True,
                Presence='Available',
            )
            u.set_password(pwd)
            db.session.add(u)
            created.append(username)

    for name in DEMO_DEPARTMENTS:
        if not Department.query.filter_by(DepartmentName=name).first():
            db.session.add(Department(DepartmentName=name, IsActive=True))
            created.append('dept:' + name)

    for name, colour, desc in DEMO_TAGS:
        if not Tag.query.filter_by(Name=name).first():
            db.session.add(Tag(Name=name, Colour=colour, Description=desc, IsActive=True))
            created.append('tag:' + name)

    if CannedResponse.query.count() == 0:
        for title, body, cat in DEMO_CANNED:
            db.session.add(CannedResponse(
                Title=title,
                Body=body,
                Category=cat,
                IsActive=True,
            ))
        created.append(f'{len(DEMO_CANNED)} canned responses')

    if DispositionCode.query.count() == 0:
        for code, label, desc in DEMO_DISPOSITIONS:
            db.session.add(DispositionCode(
                Code=code,
                Label=label,
                Description=desc,
                IsActive=True,
            ))
        created.append(f'{len(DEMO_DISPOSITIONS)} dispositions')

    db.session.flush()

    if include_sample_calls and CallLog.query.count() == 0:
        users = User.query.limit(3).all()
        assignees = [u.UserID for u in users]
        tags = Tag.query.order_by(Tag.TagID).all()
        now = datetime.utcnow()
        for i, (name, phone, dept, ctype, reason, pri, status) in enumerate(DEMO_CALLS):
            call = CallLog(
                CallerName=name,
                PhoneNumber=phone,
                Department=dept,
                CallType=ctype,
                ReasonForCall=reason,
                Priority=pri,
                Status=status,
                AssignedTo=assignees[i % len(assignees)] if assignees else None,
                DateLogged=now - timedelta(hours=i * 5),
                LastUpdated=now - timedelta(hours=i * 4),
                TimeSpent=30 if status in ('Resolved', 'Closed') else None,
                SatisfactionRating=(4 + (i % 2)) if status in ('Resolved', 'Closed') else None,
                Resolution='Issue resolved' if status in ('Resolved', 'Closed') else None,
            )
            if status in ('Open', 'In Progress', 'Pending') and i % 3 == 0:
                call.FollowUpDate = now + timedelta(days=1 if i % 2 == 0 else -1)
            if tags:
                call.tags = [tags[i % len(tags)], tags[(i + 2) % len(tags)]]
            db.session.add(call)
            db.session.flush()
            actor_id = assignees[i % len(assignees)] if assignees else (users[0].UserID if users else None)
            if actor_id:
                db.session.add(CallActivity(
                    CallID=call.CallID,
                    UserID=actor_id,
                    Action='Created',
                    Details=f'Demo seed · {status}',
                    ActivityDate=call.DateLogged,
                ))
            if not Contact.query.filter_by(PhoneNumber=phone).first():
                db.session.add(Contact(
                    PhoneNumber=phone,
                    DisplayName=name,
                    IsVIP=(i % 5 == 0),
                ))
        created.append(str(len(DEMO_CALLS)) + ' sample calls')
    elif include_sample_calls and CallLog.query.count() > 0:
        # Re-seed enrich: fill gaps so dashboard analytics are complete
        for note in _enrich_existing_calls():
            created.append(note)

    return created
