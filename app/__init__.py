"""
Call Logging Application factory.
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import config

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
cache = Cache()
limiter = Limiter(key_func=get_remote_address)


def create_app(config_name=None):
    """Application factory."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    cache.init_app(app)
    limiter.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'warning'
    login_manager.session_protection = 'strong'

    # Register blueprints
    from app.blueprints.auth import auth_bp
    from app.blueprints.dashboard import dashboard_bp
    from app.blueprints.calls import calls_bp
    from app.blueprints.admin import admin_bp
    from app.blueprints.reports import reports_bp
    from app.blueprints.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(calls_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(api_bp, url_prefix='/api')

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    # Health check
    @app.route('/health')
    def health():
        return {'status': 'healthy', 'service': 'call-logging-app'}, 200

    # Configure logging (skip file handlers on Vercel / read-only FS)
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
                pass  # filesystem may be read-only
        app.logger.setLevel(logging.INFO)
        app.logger.info('Call Logging Application startup')

    # Create tables if needed (development convenience)
    with app.app_context():
        try:
            db.create_all()
            # Bootstrap default admin when database is empty (e.g. Vercel cold start)
            from app.models import User, Department
            if User.query.count() == 0:
                admin = User(
                    Username='admin',
                    Email='admin@calllog.local',
                    FullName='System Administrator',
                    Role='Admin',
                    IsActive=True,
                )
                admin.set_password('admin123')
                db.session.add(admin)
                for name in ['IT', 'HR', 'Sales', 'Support', 'Billing']:
                    if not Department.query.filter_by(DepartmentName=name).first():
                        db.session.add(Department(DepartmentName=name, IsActive=True))
                db.session.commit()
                app.logger.info('Bootstrapped default admin user and departments')
        except Exception as e:
            app.logger.warning('db bootstrap failed: %s', e)

    # Optional one-time seed endpoint (safe: only creates admin if missing)
    @app.route('/seed', methods=['POST', 'GET'])
    def seed_endpoint():
        from app.models import User, Department
        created = []
        if not User.query.filter_by(Username='admin').first():
            admin = User(
                Username='admin',
                Email='admin@calllog.local',
                FullName='System Administrator',
                Role='Admin',
                IsActive=True,
            )
            admin.set_password('admin123')
            db.session.add(admin)
            created.append('admin user')
        for name in ['IT', 'HR', 'Sales', 'Support', 'Billing']:
            if not Department.query.filter_by(DepartmentName=name).first():
                db.session.add(Department(DepartmentName=name, IsActive=True))
                created.append(f'dept:{name}')
        if created:
            db.session.commit()
            return {'status': 'ok', 'created': created, 'login': 'admin / admin123'}, 200
        return {'status': 'ok', 'message': 'Already seeded', 'login': 'admin / admin123'}, 200

    return app
