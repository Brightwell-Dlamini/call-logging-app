"""
Idempotent secondary indexes for inbox, audit, reports, notifications, and views.

create_all() does not add new indexes to existing tables. These statements
use IF NOT EXISTS so they are safe on SQLite and Postgres.
"""
from sqlalchemy import text

INDEX_STATEMENTS = (
    'CREATE INDEX IF NOT EXISTS ix_call_log_status_datelogged '
    'ON call_log ("Status", "DateLogged")',
    'CREATE INDEX IF NOT EXISTS ix_call_log_assigned_status '
    'ON call_log ("AssignedTo", "Status")',
    'CREATE INDEX IF NOT EXISTS ix_call_log_dept_status '
    'ON call_log ("Department", "Status")',
    'CREATE INDEX IF NOT EXISTS ix_call_log_followup '
    'ON call_log ("FollowUpDate")',
    'CREATE INDEX IF NOT EXISTS ix_call_log_lastupdated '
    'ON call_log ("LastUpdated")',
    'CREATE INDEX IF NOT EXISTS ix_call_log_datelogged '
    'ON call_log ("DateLogged")',
    'CREATE INDEX IF NOT EXISTS ix_call_log_priority_status '
    'ON call_log ("Priority", "Status")',
    'CREATE INDEX IF NOT EXISTS ix_call_activity_activitydate '
    'ON call_activity ("ActivityDate")',
    'CREATE INDEX IF NOT EXISTS ix_users_role_active '
    'ON users ("Role", "IsActive")',
    'CREATE INDEX IF NOT EXISTS ix_notifications_user_read '
    'ON notifications ("UserID", "IsRead")',
    'CREATE INDEX IF NOT EXISTS ix_notifications_created '
    'ON notifications ("CreatedAt")',
    'CREATE INDEX IF NOT EXISTS ix_saved_views_user '
    'ON saved_views ("UserID")',
    'CREATE INDEX IF NOT EXISTS ix_api_tokens_user '
    'ON api_tokens ("UserID")',
    'CREATE INDEX IF NOT EXISTS ix_api_tokens_prefix '
    'ON api_tokens ("TokenPrefix")',
    'CREATE INDEX IF NOT EXISTS ix_contacts_phone '
    'ON contacts ("PhoneNumber")',
    'CREATE INDEX IF NOT EXISTS ix_system_audit_user_created '
    'ON system_audit ("UserID", "CreatedAt")',
)


def ensure_indexes(db) -> None:
    """Create supporting indexes if they are missing."""
    for stmt in INDEX_STATEMENTS:
        db.session.execute(text(stmt))
    db.session.commit()
