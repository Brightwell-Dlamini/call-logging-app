"""
CSV bulk import for historical / batch call logging.
"""
from datetime import datetime
from io import StringIO
import csv
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import CallLog, Tag, User
from app.utils.decorators import login_required_active, manager_required
from app.utils.helpers import log_activity, ensure_contact, notify_assignment

import_bp = Blueprint('import_calls', __name__, url_prefix='/import')

VALID_STATUS = {'Open', 'In Progress', 'Pending', 'Resolved', 'Closed'}
VALID_PRIORITY = {'Low', 'Medium', 'High', 'Critical'}
VALID_TYPE = {'Incoming', 'Outgoing'}

EXPECTED_HEADERS = {
    'callername', 'caller_name', 'caller',
    'phonenumber', 'phone_number', 'phone',
    'reasonforcall', 'reason_for_call', 'reason',
}


def _norm_header(h):
    return (h or '').strip().lower().replace(' ', '').replace('-', '')


def _parse_datetime(val):
    if not val:
        return None
    s = str(val).strip()
    for fmt in (
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%d',
        '%d/%m/%Y %H:%M',
        '%d/%m/%Y',
    ):
        try:
            return datetime.strptime(s[:19], fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s.replace('Z', '+00:00')).replace(tzinfo=None)
    except ValueError:
        return None


def _map_row(row):
    """Map a CSV row dict (original headers) to call fields."""
    keyed = {_norm_header(k): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}

    def first(*names):
        for n in names:
            v = keyed.get(_norm_header(n))
            if v not in (None, ''):
                return v
        return None

    caller = first('CallerName', 'caller_name', 'caller', 'name')
    phone = first('PhoneNumber', 'phone_number', 'phone')
    reason = first('ReasonForCall', 'reason_for_call', 'reason')
    if not caller or not phone or not reason:
        return None, 'Missing required fields (caller, phone, reason)'

    call_type = first('CallType', 'call_type', 'type') or 'Incoming'
    if call_type not in VALID_TYPE:
        call_type = 'Incoming'

    priority = first('Priority', 'priority') or 'Medium'
    if priority not in VALID_PRIORITY:
        priority = 'Medium'

    status = first('Status', 'status') or 'Open'
    if status not in VALID_STATUS:
        status = 'Open'

    department = first('Department', 'department')
    notes = first('Notes', 'notes')
    resolution = first('Resolution', 'resolution')
    date_logged = _parse_datetime(first('DateLogged', 'date_logged', 'date', 'logged'))
    follow_up = _parse_datetime(first('FollowUpDate', 'follow_up_date', 'followup'))
    tags_raw = first('Tags', 'tags') or ''
    tag_names = [t.strip() for t in str(tags_raw).split(',') if t.strip()]

    assigned_name = first('AssignedTo', 'assigned_to', 'assignee')
    assigned_id = None
    if assigned_name:
        u = User.query.filter(
            db.or_(
                User.FullName == assigned_name,
                User.Username == assigned_name,
            )
        ).first()
        if u:
            assigned_id = u.UserID

    return {
        'CallerName': str(caller)[:120],
        'PhoneNumber': str(phone)[:30],
        'ReasonForCall': str(reason),
        'CallType': call_type,
        'Priority': priority,
        'Status': status,
        'Department': str(department)[:50] if department else None,
        'Notes': notes,
        'Resolution': resolution,
        'DateLogged': date_logged or datetime.utcnow(),
        'FollowUpDate': follow_up,
        'AssignedTo': assigned_id,
        'tag_names': tag_names,
    }, None


@import_bp.route('/', methods=['GET', 'POST'])
@login_required
@login_required_active
@manager_required
def import_page():
    result = None
    if request.method == 'POST':
        f = request.files.get('file')
        if not f or not f.filename:
            flash('Choose a CSV file to upload.', 'warning')
            return redirect(url_for('import_calls.import_page'))

        dry_run = request.form.get('dry_run') in ('1', 'true', 'on', 'yes')
        try:
            raw = f.read()
            try:
                text = raw.decode('utf-8-sig')
            except UnicodeDecodeError:
                text = raw.decode('latin-1')
            reader = csv.DictReader(StringIO(text))
            if not reader.fieldnames:
                flash('CSV appears empty or has no header row.', 'danger')
                return redirect(url_for('import_calls.import_page'))

            created = 0
            skipped = 0
            errors = []
            preview = []

            for i, row in enumerate(reader, start=2):
                if created + skipped >= 2000:
                    errors.append(f'Stopped at row {i}: 2000 row limit per upload')
                    break
                mapped, err = _map_row(row)
                if err:
                    skipped += 1
                    if len(errors) < 20:
                        errors.append(f'Row {i}: {err}')
                    continue

                if dry_run:
                    preview.append({
                        'row': i,
                        'caller': mapped['CallerName'],
                        'phone': mapped['PhoneNumber'],
                        'priority': mapped['Priority'],
                        'status': mapped['Status'],
                    })
                    created += 1
                    continue

                call = CallLog(
                    CallerName=mapped['CallerName'],
                    PhoneNumber=mapped['PhoneNumber'],
                    Department=mapped['Department'],
                    CallType=mapped['CallType'],
                    ReasonForCall=mapped['ReasonForCall'],
                    Priority=mapped['Priority'],
                    Status=mapped['Status'],
                    AssignedTo=mapped['AssignedTo'],
                    Notes=mapped['Notes'],
                    Resolution=mapped['Resolution'],
                    DateLogged=mapped['DateLogged'],
                    FollowUpDate=mapped['FollowUpDate'],
                )
                db.session.add(call)
                db.session.flush()

                if mapped['tag_names']:
                    tags = Tag.query.filter(
                        Tag.Name.in_(mapped['tag_names']),
                        Tag.IsActive == True,
                    ).all()
                    call.tags = tags

                ensure_contact(call.PhoneNumber, display_name=call.CallerName)
                log_activity(
                    call.CallID,
                    current_user.UserID,
                    'Created',
                    f'Imported from CSV by {current_user.FullName}',
                )
                if call.AssignedTo:
                    notify_assignment(call, actor=current_user)
                created += 1

            if not dry_run:
                db.session.commit()
                flash(f'Imported {created} call(s). Skipped {skipped}.', 'success')
            else:
                flash(f'Dry run: {created} row(s) would import, {skipped} skipped.', 'info')

            result = {
                'created': created,
                'skipped': skipped,
                'errors': errors,
                'dry_run': dry_run,
                'preview': preview[:25],
            }
        except Exception as e:
            db.session.rollback()
            flash(f'Import failed: {type(e).__name__}: {e}', 'danger')

    return render_template(
        'admin/import.html',
        title='Import calls',
        result=result,
    )
