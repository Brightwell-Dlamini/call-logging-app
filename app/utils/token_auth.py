"""Bearer personal-access-token authentication for /api routes."""
from datetime import datetime, timedelta
from flask import g, jsonify, request
from flask_login import login_user
from app import db
from app.models.api_token import ApiToken


def extract_bearer_token(req=None):
    """Return the raw token from Authorization: Bearer, or None."""
    req = req or request
    header = (req.headers.get('Authorization') or '').strip()
    if header.lower().startswith('bearer '):
        raw = header[7:].strip()
        return raw or None
    return None


def find_valid_token(raw):
    """Look up an active, unexpired token matching the raw secret."""
    if not raw or not raw.startswith('clp_') or len(raw) < 16:
        return None
    prefix = raw[:12]
    candidates = (
        ApiToken.query
        .filter_by(TokenPrefix=prefix, IsActive=True)
        .all()
    )
    now = datetime.utcnow()
    for token in candidates:
        if token.ExpiresAt and token.ExpiresAt < now:
            continue
        if not token.check_token(raw):
            continue
        user = token.user
        if user is None or not user.IsActive:
            return None
        return token
    return None


def token_allows_method(token, method):
    """GET/HEAD/OPTIONS need read; mutating methods need write or admin."""
    method = (method or 'GET').upper()
    if method in ('GET', 'HEAD', 'OPTIONS'):
        return token.has_scope('read') or token.has_scope('write') or token.has_scope('admin')
    return token.has_scope('write') or token.has_scope('admin')


def touch_last_used(token, min_interval_seconds=60):
    """Update LastUsedAt at most once per interval to limit writes."""
    now = datetime.utcnow()
    last = token.LastUsedAt
    if last and (now - last) < timedelta(seconds=min_interval_seconds):
        return
    token.LastUsedAt = now
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()


def authenticate_request():
    """
    If the request carries a Bearer token, validate it and log the user in.

    Returns a Flask response when the token is present but invalid, otherwise None.
    """
    raw = extract_bearer_token()
    if not raw:
        return None

    path = request.path or ''
    if not path.startswith('/api'):
        return jsonify({'ok': False, 'error': 'API tokens are only valid on /api routes'}), 401

    token = find_valid_token(raw)
    if token is None:
        return jsonify({'ok': False, 'error': 'Invalid or expired API token'}), 401

    if not token_allows_method(token, request.method):
        return jsonify({
            'ok': False,
            'error': 'Token scope does not allow this method',
            'scopes': token.Scopes,
        }), 403

    g.api_token = token
    login_user(token.user, remember=False, fresh=False)
    touch_last_used(token)
    return None
