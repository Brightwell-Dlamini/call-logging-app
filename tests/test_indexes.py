from app.db_indexes import INDEX_STATEMENTS, ensure_indexes
from app import db


def test_index_statements_are_idempotent():
    assert INDEX_STATEMENTS
    for stmt in INDEX_STATEMENTS:
        assert stmt.upper().startswith('CREATE INDEX IF NOT EXISTS')


def test_ensure_indexes_runs(app):
    with app.app_context():
        ensure_indexes(db)
        ensure_indexes(db)
