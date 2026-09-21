"""Shared input checks for HTML forms and the JSON API."""
import re
from datetime import datetime

PHONE_RE = re.compile(r'^\+?[\d\s().-]{7,30}$')
MAX_CALLER = 120
MAX_PHONE = 30
MAX_DEPT = 50
MAX_REASON = 4000
MAX_NOTES = 8000
MAX_RESOLUTION = 8000


def digits_only(value: str) -> str:
    return ''.join(ch for ch in (value or '') if ch.isdigit())


def validate_phone(value) -> str | None:
    """Return a cleaned phone string, or None if invalid."""
    if value is None:
        return None
    raw = str(value).strip()
    if not raw or len(raw) > MAX_PHONE:
        return None
    if not PHONE_RE.match(raw):
        return None
    if len(digits_only(raw)) < 7:
        return None
    return raw


def clip_text(value, max_len: int, required: bool = False) -> str | None:
    if value is None:
        return None if not required else ''
    text = str(value).strip()
    if required and not text:
        return ''
    if len(text) > max_len:
        return text[:max_len]
    return text or None


def parse_iso_datetime(value):
    """Parse an ISO-8601 datetime. Returns (dt, error_message)."""
    if value is None or value == '':
        return None, None
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00')), None
    except ValueError:
        return None, 'Invalid datetime format'


def parse_optional_int(value, field_name: str):
    if value is None or value == '':
        return None, None
    try:
        return int(value), None
    except (TypeError, ValueError):
        return None, f'{field_name} must be an integer'
