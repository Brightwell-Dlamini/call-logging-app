from datetime import datetime, timedelta

from app.blueprints.auth import safe_next_url


def test_safe_next_url_rejects_open_redirects():
    fallback = '/dashboard'
    assert safe_next_url('/calls', fallback) == '/calls'
    assert safe_next_url('/calls/1?tab=notes', fallback) == '/calls/1?tab=notes'
    assert safe_next_url('https://evil.example/phish', fallback) == fallback
    assert safe_next_url('//evil.example/phish', fallback) == fallback
    assert safe_next_url('/\\\\evil.example', fallback) == fallback
    assert safe_next_url(None, fallback) == fallback
    assert safe_next_url('', fallback) == fallback


def test_login_next_does_not_redirect_offsite(client):
    r = client.post(
        '/login?next=//evil.example/steal',
        data={'username': 'admin', 'password': 'admin123'},
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)
    location = r.headers.get('Location', '')
    assert 'evil.example' not in location
    assert location.startswith('/')


def test_login_next_allows_local_path(client):
    r = client.post(
        '/login?next=/calls',
        data={'username': 'admin', 'password': 'admin123'},
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)
    assert '/calls' in r.headers.get('Location', '')


def test_health_sets_security_headers(client):
    r = client.get('/health')
    assert r.status_code == 200
    assert r.headers.get('X-Content-Type-Options') == 'nosniff'
    assert r.headers.get('X-Frame-Options') == 'DENY'
    assert r.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'
    assert r.headers.get('X-Request-ID')


def test_agent_cannot_open_admin_users(client):
    client.post('/login', data={'username': 'agent1', 'password': 'agent123'}, follow_redirects=True)
    r = client.get('/admin/users')
    assert r.status_code in (302, 403)


def test_remember_cookie_flags():
    from config import Config, ProductionConfig
    assert Config.REMEMBER_COOKIE_HTTPONLY is True
    assert Config.REMEMBER_COOKIE_SAMESITE == 'Lax'
    assert Config.REMEMBER_COOKIE_DURATION <= timedelta(days=90)
    assert ProductionConfig.REMEMBER_COOKIE_SECURE is True
    assert ProductionConfig.SESSION_COOKIE_SECURE is True
    assert Config.SESSION_IDLE_MINUTES == 30


def test_idle_session_requires_login(client):
    client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
    stale = (datetime.utcnow() - timedelta(hours=2)).replace(microsecond=0).isoformat()
    with client.session_transaction() as sess:
        sess['last_activity'] = stale
    r = client.get('/dashboard', follow_redirects=False)
    assert r.status_code in (302, 303)
    assert '/login' in (r.headers.get('Location') or '')
    again = client.get('/dashboard', follow_redirects=False)
    assert again.status_code in (302, 303)
    assert '/login' in (again.headers.get('Location') or '')


def test_active_session_is_refreshed(client):
    client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
    recent = (datetime.utcnow() - timedelta(minutes=1)).replace(microsecond=0).isoformat()
    with client.session_transaction() as sess:
        sess['last_activity'] = recent
    r = client.get('/dashboard', follow_redirects=False)
    assert r.status_code == 200
    with client.session_transaction() as sess:
        assert sess.get('last_activity')
        assert sess.get('last_activity') != recent
