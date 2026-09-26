from datetime import datetime
from calendar import monthrange

from app.blueprints.reports import month_bounds, parse_export_range


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


def test_parse_export_range(app):
    with app.test_request_context('/reports/export/excel?from=2026-01-01&to=2026-01-31'):
        start, end = parse_export_range()
        assert start == datetime(2026, 1, 1)
        assert end == datetime(2026, 2, 1)


def test_reports_require_manager(client):
    r = client.get('/reports/', follow_redirects=False)
    assert r.status_code in (302, 401, 403)
