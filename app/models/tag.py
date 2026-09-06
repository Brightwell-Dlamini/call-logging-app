"""
Tag model for flexible labelling of calls.
"""
from app import db

# Association table for many-to-many relationship between CallLog and Tag
call_tags = db.Table(
    'call_tags',
    db.Column('call_id', db.Integer, db.ForeignKey('call_log.CallID', ondelete='CASCADE'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.TagID', ondelete='CASCADE'), primary_key=True),
)


class Tag(db.Model):
    """Reusable label that can be applied to one or more calls."""
    __tablename__ = 'tags'

    TagID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Name = db.Column(db.String(40), unique=True, nullable=False, index=True)
    Colour = db.Column(db.String(7), nullable=False, default='#6366f1')  # hex colour
    Description = db.Column(db.String(120), nullable=True)
    IsActive = db.Column(db.Boolean, default=True, nullable=False)

    # Relationship back to calls
    calls = db.relationship(
        'CallLog',
        secondary=call_tags,
        back_populates='tags',
        lazy='dynamic',
    )

    def __repr__(self) -> str:
        return f'<Tag {self.Name}>'
