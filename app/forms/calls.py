"""Call-related forms."""
from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, SelectField, SubmitField,
    IntegerField, HiddenField
)
from wtforms.validators import DataRequired, Length, Optional, NumberRange


class CallLogForm(FlaskForm):
    """Form for logging a new call."""
    caller_name = StringField(
        'Caller Name',
        validators=[DataRequired(), Length(min=2, max=120)]
    )
    phone_number = StringField(
        'Phone Number',
        validators=[DataRequired(), Length(min=7, max=30)]
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
        validators=[DataRequired(), Length(min=5)]
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
    notes = TextAreaField('Notes', validators=[Optional()])
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
    resolution = TextAreaField('Resolution', validators=[Optional()])
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
    submit = SubmitField('Update Call')


class NoteForm(FlaskForm):
    """Form for appending notes to a call."""
    note = TextAreaField(
        'Add Note',
        validators=[DataRequired(), Length(min=3)]
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
