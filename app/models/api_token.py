"""
Long-lived API tokens for external integrations (session-independent).
"""
import secrets
from datetime import datetime
from app import db
from werkzeug.security import generate_password_hash, check_password_hash


class ApiToken(db.Model):
    """Personal access token for API clients."""
    __tablename__ = 'api_tokens'
    __table_args__ = (
        db.Index('ix_api_tokens_user', 'UserID'),
        db.Index('ix_api_tokens_prefix', 'TokenPrefix'),
    )

    TokenID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserID = db.Column(
        db.Integer,
        db.ForeignKey('users.UserID', ondelete='CASCADE'),
        nullable=False,
    )
    Name = db.Column(db.String(80), nullable=False)
    # Store only a hash; show the raw token once on creation.
    TokenHash = db.Column(db.String(256), nullable=False)
    TokenPrefix = db.Column(db.String(12), nullable=False)  # first chars for identification
    Scopes = db.Column(db.String(255), nullable=False, default='read')  # comma-separated: read,write,admin
    LastUsedAt = db.Column(db.DateTime, nullable=True)
    ExpiresAt = db.Column(db.DateTime, nullable=True)
    IsActive = db.Column(db.Boolean, default=True, nullable=False)
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship('User', backref=db.backref('api_tokens', lazy='dynamic'))

    @staticmethod
    def generate_token() -> str:
        """Return a secure random token string (clp_...)."""
        return 'clp_' + secrets.token_urlsafe(32)

    def set_token(self, raw_token: str) -> None:
        self.TokenHash = generate_password_hash(raw_token, method='pbkdf2:sha256:260000')
        self.TokenPrefix = raw_token[:12]

    def check_token(self, raw_token: str) -> bool:
        return check_password_hash(self.TokenHash, raw_token)

    def has_scope(self, scope: str) -> bool:
        scopes = {s.strip() for s in (self.Scopes or '').split(',') if s.strip()}
        return scope in scopes or 'admin' in scopes

    def to_dict(self, include_token: str = None) -> dict:
        data = {
            'id': self.TokenID,
            'name': self.Name,
            'prefix': self.TokenPrefix,
            'scopes': self.Scopes,
            'last_used_at': self.LastUsedAt.isoformat() if self.LastUsedAt else None,
            'expires_at': self.ExpiresAt.isoformat() if self.ExpiresAt else None,
            'is_active': self.IsActive,
            'created_at': self.CreatedAt.isoformat() if self.CreatedAt else None,
        }
        if include_token:
            data['token'] = include_token  # only on creation
        return data

    def __repr__(self) -> str:
        return f'<ApiToken {self.TokenID}: {self.Name}>'
