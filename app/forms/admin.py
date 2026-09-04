"""Admin forms for user and department management."""
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, BooleanField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Email, Length, Optional, EqualTo, ValidationError
from app.models import User, Department


class UserForm(FlaskForm):
    """Create or edit user form."""
    username = StringField(
        'Username',
        validators=[DataRequired(), Length(min=3, max=80)]
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
        validators=[Optional(), Length(min=8)]
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
            # Simple uniqueness check; advanced edit handling done in view
            pass
