"""Shared demo-data bootstrap used by the factory and /seed."""
from datetime import datetime, timedelta

DEMO_USERS = [
    ('admin', 'admin@calllog.local', 'System Administrator', 'Admin', 'admin123'),
    ('agent1', 'agent1@calllog.local', 'Thabo Molefe', 'Agent', 'agent123'),
    ('manager1', 'manager1@calllog.local', 'Lerato Nkosi', 'Manager', 'manager123'),
]

DEMO_DEPARTMENTS = ['IT', 'HR', 'Sales', 'Support', 'Billing']

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


def bootstrap_demo_data(include_sample_calls=True):
    """Create demo users, departments, and optional sample calls if missing.

    Returns a list of created labels. Does not commit.
    """
    from app import db
    from app.models import User, Department, CallLog

    created = []

    if User.query.count() == 0:
        for username, email, full, role, pwd in DEMO_USERS:
            u = User(Username=username, Email=email, FullName=full, Role=role, IsActive=True)
            u.set_password(pwd)
            db.session.add(u)
            created.append(username)

    for name in DEMO_DEPARTMENTS:
        if not Department.query.filter_by(DepartmentName=name).first():
            db.session.add(Department(DepartmentName=name, IsActive=True))
            created.append('dept:' + name)

    db.session.flush()

    if include_sample_calls and CallLog.query.count() == 0:
        assignees = [u.UserID for u in User.query.limit(3).all()]
        now = datetime.utcnow()
        for i, (name, phone, dept, ctype, reason, pri, status) in enumerate(DEMO_CALLS):
            db.session.add(CallLog(
                CallerName=name,
                PhoneNumber=phone,
                Department=dept,
                CallType=ctype,
                ReasonForCall=reason,
                Priority=pri,
                Status=status,
                AssignedTo=assignees[i % len(assignees)] if assignees else None,
                DateLogged=now - timedelta(hours=i * 5),
                TimeSpent=30 if status in ('Resolved', 'Closed') else None,
                SatisfactionRating=5 if status in ('Resolved', 'Closed') else None,
                Resolution='Issue resolved' if status in ('Resolved', 'Closed') else None,
            ))
        created.append(str(len(DEMO_CALLS)) + ' sample calls')

    return created
