def test_login_has_skip_link_and_labelled_form(client):
    r = client.get('/login')
    assert r.status_code == 200
    html = r.data.decode('utf-8')
    assert 'Skip to content' in html
    assert 'id="mainContent"' in html
    assert 'id="login-heading"' in html
    assert 'aria-labelledby="login-heading"' in html
    assert 'autocomplete="username"' in html
    assert 'autocomplete="current-password"' in html


def test_inbox_filter_labels(auth_client):
    r = auth_client.get('/calls/')
    assert r.status_code == 200
    html = r.data.decode('utf-8')
    assert 'aria-label="Filter calls"' in html
    assert 'for="inboxSearch"' in html
    assert 'id="filterPriority"' in html
    assert 'id="inboxFilterBar"' in html
    assert 'Call inbox' in html
    assert 'aria-label="Primary"' in html
    assert 'aria-label="Inbox presets"' in html
