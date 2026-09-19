"""Correlate HTTP requests with logs and audit rows."""
import uuid
from flask import g, has_request_context, request

HEADER = 'X-Request-ID'


def new_request_id():
    incoming = ''
    if has_request_context():
        incoming = (request.headers.get(HEADER) or '').strip()
    if incoming and incoming.replace('-', '').isalnum() and 8 <= len(incoming) <= 64:
        return incoming[:64]
    return uuid.uuid4().hex


def current_request_id():
    if has_request_context():
        return getattr(g, 'request_id', None)
    return None
