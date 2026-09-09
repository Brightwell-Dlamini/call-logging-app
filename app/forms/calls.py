"""Call-related forms."""
from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, SelectField, SubmitField,
    IntegerField, DateTimeLocalField, SelectMultipleField, BooleanField
)
from wtforms.validators import DataRequired, Length, Optional, NumberRange, Email
from app.utils.validators import PhoneNumber, MAX_NOTES, MAX_REASON, MAX_RESOLUTION


class CallLogForm(FlaskForm):
    """Form for logging a new call."""
    caller_name = StringField(
        'Caller Name',
        validators=[DataRequired(), Length(min=2, max=120)]
    )
    phone_number = StringField(
        'Phone Number',
        validators=[DataRequired(), Length(min=7, max=30), PhoneNumber()]
    )
    department = SelectField(
        'Department',
        coerce=str,
        validators=[Optional()]
    )
    call_type = SelectField(
        'Call Type',
        choices=[('Incoming', 'Incoming'), ('Outgoing', 'Outgoing')],
        validators=[DataRequired()]
    )
    reason_for_call = TextAreaField(
        'Reason for Call',
        validators=[DataRequired(), Length(min=5, max=MAX_REASON)]
    )
    priority = SelectField(
        'Priority',
        choices=[
            ('Low', 'Low'),
            ('Medium', 'Medium'),
            ('High', 'High'),
            ('Critical', 'Critical')
        ],
        default='Medium',
        validators=[DataRequired()]
    )
    assigned_to = SelectField(
        'Assign To',
        coerce=int,
        validators=[Optional()]
    )
    tags = SelectMultipleField(
        'Tags',
        coerce=int,
        validators=[Optional()]
    )
    follow_up_date = DateTimeLocalField(
        'Follow-up Date',
        format='%Y-%m-%dT%H:%M',
        validators=[Optional()]
    )
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=MAX_NOTES)])
    submit = SubmitField('Log Call')


class CallUpdateForm(FlaskForm):
    """Form for updating call status and resolution."""
    status = SelectField(
        'Status',
        choices=[
            ('Open', 'Open'),
            ('In Progress', 'In Progress'),
            ('Pending', 'Pending'),
            ('Resolved', 'Resolved'),
            ('Closed', 'Closed')
        ],
        validators=[DataRequired()]
    )
    disposition_id = SelectField(
        'Disposition',
        coerce=int,
        validators=[Optional()]
    )
    resolution = TextAreaField(
        'Resolution',
        validators=[Optional(), Length(max=MAX_RESOLUTION)]
    )
    time_spent = IntegerField(
        'Time Spent (minutes)',
        validators=[Optional(), NumberRange(min=0, max=10000)]
    )
    satisfaction_rating = SelectField(
        'Satisfaction Rating',
        choices=[
            ('', 'Not rated'),
            ('1', '1 - Very Poor'),
            ('2', '2 - Poor'),
            ('3', '3 - Average'),
            ('4', '4 - Good'),
            ('5', '5 - Excellent')
        ],
        validators=[Optional()],
        coerce=lambda x: int(x) if x else None
    )
    follow_up_date = DateTimeLocalField(
        'Follow-up Date',
        format='%Y-%m-%dT%H:%M',
        validators=[Optional()]
    )
    tags = SelectMultipleField(
        'Tags',
        coerce=int,
        validators=[Optional()]
    )
    submit = SubmitField('Update Call')


class NoteForm(FlaskForm):
    """Form for appending notes to a call."""
    note = TextAreaField(
        'Add Note',
        validators=[DataRequired(), Length(min=3, max=MAX_NOTES)]
    )
    canned_id = SelectField(
        'Insert Canned Response',
        coerce=int,
        validators=[Optional()]
    )
    submit = SubmitField('Add Note')


class AssignForm(FlaskForm):
    """Form for assigning/reassigning a call."""
    assigned_to = SelectField(
        'Assign To',
        coerce=int,
        validators=[DataRequired()]
    )
    submit = SubmitField('Assign')


class ContactForm(FlaskForm):
    """Edit contact profile."""
    display_name = StringField('Display name', validators=[Optional(), Length(max=120)])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])
    company = StringField('Company', validators=[Optional(), Length(max=120)])
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=MAX_NOTES)])
    is_vip = BooleanField('VIP customer')
    submit = SubmitField('Save contact')


class PresenceForm(FlaskForm):
    """Agent presence toggle."""
    presence = SelectField(
        'Status',
        choices=[
            ('Available', 'Available'),
            ('Busy', 'Busy'),
            ('Away', 'Away'),
            ('Offline', 'Offline'),
        ],
        validators=[DataRequired()]
    )
    submit = SubmitField('Update')
