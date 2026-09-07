"""Helpers for writing system audit events."""
from flask import has_request_context, request
from flask_login import current_user
from app import db
from app.models.audit import SystemAudit


def _client_ip() -> str | None:
    if not has_request_context():
        return None
    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded:
        return forwarded.split(',')[0].strip()[:64]
    return (request.remote_addr or '')[:64] or None


def log_audit(
    action: str,
    details: str | None = None,
    *,
    user_id: int | None = None,
    target_type: str | None = None,
    target_id=None,
) -> SystemAudit:
    """Persist a system audit row. Caller is responsible for commit."""
    if user_id is None and has_request_context() and getattr(current_user, 'is_authenticated', False):
        user_id = getattr(current_user, 'UserID', None)
    event = SystemAudit(
        UserID=user_id,
        Action=action[:80],
        Details=(details or '')[:4000] or None,
        TargetType=(target_type or None),
        TargetID=str(target_id)[:80] if target_id is not None else None,
        IpAddress=_client_ip(),
    )
    db.session.add(event)
    return event
