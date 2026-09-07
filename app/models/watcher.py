"""Many-to-many: users watching calls for updates."""
from app import db

call_watchers = db.Table(
    'call_watchers',
    db.Column('CallID', db.Integer, db.ForeignKey('call_log.CallID', ondelete='CASCADE'), primary_key=True),
    db.Column('UserID', db.Integer, db.ForeignKey('users.UserID', ondelete='CASCADE'), primary_key=True),
)
