"""
Department model for dropdown options and reporting.
"""
from app import db


class Department(db.Model):
    """Organizational department."""
    __tablename__ = 'departments'

    DepartmentID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    DepartmentName = db.Column(db.String(50), unique=True, nullable=False)
    IsActive = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f'<Department {self.DepartmentName}>'
