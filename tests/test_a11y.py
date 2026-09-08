def test_login_has_skip_link(client):
    r = client.get('/login')
    assert r.status_code == 200
    assert b'skip-link' in r.data
    assert b'href="#mainContent"' in r.data
    assert b'id="mainContent"' in r.data


def test_authenticated_nav_current_and_labels(auth_client):
    r = auth_client.get('/')
    assert r.status_code == 200
    body = r.data
    assert b'aria-label="Primary"' in body
    assert b'aria-current="page"' in body
    assert b'id="mainContent"' in body
    assert b'aria-label="Toggle menu"' in body


def test_reports_hub_labels_date_field(auth_client):
    r = auth_client.get('/reports/')
    assert r.status_code == 200
    assert b'for="report-date"' in r.data or b'id="report-date"' in r.data
    assert b'Report date' in r.data
