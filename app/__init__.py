"""
Call Logging Application factory.
"""
import logging
import os
import uuid
from logging.handlers import RotatingFileHandler
from flask import Flask, g, jsonify, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from config import config

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
cache = Cache()
limiter = Limiter(key_func=get_remote_address)
csrf = CSRFProtect()

# Compatible with existing CDN scripts/styles and inline theme/presence snippets.
_CSP = (
    "default-src 'self'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'; "
    "object-src 'none'; "
    "img-src 'self' data:; "
    "font-src 'self' https://cdnjs.cloudflare.com data:; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://cdn.datatables.net; "
    "script-src 'self' 'unsafe-inline' https://code.jquery.com https://cdn.jsdelivr.net https://cdn.datatables.net; "
    "connect-src 'self'"
)


def _is_production():
    return (
        os.environ.get('FLASK_ENV') == 'production'
        or os.environ.get('VERCEL_ENV') == 'production'
    )


def _wants_json_error():
    path = request.path or ''
    if path.startswith('/api') or path in ('/health', '/seed'):
        return True
    accept = (request.headers.get('Accept') or '').lower()
    if 'application/json' in accept and 'text/html' not in accept:
        return True
    return request.is_json


def create_app(config_name=None):
    """Application factory."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config.get(config_name, config['default']))
    app.config.setdefault('WTF_CSRF_HEADERS', ['X-CSRFToken', 'X-CSRF-Token'])
    # CSRF is applied after Bearer-token auth so verified API clients are not blocked.
    app.config['WTF_CSRF_CHECK_DEFAULT'] = False

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    cache.init_app(app)
    limiter.init_app(app)
    csrf.init_app(app)

    from app.jinja_filters import register_filters
    register_filters(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'warning'
    login_manager.session_protection = 'strong'

    from app.blueprints.auth import auth_bp
    from app.blueprints.dashboard import dashboard_bp
    from app.blueprints.calls import calls_bp
    from app.blueprints.admin import admin_bp
    from app.blueprints.reports import reports_bp
    from app.blueprints.api import api_bp
    from app.blueprints.board import board_bp
    from app.blueprints.api_extras import api_extras_bp
    from app.blueprints.import_calls import import_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(calls_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(api_extras_bp, url_prefix='/api')
    app.register_blueprint(board_bp)
    app.register_blueprint(import_bp)

    @app.before_request
    def _assign_request_id():
        incoming = (request.headers.get('X-Request-ID') or '').strip()
        if incoming and 8 <= len(incoming) <= 64 and all(
            c.isalnum() or c in '-_' for c in incoming
        ):
            g.request_id = incoming
        else:
            g.request_id = uuid.uuid4().hex

    @app.before_request
    def _authenticate_api_token_and_csrf():
        from app.utils.token_auth import authenticate_request
        rejected = authenticate_request()
        if rejected is not None:
            return rejected
        if getattr(g, 'api_token', None):
            return None
        if not app.config.get('WTF_CSRF_ENABLED', True):
            return None
        csrf.protect()

    @app.after_request
    def _security_headers(response):
        rid = getattr(g, 'request_id', None) or uuid.uuid4().hex
        response.headers.setdefault('X-Request-ID', rid)
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'DENY')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.headers.setdefault(
            'Permissions-Policy',
            'camera=(), microphone=(), geolocation=()',
        )
        response.headers.setdefault('Cross-Origin-Opener-Policy', 'same-origin')
        response.headers.setdefault('Content-Security-Policy', _CSP)
        ctype = (response.headers.get('Content-Type') or '').lower()
        if 'text/html' in ctype:
            response.headers.setdefault('Cache-Control', 'no-store')
        if _is_production():
            response.headers.setdefault(
                'Strict-Transport-Security',
                'max-age=31536000; includeSubDomains',
            )
        return response

    def _json_error(message, status):
        payload = {
            'ok': False,
            'error': message,
            'status': status,
            'request_id': getattr(g, 'request_id', None),
        }
        return jsonify(payload), status

    @app.errorhandler(400)
    def bad_request_error(error):
        if _wants_json_error():
            return _json_error(getattr(error, 'description', None) or 'Bad request', 400)
        return render_template('errors/404.html'), 400

    @app.errorhandler(404)
    def not_found_error(error):
        if _wants_json_error():
            return _json_error('Not found', 404)
        return render_template('errors/404.html'), 404

    @app.errorhandler(403)
    def forbidden_error(error):
        if _wants_json_error():
            return _json_error('Forbidden', 403)
        return render_template('errors/403.html'), 403

    @app.errorhandler(429)
    def rate_limit_error(error):
        if _wants_json_error():
            return _json_error('Rate limit exceeded', 429)
        return render_template('errors/403.html'), 429

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        if _wants_json_error():
            return _json_error('Internal server error', 500)
        return render_template('errors/500.html'), 500

    @app.route('/favicon.ico')
    def favicon():
        return redirect(url_for('static', filename='favicon.svg'), code=302)

    @app.route('/health')
    def health():
        db_status = 'unknown'
        backend = 'unknown'
        try:
            uri = app.config.get('SQLALCHEMY_DATABASE_URI') or ''
            if uri.startswith('sqlite'):
                backend = 'sqlite'
            elif 'postgres' in uri:
                backend = 'postgres'
            else:
                backend = 'other'
            from sqlalchemy import text as sa_text
            db.session.execute(sa_text('SELECT 1'))
            db_status = 'ok'
        except Exception as e:
            db_status = f'error: {type(e).__name__}'
        code = 200 if db_status == 'ok' else 503
        return {
            'status': 'healthy' if db_status == 'ok' else 'degraded',
            'service': 'call-logging-app',
            'database': db_status,
            'backend': backend,
            'request_id': getattr(g, 'request_id', None),
        }, code

    @app.route('/seed', methods=['POST', 'GET'])
    @limiter.limit('5 per minute')
    def seed_endpoint():
        from app.utils.audit import log_audit

        if _is_production() and os.environ.get('ENABLE_SEED') != '1':
            log_audit('ops.seed_denied', 'ENABLE_SEED not set in production', target_type='ops', target_id='seed')
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
            return {
                'status': 'disabled',
                'message': 'Seed endpoint disabled. Set ENABLE_SEED=1 to allow.',
            }, 403

        expected_token = os.environ.get('SEED_TOKEN')
        if expected_token:
            provided = request.headers.get('X-Seed-Token') or request.args.get('token') or ''
            if provided != expected_token:
                log_audit('ops.seed_denied', 'invalid or missing seed token', target_type='ops', target_id='seed')
                try:
                    db.session.commit()
                except Exception:
                    db.session.rollback()
                return {'status': 'forbidden', 'message': 'Invalid or missing seed token.'}, 403

        from app.utils.bootstrap import bootstrap_demo_data
        created = []
        try:
            created = bootstrap_demo_data(include_sample_calls=True)
            if created:
                log_audit(
                    'ops.seed',
                    f'created={created}',
                    target_type='ops',
                    target_id='seed',
                )
                db.session.commit()
                payload = {'status': 'ok', 'created': created}
                if not _is_production() and any(
                    label in ('admin', 'agent1', 'manager1') for label in created
                ):
                    payload['logins'] = {
                        'admin': 'admin123',
                        'agent1': 'agent123',
                        'manager1': 'manager123',
                    }
                    payload['warning'] = 'Change demo passwords before exposing this instance.'
                elif _is_production() and any(
                    label in ('admin', 'agent1', 'manager1') for label in created
                ):
                    payload['warning'] = (
                        'Demo accounts may have been created. '
                        'Passwords are not returned in production; change them immediately.'
                    )
                return payload, 200
            log_audit('ops.seed', 'already seeded', target_type='ops', target_id='seed')
            db.session.commit()
            return {'status': 'ok', 'message': 'Already seeded'}, 200
        except Exception as e:
            db.session.rollback()
            app.logger.warning('seed failed: %s', type(e).__name__)
            return {'status': 'error', 'message': type(e).__name__}, 500

    csrf.exempt(health)
    csrf.exempt(seed_endpoint)

    if not app.debug and not app.testing:
        if not (os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV')):
            try:
                if not os.path.exists('logs'):
                    os.mkdir('logs')
                file_handler = RotatingFileHandler(
                    'logs/call_logging.log', maxBytes=10240000, backupCount=10
                )
                file_handler.setFormatter(logging.Formatter(
                    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
                ))
                file_handler.setLevel(logging.INFO)
                app.logger.addHandler(file_handler)
            except OSError:
                pass
        app.logger.setLevel(logging.INFO)
        app.logger.info('Call Logging Application startup')

    with app.app_context():
        try:
            db.create_all()
            from app.db_schema import ensure_schema
            try:
                ensure_schema(db)
            except Exception as schema_err:
                db.session.rollback()
                app.logger.warning('schema ensure failed: %s', schema_err)
            from app.db_indexes import ensure_indexes
            try:
                ensure_indexes(db)
            except Exception as idx_err:
                db.session.rollback()
                app.logger.warning('index ensure failed: %s', idx_err)
            if not _is_production():
                from app.utils.bootstrap import bootstrap_demo_data
                created = bootstrap_demo_data(include_sample_calls=True)
                if created:
                    db.session.commit()
                    app.logger.info('Bootstrapped demo data: %s', created)
        except Exception as e:
            app.logger.warning('db bootstrap failed: %s', e)

    return app
