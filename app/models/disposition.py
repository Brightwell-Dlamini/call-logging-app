"""Disposition codes for structured call outcomes."""
from datetime import datetime
from app import db


class DispositionCode(db.Model):
    """Admin-managed outcome labels applied when resolving a call."""
    __tablename__ = 'disposition_codes'

    DispositionID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Code = db.Column(db.String(40), unique=True, nullable=False, index=True)
    Label = db.Column(db.String(120), nullable=False)
    Description = db.Column(db.String(255), nullable=True)
    IsActive = db.Column(db.Boolean, default=True, nullable=False)
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    calls = db.relationship('CallLog', back_populates='disposition', lazy='dynamic')

    def __repr__(self) -> str:
        return f'<DispositionCode {self.Code}>'
