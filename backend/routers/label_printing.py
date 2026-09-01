from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..label_printing import (
    DEFAULT_BROTHER_MODEL,
    DEFAULT_LENGTH_MM,
    DEFAULT_LENGTH_MODE,
    DEFAULT_ORIENTATION,
    DEFAULT_PROTOCOL,
    DEFAULT_WIDTH_MM,
    LENGTH_MODE_CHOICES,
    ORIENTATION_CHOICES,
    PROTOCOL_CHOICES,
    WIDTH_CHOICES_MM,
    clear_print_queue,
    print_label,
    render_label_png,
)
from ..models import Setting

router = APIRouter()

# Sample data used for the settings preview and the test print.
_SAMPLE = dict(
    product_name="Beispielprodukt",
    vendor="Beispielhersteller GmbH",
    stock_id_code="DEMO-0001",
    quantity=2,
    unit="Stk.",
)


def _get_setting(db: Session, key: str, default: str = "") -> str:
    s = db.get(Setting, key)
    return s.value if s else default


def _float_setting(db: Session, key: str, default: float) -> float:
    try:
        return float(_get_setting(db, key, str(default)) or default)
    except (TypeError, ValueError):
        return default


def _sample_png(width_mm: float, length_mm: float, orientation: str, length_mode: str) -> bytes:
    best_before = (date.today() + timedelta(days=30)).isoformat()
    return render_label_png(
        best_before=best_before, width_mm=width_mm, length_mm=length_mm,
        orientation=orientation, length_mode=length_mode, **_SAMPLE,
    )


@router.get("/options")
def label_options():
    """Selectable tape widths, orientations, length modes, protocols and defaults."""
    return {
        "width_choices_mm": WIDTH_CHOICES_MM,
        "orientation_choices": ORIENTATION_CHOICES,
        "length_mode_choices": LENGTH_MODE_CHOICES,
        "protocol_choices": PROTOCOL_CHOICES,
        "default_width_mm": DEFAULT_WIDTH_MM,
        "default_length_mm": DEFAULT_LENGTH_MM,
        "default_orientation": DEFAULT_ORIENTATION,
        "default_length_mode": DEFAULT_LENGTH_MODE,
        "default_protocol": DEFAULT_PROTOCOL,
        "default_model": DEFAULT_BROTHER_MODEL,
    }


@router.get("/preview")
def label_preview(
    db: Session = Depends(get_db),
    width_mm: Optional[float] = Query(None),
    length_mm: Optional[float] = Query(None),
    orientation: Optional[str] = Query(None),
    length_mode: Optional[str] = Query(None),
):
    """Return the label preview PNG (rendered from sample data).

    Query params override the stored settings for a live preview.
    """
    w = width_mm if width_mm is not None else _float_setting(db, "label_width_mm", DEFAULT_WIDTH_MM)
    length = length_mm if length_mm is not None else _float_setting(db, "label_length_mm", DEFAULT_LENGTH_MM)
    orient = orientation or _get_setting(db, "label_orientation", DEFAULT_ORIENTATION)
    mode = length_mode or _get_setting(db, "label_length_mode", DEFAULT_LENGTH_MODE)
    return Response(content=_sample_png(w, length, orient, mode), media_type="image/png")


@router.post("/test-print")
def label_test_print(db: Session = Depends(get_db)):
    """Render the sample label and send it to the configured printer."""
    printer_ip = _get_setting(db, "label_printer_ip")
    if not printer_ip:
        raise HTTPException(status_code=400, detail="No printer IP configured")
    w = _float_setting(db, "label_width_mm", DEFAULT_WIDTH_MM)
    length = _float_setting(db, "label_length_mm", DEFAULT_LENGTH_MM)
    orient = _get_setting(db, "label_orientation", DEFAULT_ORIENTATION)
    mode = _get_setting(db, "label_length_mode", DEFAULT_LENGTH_MODE)
    protocol = _get_setting(db, "label_printer_protocol", DEFAULT_PROTOCOL)
    model = _get_setting(db, "label_printer_model", DEFAULT_BROTHER_MODEL)
    try:
        print_label(_sample_png(w, length, orient, mode), printer_ip,
                    protocol=protocol, width_mm=w, model=model)
    except Exception as exc:  # noqa: BLE001 – surface the printer error to the user
        raise HTTPException(status_code=502, detail=f"Print failed: {exc}") from exc
    return {"status": "ok"}


@router.post("/clear-queue")
def label_clear_queue(db: Session = Depends(get_db)):
    """Tell the printer to drop all pending IPP jobs (unstick a full spool)."""
    printer_ip = _get_setting(db, "label_printer_ip")
    if not printer_ip:
        raise HTTPException(status_code=400, detail="No printer IP configured")
    try:
        op = clear_print_queue(printer_ip)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Clear queue failed: {exc}") from exc
    return {"status": "ok", "operation": op}
