"""Auth lockout, seed gating, and report RBAC."""
import os

from app.blueprints import auth as auth_mod
from app.models import SystemAudit


def setup_function():
    auth_mod._login_attempts.clear()


def test_login_lockout_after_configured_failures(client, app):
    app.config['MAX_LOGIN_ATTEMPTS'] = 3
    app.config['LOGIN_LOCKOUT_MINUTES'] = 15
    for _ in range(3):
        r = client.post('/login', data={'username': 'admin', 'password': 'wrong'})
        assert r.status_code == 200
        assert b'Invalid username or password' in r.data
    locked = client.post('/login', data={'username': 'admin', 'password': 'wrong'})
    assert b'temporarily locked' in locked.data
    still_locked = client.post('/login', data={'username': 'admin', 'password': 'admin123'})
    assert b'temporarily locked' in still_locked.data
    with app.app_context():
        assert SystemAudit.query.filter_by(Action='auth.lockout').count() >= 1


def test_inactive_user_cannot_login(client, app):
    from app import db
    from app.models import User

    with app.app_context():
        user = User.query.filter_by(Username='agent1').first()
        user.IsActive = False
        db.session.commit()
    r = client.post('/login', data={'username': 'agent1', 'password': 'agent123'})
    assert r.status_code == 200
    assert b'inactive' in r.data.lower()
    dash = client.get('/dashboard', follow_redirects=False)
    assert dash.status_code in (302, 401, 404) or b'login' in dash.data.lower() or dash.status_code == 308


def test_open_redirect_rejected(client):
    r = client.post(
        '/login?next=https://evil.example/',
        data={'username': 'admin', 'password': 'admin123'},
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)
    loc = r.headers.get('Location', '')
    assert 'evil.example' not in loc


def test_seed_requires_token_when_configured(client, monkeypatch):
    monkeypatch.setenv('SEED_TOKEN', 'secret-seed')
    denied = client.get('/seed')
    assert denied.status_code == 403
    body = denied.get_json()
    assert body['status'] == 'forbidden'
    ok = client.get('/seed', headers={'X-Seed-Token': 'secret-seed'})
    assert ok.status_code == 200
    data = ok.get_json()
    assert data['status'] == 'ok'
    monkeypatch.delenv('SEED_TOKEN', raising=False)


def test_seed_disabled_in_production(client, monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.delenv('ENABLE_SEED', raising=False)
    r = client.get('/seed')
    assert r.status_code == 403
    assert r.get_json()['status'] == 'disabled'
    monkeypatch.delenv('FLASK_ENV', raising=False)


def test_agent_forbidden_from_reports(agent_client):
    r = agent_client.get('/reports/')
    assert r.status_code == 403


def test_manager_can_open_reports(manager_client):
    r = manager_client.get('/reports/')
    assert r.status_code == 200


def test_agent_forbidden_from_admin(agent_client):
    r = agent_client.get('/admin/users')
    assert r.status_code in (302, 403)


def test_health_backend_sqlite(client):
    r = client.get('/health')
    assert r.status_code == 200
    data = r.get_json()
    assert data['backend'] == 'sqlite'
    assert data['database'] == 'ok'
