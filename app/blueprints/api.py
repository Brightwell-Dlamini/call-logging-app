"""
RESTful JSON API endpoints for mobile / external integration.
Requires authentication via session (or can be extended with tokens).
"""
from datetime import datetime
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models import CallLog, User
from app.utils.helpers import get_dashboard_stats, log_activity
from app.utils.decorators import agent_required, login_required_active

api_bp = Blueprint('api', __name__)


@api_bp.route('/calls', methods=['GET'])
@login_required
@login_required_active
def list_calls():
    """GET /api/calls – List calls with optional filters."""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 25, type=int), 100)
    status = request.args.get('status')
    priority = request.args.get('priority')

    query = CallLog.query
    if status:
        query = query.filter(CallLog.Status == status)
    if priority:
        query = query.filter(CallLog.Priority == priority)

    pagination = query.order_by(CallLog.DateLogged.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    items = [{
        'call_id': c.CallID,
        'caller_name': c.CallerName,
        'phone_number': c.PhoneNumber,
        'department': c.Department,
        'call_type': c.CallType,
        'priority': c.Priority,
        'status': c.Status,
        'assigned_to': c.AssignedTo,
        'date_logged': c.DateLogged.isoformat() if c.DateLogged else None
    } for c in pagination.items]

    return jsonify({
        'items': items,
        'page': pagination.page,
        'pages': pagination.pages,
        'total': pagination.total
    })


@api_bp.route('/calls', methods=['POST'])
@login_required
@login_required_active
@agent_required
def create_call():
    """POST /api/calls – Create a new call."""
    data = request.get_json() or {}
    required = ['caller_name', 'phone_number', 'call_type', 'reason_for_call']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'Missing required field: {field}'}), 400

    call = CallLog(
        CallerName=data['caller_name'].strip(),
        PhoneNumber=data['phone_number'].strip(),
        Department=data.get('department'),
        CallType=data['call_type'],
        ReasonForCall=data['reason_for_call'].strip(),
        Priority=data.get('priority', 'Medium'),
        Status='Open',
        AssignedTo=data.get('assigned_to'),
        Notes=data.get('notes')
    )
    db.session.add(call)
    db.session.flush()
    log_activity(call.CallID, current_user.UserID, 'Created (API)', 'Created via API')
    db.session.commit()

    return jsonify({
        'call_id': call.CallID,
        'message': 'Call created successfully'
    }), 201


@api_bp.route('/calls/<int:call_id>', methods=['GET'])
@login_required
@login_required_active
def get_call(call_id):
    """GET /api/calls/<id> – Call details."""
    call = CallLog.query.get_or_404(call_id)
    return jsonify({
        'call_id': call.CallID,
        'caller_name': call.CallerName,
        'phone_number': call.PhoneNumber,
        'department': call.Department,
        'call_type': call.CallType,
        'reason_for_call': call.ReasonForCall,
        'priority': call.Priority,
        'status': call.Status,
        'assigned_to': call.AssignedTo,
        'notes': call.Notes,
        'resolution': call.Resolution,
        'time_spent': call.TimeSpent,
        'satisfaction_rating': call.SatisfactionRating,
        'date_logged': call.DateLogged.isoformat() if call.DateLogged else None,
        'last_updated': call.LastUpdated.isoformat() if call.LastUpdated else None
    })


@api_bp.route('/calls/<int:call_id>', methods=['PUT'])
@login_required
@login_required_active
@agent_required
def update_call(call_id):
    """PUT /api/calls/<id> – Update call."""
    call = CallLog.query.get_or_404(call_id)
    data = request.get_json() or {}
    if 'status' in data:
        call.Status = data['status']
    if 'priority' in data:
        call.Priority = data['priority']
    if 'assigned_to' in data:
        call.AssignedTo = data['assigned_to']
    if 'notes' in data:
        call.Notes = data['notes']
    if 'resolution' in data:
        call.Resolution = data['resolution']
    if 'time_spent' in data:
        call.TimeSpent = data['time_spent']
    if 'satisfaction_rating' in data:
        call.SatisfactionRating = data['satisfaction_rating']
    call.LastUpdated = datetime.utcnow()
    log_activity(call.CallID, current_user.UserID, 'Updated (API)', str(data)[:300])
    db.session.commit()
    return jsonify({'message': 'Call updated', 'call_id': call.CallID})


@api_bp.route('/users', methods=['GET'])
@login_required
@login_required_active
def list_users():
    """GET /api/users – List active agents."""
    users = User.query.filter(
        User.IsActive == True,
        User.Role.in_(['Agent', 'Manager', 'Admin'])
    ).order_by(User.FullName).all()
    return jsonify([{
        'user_id': u.UserID,
        'username': u.Username,
        'full_name': u.FullName,
        'role': u.Role
    } for u in users])


@api_bp.route('/dashboard/stats', methods=['GET'])
@login_required
@login_required_active
def dashboard_stats():
    """GET /api/dashboard/stats – Dashboard statistics."""
    stats = get_dashboard_stats()
    return jsonify({
        'total_calls': stats['total_calls'],
        'open_calls': stats['open_calls'],
        'resolved_today': stats['resolved_today'],
        'high_priority': stats['high_priority'],
        'status_counts': stats['status_counts'],
        'calls_per_day': stats['calls_per_day'],
        'dept_counts': stats['dept_counts']
    })


@api_bp.route('/reports/daily', methods=['GET'])
@login_required
@login_required_active
def daily_report():
    """GET /api/reports/daily – Daily report data."""
    date_str = request.args.get('date', datetime.utcnow().strftime('%Y-%m-%d'))
    try:
        day = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format (YYYY-MM-DD)'}), 400
    day_end = day + __import__('datetime').timedelta(days=1)
    calls = CallLog.query.filter(
        CallLog.DateLogged >= day,
        CallLog.DateLogged < day_end
    ).all()
    return jsonify([{
        'call_id': c.CallID,
        'caller_name': c.CallerName,
        'status': c.Status,
        'priority': c.Priority,
        'department': c.Department
    } for c in calls])
