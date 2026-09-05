"""
Dashboard blueprint with statistics and charts data.
"""
from flask import Blueprint, render_template
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
    # Avoid caching personal my_open across users on serverless
    stats = get_dashboard_stats(user=current_user)
    return render_template(
        'dashboard/index.html',
        stats=stats,
        title='Dashboard'
    )
