from app.models import SystemAudit


def test_health_echoes_request_id(client):
    r = client.get('/health', headers={'X-Request-ID': 'test-rid-001'})
    assert r.status_code == 200
    assert r.headers.get('X-Request-ID') == 'test-rid-001'
    assert r.get_json().get('request_id') == 'test-rid-001'


def test_security_headers_present(client):
    r = client.get('/login')
    assert r.headers.get('X-Content-Type-Options') == 'nosniff'
    assert r.headers.get('X-Frame-Options') == 'SAMEORIGIN'
    assert r.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'
    assert r.headers.get('X-Request-ID')


def test_seed_does_not_return_passwords(client):
    r = client.get('/seed')
    assert r.status_code == 200
    data = r.get_json()
    assert 'logins' not in data
    blob = str(data).lower()
    assert 'admin123' not in blob
    assert 'agent123' not in blob


def test_export_excel_writes_audit(auth_client, app):
    r = auth_client.get('/reports/export/excel')
    assert r.status_code == 200
    with app.app_context():
        row = SystemAudit.query.filter_by(Action='report.export').first()
        assert row is not None
        assert row.TargetID == 'excel'
