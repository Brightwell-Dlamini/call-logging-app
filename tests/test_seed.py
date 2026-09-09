import os
from unittest.mock import patch

from app import create_app


def test_seed_disabled_in_production_without_flag(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.setenv('ENABLE_SEED', '')
    monkeypatch.delenv('SEED_TOKEN', raising=False)
    with patch.dict(os.environ, {'FLASK_ENV': 'production', 'ENABLE_SEED': ''}, clear=False):
        app = create_app('testing')
        app.config['TESTING'] = True
        client = app.test_client()
        # Factory still sees FLASK_ENV from os.environ at request time.
        with patch('app.blueprints.auth.current_app', app):
            pass
        r = client.get('/seed')
        # create_app('testing') uses testing config; seed gate uses FLASK_ENV env.
        assert r.status_code in (200, 403)
        data = r.get_json()
        assert data is not None
        if os.environ.get('FLASK_ENV') == 'production' and os.environ.get('ENABLE_SEED') != '1':
            assert r.status_code == 403
            assert data.get('status') == 'disabled'


def test_seed_token_required_when_set(client, monkeypatch):
    monkeypatch.setenv('SEED_TOKEN', 's3cret')
    monkeypatch.setenv('ENABLE_SEED', '1')
    r = client.get('/seed')
    assert r.status_code == 403
    data = r.get_json()
    assert data.get('status') == 'forbidden'

    r_ok = client.get('/seed', headers={'X-Seed-Token': 's3cret'})
    assert r_ok.status_code == 200
    body = r_ok.get_json()
    assert body.get('status') == 'ok'
