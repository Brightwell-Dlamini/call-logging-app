def test_health_assigns_request_id(client):
    r = client.get('/health')
    assert r.status_code == 200
    rid = r.headers.get('X-Request-ID')
    assert rid
    assert len(rid) >= 8
    body = r.get_json()
    assert body.get('request_id') == rid


def test_health_honours_incoming_request_id(client):
    r = client.get('/health', headers={'X-Request-ID': 'trace-abc-12345'})
    assert r.status_code == 200
    assert r.headers.get('X-Request-ID') == 'trace-abc-12345'
    assert r.get_json().get('request_id') == 'trace-abc-12345'


def test_rejects_unsafe_incoming_request_id(client):
    r = client.get('/health', headers={'X-Request-ID': 'bad id with spaces!!!'})
    assert r.status_code == 200
    assert r.headers.get('X-Request-ID') != 'bad id with spaces!!!'
