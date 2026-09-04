"""
User model for authentication and role-based access control.
"""
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager


class User(UserMixin, db.Model):
    """
    User account model.

    Roles:
        - Admin: Full system access
        - Manager: Team oversight and reports
        - Agent: Call handling and logging
    """
    __tablename__ = 'users'

    UserID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    PasswordHash = db.Column(db.String(256), nullable=False)
    FullName = db.Column(db.String(120), nullable=False)
    Email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    Role = db.Column(
        db.Enum('Admin', 'Agent', 'Manager', name='user_roles'),
        nullable=False,
        default='Agent'
    )
    IsActive = db.Column(db.Boolean, default=True, nullable=False)
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    LastLogin = db.Column(db.DateTime, nullable=True)

    # Relationships
    assigned_calls = db.relationship(
        'CallLog',
        back_populates='assignee',
        foreign_keys='CallLog.AssignedTo',
        lazy='dynamic'
    )
    activities = db.relationship(
        'CallActivity',
        back_populates='user',
        lazy='dynamic'
    )

    def get_id(self):
        """Required by Flask-Login."""
        return str(self.UserID)

    def set_password(self, password: str) -> None:
        """Hash and store password using bcrypt (via werkzeug which uses it)."""
        self.PasswordHash = generate_password_hash(
            password, method='pbkdf2:sha256:600000'
        )

    def check_password(self, password: str) -> bool:
        """Verify password against stored hash."""
        return check_password_hash(self.PasswordHash, password)

    @property
    def is_admin(self) -> bool:
        return self.Role == 'Admin'

    @property
    def is_manager(self) -> bool:
        return self.Role in ('Admin', 'Manager')

    @property
    def is_agent(self) -> bool:
        return self.Role in ('Admin', 'Manager', 'Agent')

    def __repr__(self) -> str:
        return f'<User {self.Username} ({self.Role})>'


@login_manager.user_loader
def load_user(user_id: str):
    """Load user by ID for Flask-Login."""
    return User.query.get(int(user_id))
