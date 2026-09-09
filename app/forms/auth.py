"""Authentication forms."""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from app.models import User
from app.utils.validators import UsernameChars


class LoginForm(FlaskForm):
    """User login form."""
    username = StringField(
        'Username',
        validators=[DataRequired(), Length(min=3, max=80)]
    )
    password = PasswordField(
        'Password',
        validators=[DataRequired()]
    )
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    """Admin-only user registration form."""
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
        validators=[DataRequired(), Length(min=8, max=128)]
    )
    password2 = PasswordField(
        'Confirm Password',
        validators=[DataRequired(), EqualTo('password')]
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
    submit = SubmitField('Create User')

    def validate_username(self, username):
        user = User.query.filter_by(Username=username.data).first()
        if user is not None:
            raise ValidationError('Username already exists. Please choose a different one.')

    def validate_email(self, email):
        user = User.query.filter_by(Email=email.data).first()
        if user is not None:
            raise ValidationError('Email already registered. Please use a different one.')
