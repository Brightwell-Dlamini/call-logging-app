"""
System-level audit events that are not tied to a single call.
"""
from datetime import datetime
from app import db


class SystemAudit(db.Model):
    """
    Durable record of authentication and administration actions.

    Call-scoped history remains on CallActivity. This table covers events
    that have no CallID (login, user CRUD, catalogue changes).
    """
    __tablename__ = 'system_audit'
    __table_args__ = (
        db.Index('ix_system_audit_created', 'CreatedAt'),
        db.Index('ix_system_audit_action', 'Action'),
    )

    AuditID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserID = db.Column(
        db.Integer,
        db.ForeignKey('users.UserID'),
        nullable=True,
        index=True,
    )
    Action = db.Column(db.String(80), nullable=False)
    Details = db.Column(db.Text, nullable=True)
    TargetType = db.Column(db.String(40), nullable=True)
    TargetID = db.Column(db.String(80), nullable=True)
    IpAddress = db.Column(db.String(64), nullable=True)
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship('User', foreign_keys=[UserID])

    def __repr__(self) -> str:
        return f'<SystemAudit {self.AuditID}: {self.Action}>'
