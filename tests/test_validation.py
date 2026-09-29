from app.utils.validation import parse_iso_datetime, parse_optional_int, validate_phone


def test_validate_phone_accepts_common_formats():
    assert validate_phone('+27820001234') == '+27820001234'
    assert validate_phone('082 000 1234') == '082 000 1234'
    assert validate_phone('(011) 555-0100') == '(011) 555-0100'


def test_validate_phone_rejects_short_or_alpha():
    assert validate_phone('123') is None
    assert validate_phone('not-a-phone') is None
    assert validate_phone('') is None
    assert validate_phone(None) is None


def test_parse_iso_datetime_errors():
    dt, err = parse_iso_datetime('2026-09-21T10:00:00')
    assert err is None and dt is not None
    dt, err = parse_iso_datetime('tomorrow')
    assert dt is None and err


def test_parse_optional_int():
    val, err = parse_optional_int('12', 'assigned_to')
    assert val == 12 and err is None
    val, err = parse_optional_int('nope', 'assigned_to')
    assert val is None and err
    val, err = parse_optional_int('', 'assigned_to')
    assert val is None and err is None


def test_api_create_rejects_bad_phone(auth_client):
    r = auth_client.post('/api/calls', json={
        'caller_name': 'Bad Phone',
        'phone_number': 'abc',
        'reason_for_call': 'needs a real number',
        'call_type': 'Incoming',
    })
    assert r.status_code == 400
    assert r.get_json()['ok'] is False


def test_api_create_rejects_short_reason(auth_client):
    r = auth_client.post('/api/calls', json={
        'caller_name': 'Short Reason',
        'phone_number': '+27820001234',
        'reason_for_call': 'hi',
        'call_type': 'Incoming',
    })
    assert r.status_code == 400


def test_api_create_rejects_bad_follow_up(auth_client):
    r = auth_client.post('/api/calls', json={
        'caller_name': 'Follow Up',
        'phone_number': '+27820001234',
        'reason_for_call': 'invalid follow-up date supplied',
        'call_type': 'Incoming',
        'follow_up_date': 'not-a-date',
    })
    assert r.status_code == 400
    assert 'follow_up' in r.get_json()['error']
