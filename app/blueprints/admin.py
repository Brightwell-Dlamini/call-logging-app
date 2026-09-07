"""
Admin blueprint: user management, departments, tags, canned responses, dispositions, system audit.
"""
from io import StringIO
import csv
from flask import (
    Blueprint, render_template, redirect, url_for, flash, request, abort, Response
)
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from app import db
from app.models import User, Department, CallActivity, Tag, CannedResponse, DispositionCode
from app.forms.admin import UserForm, DepartmentForm, TagForm, CannedResponseForm, DispositionForm
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
    tag_count = Tag.query.filter_by(IsActive=True).count()
    canned_count = CannedResponse.query.filter_by(IsActive=True).count()
    disposition_count = DispositionCode.query.filter_by(IsActive=True).count()
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
        tag_count=tag_count,
        canned_count=canned_count,
        disposition_count=disposition_count,
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


# ── Tags ──────────────────────────────────────────────────────────────────────

@admin_bp.route('/tags')
@login_required
@admin_required
def tags():
    tags_list = Tag.query.order_by(Tag.Name).all()
    return render_template('admin/tags.html', tags=tags_list, title='Tags')


@admin_bp.route('/tags/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_tag():
    form = TagForm()
    if form.validate_on_submit():
        name = form.name.data.strip().lower()
        existing = Tag.query.filter_by(Name=name).first()
        if existing:
            flash('Tag already exists.', 'danger')
        else:
            tag = Tag(
                Name=name,
                Colour=form.colour.data.strip() or '#6366f1',
                Description=form.description.data.strip() if form.description.data else None,
                IsActive=form.is_active.data,
            )
            db.session.add(tag)
            db.session.commit()
            flash('Tag created.', 'success')
            return redirect(url_for('admin.tags'))
    return render_template('admin/tag_form.html', form=form, title='New Tag')


@admin_bp.route('/tags/<int:tag_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_tag(tag_id):
    tag = Tag.query.get_or_404(tag_id)
    form = TagForm()
    if request.method == 'GET':
        form.name.data = tag.Name
        form.colour.data = tag.Colour
        form.description.data = tag.Description
        form.is_active.data = tag.IsActive
    if form.validate_on_submit():
        tag.Name = form.name.data.strip().lower()
        tag.Colour = form.colour.data.strip() or '#6366f1'
        tag.Description = form.description.data.strip() if form.description.data else None
        tag.IsActive = form.is_active.data
        db.session.commit()
        flash('Tag updated.', 'success')
        return redirect(url_for('admin.tags'))
    return render_template('admin/tag_form.html', form=form, title='Edit Tag', tag=tag)


# ── Canned Responses ──────────────────────────────────────────────────────────

@admin_bp.route('/canned')
@login_required
@admin_required
def canned():
    items = CannedResponse.query.order_by(CannedResponse.Category, CannedResponse.Title).all()
    return render_template('admin/canned.html', items=items, title='Canned Responses')


@admin_bp.route('/canned/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_canned():
    form = CannedResponseForm()
    if form.validate_on_submit():
        item = CannedResponse(
            Title=form.title.data.strip(),
            Body=form.body.data.strip(),
            Category=form.category.data.strip() if form.category.data else None,
            CreatedBy=current_user.UserID,
            IsActive=form.is_active.data,
        )
        db.session.add(item)
        db.session.commit()
        flash('Canned response created.', 'success')
        return redirect(url_for('admin.canned'))
    return render_template('admin/canned_form.html', form=form, title='New Canned Response')


@admin_bp.route('/canned/<int:resp_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_canned(resp_id):
    item = CannedResponse.query.get_or_404(resp_id)
    form = CannedResponseForm()
    if request.method == 'GET':
        form.title.data = item.Title
        form.body.data = item.Body
        form.category.data = item.Category
        form.is_active.data = item.IsActive
    if form.validate_on_submit():
        item.Title = form.title.data.strip()
        item.Body = form.body.data.strip()
        item.Category = form.category.data.strip() if form.category.data else None
        item.IsActive = form.is_active.data
        db.session.commit()
        flash('Canned response updated.', 'success')
        return redirect(url_for('admin.canned'))
    return render_template('admin/canned_form.html', form=form, title='Edit Canned Response', item=item)


# ── Disposition codes ─────────────────────────────────────────────────────────

@admin_bp.route('/dispositions')
@login_required
@admin_required
def dispositions():
    items = DispositionCode.query.order_by(DispositionCode.Code).all()
    return render_template('admin/dispositions.html', items=items, title='Disposition Codes')


@admin_bp.route('/dispositions/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_disposition():
    form = DispositionForm()
    if form.validate_on_submit():
        code = form.code.data.strip().upper()
        if DispositionCode.query.filter_by(Code=code).first():
            flash('Disposition code already exists.', 'danger')
        else:
            item = DispositionCode(
                Code=code,
                Label=form.label.data.strip(),
                Description=form.description.data.strip() if form.description.data else None,
                IsActive=form.is_active.data,
            )
            db.session.add(item)
            db.session.commit()
            flash('Disposition created.', 'success')
            return redirect(url_for('admin.dispositions'))
    return render_template('admin/disposition_form.html', form=form, title='New Disposition')


@admin_bp.route('/dispositions/<int:disp_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_disposition(disp_id):
    item = DispositionCode.query.get_or_404(disp_id)
    form = DispositionForm()
    if request.method == 'GET':
        form.code.data = item.Code
        form.label.data = item.Label
        form.description.data = item.Description
        form.is_active.data = item.IsActive
    if form.validate_on_submit():
        item.Code = form.code.data.strip().upper()
        item.Label = form.label.data.strip()
        item.Description = form.description.data.strip() if form.description.data else None
        item.IsActive = form.is_active.data
        db.session.commit()
        flash('Disposition updated.', 'success')
        return redirect(url_for('admin.dispositions'))
    return render_template('admin/disposition_form.html', form=form, title='Edit Disposition', item=item)


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
