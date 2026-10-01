from app.blueprints.auth import safe_next_url
from app.models import User
from app import db


def test_safe_next_url_rejects_open_redirects():
    fallback = '/dashboard'
    assert safe_next_url('/calls', fallback) == '/calls'
    assert safe_next_url('/calls/1?tab=notes', fallback) == '/calls/1?tab=notes'
    assert safe_next_url('https://evil.example/phish', fallback) == fallback
    assert safe_next_url('//evil.example/phish', fallback) == fallback
    assert safe_next_url('/\\evil.example', fallback) == fallback
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
    assert r.headers.get('Cross-Origin-Opener-Policy') == 'same-origin'
    csp = r.headers.get('Content-Security-Policy', '')
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert 'cdn.jsdelivr.net' in csp


def test_login_html_is_not_stored(client):
    r = client.get('/login')
    assert r.status_code == 200
    assert r.headers.get('Cache-Control') == 'no-store'
    assert "default-src 'self'" in (r.headers.get('Content-Security-Policy') or '')


def test_agent_cannot_open_admin_users(client):
    client.post('/login', data={'username': 'agent1', 'password': 'agent123'}, follow_redirects=True)
    r = client.get('/admin/users')
    assert r.status_code in (302, 403)
