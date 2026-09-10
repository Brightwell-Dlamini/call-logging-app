"""
In-app notifications for assignments, SLA, follow-ups, and system events.
"""
from datetime import datetime
from app import db


class Notification(db.Model):
    """User-targeted notification."""
    __tablename__ = 'notifications'
    __table_args__ = (
        db.Index('ix_notifications_user_read', 'UserID', 'IsRead'),
        db.Index('ix_notifications_created', 'CreatedAt'),
    )

    NotificationID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserID = db.Column(
        db.Integer,
        db.ForeignKey('users.UserID', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    Title = db.Column(db.String(160), nullable=False)
    Body = db.Column(db.Text, nullable=True)
    # assignment | sla_breach | sla_warn | follow_up | mention | system | claim
    Category = db.Column(db.String(40), nullable=False, default='system')
    # Optional deep-link target
    LinkUrl = db.Column(db.String(255), nullable=True)
    CallID = db.Column(
        db.Integer,
        db.ForeignKey('call_log.CallID', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    IsRead = db.Column(db.Boolean, default=False, nullable=False)
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship('User', backref=db.backref('notifications', lazy='dynamic'))
    call = db.relationship('CallLog', foreign_keys=[CallID])

    def to_dict(self) -> dict:
        return {
            'id': self.NotificationID,
            'title': self.Title,
            'body': self.Body,
            'category': self.Category,
            'link_url': self.LinkUrl,
            'call_id': self.CallID,
            'is_read': self.IsRead,
            'created_at': self.CreatedAt.isoformat() if self.CreatedAt else None,
        }

    def __repr__(self) -> str:
        return f'<Notification {self.NotificationID}: {self.Title[:40]}>'
