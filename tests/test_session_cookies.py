import os

from config import apply_cookie_security, https_deployed
from flask import Flask


def test_login_sets_httponly_samesite_session_cookie(client):
    with client.session_transaction() as sess:
        sess['pre_login'] = 'marker'
    response = client.post(
        '/login',
        data={'username': 'admin', 'password': 'admin123', 'remember_me': 'y'},
        follow_redirects=False,
    )
    assert response.status_code in (302, 303)
    cookies = response.headers.getlist('Set-Cookie')
    session_cookie = next((c for c in cookies if c.startswith('clp_session=')), '')
    assert session_cookie
    assert 'HttpOnly' in session_cookie
    assert 'SameSite=Lax' in session_cookie
    assert 'Secure' not in session_cookie
    with client.session_transaction() as sess:
        assert 'pre_login' not in sess
        assert sess.get('_user_id')


def test_logout_clears_session(client):
    client.post('/login', data={'username': 'admin', 'password': 'admin123'})
    response = client.get('/logout', follow_redirects=False)
    assert response.status_code in (302, 303)
    with client.session_transaction() as sess:
        assert '_user_id' not in sess


def test_https_deploy_forces_secure_cookies(monkeypatch):
    monkeypatch.setenv('VERCEL_ENV', 'production')
    monkeypatch.delenv('SESSION_COOKIE_SECURE', raising=False)
    monkeypatch.delenv('FLASK_ENV', raising=False)
    app = Flask(__name__)
    app.config['TESTING'] = False
    apply_cookie_security(app)
    assert https_deployed() is True
    assert app.config['SESSION_COOKIE_SECURE'] is True
    assert app.config['REMEMBER_COOKIE_SECURE'] is True
    assert app.config['REMEMBER_COOKIE_HTTPONLY'] is True
    assert app.config['REMEMBER_COOKIE_SAMESITE'] == 'Lax'
    assert app.config['SESSION_COOKIE_NAME'] == 'clp_session'


def test_session_cookie_secure_env_overrides_deploy(monkeypatch):
    monkeypatch.setenv('VERCEL_ENV', 'preview')
    monkeypatch.setenv('SESSION_COOKIE_SECURE', '0')
    app = Flask(__name__)
    app.config['TESTING'] = False
    apply_cookie_security(app)
    assert app.config['SESSION_COOKIE_SECURE'] is False
    assert app.config['REMEMBER_COOKIE_SECURE'] is False


def test_testing_config_does_not_force_secure(monkeypatch):
    monkeypatch.setenv('VERCEL_ENV', 'production')
    monkeypatch.delenv('SESSION_COOKIE_SECURE', raising=False)
    app = Flask(__name__)
    app.config['TESTING'] = True
    apply_cookie_security(app)
    assert app.config['SESSION_COOKIE_SECURE'] is False
    assert os.environ.get('VERCEL_ENV') == 'production'
