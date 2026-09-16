from datetime import datetime
from calendar import monthrange

from app.blueprints.reports import month_bounds
from app.db_indexes import INDEX_STATEMENTS


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


def test_index_statements_cover_dashboard_filters():
    joined = '\n'.join(INDEX_STATEMENTS)
    assert 'ix_call_log_datelogged' in joined
    assert 'ix_call_log_priority_status' in joined
    assert 'ix_system_audit_user_created' in joined
