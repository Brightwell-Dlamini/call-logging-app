from datetime import datetime, timedelta

from app import db
from app.models import CallLog
from app.utils.helpers import sla_risk, count_open_sla, get_dashboard_stats


def _add_open(name, priority, hours_ago):
    call = CallLog(
        CallerName=name,
        PhoneNumber='+27820000000',
        CallType='Incoming',
        ReasonForCall='sla fixture',
        Priority=priority,
        Status='Open',
        DateLogged=datetime.utcnow() - timedelta(hours=hours_ago),
    )
    db.session.add(call)
    return call


def test_count_open_sla_matches_row_scan(app):
    with app.app_context():
        _add_open('fresh-critical', 'Critical', 1)   # ok
        _add_open('warn-critical', 'Critical', 3)    # warn (2h warn / 4h breach)
        _add_open('breach-critical', 'Critical', 6)  # breach
        _add_open('warn-high', 'High', 10)           # warn (8/24)
        db.session.commit()

        open_calls = CallLog.query.filter(CallLog.Status == 'Open').all()
        expected_breach = sum(1 for c in open_calls if sla_risk(c) == 'breach')
        expected_warn = sum(1 for c in open_calls if sla_risk(c) == 'warn')
        assert count_open_sla('breach') == expected_breach
        assert count_open_sla('warn') == expected_warn


def test_dashboard_stats_include_sla(app):
    with app.app_context():
        stats = get_dashboard_stats()
        assert 'sla_breach' in stats
        assert 'sla_warn' in stats
        assert isinstance(stats['sla_breach'], int)
        assert isinstance(stats['sla_warn'], int)
