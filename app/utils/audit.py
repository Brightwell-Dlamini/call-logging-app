"""Helpers for writing system audit events."""
from typing import Optional
from flask import has_request_context, request
from flask_login import current_user
from app import db
from app.models.audit import SystemAudit


def _client_ip() -> Optional[str]:
    if not has_request_context():
        return None
    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded:
        return forwarded.split(',')[0].strip()[:64]
    return (request.remote_addr or '')[:64] or None


def log_audit(
    action,
    details=None,
    user_id=None,
    target_type=None,
    target_id=None,
):
    """Persist a system audit row. Caller is responsible for commit."""
    if user_id is None and has_request_context() and getattr(current_user, 'is_authenticated', False):
        user_id = getattr(current_user, 'UserID', None)
    text = (details or '')[:4000] or None
    if text is None:
        rid = None
        if has_request_context():
            from flask import g
            rid = getattr(g, 'request_id', None)
        if rid:
            text = f'request_id={rid}'
    event = SystemAudit(
        UserID=user_id,
        Action=str(action)[:80],
        Details=text,
        TargetType=target_type,
        TargetID=str(target_id)[:80] if target_id is not None else None,
        IpAddress=_client_ip(),
    )
    db.session.add(event)
    return event
