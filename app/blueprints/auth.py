"""
Authentication blueprint: login, logout, registration (admin only).
"""
from datetime import datetime, timedelta
from flask import (
    Blueprint, render_template, redirect, url_for, flash, request, session
)
from flask_login import login_user, logout_user, current_user, login_required
from app import db, limiter
from app.models import User
from app.forms.auth import LoginForm, RegistrationForm
from app.utils.decorators import admin_required

auth_bp = Blueprint('auth', __name__)


# Simple in-memory lockout store (use Redis in production)
_login_attempts = {}


def _is_locked(username: str) -> bool:
    entry = _login_attempts.get(username)
    if not entry:
        return False
    if datetime.utcnow() < entry['locked_until']:
        return True
    # Lock expired
    del _login_attempts[username]
    return False


def _record_failed_attempt(username: str) -> None:
    entry = _login_attempts.get(username, {'count': 0, 'locked_until': None})
    entry['count'] += 1
    if entry['count'] >= 5:
        entry['locked_until'] = datetime.utcnow() + timedelta(minutes=15)
        entry['count'] = 0
    _login_attempts[username] = entry


def _clear_attempts(username: str) -> None:
    _login_attempts.pop(username, None)


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('10 per minute')
def login():
    """User login page."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        if _is_locked(username):
            flash('Account temporarily locked due to too many failed attempts. Try again later.', 'danger')
            return render_template('auth/login.html', form=form)

        user = User.query.filter_by(Username=username).first()
        if user is None or not user.check_password(form.password.data):
            _record_failed_attempt(username)
            flash('Invalid username or password.', 'danger')
            return render_template('auth/login.html', form=form)

        if not user.IsActive:
            flash('Your account is inactive. Contact an administrator.', 'warning')
            return render_template('auth/login.html', form=form)

        _clear_attempts(username)
        login_user(user, remember=form.remember_me.data)
        user.LastLogin = datetime.utcnow()
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
    """Log out the current user."""
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['GET', 'POST'])
@login_required
@admin_required
def register():
    """Admin-only user registration."""
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
        db.session.commit()
        flash(f'User {user.Username} created successfully.', 'success')
        return redirect(url_for('admin.users'))
    return render_template('auth/register.html', form=form)
