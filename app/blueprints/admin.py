"""
Admin blueprint: user management, departments, system audit.
"""
from io import StringIO
import csv
from flask import (
    Blueprint, render_template, redirect, url_for, flash, request, abort, Response
)
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from app import db
from app.models import User, Department, CallActivity
from app.forms.admin import UserForm, DepartmentForm
from app.utils.decorators import admin_required, login_required_active

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/')
@login_required
@admin_required
def index():
    """Admin overview."""
    user_count = User.query.count()
    active_users = User.query.filter_by(IsActive=True).count()
    dept_count = Department.query.filter_by(IsActive=True).count()
    recent_activities = (
        CallActivity.query.options(joinedload(CallActivity.user))
        .order_by(CallActivity.ActivityDate.desc())
        .limit(20)
        .all()
    )
    return render_template(
        'admin/index.html',
        user_count=user_count,
        active_users=active_users,
        dept_count=dept_count,
        recent_activities=recent_activities,
        title='Admin'
    )


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """List all users."""
    users_list = User.query.order_by(User.Username).all()
    return render_template('admin/users.html', users=users_list, title='User Management')


@admin_bp.route('/users/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_user():
    """Create a new user."""
    form = UserForm()
    if form.validate_on_submit():
        if not form.password.data:
            flash('Password is required for new users.', 'danger')
            return render_template('admin/user_form.html', form=form, title='New User')
        user = User(
            Username=form.username.data.strip(),
            Email=form.email.data.strip().lower(),
            FullName=form.full_name.data.strip(),
            Role=form.role.data,
            IsActive=form.is_active.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(f'User {user.Username} created.', 'success')
        return redirect(url_for('admin.users'))
    return render_template('admin/user_form.html', form=form, title='New User')


@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Edit an existing user."""
    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user)
    if request.method == 'GET':
        form.username.data = user.Username
        form.email.data = user.Email
        form.full_name.data = user.FullName
        form.role.data = user.Role
        form.is_active.data = user.IsActive

    if form.validate_on_submit():
        existing_u = User.query.filter(User.Username == form.username.data, User.UserID != user_id).first()
        if existing_u:
            flash('Username already taken.', 'danger')
            return render_template('admin/user_form.html', form=form, title='Edit User', user=user)
        existing_e = User.query.filter(User.Email == form.email.data, User.UserID != user_id).first()
        if existing_e:
            flash('Email already in use.', 'danger')
            return render_template('admin/user_form.html', form=form, title='Edit User', user=user)

        user.Username = form.username.data.strip()
        user.Email = form.email.data.strip().lower()
        user.FullName = form.full_name.data.strip()
        user.Role = form.role.data
        user.IsActive = form.is_active.data
        if form.password.data:
            user.set_password(form.password.data)
        db.session.commit()
        flash('User updated successfully.', 'success')
        return redirect(url_for('admin.users'))
    return render_template('admin/user_form.html', form=form, title='Edit User', user=user)


@admin_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_user(user_id):
    """Activate or deactivate a user."""
    user = User.query.get_or_404(user_id)
    if user.UserID == current_user.UserID:
        flash('You cannot deactivate your own account.', 'danger')
        return redirect(url_for('admin.users'))
    user.IsActive = not user.IsActive
    db.session.commit()
    status = 'activated' if user.IsActive else 'deactivated'
    flash(f'User {user.Username} has been {status}.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/departments')
@login_required
@admin_required
def departments():
    """List departments."""
    depts = Department.query.order_by(Department.DepartmentName).all()
    return render_template('admin/departments.html', departments=depts, title='Departments')


@admin_bp.route('/departments/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_department():
    """Create department."""
    form = DepartmentForm()
    if form.validate_on_submit():
        existing = Department.query.filter_by(DepartmentName=form.department_name.data.strip()).first()
        if existing:
            flash('Department already exists.', 'danger')
        else:
            dept = Department(
                DepartmentName=form.department_name.data.strip(),
                IsActive=form.is_active.data
            )
            db.session.add(dept)
            db.session.commit()
            flash('Department created.', 'success')
            return redirect(url_for('admin.departments'))
    return render_template('admin/department_form.html', form=form, title='New Department')


@admin_bp.route('/departments/<int:dept_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_department(dept_id):
    """Edit department."""
    dept = Department.query.get_or_404(dept_id)
    form = DepartmentForm()
    if request.method == 'GET':
        form.department_name.data = dept.DepartmentName
        form.is_active.data = dept.IsActive
    if form.validate_on_submit():
        dept.DepartmentName = form.department_name.data.strip()
        dept.IsActive = form.is_active.data
        db.session.commit()
        flash('Department updated.', 'success')
        return redirect(url_for('admin.departments'))
    return render_template('admin/department_form.html', form=form, title='Edit Department', dept=dept)


@admin_bp.route('/activities')
@login_required
@admin_required
def activities():
    """System-wide activity / audit log."""
    page = request.args.get('page', 1, type=int)
    pagination = (
        CallActivity.query.options(joinedload(CallActivity.user))
        .order_by(CallActivity.ActivityDate.desc())
        .paginate(page=page, per_page=50, error_out=False)
    )
    return render_template(
        'admin/activities.html',
        activities=pagination.items,
        pagination=pagination,
        title='Audit Log'
    )


@admin_bp.route('/activities/export')
@login_required
@admin_required
def activities_export():
    """CSV export of recent audit events."""
    rows = (
        CallActivity.query.options(joinedload(CallActivity.user))
        .order_by(CallActivity.ActivityDate.desc())
        .limit(5000)
        .all()
    )
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['ActivityID', 'CallID', 'User', 'Action', 'Details', 'ActivityDate'])
    for a in rows:
        writer.writerow([
            a.ActivityID,
            a.CallID,
            a.user.FullName if a.user else '',
            a.Action,
            a.Details or '',
            a.ActivityDate.isoformat() if a.ActivityDate else '',
        ])
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=audit_log.csv'}
    )
