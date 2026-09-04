"""Shared helpers for reading key/value rows from the ``settings`` table.

Used by any router that reads app settings (see ``routers/app_settings.py``
for the well-known keys and their defaults).
"""
from sqlalchemy.orm import Session

from .models import Setting


def get_setting(db: Session, key: str, default: str = "") -> str:
    s = db.get(Setting, key)
    return s.value if s else default


def float_setting(db: Session, key: str, default: float) -> float:
    try:
        return float(get_setting(db, key, str(default)) or default)
    except (TypeError, ValueError):
        return default
