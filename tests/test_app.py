from app.models import CallLog, User
from app import db


def test_health(client):
    r = client.get('/health')
    assert r.status_code == 200
    data = r.get_json()
    assert data['status'] in ('healthy', 'degraded')
    assert data['service'] == 'call-logging-app'


def test_login_page(client):
    r = client.get('/login')
    assert r.status_code == 200
    assert b'CallLog' in r.data or b'login' in r.data.lower()


def test_login_success(client):
    r = client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
    assert r.status_code == 200


def test_create_call(auth_client, app):
    with app.app_context():
        before = CallLog.query.count()
    r = auth_client.post('/calls/new', data={
        'caller_name': 'Test Caller',
        'phone_number': '+27820000000',
        'department': 'Support',
        'call_type': 'Incoming',
        'reason_for_call': 'pytest create',
        'priority': 'Medium',
        'assigned_to': 0,
        'notes': '',
    }, follow_redirects=True)
    assert r.status_code == 200
    with app.app_context():
        assert CallLog.query.count() == before + 1


def test_bulk_status(auth_client, app):
    with app.app_context():
        c = CallLog(
            CallerName='Bulk', PhoneNumber='+2782111', CallType='Incoming',
            ReasonForCall='bulk test', Priority='High', Status='Open'
        )
        db.session.add(c)
        db.session.commit()
        cid = c.CallID
    r = auth_client.post('/calls/bulk', json={'ids': [cid], 'action': 'progress'})
    assert r.status_code == 200
    data = r.get_json()
    assert data.get('ok') is True
    with app.app_context():
        assert CallLog.query.get(cid).Status == 'In Progress'


def test_api_stats(auth_client):
    r = auth_client.get('/api/dashboard/stats')
    assert r.status_code == 200
    data = r.get_json()
    assert 'total_calls' in data
    assert 'open_calls' in data
