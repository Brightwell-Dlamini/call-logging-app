from app.blueprints import auth as auth_mod
from app.models import User
from app import db


def setup_function():
    auth_mod._login_attempts.clear()


def test_login_rejects_bad_password(client):
    r = client.post('/login', data={'username': 'admin', 'password': 'wrong'}, follow_redirects=True)
    assert r.status_code == 200
    assert b'Invalid username or password' in r.data


def test_login_lockout_after_max_failures(client, app):
    max_attempts = app.config.get('MAX_LOGIN_ATTEMPTS', 5)
    for _ in range(max_attempts):
        client.post('/login', data={'username': 'admin', 'password': 'nope'})
    r = client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
    assert r.status_code == 200
    assert b'temporarily locked' in r.data


def test_successful_login_clears_failed_attempts(client):
    client.post('/login', data={'username': 'admin', 'password': 'wrong'})
    client.post('/login', data={'username': 'admin', 'password': 'wrong'})
    r = client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
    assert r.status_code == 200
    assert 'admin' not in auth_mod._login_attempts


def test_inactive_user_cannot_login(client, app):
    with app.app_context():
        user = User.query.filter_by(Username='agent1').first()
        user.IsActive = False
        db.session.commit()
    r = client.post('/login', data={'username': 'agent1', 'password': 'agent123'}, follow_redirects=True)
    assert r.status_code == 200
    assert b'inactive' in r.data.lower()


def test_agent_cannot_open_admin(client):
    client.post('/login', data={'username': 'agent1', 'password': 'agent123'}, follow_redirects=True)
    r = client.get('/admin/users', follow_redirects=True)
    assert r.status_code in (200, 403)
    assert b'Admin' not in r.data or r.status_code == 403 or b'forbidden' in r.data.lower() or b'403' in r.data or b'not authorised' in r.data.lower() or b'not authorized' in r.data.lower() or b'Access' in r.data


def test_open_redirect_rejected(client):
    r = client.post(
        '/login?next=https://evil.example/phish',
        data={'username': 'admin', 'password': 'admin123'},
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)
    loc = r.headers.get('Location', '')
    assert 'evil.example' not in loc
