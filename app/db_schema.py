"""
Idempotent schema patches for columns that create_all() will not add
to existing tables.

Production Neon was created before the Presence column existed on User.
SQLAlchemy then fails every User query with UndefinedColumn.
"""
from sqlalchemy import text


def ensure_schema(db) -> None:
    """Apply missing columns / types. Safe to run on every startup."""
    uri = str(db.engine.url)
    is_postgres = 'postgres' in uri
    is_sqlite = uri.startswith('sqlite')

    if is_postgres:
        # Create enum type if missing (no-op when it already exists).
        db.session.execute(text("""
            DO $$ BEGIN
                CREATE TYPE presence_statuses AS ENUM
                    ('Available', 'Busy', 'Away', 'Offline');
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
        """))
        # Add column if missing.
        db.session.execute(text("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS "Presence" presence_statuses
            NOT NULL DEFAULT 'Available';
        """))
    elif is_sqlite:
        # SQLite has no IF NOT EXISTS for ADD COLUMN in older versions;
        # check information_schema equivalent via pragma.
        rows = db.session.execute(text('PRAGMA table_info(users)')).fetchall()
        col_names = {r[1] for r in rows}  # r[1] is column name
        if 'Presence' not in col_names:
            db.session.execute(text(
                "ALTER TABLE users ADD COLUMN Presence TEXT "
                "NOT NULL DEFAULT 'Available'"
            ))

    db.session.commit()
