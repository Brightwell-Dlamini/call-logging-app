"""Basic model unit tests."""
import pytest
from app import create_app, db
from app.models import User, CallLog, Department


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_user_password_hashing(app):
    with app.app_context():
        u = User(Username='test', Email='t@test.com', FullName='Test User', Role='Agent')
        u.set_password('secret123')
        assert u.PasswordHash != 'secret123'
        assert u.check_password('secret123')
        assert not u.check_password('wrong')


def test_user_roles(app):
    with app.app_context():
        admin = User(Username='a', Email='a@t.com', FullName='A', Role='Admin')
        manager = User(Username='m', Email='m@t.com', FullName='M', Role='Manager')
        agent = User(Username='g', Email='g@t.com', FullName='G', Role='Agent')
        assert admin.is_admin and admin.is_manager and admin.is_agent
        assert not manager.is_admin and manager.is_manager
        assert not agent.is_admin and not agent.is_manager and agent.is_agent


def test_call_creation(app):
    with app.app_context():
        call = CallLog(
            CallerName='John Doe',
            PhoneNumber='+1234567890',
            CallType='Incoming',
            ReasonForCall='Support request',
            Priority='High',
            Status='Open'
        )
        db.session.add(call)
        db.session.commit()
        assert call.CallID is not None
        assert CallLog.query.count() == 1
