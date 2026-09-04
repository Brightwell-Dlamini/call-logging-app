"""
Seed the database with sample data.
Run: python -c "from scripts.seed import seed; seed()"
"""
import random
from datetime import datetime, timedelta
from faker import Faker
from app import create_app, db
from app.models import User, CallLog, CallActivity, Department

fake = Faker()


def seed():
    app = create_app('development')
    with app.app_context():
        print('Seeding database...')

        dept_names = ['IT', 'HR', 'Sales', 'Support', 'Billing']
        for name in dept_names:
            if not Department.query.filter_by(DepartmentName=name).first():
                db.session.add(Department(DepartmentName=name, IsActive=True))
        db.session.commit()
        print('Departments created.')

        if not User.query.filter_by(Username='admin').first():
            admin = User(
                Username='admin',
                Email='admin@calllog.local',
                FullName='System Administrator',
                Role='Admin',
                IsActive=True
            )
            admin.set_password('admin123')
            db.session.add(admin)

        sample_users = [
            ('agent1', 'Alice Agent', 'agent1@calllog.local', 'Agent'),
            ('agent2', 'Bob Agent', 'agent2@calllog.local', 'Agent'),
            ('agent3', 'Carol Agent', 'agent3@calllog.local', 'Agent'),
            ('manager1', 'Diana Manager', 'manager1@calllog.local', 'Manager'),
            ('agent4', 'Eve Agent', 'agent4@calllog.local', 'Agent'),
        ]
        for username, fullname, email, role in sample_users:
            if not User.query.filter_by(Username=username).first():
                u = User(
                    Username=username,
                    Email=email,
                    FullName=fullname,
                    Role=role,
                    IsActive=True
                )
                u.set_password('password123')
                db.session.add(u)
        db.session.commit()
        print('Users created.')

        agents = User.query.filter(User.Role.in_(['Agent', 'Manager', 'Admin'])).all()
        departments = [d.DepartmentName for d in Department.query.filter_by(IsActive=True).all()]
        statuses = ['Open', 'In Progress', 'Pending', 'Resolved', 'Closed']
        priorities = ['Low', 'Medium', 'High', 'Critical']
        call_types = ['Incoming', 'Outgoing']

        if CallLog.query.count() < 20:
            for i in range(75):
                days_ago = random.randint(0, 30)
                date_logged = datetime.utcnow() - timedelta(days=days_ago, hours=random.randint(0, 23))
                status = random.choice(statuses)
                agent = random.choice(agents) if random.random() > 0.15 else None
                call = CallLog(
                    CallerName=fake.name(),
                    PhoneNumber=fake.phone_number()[:20],
                    Department=random.choice(departments),
                    CallType=random.choice(call_types),
                    ReasonForCall=fake.sentence(nb_words=12),
                    Priority=random.choice(priorities),
                    Status=status,
                    AssignedTo=agent.UserID if agent else None,
                    Notes=fake.text(max_nb_chars=100) if random.random() > 0.5 else None,
                    DateLogged=date_logged,
                    LastUpdated=date_logged + timedelta(hours=random.randint(0, 48)),
                    Resolution=fake.sentence() if status in ('Resolved', 'Closed') else None,
                    TimeSpent=random.randint(5, 120) if status in ('Resolved', 'Closed') else None,
                    SatisfactionRating=random.randint(1, 5) if status in ('Resolved', 'Closed') and random.random() > 0.3 else None
                )
                db.session.add(call)
                db.session.flush()
                actor = agent or agents[0]
                db.session.add(CallActivity(
                    CallID=call.CallID,
                    UserID=actor.UserID,
                    Action='Created',
                    Details='Seeded call',
                    ActivityDate=date_logged
                ))
            db.session.commit()
            print('Sample calls created.')
        else:
            print('Calls already present; skipping call seed.')

        print('Seed completed successfully.')
        print('Login: admin / admin123')
        print('Agents: agent1..agent4 / password123')


if __name__ == '__main__':
    seed()
