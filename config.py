"""
Application configuration module.
Supports development (SQLite) and production (MySQL) environments.
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


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
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


class DevelopmentConfig(Config):
    """Development configuration using SQLite."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or _default_sqlite_uri()


class ProductionConfig(Config):
    """Production configuration. Uses DATABASE_URL when set, otherwise SQLite."""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or _default_sqlite_uri()
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    CACHE_TYPE = 'NullCache'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
