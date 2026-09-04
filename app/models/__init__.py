"""
Database models package.
"""
from app.models.user import User
from app.models.call import CallLog, CallActivity
from app.models.department import Department

__all__ = ['User', 'CallLog', 'CallActivity', 'Department']
