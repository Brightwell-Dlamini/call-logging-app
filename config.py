"""
Application configuration.
- Local: SQLite by default
- Vercel + DATABASE_URL (Neon): persistent Postgres
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


def _default_sqlite_uri():
    """SQLite path that works on Vercel (/tmp) and locally."""
    if os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV'):
        return 'sqlite:////tmp/call_logging.db'
    return 'sqlite:///' + os.path.join(
        os.path.abspath(os.path.dirname(__file__)), 'call_logging.db'
    )


def normalize_database_url(url):
    """
    Normalize Neon / Heroku / generic Postgres URLs for SQLAlchemy + psycopg3.
    """
    if not url:
        return None
    url = url.strip().strip('"').strip("'")

    # heroku/neon legacy scheme
    if url.startswith('postgres://'):
        url = 'postgresql://' + url[len('postgres://'):]

    # Use psycopg3 driver (package: psycopg[binary])
    if url.startswith('postgresql://') and '+psycopg' not in url.split('://', 1)[0]:
        url = 'postgresql+psycopg://' + url[len('postgresql://'):]
    elif url.startswith('postgresql+psycopg2://'):
        url = 'postgresql+psycopg://' + url[len('postgresql+psycopg2://'):]

    # Neon requires SSL; add if missing
    if 'sslmode=' not in url:
        join = '&' if '?' in url else '?'
        url = f'{url}{join}sslmode=require'

    return url


def resolve_database_uri():
    raw = os.environ.get('DATABASE_URL')
    if raw:
        return normalize_database_url(raw) or _default_sqlite_uri()
    return _default_sqlite_uri()


def _engine_options():
    """Serverless-friendly pool settings on Vercel; normal pool elsewhere."""
    opts = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    if os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV'):
        from sqlalchemy.pool import NullPool
        opts['poolclass'] = NullPool
    return opts


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = _engine_options()
    PERMANENT_SESSION_LIFETIME = timedelta(
        seconds=int(os.environ.get('PERMANENT_SESSION_LIFETIME', 1800))
    )
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 300
    RATELIMIT_STORAGE_URI = os.environ.get('RATELIMIT_STORAGE_URI', 'memory://')
    RATELIMIT_DEFAULT = '200 per day;50 per hour'
    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_LOCKOUT_MINUTES = 15
    # Cap uploads (CSV import) so a single request cannot exhaust memory.
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 2 * 1024 * 1024))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


class DevelopmentConfig(Config):
    """Development — SQLite or DATABASE_URL if set."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = resolve_database_uri()


class ProductionConfig(Config):
    """Production — prefers DATABASE_URL (Neon). Falls back to SQLite only if unset."""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = resolve_database_uri()
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    CACHE_TYPE = 'NullCache'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig,
}
