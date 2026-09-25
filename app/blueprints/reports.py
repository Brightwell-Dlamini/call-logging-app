"""
Reports module: daily, monthly, agent performance, department reports.
Supports CSV/Excel export; PDF via ReportLab for key reports.
"""
from calendar import monthrange
from datetime import datetime, timedelta
from io import BytesIO
from flask import (
    Blueprint, render_template, request, flash, redirect, url_for,
    send_file
)
from flask_login import login_required, current_user
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from openpyxl import Workbook
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from app import db
from app.models import CallLog, User, Department
from app.utils.decorators import login_required_active, manager_required
from app.utils.audit import log_audit

reports_bp = Blueprint('reports', __name__)


def month_bounds(year: int, month: int):
    """Return [start, end) datetime range for a calendar month (UTC)."""
    start = datetime(year, month, 1)
    last_day = monthrange(year, month)[1]
    end = datetime(year, month, last_day) + timedelta(days=1)
    return start, end


def _counts_by(column, start, end):
    rows = (
        db.session.query(column, func.count(CallLog.CallID))
        .filter(CallLog.DateLogged >= start, CallLog.DateLogged < end)
        .group_by(column)
        .all()
    )
    return {key: count for key, count in rows if key is not None}


@reports_bp.route('/')
@login_required
@login_required_active
@manager_required
def index():
    """Reports landing page."""
    agents = User.query.filter(
        User.IsActive == True,
        User.Role.in_(['Agent', 'Manager', 'Admin'])
    ).order_by(User.FullName).all()
    return render_template('reports/index.html', agents=agents, title='Reports')


@reports_bp.route('/daily', methods=['GET', 'POST'])
@login_required
@login_required_active
@manager_required
def daily():
    """Daily call log report."""
    selected_date = request.args.get('date') or datetime.utcnow().strftime('%Y-%m-%d')
    try:
        day = datetime.strptime(selected_date, '%Y-%m-%d')
    except ValueError:
        flash('Invalid date format.', 'danger')
        return redirect(url_for('reports.index'))

    day_end = day + timedelta(days=1)
    calls = (
        CallLog.query.options(joinedload(CallLog.assignee))
        .filter(
            CallLog.DateLogged >= day,
            CallLog.DateLogged < day_end
        )
        .order_by(CallLog.DateLogged)
        .all()
    )

    return render_template(
        'reports/daily.html',
        calls=calls,
        selected_date=selected_date,
        title=f'Daily Report – {selected_date}'
    )


@reports_bp.route('/monthly')
@login_required
@login_required_active
@manager_required
def monthly():
    """Monthly summary statistics using an index-friendly date range."""
    year = request.args.get('year', datetime.utcnow().year, type=int)
    month = request.args.get('month', datetime.utcnow().month, type=int)
    if year < 2000 or year > 2100 or month < 1 or month > 12:
        flash('Invalid year or month.', 'danger')
        return redirect(url_for('reports.index'))

    start, end = month_bounds(year, month)
    month_filter = (CallLog.DateLogged >= start, CallLog.DateLogged < end)

    total = CallLog.query.filter(*month_filter).count()
    by_status = _counts_by(CallLog.Status, start, end)
    by_type = _counts_by(CallLog.CallType, start, end)
    by_priority = _counts_by(CallLog.Priority, start, end)
    avg_time = (
        db.session.query(func.avg(CallLog.TimeSpent))
        .filter(*month_filter, CallLog.TimeSpent.isnot(None))
        .scalar()
    ) or 0

    return render_template(
        'reports/monthly.html',
        year=year,
        month=month,
        total=total,
        by_status=by_status,
        by_type=by_type,
        by_priority=by_priority,
        avg_time=round(float(avg_time), 1),
        title=f'Monthly Summary – {year}-{month:02d}'
    )


@reports_bp.route('/agent')
@login_required
@login_required_active
@manager_required
def agent_performance():
    """Agent performance metrics via aggregates."""
    agent_id = request.args.get('agent_id', type=int)
    agents = User.query.filter(
        User.IsActive == True,
        User.Role.in_(['Agent', 'Manager', 'Admin'])
    ).order_by(User.FullName).all()

    metrics = None
    selected_agent = None
    if agent_id:
        selected_agent = User.query.get(agent_id)
        if selected_agent:
            base = CallLog.query.filter_by(AssignedTo=agent_id)
            total = base.count()
            resolved = base.filter(CallLog.Status.in_(['Resolved', 'Closed'])).count()
            avg_sat = (
                db.session.query(func.avg(CallLog.SatisfactionRating))
                .filter(
                    CallLog.AssignedTo == agent_id,
                    CallLog.SatisfactionRating.isnot(None),
                )
                .scalar()
            )
            avg_time = (
                db.session.query(func.avg(CallLog.TimeSpent))
                .filter(
                    CallLog.AssignedTo == agent_id,
                    CallLog.TimeSpent.isnot(None),
                )
                .scalar()
            )
            metrics = {
                'total': total,
                'resolved': resolved,
                'resolution_rate': round(100 * resolved / total, 1) if total else 0,
                'avg_satisfaction': round(float(avg_sat), 2) if avg_sat is not None else None,
                'avg_time': round(float(avg_time), 1) if avg_time is not None else None
            }

    return render_template(
        'reports/agent.html',
        agents=agents,
        selected_agent=selected_agent,
        metrics=metrics,
        title='Agent Performance'
    )


@reports_bp.route('/department')
@login_required
@login_required_active
@manager_required
def by_department():
    """Calls grouped by department."""
    results = (
        db.session.query(CallLog.Department, func.count(CallLog.CallID))
        .filter(CallLog.Department.isnot(None))
        .group_by(CallLog.Department)
        .order_by(func.count(CallLog.CallID).desc())
        .all()
    )
    return render_template(
        'reports/department.html',
        results=results,
        title='Calls by Department'
    )


@reports_bp.route('/export/excel')
@login_required
@login_required_active
@manager_required
def export_excel():
    """Export a simple calls workbook."""
    wb = Workbook()
    ws = wb.active
    ws.title = 'Calls'
    headers = ['CallID', 'Caller', 'Phone', 'Department', 'Type', 'Priority', 'Status', 'Date']
    ws.append(headers)
    query = CallLog.query.order_by(CallLog.DateLogged.desc()).limit(2000)
    for c in query.yield_per(200):
        ws.append([
            c.CallID, c.CallerName, c.PhoneNumber, c.Department or '',
            c.CallType, c.Priority, c.Status,
            c.DateLogged.strftime('%Y-%m-%d %H:%M') if c.DateLogged else ''
        ])
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    log_audit('report.export', 'format=excel limit=2000', target_type='report', target_id='excel')
    db.session.commit()
    return send_file(
        buffer,
        as_attachment=True,
        download_name='calls_report.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


@reports_bp.route('/export/pdf')
@login_required
@login_required_active
@manager_required
def export_pdf():
    """Generate a basic PDF summary report."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []
    elements.append(Paragraph('Call Logging – Summary Report', styles['Title']))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(
        f'Generated: {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}',
        styles['Normal']
    ))
    elements.append(Spacer(1, 20))

    total = CallLog.query.count()
    open_c = CallLog.query.filter(CallLog.Status.in_(['Open', 'In Progress', 'Pending'])).count()
    data = [
        ['Metric', 'Value'],
        ['Total Calls', str(total)],
        ['Open / In Progress / Pending', str(open_c)],
    ]
    table = Table(data, colWidths=[300, 150])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    log_audit('report.export', 'format=pdf', target_type='report', target_id='pdf')
    db.session.commit()
    return send_file(
        buffer,
        as_attachment=True,
        download_name='call_summary.pdf',
        mimetype='application/pdf'
    )
