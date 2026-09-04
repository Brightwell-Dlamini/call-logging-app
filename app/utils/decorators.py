"""
Role-based access control decorators.
"""
from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user


def login_required_active(f):
    """Ensure user is authenticated and active."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not current_user.IsActive:
            flash('Your account has been deactivated. Contact an administrator.', 'danger')
            return redirect(url_for('auth.logout'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Require Admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def manager_required(f):
    """Require Manager or Admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_manager:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def agent_required(f):
    """Require any authenticated agent-level user (Agent, Manager, Admin)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_agent:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
