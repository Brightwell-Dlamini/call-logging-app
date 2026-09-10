"""
Saved filter views for agents and managers.
"""
from datetime import datetime
from app import db
import json


class SavedView(db.Model):
    """User-defined filter combination that can be pinned and reused."""
    __tablename__ = 'saved_views'
    __table_args__ = (
        db.Index('ix_saved_views_user', 'UserID'),
    )

    ViewID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserID = db.Column(
        db.Integer,
        db.ForeignKey('users.UserID', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    Name = db.Column(db.String(80), nullable=False)
    # JSON blob of filter criteria: status, priority, tag_ids, department,
    # assigned_to, overdue, date_from, date_to, q, etc.
    FiltersJson = db.Column(db.Text, nullable=False, default='{}')
    IsPinned = db.Column(db.Boolean, default=False, nullable=False)
    SortOrder = db.Column(db.Integer, default=0, nullable=False)
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    UpdatedAt = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user = db.relationship('User', backref=db.backref('saved_views', lazy='dynamic', cascade='all, delete-orphan'))

    def get_filters(self) -> dict:
        try:
            return json.loads(self.FiltersJson or '{}')
        except (TypeError, ValueError):
            return {}

    def set_filters(self, data: dict) -> None:
        self.FiltersJson = json.dumps(data or {})

    def to_dict(self) -> dict:
        return {
            'id': self.ViewID,
            'name': self.Name,
            'filters': self.get_filters(),
            'is_pinned': self.IsPinned,
            'sort_order': self.SortOrder,
            'created_at': self.CreatedAt.isoformat() if self.CreatedAt else None,
            'updated_at': self.UpdatedAt.isoformat() if self.UpdatedAt else None,
        }

    def __repr__(self) -> str:
        return f'<SavedView {self.ViewID}: {self.Name}>'
