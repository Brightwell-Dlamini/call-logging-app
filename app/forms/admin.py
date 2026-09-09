"""Admin forms for user, department, tag and canned response management."""
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, BooleanField, SubmitField, PasswordField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional, EqualTo, ValidationError
from app.models import User, Department
from app.utils.validators import UsernameChars, HexColour, DispositionCodeChars, MAX_NOTES


class UserForm(FlaskForm):
    """Create or edit user form."""
    username = StringField(
        'Username',
        validators=[DataRequired(), Length(min=3, max=80), UsernameChars()]
    )
    email = StringField(
        'Email',
        validators=[DataRequired(), Email(), Length(max=120)]
    )
    full_name = StringField(
        'Full Name',
        validators=[DataRequired(), Length(min=2, max=120)]
    )
    password = PasswordField(
        'Password',
        validators=[Optional(), Length(min=8, max=128)]
    )
    password2 = PasswordField(
        'Confirm Password',
        validators=[Optional(), EqualTo('password')]
    )
    role = SelectField(
        'Role',
        choices=[
            ('Agent', 'Agent'),
            ('Manager', 'Manager'),
            ('Admin', 'Admin')
        ],
        validators=[DataRequired()]
    )
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save User')


class DepartmentForm(FlaskForm):
    """Create or edit department form."""
    department_name = StringField(
        'Department Name',
        validators=[DataRequired(), Length(min=2, max=50)]
    )
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Department')

    def validate_department_name(self, field):
        existing = Department.query.filter_by(DepartmentName=field.data).first()
        if existing and (not hasattr(self, '_obj') or existing.DepartmentID != getattr(self, '_obj', None)):
            pass


class TagForm(FlaskForm):
    """Create or edit tag form."""
    name = StringField(
        'Tag Name',
        validators=[DataRequired(), Length(min=2, max=40)]
    )
    colour = StringField(
        'Colour (hex)',
        validators=[DataRequired(), Length(min=4, max=7), HexColour()],
        default='#6366f1'
    )
    description = StringField(
        'Description',
        validators=[Optional(), Length(max=120)]
    )
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Tag')


class CannedResponseForm(FlaskForm):
    """Create or edit canned response form."""
    title = StringField(
        'Title',
        validators=[DataRequired(), Length(min=2, max=80)]
    )
    body = TextAreaField(
        'Body',
        validators=[DataRequired(), Length(min=5, max=MAX_NOTES)]
    )
    category = StringField(
        'Category',
        validators=[Optional(), Length(max=40)]
    )
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Response')


class DispositionForm(FlaskForm):
    """Create or edit disposition code."""
    code = StringField(
        'Code',
        validators=[DataRequired(), Length(min=2, max=40), DispositionCodeChars()]
    )
    label = StringField(
        'Label',
        validators=[DataRequired(), Length(min=2, max=120)]
    )
    description = StringField(
        'Description',
        validators=[Optional(), Length(max=255)]
    )
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Disposition')
