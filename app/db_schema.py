"""
Idempotent schema patches for columns that create_all() will not add
to existing tables.

Production Neon was created before several model columns existed.
SQLAlchemy then fails queries with UndefinedColumn.
"""
from sqlalchemy import text


def _sqlite_columns(db, table: str) -> set:
    rows = db.session.execute(text(f'PRAGMA table_info({table})')).fetchall()
    return {r[1] for r in rows}


def ensure_schema(db) -> None:
    """Apply missing columns / types. Safe to run on every startup."""
    uri = str(db.engine.url)
    is_postgres = 'postgres' in uri
    is_sqlite = uri.startswith('sqlite')

    if is_postgres:
        # --- users.Presence ---
        db.session.execute(text("""
            DO $$ BEGIN
                CREATE TYPE presence_statuses AS ENUM
                    ('Available', 'Busy', 'Away', 'Offline');
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
        """))
        db.session.execute(text("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS "Presence" presence_statuses
            NOT NULL DEFAULT 'Available';
        """))

        # --- call_log columns added after initial schema ---
        db.session.execute(text("""
            ALTER TABLE call_log
            ADD COLUMN IF NOT EXISTS "DispositionID" INTEGER;
        """))
        db.session.execute(text("""
            ALTER TABLE call_log
            ADD COLUMN IF NOT EXISTS "TimeSpent" INTEGER;
        """))
        db.session.execute(text("""
            ALTER TABLE call_log
            ADD COLUMN IF NOT EXISTS "SatisfactionRating" INTEGER;
        """))
        db.session.execute(text("""
            ALTER TABLE call_log
            ADD COLUMN IF NOT EXISTS "FollowUpDate" TIMESTAMP WITHOUT TIME ZONE;
        """))
        db.session.execute(text("""
            ALTER TABLE call_log
            ADD COLUMN IF NOT EXISTS "LastUpdated" TIMESTAMP WITHOUT TIME ZONE
            DEFAULT NOW();
        """))
        db.session.execute(text("""
            ALTER TABLE call_log
            ADD COLUMN IF NOT EXISTS "Notes" TEXT;
        """))
        db.session.execute(text("""
            ALTER TABLE call_log
            ADD COLUMN IF NOT EXISTS "Resolution" TEXT;
        """))

        # Soft FK for DispositionID (ignore if table/constraint already present)
        db.session.execute(text("""
            DO $$ BEGIN
                ALTER TABLE call_log
                ADD CONSTRAINT fk_call_log_disposition
                FOREIGN KEY ("DispositionID")
                REFERENCES disposition_codes ("DispositionID");
            EXCEPTION
                WHEN duplicate_object THEN NULL;
                WHEN undefined_table THEN NULL;
            END $$;
        """))

    elif is_sqlite:
        user_cols = _sqlite_columns(db, 'users')
        if 'Presence' not in user_cols:
            db.session.execute(text(
                "ALTER TABLE users ADD COLUMN Presence TEXT "
                "NOT NULL DEFAULT 'Available'"
            ))

        call_cols = _sqlite_columns(db, 'call_log')
        additions = [
            ('DispositionID', 'INTEGER'),
            ('TimeSpent', 'INTEGER'),
            ('SatisfactionRating', 'INTEGER'),
            ('FollowUpDate', 'DATETIME'),
            ('LastUpdated', "DATETIME DEFAULT CURRENT_TIMESTAMP"),
            ('Notes', 'TEXT'),
            ('Resolution', 'TEXT'),
        ]
        for name, typedef in additions:
            if name not in call_cols:
                db.session.execute(text(
                    f'ALTER TABLE call_log ADD COLUMN "{name}" {typedef}'
                ))

    db.session.commit()
