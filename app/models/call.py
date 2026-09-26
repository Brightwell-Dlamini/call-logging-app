"""
Call Log and Call Activity models.
"""
from datetime import datetime
from app import db
from app.models.tag import call_tags
from app.models.watcher import call_watchers


class CallLog(db.Model):
    """
    Primary call logging entity.
    Tracks customer calls, support requests, and incidents.
    """
    __tablename__ = 'call_log'
    __table_args__ = (
        db.Index('ix_call_log_status_datelogged', 'Status', 'DateLogged'),
        db.Index('ix_call_log_assigned_status', 'AssignedTo', 'Status'),
        db.Index('ix_call_log_dept_status', 'Department', 'Status'),
        db.Index('ix_call_log_followup', 'FollowUpDate'),
        db.Index('ix_call_log_lastupdated', 'LastUpdated'),
        db.Index('ix_call_log_type_datelogged', 'CallType', 'DateLogged'),
        db.Index('ix_call_log_priority_status', 'Priority', 'Status'),
        db.Index('ix_call_log_status_lastupdated', 'Status', 'LastUpdated'),
    )

    CallID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    CallerName = db.Column(db.String(120), nullable=False, index=True)
    PhoneNumber = db.Column(db.String(30), nullable=False, index=True)
    Department = db.Column(db.String(50), nullable=True, index=True)
    CallType = db.Column(
        db.Enum('Incoming', 'Outgoing', name='call_types'),
        nullable=False
    )
    ReasonForCall = db.Column(db.Text, nullable=False)
    Priority = db.Column(
        db.Enum('Low', 'Medium', 'High', 'Critical', name='priority_levels'),
        nullable=False,
        default='Medium',
        index=True
    )
    Status = db.Column(
        db.Enum('Open', 'In Progress', 'Pending', 'Resolved', 'Closed', name='call_statuses'),
        nullable=False,
        default='Open',
        index=True
    )
    AssignedTo = db.Column(
        db.Integer,
        db.ForeignKey('users.UserID'),
        nullable=True,
        index=True
    )
    DispositionID = db.Column(
        db.Integer,
        db.ForeignKey('disposition_codes.DispositionID'),
        nullable=True,
        index=True
    )
    Notes = db.Column(db.Text, nullable=True)
    DateLogged = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    LastUpdated = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    Resolution = db.Column(db.Text, nullable=True)
    TimeSpent = db.Column(db.Integer, nullable=True)  # minutes
    SatisfactionRating = db.Column(db.Integer, nullable=True)  # 1-5
    FollowUpDate = db.Column(db.DateTime, nullable=True)  # next action due

    # Relationships
    assignee = db.relationship(
        'User',
        back_populates='assigned_calls',
        foreign_keys=[AssignedTo]
    )
    disposition = db.relationship(
        'DispositionCode',
        back_populates='calls',
        foreign_keys=[DispositionID]
    )
    activities = db.relationship(
        'CallActivity',
        back_populates='call',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='CallActivity.ActivityDate.desc()'
    )
    tags = db.relationship(
        'Tag',
        secondary=call_tags,
        back_populates='calls',
        lazy='joined',
    )
    watchers = db.relationship(
        'User',
        secondary=call_watchers,
        lazy='joined',
        backref=db.backref('watched_calls', lazy='dynamic'),
    )

    def __repr__(self) -> str:
        return f'<CallLog {self.CallID}: {self.CallerName} [{self.Status}]>'

    @property
    def is_overdue(self) -> bool:
        if not self.FollowUpDate or self.Status in ('Resolved', 'Closed'):
            return False
        return self.FollowUpDate < datetime.utcnow()

    def is_watched_by(self, user) -> bool:
        if not user:
            return False
        return any(w.UserID == user.UserID for w in (self.watchers or []))


class CallActivity(db.Model):
    """
    Audit log for all actions performed on a call.
    """
    __tablename__ = 'call_activity'
    __table_args__ = (
        db.Index('ix_call_activity_activitydate', 'ActivityDate'),
        db.Index('ix_call_activity_call_date', 'CallID', 'ActivityDate'),
    )

    ActivityID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    CallID = db.Column(
        db.Integer,
        db.ForeignKey('call_log.CallID', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    UserID = db.Column(
        db.Integer,
        db.ForeignKey('users.UserID'),
        nullable=False,
        index=True
    )
    Action = db.Column(db.String(50), nullable=False)
    Details = db.Column(db.Text, nullable=True)
    ActivityDate = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    call = db.relationship('CallLog', back_populates='activities')
    user = db.relationship('User', back_populates='activities')

    def __repr__(self) -> str:
        return f'<CallActivity {self.ActivityID}: {self.Action} on Call {self.CallID}>'
