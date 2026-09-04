"""Forms package."""
from app.forms.auth import LoginForm, RegistrationForm
from app.forms.calls import CallLogForm, CallUpdateForm, NoteForm, AssignForm
from app.forms.admin import UserForm, DepartmentForm

__all__ = [
    'LoginForm', 'RegistrationForm',
    'CallLogForm', 'CallUpdateForm', 'NoteForm', 'AssignForm',
    'UserForm', 'DepartmentForm'
]
