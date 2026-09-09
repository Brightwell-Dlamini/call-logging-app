"""Shared field validators for forms and API payloads."""
import re
from wtforms.validators import ValidationError

PHONE_RE = re.compile(r'^[+0-9][0-9\s().-]{6,29}$')
USERNAME_RE = re.compile(r'^[A-Za-z0-9._-]{3,80}$')
HEX_COLOUR_RE = re.compile(r'^#(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$')
DISPOSITION_CODE_RE = re.compile(r'^[A-Za-z0-9_-]{2,40}$')

MAX_REASON = 4000
MAX_NOTES = 8000
MAX_RESOLUTION = 4000


def is_valid_phone(value: str) -> bool:
    if not value:
        return False
    compact = value.strip()
    return bool(PHONE_RE.match(compact))


def is_valid_username(value: str) -> bool:
    if not value:
        return False
    return bool(USERNAME_RE.match(value.strip()))


def is_valid_hex_colour(value: str) -> bool:
    if not value:
        return False
    return bool(HEX_COLOUR_RE.match(value.strip()))


def is_valid_disposition_code(value: str) -> bool:
    if not value:
        return False
    return bool(DISPOSITION_CODE_RE.match(value.strip()))


def PhoneNumber():
    def _check(form, field):
        if field.data and not is_valid_phone(field.data):
            raise ValidationError(
                'Enter a phone number using digits, spaces, +, (), or dashes.'
            )
    return _check


def UsernameChars():
    def _check(form, field):
        if field.data and not is_valid_username(field.data):
            raise ValidationError(
                'Username may contain letters, numbers, dots, underscores, and hyphens only.'
            )
    return _check


def HexColour():
    def _check(form, field):
        if field.data and not is_valid_hex_colour(field.data):
            raise ValidationError('Colour must be a hex value such as #6366f1.')
    return _check


def DispositionCodeChars():
    def _check(form, field):
        if field.data and not is_valid_disposition_code(field.data):
            raise ValidationError(
                'Code may contain letters, numbers, underscores, and hyphens only.'
            )
    return _check
