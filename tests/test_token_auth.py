from datetime import datetime, timedelta
from app import db
from app.models import User, ApiToken


def _make_token(app, username='agent1', scopes='read,write', expires_at=None, name='ci'):
    with app.app_context():
        user = User.query.filter_by(Username=username).first()
        raw = ApiToken.generate_token()
        token = ApiToken(
            UserID=user.UserID,
            Name=name,
            Scopes=scopes,
            ExpiresAt=expires_at,
        )
        token.set_token(raw)
        db.session.add(token)
        db.session.commit()
        return raw, token.TokenID


def test_bearer_token_reads_stats(client, app):
    raw, _ = _make_token(app, scopes='read')
    r = client.get('/api/dashboard/stats', headers={'Authorization': f'Bearer {raw}'})
    assert r.status_code == 200
    data = r.get_json()
    assert data['ok'] is True
    assert 'total_calls' in data


def test_invalid_bearer_is_json_401(client):
    r = client.get('/api/dashboard/stats', headers={'Authorization': 'Bearer clp_notarealtokenvaluexx'})
    assert r.status_code == 401
    data = r.get_json()
    assert data['ok'] is False
    assert 'token' in data['error'].lower()


def test_read_scope_cannot_create_call(client, app):
    raw, _ = _make_token(app, scopes='read', name='readonly')
    r = client.post('/api/calls', json={
        'caller_name': 'Tok',
        'phone_number': '+27820000001',
        'reason_for_call': 'scope test',
        'call_type': 'Incoming',
    }, headers={'Authorization': f'Bearer {raw}'})
    assert r.status_code == 403
    data = r.get_json()
    assert data['ok'] is False


def test_write_scope_can_create_call(client, app):
    raw, tid = _make_token(app, scopes='write', name='writer')
    r = client.post('/api/calls', json={
        'caller_name': 'Token Caller',
        'phone_number': '+27820000002',
        'reason_for_call': 'created with pat',
        'call_type': 'Incoming',
        'priority': 'Low',
    }, headers={'Authorization': f'Bearer {raw}'})
    assert r.status_code == 201
    body = r.get_json()
    assert body['ok'] is True
    with app.app_context():
        stored = ApiToken.query.get(tid)
        assert stored.LastUsedAt is not None


def test_expired_token_rejected(client, app):
    raw, _ = _make_token(
        app,
        scopes='read,write',
        expires_at=datetime.utcnow() - timedelta(hours=1),
        name='expired',
    )
    r = client.get('/api/tags', headers={'Authorization': f'Bearer {raw}'})
    assert r.status_code == 401
