"""Shared CRUD-router helpers: 404 lookups, duplicate checks, tag add/remove."""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from .models import Tag


def get_or_404(db: Session, model, obj_id, detail: str = "Not found"):
    """``db.get(model, obj_id)`` or raise a 404 with ``detail``."""
    obj = db.get(model, obj_id)
    if not obj:
        raise HTTPException(status_code=404, detail=detail)
    return obj


def raise_if_exists(db: Session, model, detail: str, **filters) -> None:
    """Raise 409 if a row matching ``filters`` already exists."""
    if db.query(model).filter_by(**filters).first():
        raise HTTPException(status_code=409, detail=detail)


def add_tag(db: Session, owner, name: str) -> Tag:
    """Attach a tag (find-or-create) to ``owner.tags``. Idempotent."""
    tag = db.query(Tag).filter(Tag.name == name).first()
    if not tag:
        tag = Tag(name=name)
        db.add(tag)
        db.flush()
    if tag not in owner.tags:
        owner.tags.append(tag)
    db.commit()
    db.refresh(tag)
    return tag


def remove_tag(db: Session, owner, name: str) -> None:
    """Detach a tag by name from ``owner.tags``, if present."""
    tag = db.query(Tag).filter(Tag.name == name).first()
    if tag and tag in owner.tags:
        owner.tags.remove(tag)
        db.commit()
