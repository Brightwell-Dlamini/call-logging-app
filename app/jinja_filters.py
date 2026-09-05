"""Template filters for SLA and formatting."""
from app.utils.helpers import sla_risk


def sla_badge(call):
    """Return ok | warn | breach for a CallLog instance."""
    try:
        return sla_risk(call)
    except Exception:
        return 'ok'


def register_filters(app):
    app.jinja_env.filters['sla_badge'] = sla_badge
