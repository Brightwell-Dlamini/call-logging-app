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

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    cache.init_app(app)
    limiter.init_app(app)

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

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(calls_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(board_bp)

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
        }, code

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
            from app.models import User, Department, CallLog
            from datetime import datetime, timedelta
            import random

            created = []
            if User.query.count() == 0:
                for username, email, full, role, pwd in [
                    ('admin', 'admin@calllog.local', 'System Administrator', 'Admin', 'admin123'),
                    ('agent1', 'agent1@calllog.local', 'Thabo Molefe', 'Agent', 'agent123'),
                    ('manager1', 'manager1@calllog.local', 'Lerato Nkosi', 'Manager', 'manager123'),
                ]:
                    u = User(Username=username, Email=email, FullName=full, Role=role, IsActive=True)
                    u.set_password(pwd)
                    db.session.add(u)
                    created.append(username)

            for name in ['IT', 'HR', 'Sales', 'Support', 'Billing']:
                if not Department.query.filter_by(DepartmentName=name).first():
                    db.session.add(Department(DepartmentName=name, IsActive=True))
                    created.append('dept:' + name)

            db.session.flush()

            if CallLog.query.count() == 0:
                assignees = [u.UserID for u in User.query.limit(3).all()]
                samples = [
                    ('Sipho Dlamini', '+27821234567', 'Support', 'Incoming', 'Password reset not working', 'High', 'Open'),
                    ('Nomsa Khumalo', '+27829876543', 'Billing', 'Incoming', 'Invoice discrepancy for March', 'Medium', 'In Progress'),
                    ('Johan van der Berg', '+27831112233', 'IT', 'Incoming', 'VPN connection drops every hour', 'Critical', 'Open'),
                    ('Aisha Patel', '+27824445566', 'HR', 'Outgoing', 'Follow-up on leave request', 'Low', 'Resolved'),
                    ('Michael Chen', '+27827778899', 'Sales', 'Incoming', 'Quote for enterprise plan', 'Medium', 'Pending'),
                    ('Fatima Abrahams', '+27820001122', 'Support', 'Incoming', 'App crashes on login', 'High', 'In Progress'),
                    ('David Mokoena', '+27823334455', 'Billing', 'Incoming', 'Refund not received', 'High', 'Open'),
                    ('Sarah Jacobs', '+27826667788', 'IT', 'Outgoing', 'Scheduled maintenance notification', 'Low', 'Closed'),
                    ('Pieter Botha', '+27829990011', 'Sales', 'Incoming', 'Demo request for next week', 'Medium', 'Resolved'),
                    ('Zanele Mthembu', '+27822223344', 'Support', 'Incoming', '2FA setup assistance', 'Medium', 'Open'),
                    ('Ryan Smith', '+27825556677', 'HR', 'Incoming', 'Payslip access issue', 'Low', 'Pending'),
                    ('Grace Ndlovu', '+27828889900', 'IT', 'Incoming', 'Email not syncing on mobile', 'High', 'In Progress'),
                ]
                now = datetime.utcnow()
                for i, (name, phone, dept, ctype, reason, pri, status) in enumerate(samples):
                    db.session.add(CallLog(
                        CallerName=name,
                        PhoneNumber=phone,
                        Department=dept,
                        CallType=ctype,
                        ReasonForCall=reason,
                        Priority=pri,
                        Status=status,
                        AssignedTo=assignees[i % len(assignees)] if assignees else None,
                        DateLogged=now - timedelta(hours=i * 5 + random.randint(0, 3)),
                        Notes='Demo seed data' if i % 3 == 0 else None,
                        TimeSpent=random.choice([15, 30, 45, 60]) if status in ('Resolved', 'Closed') else None,
                        SatisfactionRating=random.choice([4, 5]) if status in ('Resolved', 'Closed') else None,
                        Resolution='Issue resolved with caller' if status in ('Resolved', 'Closed') else None,
                    ))
                created.append(str(len(samples)) + ' sample calls')

            if created:
                db.session.commit()
                app.logger.info('Bootstrapped demo data: %s', created)
        except Exception as e:
            app.logger.warning('db bootstrap failed: %s', e)

    @app.route('/seed', methods=['POST', 'GET'])
    def seed_endpoint():
        from app.models import User, Department, CallLog
        from datetime import datetime, timedelta
        import random
        created = []
        try:
            if User.query.count() == 0:
                for username, email, full, role, pwd in [
                    ('admin', 'admin@calllog.local', 'System Administrator', 'Admin', 'admin123'),
                    ('agent1', 'agent1@calllog.local', 'Thabo Molefe', 'Agent', 'agent123'),
                    ('manager1', 'manager1@calllog.local', 'Lerato Nkosi', 'Manager', 'manager123'),
                ]:
                    u = User(Username=username, Email=email, FullName=full, Role=role, IsActive=True)
                    u.set_password(pwd)
                    db.session.add(u)
                    created.append(username)
            for name in ['IT', 'HR', 'Sales', 'Support', 'Billing']:
                if not Department.query.filter_by(DepartmentName=name).first():
                    db.session.add(Department(DepartmentName=name, IsActive=True))
                    created.append('dept:' + name)
            db.session.flush()
            if CallLog.query.count() == 0:
                assignees = [u.UserID for u in User.query.limit(3).all()]
                samples = [
                    ('Sipho Dlamini', '+27821234567', 'Support', 'Incoming', 'Password reset not working', 'High', 'Open'),
                    ('Nomsa Khumalo', '+27829876543', 'Billing', 'Incoming', 'Invoice discrepancy for March', 'Medium', 'In Progress'),
                    ('Johan van der Berg', '+27831112233', 'IT', 'Incoming', 'VPN connection drops every hour', 'Critical', 'Open'),
                    ('Aisha Patel', '+27824445566', 'HR', 'Outgoing', 'Follow-up on leave request', 'Low', 'Resolved'),
                    ('Michael Chen', '+27827778899', 'Sales', 'Incoming', 'Quote for enterprise plan', 'Medium', 'Pending'),
                    ('Fatima Abrahams', '+27820001122', 'Support', 'Incoming', 'App crashes on login', 'High', 'In Progress'),
                    ('David Mokoena', '+27823334455', 'Billing', 'Incoming', 'Refund not received', 'High', 'Open'),
                    ('Sarah Jacobs', '+27826667788', 'IT', 'Outgoing', 'Scheduled maintenance notification', 'Low', 'Closed'),
                    ('Pieter Botha', '+27829990011', 'Sales', 'Incoming', 'Demo request for next week', 'Medium', 'Resolved'),
                    ('Zanele Mthembu', '+27822223344', 'Support', 'Incoming', '2FA setup assistance', 'Medium', 'Open'),
                    ('Ryan Smith', '+27825556677', 'HR', 'Incoming', 'Payslip access issue', 'Low', 'Pending'),
                    ('Grace Ndlovu', '+27828889900', 'IT', 'Incoming', 'Email not syncing on mobile', 'High', 'In Progress'),
                ]
                now = datetime.utcnow()
                for i, (name, phone, dept, ctype, reason, pri, status) in enumerate(samples):
                    db.session.add(CallLog(
                        CallerName=name, PhoneNumber=phone, Department=dept, CallType=ctype,
                        ReasonForCall=reason, Priority=pri, Status=status,
                        AssignedTo=assignees[i % len(assignees)] if assignees else None,
                        DateLogged=now - timedelta(hours=i * 5),
                        TimeSpent=30 if status in ('Resolved', 'Closed') else None,
                        SatisfactionRating=5 if status in ('Resolved', 'Closed') else None,
                        Resolution='Issue resolved' if status in ('Resolved', 'Closed') else None,
                    ))
                created.append(str(len(samples)) + ' sample calls')
            if created:
                db.session.commit()
                return {
                    'status': 'ok',
                    'created': created,
                    'logins': {'admin': 'admin123', 'agent1': 'agent123', 'manager1': 'manager123'},
                }, 200
            return {
                'status': 'ok',
                'message': 'Already seeded',
                'logins': {'admin': 'admin123', 'agent1': 'agent123', 'manager1': 'manager123'},
            }, 200
        except Exception as e:
            db.session.rollback()
            return {'status': 'error', 'message': str(e)}, 500

    return app
