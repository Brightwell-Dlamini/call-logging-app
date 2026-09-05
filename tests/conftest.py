import pytest
from app import create_app, db
from app.models import User, Department


@pytest.fixture
def app():
    application = create_app('testing')
    with application.app_context():
        db.create_all()
        admin = User(Username='admin', Email='admin@test.local', FullName='Admin', Role='Admin', IsActive=True)
        admin.set_password('admin123')
        agent = User(Username='agent1', Email='agent@test.local', FullName='Agent One', Role='Agent', IsActive=True)
        agent.set_password('agent123')
        db.session.add_all([admin, agent, Department(DepartmentName='Support', IsActive=True)])
        db.session.commit()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client):
    client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
    return client
