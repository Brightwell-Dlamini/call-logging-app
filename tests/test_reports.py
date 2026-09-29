from datetime import datetime
from calendar import monthrange

from app.blueprints.reports import month_bounds
from app.models import SystemAudit


def test_month_bounds_january():
    start, end = month_bounds(2026, 1)
    assert start == datetime(2026, 1, 1)
    assert end == datetime(2026, 2, 1)


def test_month_bounds_february_non_leap():
    start, end = month_bounds(2025, 2)
    assert start == datetime(2025, 2, 1)
    assert end == datetime(2025, 3, 1)
    assert (end - start).days == monthrange(2025, 2)[1]


def test_month_bounds_december_rolls_year():
    start, end = month_bounds(2026, 12)
    assert start == datetime(2026, 12, 1)
    assert end == datetime(2027, 1, 1)


def test_reports_index_requires_manager(client):
    client.post('/login', data={'username': 'agent1', 'password': 'agent123'}, follow_redirects=True)
    r = client.get('/reports/')
    assert r.status_code == 403


def test_reports_index_allows_admin(auth_client):
    r = auth_client.get('/reports/')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Download Excel' in body
    assert 'Download PDF' in body


def test_export_excel_writes_audit(auth_client, app):
    r = auth_client.get('/reports/export/excel')
    assert r.status_code == 200
    assert 'spreadsheetml' in (r.mimetype or '')
    with app.app_context():
        row = SystemAudit.query.filter_by(Action='report.export.excel').first()
        assert row is not None
        assert row.TargetType == 'report'


def test_export_pdf_writes_audit(auth_client, app):
    r = auth_client.get('/reports/export/pdf')
    assert r.status_code == 200
    assert r.mimetype == 'application/pdf'
    with app.app_context():
        row = SystemAudit.query.filter_by(Action='report.export.pdf').first()
        assert row is not None
        assert row.TargetID == 'pdf'


def test_agent_cannot_export(client):
    client.post('/login', data={'username': 'agent1', 'password': 'agent123'}, follow_redirects=True)
    assert client.get('/reports/export/excel').status_code == 403
    assert client.get('/reports/export/pdf').status_code == 403
