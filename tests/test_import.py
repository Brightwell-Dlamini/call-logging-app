from io import BytesIO
from app.blueprints.import_calls import _map_row, allowed_import_filename
from app.models import SystemAudit, CallLog


def test_allowed_import_filename():
    assert allowed_import_filename('calls.csv')
    assert allowed_import_filename('calls.CSV')
    assert allowed_import_filename('notes.txt')
    assert not allowed_import_filename('payload.exe')
    assert not allowed_import_filename('noext')
    assert not allowed_import_filename('')


def test_map_row_requires_core_fields(app):
    with app.app_context():
        mapped, err = _map_row({'caller': 'Ada', 'phone': ''})
        assert mapped is None
        assert 'Missing required' in err


def test_map_row_normalises_enums(app):
    with app.app_context():
        mapped, err = _map_row({
            'CallerName': 'Ada Lovelace',
            'PhoneNumber': '011111',
            'ReasonForCall': 'Billing',
            'Priority': 'NotAPriority',
            'Status': 'Weird',
            'CallType': 'Fax',
        })
        assert err is None
        assert mapped['Priority'] == 'Medium'
        assert mapped['Status'] == 'Open'
        assert mapped['CallType'] == 'Incoming'
        assert mapped['CallerName'] == 'Ada Lovelace'


def test_import_rejects_non_csv(auth_client):
    data = {
        'file': (BytesIO(b'not a csv'), 'malware.exe'),
    }
    r = auth_client.post('/import/', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert r.status_code == 200
    assert b'Only .csv or .txt' in r.data


def test_import_dry_run_writes_audit(auth_client, app):
    csv_body = (
        b'CallerName,PhoneNumber,ReasonForCall\n'
        b'Ada Lovelace,011111,Billing question\n'
    )
    data = {
        'file': (BytesIO(csv_body), 'batch.csv'),
        'dry_run': 'on',
    }
    r = auth_client.post('/import/', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert r.status_code == 200
    with app.app_context():
        assert SystemAudit.query.filter_by(Action='import.dry_run').count() >= 1
        assert CallLog.query.count() == 0
