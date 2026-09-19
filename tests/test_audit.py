from app import db
from app.models import SystemAudit, User
from app.utils.audit import log_audit


def test_log_audit_helper(app):
    with app.app_context():
        admin = User.query.filter_by(Username='admin').first()
        log_audit('user.create', 'created agent', user_id=admin.UserID, target_type='user', target_id=99)
        db.session.commit()
        row = SystemAudit.query.filter_by(Action='user.create').first()
        assert row is not None
        assert row.TargetType == 'user'
        assert row.TargetID == '99'
        assert row.UserID == admin.UserID


def test_login_writes_audit(client, app):
    client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
    with app.app_context():
        assert SystemAudit.query.filter_by(Action='auth.login').count() >= 1


def test_failed_login_writes_audit(client, app):
    client.post('/login', data={'username': 'admin', 'password': 'wrong'}, follow_redirects=True)
    with app.app_context():
        assert SystemAudit.query.filter_by(Action='auth.login_failed').count() >= 1


def test_admin_user_create_audited(auth_client, app):
    auth_client.post('/admin/users/new', data={
        'username': 'auditor',
        'email': 'auditor@test.local',
        'full_name': 'Audit User',
        'role': 'Agent',
        'password': 'agent12345',
        'is_active': 'y',
    }, follow_redirects=True)
    with app.app_context():
        created = User.query.filter_by(Username='auditor').first()
        assert created is not None
        assert SystemAudit.query.filter_by(Action='user.create').count() >= 1


def test_audit_page_requires_admin(client):
    client.post('/login', data={'username': 'agent1', 'password': 'agent123'}, follow_redirects=True)
    r = client.get('/admin/activities')
    assert r.status_code in (302, 403)


def test_health_returns_request_id(client):
    r = client.get('/health', headers={'X-Request-ID': 'abc12345deadbeef'})
    assert r.status_code == 200
    assert r.headers.get('X-Request-ID') == 'abc12345deadbeef'


def test_health_generates_request_id(client):
    r = client.get('/health')
    assert r.status_code == 200
    rid = r.headers.get('X-Request-ID')
    assert rid
    assert len(rid) >= 8


def test_report_export_writes_audit(auth_client, app):
    r = auth_client.get('/reports/export/excel')
    assert r.status_code == 200
    with app.app_context():
        assert SystemAudit.query.filter_by(Action='report.export_excel').count() >= 1


def test_seed_writes_audit(client, app):
    r = client.get('/seed')
    assert r.status_code == 200
    with app.app_context():
        assert SystemAudit.query.filter_by(Action='ops.seed').count() >= 1
