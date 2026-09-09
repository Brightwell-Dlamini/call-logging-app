from app.models import CallLog
from app import db


def test_api_stats_includes_handle_time(auth_client):
    r = auth_client.get('/api/dashboard/stats')
    assert r.status_code == 200
    data = r.get_json()
    assert data.get('ok') is True
    assert 'avg_handle_mins' in data
    assert 'total_calls' in data


def test_api_create_rejects_missing_fields(auth_client):
    r = auth_client.post('/api/calls', json={'caller_name': 'Only name'})
    assert r.status_code == 400
    data = r.get_json()
    assert data['ok'] is False
    assert 'missing' in data


def test_api_create_rejects_bad_priority(auth_client):
    r = auth_client.post('/api/calls', json={
        'caller_name': 'Pri',
        'phone_number': '+27820009999',
        'reason_for_call': 'bad pri',
        'call_type': 'Incoming',
        'priority': 'URGENT',
    })
    assert r.status_code == 400
    data = r.get_json()
    assert data['ok'] is False
    assert 'allowed' in data


def test_api_create_rejects_bad_follow_up(auth_client):
    r = auth_client.post('/api/calls', json={
        'caller_name': 'Date',
        'phone_number': '+27820008888',
        'reason_for_call': 'bad date',
        'call_type': 'Incoming',
        'follow_up_date': 'not-a-date',
    })
    assert r.status_code == 400
    data = r.get_json()
    assert data['ok'] is False
    assert 'follow_up' in data['error']


def test_api_create_and_get(auth_client):
    r = auth_client.post('/api/calls', json={
        'caller_name': 'API Caller',
        'phone_number': '+27820001234',
        'reason_for_call': 'created via api test',
        'call_type': 'Incoming',
        'priority': 'High',
    })
    assert r.status_code == 201
    body = r.get_json()
    assert body['ok'] is True
    cid = body['id']
    g = auth_client.get(f'/api/calls/{cid}')
    assert g.status_code == 200
    got = g.get_json()
    assert got['caller'] == 'API Caller'
    assert got['priority'] == 'High'
    assert got['ok'] is True


def test_api_get_missing_is_json(auth_client):
    r = auth_client.get('/api/calls/999999')
    assert r.status_code == 404
    data = r.get_json()
    assert data['ok'] is False
    assert data['error']


def test_api_list_rejects_bad_status(auth_client):
    r = auth_client.get('/api/calls?status=Nope')
    assert r.status_code == 400
    data = r.get_json()
    assert data['ok'] is False
    assert 'allowed' in data


def test_api_list_envelope(auth_client):
    r = auth_client.get('/api/calls?per_page=10')
    assert r.status_code == 200
    data = r.get_json()
    assert data['ok'] is True
    assert isinstance(data['items'], list)
    assert data['page'] == 1
    assert data['per_page'] == 10
    assert 'total' in data
    assert r.headers.get('X-Total-Count') == str(data['total'])


def test_api_users_envelope(auth_client):
    r = auth_client.get('/api/users')
    assert r.status_code == 200
    data = r.get_json()
    assert data['ok'] is True
    assert isinstance(data['items'], list)
    assert data['total'] >= 2
    names = {u['username'] for u in data['items']}
    assert 'admin' in names


def test_api_unauthenticated_is_json(client):
    r = client.get('/api/calls')
    assert r.status_code == 401
    data = r.get_json()
    assert data['ok'] is False
    assert 'Authentication' in data['error']


def test_api_claim_next_empty(auth_client):
    r = auth_client.post('/api/calls/claim-next', json={})
    assert r.status_code == 404
    data = r.get_json()
    assert data['ok'] is False


def test_api_quick_unknown_action(auth_client, app):
    with app.app_context():
        c = CallLog(
            CallerName='Q', PhoneNumber='+27821112222', CallType='Incoming',
            ReasonForCall='quick', Priority='Low', Status='Open'
        )
        db.session.add(c)
        db.session.commit()
        cid = c.CallID
    r = auth_client.post(f'/api/calls/{cid}/quick', json={'action': 'explode'})
    assert r.status_code == 400
    assert r.get_json()['ok'] is False
