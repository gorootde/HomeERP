from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..helpers import add_tag, get_or_404, remove_tag
from ..label_printing import print_label, render_label_png
from ..models import (
    Product,
    ProductCategory,
    StockEntry,
    StockEntryId,
    UnitConversion,
    Vault,
)
from ..schemas import (
    CategoryStockSummaryItem,
    StockEntryCreate,
    StockEntryIdCreate,
    StockEntryIdRead,
    StockEntryRead,
    StockEntryUpdate,
    StockSummaryItem,
    StockSummaryVaultQty,
    TagCreate,
    TagRead,
)
from ..services.stock_id import apply_generated_stock_id, apply_webhook_stock_id
from ..services.stock_movements import entry_snapshot, record_movement
from ..settings_helpers import float_setting, get_setting
from .app_settings import (
    LABEL_AUTO_PRINT,
    LABEL_LENGTH_MM,
    LABEL_LENGTH_MODE,
    LABEL_ORIENTATION,
    LABEL_PRINTER_IP,
    LABEL_PRINTER_MODEL,
    LABEL_PRINTER_PROTOCOL,
    LABEL_WIDTH_MM,
)

router = APIRouter()


@router.get("/summary", response_model=list[StockSummaryItem])
def get_stock_summary(db: Session = Depends(get_db)):
    rows = (
        db.query(
            StockEntry.product_id,
            StockEntry.vault_id,
            func.sum(StockEntry.quantity).label("total_qty"),
        )
        .group_by(StockEntry.product_id, StockEntry.vault_id)
        .all()
    )
    if not rows:
        return []

    product_ids = list({r.product_id for r in rows})
    vault_ids = list({r.vault_id for r in rows})

    products = {p.id: p for p in db.query(Product).filter(Product.id.in_(product_ids)).all()}
    vaults = {v.id: v for v in db.query(Vault).filter(Vault.id.in_(vault_ids)).all()}

    by_product: dict[int, dict] = {}
    for row in rows:
        pid = row.product_id
        if pid not in by_product:
            p = products[pid]
            by_product[pid] = {
                "product_id": pid,
                "vendor": p.vendor,
                "product_name": p.name,
                "unit": p.unit,
                "total_quantity": 0.0,
                "by_vault": [],
            }
        by_product[pid]["total_quantity"] += row.total_qty
        v = vaults[row.vault_id]
        by_product[pid]["by_vault"].append(
            StockSummaryVaultQty(
                vault_id=row.vault_id,
                vault_description=v.description,
                total_quantity=row.total_qty,
            )
        )

    return [StockSummaryItem(**d) for d in by_product.values()]


@router.get("/category-summary", response_model=list[CategoryStockSummaryItem])
def get_category_stock_summary(db: Session = Depends(get_db)):
    # Total stock per product, in the product's own base unit.
    product_stock = {
        row.product_id: float(row.total_qty)
        for row in db.query(
            StockEntry.product_id,
            func.sum(StockEntry.quantity).label("total_qty"),
        ).group_by(StockEntry.product_id).all()
    }

    categories = {c.id: c for c in db.query(ProductCategory).all()}

    # Direct unit conversions, both directions (the API stores the reverse too).
    conversions = {
        (c.from_unit_id, c.to_unit_id): c.factor
        for c in db.query(UnitConversion).all()
    }

    def _to_category_unit(qty: float, from_unit_id, target_unit_id):
        """Return (converted_qty, ok). ok is False when no conversion path exists."""
        if target_unit_id is None or from_unit_id == target_unit_id:
            return qty, True
        if from_unit_id is None:
            return 0.0, False
        factor = conversions.get((from_unit_id, target_unit_id))
        if factor is None:
            return 0.0, False
        return qty * factor, True

    # Aggregate by category, converting each product into the category's
    # min_stock_unit first so the dashboard compares like with like.
    cat_totals: dict = {}
    for p in db.query(Product).all():
        key = p.category_id
        cat = categories.get(key)
        target_unit_id = cat.min_stock_unit_id if cat else None
        qty = product_stock.get(p.id, 0.0)
        converted, ok = _to_category_unit(qty, p.unit_id, target_unit_id)

        stats = cat_totals.setdefault(
            key, {"total_quantity": 0.0, "product_count": 0, "unconverted_product_count": 0}
        )
        stats["product_count"] += 1
        if ok:
            stats["total_quantity"] += converted
        elif qty > 0:
            stats["unconverted_product_count"] += 1

    result = []
    for cat_id, stats in cat_totals.items():
        cat = categories.get(cat_id)
        if cat:
            result.append(CategoryStockSummaryItem(
                category_id=cat_id,
                category_name=cat.name,
                min_stock_quantity=cat.min_stock_quantity,
                min_stock_unit=cat.min_stock_unit,
                **stats,
            ))
        else:
            result.append(CategoryStockSummaryItem(
                category_id=None,
                category_name="Ohne Kategorie",
                min_stock_quantity=None,
                min_stock_unit=None,
                **stats,
            ))

    # Categories with no products at all
    for cat_id, cat in categories.items():
        if cat_id not in cat_totals:
            result.append(CategoryStockSummaryItem(
                category_id=cat_id,
                category_name=cat.name,
                min_stock_quantity=cat.min_stock_quantity,
                min_stock_unit=cat.min_stock_unit,
                total_quantity=0.0,
                product_count=0,
                unconverted_product_count=0,
            ))

    return sorted(result, key=lambda x: (x.category_id is None, x.category_name))


@router.get("/entries/by-stockid/{code}", response_model=StockEntryRead)
def get_entry_by_stock_id(code: str, db: Session = Depends(get_db)):
    sid = db.query(StockEntryId).filter(StockEntryId.code == code).first()
    if not sid:
        raise HTTPException(status_code=404, detail="Stock ID not found")
    return sid.stock_entry


@router.get("/entries", response_model=list[StockEntryRead])
def list_stock_entries(
    vault_id: Optional[int] = Query(None),
    product_id: Optional[int] = Query(None),
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    q = db.query(StockEntry)
    if vault_id is not None:
        q = q.filter(StockEntry.vault_id == vault_id)
    if product_id is not None:
        q = q.filter(StockEntry.product_id == product_id)
    return q.offset(skip).limit(limit).all()


# ── Label printing ──────────────────────────────────────────────────────────

def _render_and_print(product_name: str, vendor: str, best_before: Optional[str],
                      code: Optional[str], printer_ip: str, width_mm: float,
                      length_mm: float, orientation: str, length_mode: str,
                      quantity: Optional[float], unit: str,
                      protocol: str, model: str, raise_on_error: bool = False) -> None:
    try:
        png = render_label_png(
            product_name=product_name,
            vendor=vendor,
            best_before=best_before,
            stock_id_code=code,  # may be None → label without QR
            width_mm=width_mm,
            length_mm=length_mm,
            orientation=orientation,
            length_mode=length_mode,
            quantity=quantity,
            unit=unit,
        )
        print_label(png, printer_ip, protocol=protocol, width_mm=width_mm, model=model)
    except Exception:
        if raise_on_error:  # manual reprint: surface the failure to the caller
            raise
        # background auto-print: a printer failure must not affect stock-entry creation


def _label_kwargs_for_entry(entry: StockEntry, db: Session) -> dict:
    """Build the ``_render_and_print`` kwargs for one stock entry from settings."""
    unit = ""
    product_unit = getattr(entry.product, "unit", None)
    if product_unit is not None:
        unit = product_unit.abbreviation or product_unit.name or ""
    return dict(
        product_name=entry.product.name,
        vendor=entry.product.vendor,
        best_before=entry.best_before_date.isoformat() if entry.best_before_date else None,
        code=entry.stock_ids[0].code if entry.stock_ids else None,
        printer_ip=get_setting(db, LABEL_PRINTER_IP),
        width_mm=float_setting(db, LABEL_WIDTH_MM, 62),
        length_mm=float_setting(db, LABEL_LENGTH_MM, 90),
        orientation=get_setting(db, LABEL_ORIENTATION, "landscape"),
        length_mode=get_setting(db, LABEL_LENGTH_MODE, "auto"),
        quantity=entry.quantity,
        unit=unit,
        protocol=get_setting(db, LABEL_PRINTER_PROTOCOL, "ipp"),
        model=get_setting(db, LABEL_PRINTER_MODEL, "QL-710W"),
    )


def _maybe_print_label(entry: StockEntry, db: Session, requested: Optional[bool],
                       background_tasks: BackgroundTasks) -> None:
    """Queue a label print for a freshly created stock entry.

    Gated by the ``label_auto_print`` setting; ``requested is False`` is a
    per-entry opt-out. The actual print runs in a background task so a slow or
    unreachable printer never delays the response.
    """
    if requested is False:
        return
    if get_setting(db, LABEL_AUTO_PRINT) != "1":
        return
    kwargs = _label_kwargs_for_entry(entry, db)
    if not kwargs["printer_ip"]:
        return
    background_tasks.add_task(_render_and_print, **kwargs)


@router.post("/entries", response_model=StockEntryRead, status_code=201)
def create_stock_entry(data: StockEntryCreate, background_tasks: BackgroundTasks,
                       db: Session = Depends(get_db)):
    get_or_404(db, Product, data.product_id, "Product not found")
    get_or_404(db, Vault, data.vault_id, "Vault not found")
    entry = StockEntry(**data.model_dump(exclude={"stock_id", "print_label"}))
    db.add(entry)
    db.commit()
    db.refresh(entry)
    if data.stock_id:
        db.add(StockEntryId(code=data.stock_id, stock_entry_id=entry.id))
        db.commit()
        db.refresh(entry)
    else:
        apply_generated_stock_id(entry, db)
        apply_webhook_stock_id(entry, db)
    _maybe_print_label(entry, db, data.print_label, background_tasks)
    record_movement(
        db, stock_entry_id=entry.id, product_id=entry.product_id, vault_id=entry.vault_id,
        before=0.0, after=entry.quantity, reason="create", note=entry.comment,
    )
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/entries/{entry_id}", response_model=StockEntryRead)
def get_stock_entry(entry_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, StockEntry, entry_id, "Stock entry not found")


@router.post("/entries/{entry_id}/print-label")
def print_stock_entry_label(entry_id: int, db: Session = Depends(get_db)):
    """Reprint the label for an existing stock entry on the configured printer."""
    entry = get_or_404(db, StockEntry, entry_id, "Stock entry not found")
    kwargs = _label_kwargs_for_entry(entry, db)
    if not kwargs["printer_ip"]:
        raise HTTPException(status_code=400, detail="No printer IP configured")
    try:
        _render_and_print(**kwargs, raise_on_error=True)
    except Exception as exc:  # noqa: BLE001 – surface the printer error to the user
        raise HTTPException(status_code=502, detail=f"Print failed: {exc}") from exc
    return {"status": "ok"}


@router.put("/entries/{entry_id}", response_model=StockEntryRead)
def update_stock_entry(entry_id: int, data: StockEntryUpdate, db: Session = Depends(get_db)):
    entry = get_or_404(db, StockEntry, entry_id, "Stock entry not found")

    changes = data.model_dump(exclude_unset=True)
    reason = changes.pop("reason", None) or "edit"
    note = changes.pop("note", None)

    old_qty = entry.quantity
    for field, value in changes.items():
        setattr(entry, field, value)
    db.commit()
    db.refresh(entry)

    if "quantity" in changes and entry.quantity != old_qty:
        record_movement(
            db, stock_entry_id=entry.id, product_id=entry.product_id, vault_id=entry.vault_id,
            before=old_qty, after=entry.quantity, reason=reason, note=note,
        )
        db.commit()
        db.refresh(entry)
    return entry


@router.delete("/entries/{entry_id}", status_code=204)
def delete_stock_entry(
    entry_id: int,
    reason: str = Query("delete", description="Audit-log reason: delete | consume | adjust"),
    db: Session = Depends(get_db),
):
    entry = get_or_404(db, StockEntry, entry_id, "Stock entry not found")
    record_movement(
        db, stock_entry_id=None, product_id=entry.product_id, vault_id=entry.vault_id,
        before=entry.quantity, after=0.0, reason=reason, note=entry.comment,
        snapshot=entry_snapshot(entry),
    )
    db.delete(entry)
    db.commit()


@router.post("/entries/{entry_id}/tags", response_model=TagRead, status_code=201)
def add_tag_to_stock_entry(entry_id: int, data: TagCreate, db: Session = Depends(get_db)):
    entry = get_or_404(db, StockEntry, entry_id, "Stock entry not found")
    return add_tag(db, entry, data.name)


@router.delete("/entries/{entry_id}/tags/{tag_name}", status_code=204)
def remove_tag_from_stock_entry(entry_id: int, tag_name: str, db: Session = Depends(get_db)):
    entry = get_or_404(db, StockEntry, entry_id, "Stock entry not found")
    remove_tag(db, entry, tag_name)


@router.post("/entries/{entry_id}/stockids", response_model=StockEntryIdRead, status_code=201)
def add_stock_id(entry_id: int, data: StockEntryIdCreate, db: Session = Depends(get_db)):
    get_or_404(db, StockEntry, entry_id, "Stock entry not found")
    sid = StockEntryId(code=data.code, stock_entry_id=entry_id)
    db.add(sid)
    db.commit()
    db.refresh(sid)
    return sid


@router.delete("/entries/{entry_id}/stockids/{sid}", status_code=204)
def remove_stock_id(entry_id: int, sid: int, db: Session = Depends(get_db)):
    stock_id = db.query(StockEntryId).filter(
        StockEntryId.id == sid,
        StockEntryId.stock_entry_id == entry_id,
    ).first()
    if not stock_id:
        raise HTTPException(status_code=404, detail="Stock ID not found")
    db.delete(stock_id)
    db.commit()
