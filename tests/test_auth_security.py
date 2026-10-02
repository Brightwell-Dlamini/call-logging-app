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


def test_agent_cannot_open_admin_users(client):
    client.post('/login', data={'username': 'agent1', 'password': 'agent123'}, follow_redirects=True)
    r = client.get('/admin/users')
    assert r.status_code in (302, 403)


def test_get_logout_does_not_end_session(client):
    client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
    page = client.get('/logout')
    assert page.status_code == 200
    assert b'Sign out' in page.data
    still = client.get('/dashboard')
    assert still.status_code == 200


def test_post_logout_ends_session(client):
    client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
    done = client.post('/logout', follow_redirects=False)
    assert done.status_code in (302, 303)
    assert '/login' in done.headers.get('Location', '')
    after = client.get('/dashboard', follow_redirects=False)
    assert after.status_code in (302, 303)
    assert '/login' in after.headers.get('Location', '')
