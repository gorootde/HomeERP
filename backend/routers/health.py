"""Liveness/readiness probe for external monitoring (e.g. Uptime Kuma)."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import HealthRead

router = APIRouter()


@router.get("", response_model=HealthRead)
def health(request: Request, db: Session = Depends(get_db)):
    """Report process liveness plus database connectivity.

    Always returns HTTP 200; a monitor detects a degraded instance via the
    ``status`` / ``database`` fields (keyword match) rather than the status code.
    """
    try:
        db.execute(text("SELECT 1"))
        database = "ok"
    except Exception:
        database = "error"
    return {
        "status": "ok" if database == "ok" else "degraded",
        "version": request.app.version,
        "database": database,
    }
