"""
Authentication blueprint: login, logout, registration (admin only).
"""
from datetime import datetime, timedelta
from flask import (
    Blueprint, render_template, redirect, url_for, flash, request, session,
    current_app,
)
from flask_login import login_user, logout_user, current_user, login_required
from app import db, limiter
from app.models import User
from app.forms.auth import LoginForm, RegistrationForm
from app.utils.decorators import admin_required
from app.utils.audit import log_audit

auth_bp = Blueprint('auth', __name__)

_login_attempts = {}


def _lockout_limits():
    max_attempts = int(current_app.config.get('MAX_LOGIN_ATTEMPTS', 5))
    minutes = int(current_app.config.get('LOGIN_LOCKOUT_MINUTES', 15))
    return max(1, max_attempts), max(1, minutes)


def _is_locked(username: str) -> bool:
    entry = _login_attempts.get(username)
    if not entry:
        return False
    locked_until = entry.get('locked_until')
    if locked_until and datetime.utcnow() < locked_until:
        return True
    if locked_until:
        del _login_attempts[username]
    return False


def _record_failed_attempt(username: str) -> None:
    max_attempts, minutes = _lockout_limits()
    entry = _login_attempts.get(username, {'count': 0, 'locked_until': None})
    entry['count'] += 1
    if entry['count'] >= max_attempts:
        entry['locked_until'] = datetime.utcnow() + timedelta(minutes=minutes)
        entry['count'] = 0
    _login_attempts[username] = entry


def _clear_attempts(username: str) -> None:
    _login_attempts.pop(username, None)


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('10 per minute')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        if _is_locked(username):
            log_audit('auth.lockout', f'username={username}', target_type='user', target_id=username)
            db.session.commit()
            flash('Account temporarily locked due to too many failed attempts. Try again later.', 'danger')
            return render_template('auth/login.html', form=form)
        user = User.query.filter_by(Username=username).first()
        if user is None or not user.check_password(form.password.data):
            _record_failed_attempt(username)
            uid = user.UserID if user is not None else None
            log_audit(
                'auth.login_failed',
                f'username={username}',
                user_id=uid,
                target_type='user',
                target_id=username,
            )
            db.session.commit()
            flash('Invalid username or password.', 'danger')
            return render_template('auth/login.html', form=form)
        if not user.IsActive:
            log_audit(
                'auth.inactive',
                f'username={username}',
                user_id=user.UserID,
                target_type='user',
                target_id=user.UserID,
            )
            db.session.commit()
            flash('Your account is inactive. Contact an administrator.', 'warning')
            return render_template('auth/login.html', form=form)
        _clear_attempts(username)
        login_user(user, remember=form.remember_me.data)
        user.LastLogin = datetime.utcnow()
        log_audit('auth.login', user_id=user.UserID, target_type='user', target_id=user.UserID)
        db.session.commit()
        session.permanent = True
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('dashboard.index')
        flash(f'Welcome back, {user.FullName}.', 'success')
        return redirect(next_page)
    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    uid = current_user.UserID
    log_audit('auth.logout', user_id=uid, target_type='user', target_id=uid)
    db.session.commit()
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['GET', 'POST'])
@login_required
@admin_required
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            Username=form.username.data.strip(),
            Email=form.email.data.strip().lower(),
            FullName=form.full_name.data.strip(),
            Role=form.role.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()
        log_audit(
            'user.create',
            f'username={user.Username} role={user.Role}',
            target_type='user',
            target_id=user.UserID,
        )
        db.session.commit()
        flash(f'User {user.Username} created successfully.', 'success')
        return redirect(url_for('admin.users'))
    return render_template('auth/register.html', form=form)


@auth_bp.route('/settings')
@login_required
def settings():
    """Profile / preferences shell (frontend-first)."""
    return render_template('auth/settings.html', title='Settings')
