from datetime import datetime, timedelta
from calendar import monthrange

from app.blueprints.reports import month_bounds, parse_iso_date, export_window
from app.models.audit import SystemAudit


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


def test_parse_iso_date_valid_and_invalid():
    assert parse_iso_date('2026-09-12') == datetime(2026, 9, 12)
    assert parse_iso_date('not-a-date', fallback=datetime(2020, 1, 1)) == datetime(2020, 1, 1)
    assert parse_iso_date(None, fallback=None) is None


def test_export_window_swaps_inverted_and_caps_span():
    start, end, from_s, to_s = export_window('2026-12-31', '2026-01-01')
    assert from_s == '2026-01-01'
    assert to_s == '2026-12-31'
    assert start == datetime(2026, 1, 1)
    assert end == datetime(2027, 1, 1)

    start, end, from_s, to_s = export_window('2020-01-01', '2024-12-31')
    assert (end - start).days <= 367
    assert to_s == '2024-12-31'


def test_export_excel_writes_audit(auth_client, app):
    r = auth_client.get('/reports/export/excel?from=2026-09-01&to=2026-09-12')
    assert r.status_code == 200
    assert 'spreadsheet' in (r.mimetype or '')
    with app.app_context():
        row = SystemAudit.query.filter_by(Action='report.export_excel').order_by(
            SystemAudit.AuditID.desc()
        ).first()
        assert row is not None
        assert '2026-09-01' in (row.Details or '')
