from app.utils.validators import (
    is_valid_phone, is_valid_username, is_valid_hex_colour,
    is_valid_disposition_code,
)


def test_phone_accepts_common_formats():
    assert is_valid_phone('+27820001234')
    assert is_valid_phone('082 000 1234')
    assert is_valid_phone('(011) 555-0100')


def test_phone_rejects_letters():
    assert not is_valid_phone('not-a-phone')
    assert not is_valid_phone('123')
    assert not is_valid_phone('')


def test_username_rules():
    assert is_valid_username('agent1')
    assert is_valid_username('Ada.Lovelace')
    assert not is_valid_username('bad name')
    assert not is_valid_username('x')


def test_hex_colour_rules():
    assert is_valid_hex_colour('#6366f1')
    assert is_valid_hex_colour('#fff')
    assert not is_valid_hex_colour('red')
    assert not is_valid_hex_colour('#gg0000')


def test_disposition_code_rules():
    assert is_valid_disposition_code('RESOLVED')
    assert is_valid_disposition_code('no-answer')
    assert not is_valid_disposition_code('has space')


def test_api_create_rejects_invalid_phone(auth_client):
    r = auth_client.post('/api/calls', json={
        'caller_name': 'Bad Phone',
        'phone_number': 'abc',
        'reason_for_call': 'invalid phone should fail',
        'call_type': 'Incoming',
    })
    assert r.status_code == 400
    data = r.get_json()
    assert data['ok'] is False
    assert 'phone' in data['error'].lower()


def test_api_create_rejects_unknown_assignee(auth_client):
    r = auth_client.post('/api/calls', json={
        'caller_name': 'Assign Ghost',
        'phone_number': '+27820005555',
        'reason_for_call': 'assign to missing user',
        'call_type': 'Incoming',
        'assigned_to': 999999,
    })
    assert r.status_code == 400
    data = r.get_json()
    assert data['ok'] is False
    assert 'assigned_to' in data['error']


def test_api_create_rejects_bad_follow_up(auth_client):
    r = auth_client.post('/api/calls', json={
        'caller_name': 'Date Caller',
        'phone_number': '+27820006666',
        'reason_for_call': 'bad follow up date',
        'call_type': 'Incoming',
        'follow_up_date': 'not-a-date',
    })
    assert r.status_code == 400
    assert r.get_json()['ok'] is False
