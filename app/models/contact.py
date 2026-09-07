"""Customer contact profiles aggregated by phone number."""
from datetime import datetime
from app import db


class Contact(db.Model):
    """Lightweight CRM-style contact linked to calls by phone."""
    __tablename__ = 'contacts'
    __table_args__ = (
        db.Index('ix_contacts_phone', 'PhoneNumber'),
    )

    ContactID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    PhoneNumber = db.Column(db.String(30), unique=True, nullable=False)
    DisplayName = db.Column(db.String(120), nullable=True)
    Email = db.Column(db.String(120), nullable=True)
    Company = db.Column(db.String(120), nullable=True)
    Notes = db.Column(db.Text, nullable=True)
    IsVIP = db.Column(db.Boolean, default=False, nullable=False)
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    UpdatedAt = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    def __repr__(self) -> str:
        return f'<Contact {self.PhoneNumber}>'
