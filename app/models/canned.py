"""
Canned response / quick-reply templates.
"""
from datetime import datetime
from app import db


class CannedResponse(db.Model):
    """Reusable text snippets for notes and resolutions."""
    __tablename__ = 'canned_responses'

    ResponseID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Title = db.Column(db.String(80), nullable=False)
    Body = db.Column(db.Text, nullable=False)
    Category = db.Column(db.String(40), nullable=True, index=True)  # e.g. Greeting, Resolution, Follow-up
    CreatedBy = db.Column(db.Integer, db.ForeignKey('users.UserID'), nullable=True)
    IsActive = db.Column(db.Boolean, default=True, nullable=False)
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    UpdatedAt = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    creator = db.relationship('User', foreign_keys=[CreatedBy])

    def __repr__(self) -> str:
        return f'<CannedResponse {self.Title}>'
