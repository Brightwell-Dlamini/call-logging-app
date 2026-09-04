"""
Reports module: daily, monthly, agent performance, department reports.
Supports CSV/Excel export; PDF via ReportLab for key reports.
"""
from datetime import datetime, timedelta
from io import BytesIO
from flask import (
    Blueprint, render_template, request, flash, redirect, url_for,
    send_file, Response
)
from flask_login import login_required, current_user
from sqlalchemy import func, extract
from openpyxl import Workbook
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from app import db
from app.models import CallLog, User, Department
from app.utils.decorators import login_required_active, manager_required

reports_bp = Blueprint('reports', __name__)


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
    calls = CallLog.query.filter(
        CallLog.DateLogged >= day,
        CallLog.DateLogged < day_end
    ).order_by(CallLog.DateLogged).all()

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
    """Monthly summary statistics."""
    year = request.args.get('year', datetime.utcnow().year, type=int)
    month = request.args.get('month', datetime.utcnow().month, type=int)

    calls = CallLog.query.filter(
        extract('year', CallLog.DateLogged) == year,
        extract('month', CallLog.DateLogged) == month
    ).all()

    total = len(calls)
    by_status = {}
    by_type = {}
    by_priority = {}
    resolved_times = []
    for c in calls:
        by_status[c.Status] = by_status.get(c.Status, 0) + 1
        by_type[c.CallType] = by_type.get(c.CallType, 0) + 1
        by_priority[c.Priority] = by_priority.get(c.Priority, 0) + 1
        if c.TimeSpent is not None:
            resolved_times.append(c.TimeSpent)

    avg_time = sum(resolved_times) / len(resolved_times) if resolved_times else 0

    return render_template(
        'reports/monthly.html',
        year=year,
        month=month,
        total=total,
        by_status=by_status,
        by_type=by_type,
        by_priority=by_priority,
        avg_time=round(avg_time, 1),
        title=f'Monthly Summary – {year}-{month:02d}'
    )


@reports_bp.route('/agent')
@login_required
@login_required_active
@manager_required
def agent_performance():
    """Agent performance metrics."""
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
            handled = CallLog.query.filter_by(AssignedTo=agent_id).all()
            total = len(handled)
            resolved = sum(1 for c in handled if c.Status in ('Resolved', 'Closed'))
            ratings = [c.SatisfactionRating for c in handled if c.SatisfactionRating]
            times = [c.TimeSpent for c in handled if c.TimeSpent is not None]
            metrics = {
                'total': total,
                'resolved': resolved,
                'resolution_rate': round(100 * resolved / total, 1) if total else 0,
                'avg_satisfaction': round(sum(ratings) / len(ratings), 2) if ratings else None,
                'avg_time': round(sum(times) / len(times), 1) if times else None
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
    for c in CallLog.query.order_by(CallLog.DateLogged.desc()).limit(2000).all():
        ws.append([
            c.CallID, c.CallerName, c.PhoneNumber, c.Department or '',
            c.CallType, c.Priority, c.Status,
            c.DateLogged.strftime('%Y-%m-%d %H:%M') if c.DateLogged else ''
        ])
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
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
    return send_file(
        buffer,
        as_attachment=True,
        download_name='call_summary.pdf',
        mimetype='application/pdf'
    )
