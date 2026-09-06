"""
Call logging and management blueprint.
"""
from datetime import datetime
from io import StringIO
import csv
from flask import (
    Blueprint, render_template, redirect, url_for, flash, request,
    Response, abort, jsonify
)
from flask_login import login_required, current_user
from sqlalchemy import or_
from app import db
from app.models import CallLog, CallActivity, User, Department
from app.forms.calls import CallLogForm, CallUpdateForm, NoteForm, AssignForm
from app.utils.decorators import login_required_active, agent_required, admin_required
from app.utils.helpers import log_activity

calls_bp = Blueprint('calls', __name__, url_prefix='/calls')


def _populate_agent_choices(form):
    agents = User.query.filter(
        User.IsActive == True,
        User.Role.in_(['Agent', 'Manager', 'Admin'])
    ).order_by(User.FullName).all()
    form.assigned_to.choices = [(0, '— Unassigned —')] + [
        (u.UserID, f'{u.FullName} ({u.Role})') for u in agents
    ]


def _populate_department_choices(form):
    depts = Department.query.filter_by(IsActive=True).order_by(Department.DepartmentName).all()
    form.department.choices = [('', '— Select —')] + [
        (d.DepartmentName, d.DepartmentName) for d in depts
    ]


@calls_bp.route('/')
@login_required
@login_required_active
def list_calls():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    if per_page not in (10, 25, 50):
        per_page = 25

    search = request.args.get('search', '').strip()
    status = request.args.get('status', '')
    priority = request.args.get('priority', '')
    department = request.args.get('department', '')
    assigned_to = request.args.get('assigned_to', type=int)
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    sort = request.args.get('sort', 'date_desc')
    mine = request.args.get('mine')
    unassigned = request.args.get('unassigned')

    query = CallLog.query

    if search:
        like = f'%{search}%'
        try:
            call_id_search = int(search)
            query = query.filter(or_(
                CallLog.CallerName.ilike(like),
                CallLog.PhoneNumber.ilike(like),
                CallLog.CallID == call_id_search
            ))
        except ValueError:
            query = query.filter(or_(
                CallLog.CallerName.ilike(like),
                CallLog.PhoneNumber.ilike(like)
            ))

    if status:
        query = query.filter(CallLog.Status == status)
    if priority:
        query = query.filter(CallLog.Priority == priority)
    if department:
        query = query.filter(CallLog.Department == department)
    if assigned_to:
        query = query.filter(CallLog.AssignedTo == assigned_to)
    if mine:
        query = query.filter(CallLog.AssignedTo == current_user.UserID)
    if unassigned:
        query = query.filter(CallLog.AssignedTo.is_(None))
    if date_from:
        try:
            query = query.filter(CallLog.DateLogged >= datetime.strptime(date_from, '%Y-%m-%d'))
        except ValueError:
            pass
    if date_to:
        try:
            from datetime import timedelta
            query = query.filter(CallLog.DateLogged <= datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))
        except ValueError:
            pass

    if sort == 'priority':
        priority_order = db.case(
            (CallLog.Priority == 'Critical', 1),
            (CallLog.Priority == 'High', 2),
            (CallLog.Priority == 'Medium', 3),
            else_=4
        )
        query = query.order_by(priority_order, CallLog.DateLogged.desc())
    elif sort == 'status':
        query = query.order_by(CallLog.Status, CallLog.DateLogged.desc())
    else:
        query = query.order_by(CallLog.DateLogged.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    calls = pagination.items
    departments = Department.query.filter_by(IsActive=True).order_by(Department.DepartmentName).all()

    return render_template(
        'calls/list.html',
        calls=calls,
        pagination=pagination,
        departments=departments,
        title='Calls'
    )


@calls_bp.route('/new', methods=['GET', 'POST'])
@login_required
@login_required_active
@agent_required
def new_call():
    form = CallLogForm()
    _populate_department_choices(form)
    _populate_agent_choices(form)

    if form.validate_on_submit():
        assigned = form.assigned_to.data if form.assigned_to.data and form.assigned_to.data != 0 else None
        call = CallLog(
            CallerName=form.caller_name.data.strip(),
            PhoneNumber=form.phone_number.data.strip(),
            Department=form.department.data or None,
            CallType=form.call_type.data,
            ReasonForCall=form.reason_for_call.data.strip(),
            Priority=form.priority.data,
            Status='Open',
            AssignedTo=assigned,
            Notes=form.notes.data.strip() if form.notes.data else None
        )
        db.session.add(call)
        db.session.flush()

        log_activity(
            call.CallID,
            current_user.UserID,
            'Created',
            f'Call logged by {current_user.FullName}'
        )
        if assigned:
            agent = User.query.get(assigned)
            log_activity(
                call.CallID,
                current_user.UserID,
                'Assigned',
                f'Assigned to {agent.FullName if agent else assigned}'
            )
        db.session.commit()
        flash(f'Call #{call.CallID} logged successfully.', 'success')
        return redirect(url_for('calls.detail', call_id=call.CallID))

    return render_template('calls/new.html', form=form, title='Log New Call')


@calls_bp.route('/<int:call_id>')
@login_required
@login_required_active
def detail(call_id):
    call = CallLog.query.get_or_404(call_id)
    update_form = CallUpdateForm(obj=call)
    if call.SatisfactionRating:
        update_form.satisfaction_rating.data = str(call.SatisfactionRating)
    note_form = NoteForm()
    assign_form = AssignForm()
    _populate_agent_choices(assign_form)
    if call.AssignedTo:
        assign_form.assigned_to.data = call.AssignedTo

    activities = call.activities.order_by(CallActivity.ActivityDate.desc()).all()
    related_count = CallLog.query.filter(
        CallLog.PhoneNumber == call.PhoneNumber,
        CallLog.CallID != call.CallID
    ).count()
    related_open = CallLog.query.filter(
        CallLog.PhoneNumber == call.PhoneNumber,
        CallLog.CallID != call.CallID,
        CallLog.Status.in_(['Open', 'In Progress', 'Pending'])
    ).order_by(CallLog.DateLogged.desc()).limit(5).all()

    ctx = dict(
        call=call,
        update_form=update_form,
        note_form=note_form,
        assign_form=assign_form,
        activities=activities,
        related_count=related_count,
        related_open=related_open,
        title=f'Call #{call.CallID}'
    )
    if request.args.get('partial') == '1' or request.headers.get('X-Partial') == '1':
        return render_template('calls/detail_partial.html', **ctx)
    return render_template('calls/detail.html', **ctx)


@calls_bp.route('/<int:call_id>/update', methods=['POST'])
@login_required
@login_required_active
@agent_required
def update_call(call_id):
    call = CallLog.query.get_or_404(call_id)
    form = CallUpdateForm()
    if form.validate_on_submit():
        old_status = call.Status
        call.Status = form.status.data
        if form.resolution.data:
            call.Resolution = form.resolution.data.strip()
        if form.time_spent.data is not None:
            call.TimeSpent = form.time_spent.data
        if form.satisfaction_rating.data:
            call.SatisfactionRating = form.satisfaction_rating.data
        call.LastUpdated = datetime.utcnow()

        details = f'Status changed from {old_status} to {call.Status}'
        if form.resolution.data:
            details += '; Resolution updated'
        log_activity(call.CallID, current_user.UserID, 'Updated', details)
        db.session.commit()
        flash('Call updated successfully.', 'success')
    else:
        flash('Validation error while updating call.', 'danger')
    if request.form.get('return_to') == 'list' or request.args.get('return_to') == 'list':
        return redirect(url_for('calls.list_calls'))
    return redirect(url_for('calls.detail', call_id=call_id))


@calls_bp.route('/<int:call_id>/note', methods=['POST'])
@login_required
@login_required_active
@agent_required
def add_note(call_id):
    call = CallLog.query.get_or_404(call_id)
    form = NoteForm()
    if form.validate_on_submit():
        note_text = form.note.data.strip()
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M')
        new_note = f'[{timestamp} - {current_user.FullName}] {note_text}'
        if call.Notes:
            call.Notes = call.Notes + '\n\n' + new_note
        else:
            call.Notes = new_note
        call.LastUpdated = datetime.utcnow()
        log_activity(call.CallID, current_user.UserID, 'Note Added', note_text[:200])
        db.session.commit()
        flash('Note added.', 'success')
    return redirect(url_for('calls.detail', call_id=call_id))


@calls_bp.route('/<int:call_id>/assign', methods=['POST'])
@login_required
@login_required_active
@agent_required
def assign_call(call_id):
    call = CallLog.query.get_or_404(call_id)
    form = AssignForm()
    _populate_agent_choices(form)
    if form.validate_on_submit():
        agent_id = form.assigned_to.data
        if agent_id == 0:
            agent_id = None
        old = call.assignee.FullName if call.assignee else 'Unassigned'
        call.AssignedTo = agent_id
        call.LastUpdated = datetime.utcnow()
        agent = User.query.get(agent_id) if agent_id else None
        new_name = agent.FullName if agent else 'Unassigned'
        log_activity(
            call.CallID,
            current_user.UserID,
            'Assigned',
            f'Reassigned from {old} to {new_name}'
        )
        db.session.commit()
        flash(f'Call assigned to {new_name}.', 'success')
    return redirect(url_for('calls.detail', call_id=call_id))


@calls_bp.route('/bulk', methods=['POST'])
@login_required
@login_required_active
@agent_required
def bulk_update():
    """Bulk status or assign for selected calls (JSON or form)."""
    data = request.get_json(silent=True) or {}
    ids = data.get('ids') or request.form.getlist('ids')
    action = (data.get('action') or request.form.get('action') or '').strip().lower()

    try:
        ids = [int(i) for i in ids]
    except (TypeError, ValueError):
        return jsonify(ok=False, error='Invalid ids'), 400
    if not ids:
        return jsonify(ok=False, error='No calls selected'), 400
    ids = ids[:100]
    calls_q = CallLog.query.filter(CallLog.CallID.in_(ids)).all()

    if action in ('assign', 'claim'):
        if action == 'claim':
            agent_id = current_user.UserID
        else:
            agent_id = data.get('assigned_to') or request.form.get('assigned_to', type=int)
            try:
                agent_id = int(agent_id) if agent_id is not None else None
            except (TypeError, ValueError):
                agent_id = None
            if agent_id == 0:
                agent_id = None
        agent = User.query.get(agent_id) if agent_id else None
        name = agent.FullName if agent else 'Unassigned'
        updated = 0
        for call in calls_q:
            call.AssignedTo = agent_id
            call.LastUpdated = datetime.utcnow()
            if action == 'claim' and call.Status == 'Open':
                call.Status = 'In Progress'
            log_activity(
                call.CallID,
                current_user.UserID,
                'Bulk Assign',
                f'Assigned to {name}'
            )
            updated += 1
        db.session.commit()
        return jsonify(ok=True, updated=updated, message=f'{updated} call(s) assigned to {name}')

    status_map = {
        'progress': 'In Progress',
        'in_progress': 'In Progress',
        'resolve': 'Resolved',
        'resolved': 'Resolved',
        'pending': 'Pending',
        'close': 'Closed',
        'closed': 'Closed',
        'open': 'Open',
    }
    new_status = status_map.get(action)
    if not new_status:
        return jsonify(ok=False, error='Unknown action'), 400

    updated = 0
    for call in calls_q:
        old = call.Status
        if old == new_status:
            continue
        call.Status = new_status
        call.LastUpdated = datetime.utcnow()
        if new_status in ('Resolved', 'Closed') and not call.Resolution:
            call.Resolution = f'Bulk marked {new_status} by {current_user.FullName}'
        log_activity(
            call.CallID,
            current_user.UserID,
            'Bulk Update',
            f'Status {old} → {new_status}'
        )
        updated += 1
    db.session.commit()
    return jsonify(
        ok=True,
        updated=updated,
        status=new_status,
        message=f'{updated} call(s) set to {new_status}',
    )


@calls_bp.route('/export')
@login_required
@login_required_active
def export_csv():
    query = CallLog.query.order_by(CallLog.DateLogged.desc())
    status = request.args.get('status')
    if status:
        query = query.filter(CallLog.Status == status)
    priority = request.args.get('priority')
    if priority:
        query = query.filter(CallLog.Priority == priority)
    department = request.args.get('department')
    if department:
        query = query.filter(CallLog.Department == department)
    assigned_to = request.args.get('assigned_to', type=int)
    if assigned_to:
        query = query.filter(CallLog.AssignedTo == assigned_to)
    search = request.args.get('search', '').strip()
    if search:
        like = f'%{search}%'
        query = query.filter(or_(
            CallLog.CallerName.ilike(like),
            CallLog.PhoneNumber.ilike(like)
        ))

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'CallID', 'CallerName', 'PhoneNumber', 'Department', 'CallType',
        'Priority', 'Status', 'AssignedTo', 'DateLogged', 'ReasonForCall', 'Resolution'
    ])
    for c in query.limit(5000).all():
        writer.writerow([
            c.CallID, c.CallerName, c.PhoneNumber, c.Department or '', c.CallType,
            c.Priority, c.Status,
            c.assignee.FullName if c.assignee else '',
            c.DateLogged.isoformat() if c.DateLogged else '',
            c.ReasonForCall or '',
            c.Resolution or '',
        ])
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=calls_export.csv'}
    )


@calls_bp.route('/<int:call_id>/delete', methods=['POST'])
@login_required
@login_required_active
@admin_required
def delete_call(call_id):
    call = CallLog.query.get_or_404(call_id)
    cid = call.CallID
    db.session.delete(call)
    db.session.commit()
    flash(f'Call #{cid} deleted.', 'success')
    return redirect(url_for('calls.list_calls'))
