from datetime import datetime, timedelta

from app import db
from app.models import CallLog, User
from app.utils.helpers import get_dashboard_stats, sla_risk


EXPECTED_STAT_KEYS = {
    'total_calls',
    'open_calls',
    'resolved_today',
    'high_priority',
    'unassigned',
    'my_open',
    'my_overdue',
    'overdue_followups',
    'sla_breach',
    'sla_warn',
    'avg_satisfaction',
    'avg_handle_mins',
    'status_counts',
    'priority_counts',
    'calls_per_day',
    'dept_counts',
    'tag_counts',
    'workload',
    'recent_calls',
    'recent_activity',
    'unread_notifications',
    'sla_thresholds',
}


def test_dashboard_requires_login(client):
    r = client.get('/dashboard', follow_redirects=False)
    assert r.status_code in (301, 302)


def test_dashboard_page_loads(auth_client):
    r = auth_client.get('/dashboard')
    assert r.status_code == 200
    assert b'Dashboard' in r.data or b'dashboard' in r.data.lower()
    cache = r.headers.get('Cache-Control', '')
    assert 'no-store' in cache
    assert 'private' in cache


def test_agent_can_open_dashboard(agent_client):
    r = agent_client.get('/dashboard')
    assert r.status_code == 200


def test_dashboard_stats_shape(app):
    with app.app_context():
        admin = User.query.filter_by(Username='admin').first()
        call = CallLog(
            CallerName='Dash Caller',
            PhoneNumber='+27829990000',
            CallType='Incoming',
            ReasonForCall='dashboard stats',
            Priority='High',
            Status='Open',
            Department='Support',
            DateLogged=datetime.utcnow() - timedelta(hours=1),
        )
        db.session.add(call)
        db.session.commit()
        stats = get_dashboard_stats(user=admin)
        assert EXPECTED_STAT_KEYS.issubset(stats.keys())
        assert stats['total_calls'] >= 1
        assert stats['open_calls'] >= 1
        assert stats['high_priority'] >= 1
        assert isinstance(stats['status_counts'], dict)
        assert isinstance(stats['priority_counts'], dict)
        assert 'High' in stats['priority_counts']
        assert len(stats['calls_per_day']) == 7
        for key in stats['calls_per_day']:
            assert isinstance(key, str)
            assert len(key) == 10


def test_sla_risk_open_high_is_not_ok_when_old(app):
    with app.app_context():
        call = CallLog(
            CallerName='Old',
            PhoneNumber='+27821112222',
            CallType='Incoming',
            ReasonForCall='aged',
            Priority='High',
            Status='Open',
            DateLogged=datetime.utcnow() - timedelta(hours=30),
        )
        assert sla_risk(call) == 'breach'


def test_agent_denied_reports(agent_client):
    r = agent_client.get('/reports/')
    assert r.status_code in (302, 403)


def test_manager_can_open_reports(manager_client):
    r = manager_client.get('/reports/')
    assert r.status_code == 200
