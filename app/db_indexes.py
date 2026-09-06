"""
Idempotent secondary indexes for inbox, audit, and report filters.

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
    'CREATE INDEX IF NOT EXISTS ix_call_activity_activitydate '
    'ON call_activity ("ActivityDate")',
    'CREATE INDEX IF NOT EXISTS ix_users_role_active '
    'ON users ("Role", "IsActive")',
)


def ensure_indexes(db) -> None:
    """Create supporting indexes if they are missing."""
    for stmt in INDEX_STATEMENTS:
        db.session.execute(text(stmt))
    db.session.commit()
