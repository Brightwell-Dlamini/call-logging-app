"""
Dashboard blueprint with statistics and charts data.
"""
from flask import Blueprint, make_response, render_template
from flask_login import login_required, current_user
from app.utils.helpers import get_dashboard_stats
from app.utils.decorators import login_required_active

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
@login_required_active
def index():
    """Main dashboard with role-aware statistics."""
    stats = get_dashboard_stats(user=current_user)
    response = make_response(render_template(
        'dashboard/index.html',
        stats=stats,
        title='Dashboard'
    ))
    response.headers['Cache-Control'] = 'private, no-store'
    return response
