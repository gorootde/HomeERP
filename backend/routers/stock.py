from datetime import date, datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
import httpx

from ..database import get_db
from ..label_printing import print_label, render_label_png
from ..models import (
    StockEntry, StockMovement, Product, Vault, Tag, ProductCategory,
    StockEntryId, Setting,
)
from ..schemas import (
    StockEntryCreate, StockEntryRead, StockEntryUpdate,
    StockSummaryItem, StockSummaryVaultQty,
    CategoryStockSummaryItem,
    StockEntryIdCreate, StockEntryIdRead,
    StockMovementRead, ConsumptionForecastItem,
    TagCreate, TagRead,
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
                "size": p.size,
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
    # Total stock per product
    product_stock = {
        row.product_id: float(row.total_qty)
        for row in db.query(
            StockEntry.product_id,
            func.sum(StockEntry.quantity).label("total_qty"),
        ).group_by(StockEntry.product_id).all()
    }

    # Aggregate by category
    cat_totals: dict = {}
    for p in db.query(Product).all():
        key = p.category_id
        qty = product_stock.get(p.id, 0.0)
        if key not in cat_totals:
            cat_totals[key] = {"total_quantity": 0.0, "product_count": 0}
        cat_totals[key]["total_quantity"] += qty
        cat_totals[key]["product_count"] += 1

    categories = {c.id: c for c in db.query(ProductCategory).all()}

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


def _get_setting(db: Session, key: str, default: str = "") -> str:
    s = db.get(Setting, key)
    return s.value if s else default


# ── Stock-movement audit log ─────────────────────────────────────────────────

_MOVEMENT_REASONS = {"create", "edit", "consume", "adjust", "delete", "undo", "import"}


def _record_movement(db: Session, *, stock_entry_id: Optional[int], product_id: Optional[int],
                     vault_id: Optional[int], before: float, after: float, reason: str,
                     note: Optional[str] = None, snapshot: Optional[dict] = None) -> StockMovement:
    """Append one audit row. Caller is responsible for committing."""
    before = float(before or 0.0)
    after = float(after or 0.0)
    mv = StockMovement(
        stock_entry_id=stock_entry_id,
        product_id=product_id,
        vault_id=vault_id,
        delta=after - before,
        quantity_before=before,
        quantity_after=after,
        reason=reason if reason in _MOVEMENT_REASONS else "edit",
        note=(note or None),
        entry_snapshot=snapshot,
    )
    db.add(mv)
    return mv


def _entry_snapshot(entry: StockEntry) -> dict:
    """Enough state to recreate an entry that a mis-scan removed."""
    return {
        "product_id": entry.product_id,
        "vault_id": entry.vault_id,
        "quantity": entry.quantity,
        "comment": entry.comment,
        "best_before_date": entry.best_before_date.isoformat() if entry.best_before_date else None,
        "stock_ids": [s.code for s in entry.stock_ids],
    }


def _movement_can_undo(mv: StockMovement) -> bool:
    if mv.undone or mv.reason == "undo":
        return False
    # Reversible if the entry still exists, or we kept a snapshot to rebuild it.
    return mv.stock_entry_id is not None or bool(mv.entry_snapshot)


def _serialize_movements(db: Session, rows: list[StockMovement]) -> list[StockMovementRead]:
    product_ids = {r.product_id for r in rows if r.product_id is not None}
    vault_ids = {r.vault_id for r in rows if r.vault_id is not None}
    entry_ids = {r.stock_entry_id for r in rows if r.stock_entry_id is not None}

    products = {p.id: p for p in db.query(Product).filter(Product.id.in_(product_ids)).all()} if product_ids else {}
    vaults = {v.id: v for v in db.query(Vault).filter(Vault.id.in_(vault_ids)).all()} if vault_ids else {}
    live_entries = (
        {e for (e,) in db.query(StockEntry.id).filter(StockEntry.id.in_(entry_ids)).all()}
        if entry_ids else set()
    )

    out: list[StockMovementRead] = []
    for r in rows:
        p = products.get(r.product_id)
        v = vaults.get(r.vault_id)
        can_undo = _movement_can_undo(r) and (
            r.stock_entry_id is None or r.stock_entry_id in live_entries
        )
        out.append(StockMovementRead(
            id=r.id,
            stock_entry_id=r.stock_entry_id,
            product_id=r.product_id,
            vault_id=r.vault_id,
            product_name=p.name if p else None,
            vendor=p.vendor if p else None,
            unit=p.unit if p else None,
            vault_description=v.description if v else None,
            delta=r.delta,
            quantity_before=r.quantity_before,
            quantity_after=r.quantity_after,
            reason=r.reason,
            note=r.note,
            undone=bool(r.undone),
            can_undo=can_undo,
            created_at=r.created_at,
        ))
    return out


def _apply_generated_stock_id(entry: StockEntry, db: Session) -> None:
    """If mode is 'generated', build an incremental ID and attach it to the entry."""
    if _get_setting(db, "stock_id_mode") != "generated":
        return
    prefix     = _get_setting(db, "stock_id_prefix", "")
    counter    = int(_get_setting(db, "stock_id_counter", "0") or "0")
    pad_length = int(_get_setting(db, "stock_id_pad_length", "0") or "0")

    next_counter = counter + 1
    num_str = str(next_counter).zfill(pad_length) if pad_length > 0 else str(next_counter)
    code = f"{prefix}{num_str}"

    # Persist incremented counter
    setting = db.get(Setting, "stock_id_counter")
    if setting:
        setting.value = str(next_counter)
    else:
        db.add(Setting(key="stock_id_counter", value=str(next_counter)))

    db.add(StockEntryId(code=code, stock_entry_id=entry.id))
    db.commit()
    db.refresh(entry)


def _apply_webhook_stock_id(entry: StockEntry, db: Session) -> None:
    """If mode is 'extern', call the configured webhook and attach the returned ID."""
    if _get_setting(db, "stock_id_mode") != "extern":
        return
    url_template = _get_setting(db, "stock_id_webhook_url")
    if not url_template:
        return

    bbd = entry.best_before_date.isoformat() if entry.best_before_date else ""
    url = (
        url_template
        .replace("{quantity}",         str(entry.quantity))
        .replace("{product_id}",       str(entry.product_id))
        .replace("{vault_id}",         str(entry.vault_id))
        .replace("{best_before_date}", bbd)
        .replace("{comment}",          entry.comment or "")
    )
    try:
        resp = httpx.get(url, timeout=10.0)
        resp.raise_for_status()
        code = resp.text.strip()
        if code:
            db.add(StockEntryId(code=code, stock_entry_id=entry.id))
            db.commit()
            db.refresh(entry)
    except Exception:
        pass  # Webhook failure must not prevent entry creation


def _render_and_print(product_name: str, vendor: str, best_before: Optional[str],
                      code: Optional[str], printer_ip: str, width_mm: float,
                      length_mm: float, orientation: str, length_mode: str,
                      quantity: Optional[float], unit: str,
                      protocol: str, model: str) -> None:
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
        pass  # Printer failure must not affect stock-entry creation


def _float_setting(db: Session, key: str, default: float) -> float:
    try:
        return float(_get_setting(db, key, str(default)) or default)
    except (TypeError, ValueError):
        return default


def _maybe_print_label(entry: StockEntry, db: Session, requested: Optional[bool],
                       background_tasks: BackgroundTasks) -> None:
    """Queue a label print for a freshly created stock entry.

    Gated by the ``label_auto_print`` setting; ``requested is False`` is a
    per-entry opt-out. The actual print runs in a background task so a slow or
    unreachable printer never delays the response.
    """
    if requested is False:
        return
    if _get_setting(db, "label_auto_print") != "1":
        return
    printer_ip = _get_setting(db, "label_printer_ip")
    if not printer_ip:
        return
    unit = ""
    product_unit = getattr(entry.product, "unit", None)
    if product_unit is not None:
        unit = product_unit.abbreviation or product_unit.name or ""
    background_tasks.add_task(
        _render_and_print,
        entry.product.name,
        entry.product.vendor,
        entry.best_before_date.isoformat() if entry.best_before_date else None,
        entry.stock_ids[0].code if entry.stock_ids else None,
        printer_ip,
        _float_setting(db, "label_width_mm", 62),
        _float_setting(db, "label_length_mm", 90),
        _get_setting(db, "label_orientation", "landscape"),
        _get_setting(db, "label_length_mode", "auto"),
        entry.quantity,
        unit,
        _get_setting(db, "label_printer_protocol", "ipp"),
        _get_setting(db, "label_printer_model", "QL-710W"),
    )


@router.post("/entries", response_model=StockEntryRead, status_code=201)
def create_stock_entry(data: StockEntryCreate, background_tasks: BackgroundTasks,
                       db: Session = Depends(get_db)):
    if not db.get(Product, data.product_id):
        raise HTTPException(status_code=404, detail="Product not found")
    if not db.get(Vault, data.vault_id):
        raise HTTPException(status_code=404, detail="Vault not found")
    entry = StockEntry(**data.model_dump(exclude={"stock_id", "print_label"}))
    db.add(entry)
    db.commit()
    db.refresh(entry)
    if data.stock_id:
        db.add(StockEntryId(code=data.stock_id, stock_entry_id=entry.id))
        db.commit()
        db.refresh(entry)
    else:
        _apply_generated_stock_id(entry, db)
        _apply_webhook_stock_id(entry, db)
    _maybe_print_label(entry, db, data.print_label, background_tasks)
    _record_movement(
        db, stock_entry_id=entry.id, product_id=entry.product_id, vault_id=entry.vault_id,
        before=0.0, after=entry.quantity, reason="create", note=entry.comment,
    )
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/entries/{entry_id}", response_model=StockEntryRead)
def get_stock_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.get(StockEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Stock entry not found")
    return entry


@router.put("/entries/{entry_id}", response_model=StockEntryRead)
def update_stock_entry(entry_id: int, data: StockEntryUpdate, db: Session = Depends(get_db)):
    entry = db.get(StockEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Stock entry not found")

    changes = data.model_dump(exclude_unset=True)
    reason = changes.pop("reason", None) or "edit"
    note = changes.pop("note", None)

    old_qty = entry.quantity
    for field, value in changes.items():
        setattr(entry, field, value)
    db.commit()
    db.refresh(entry)

    if "quantity" in changes and entry.quantity != old_qty:
        _record_movement(
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
    entry = db.get(StockEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Stock entry not found")
    _record_movement(
        db, stock_entry_id=None, product_id=entry.product_id, vault_id=entry.vault_id,
        before=entry.quantity, after=0.0, reason=reason, note=entry.comment,
        snapshot=_entry_snapshot(entry),
    )
    db.delete(entry)
    db.commit()


@router.post("/entries/{entry_id}/tags", response_model=TagRead, status_code=201)
def add_tag_to_stock_entry(entry_id: int, data: TagCreate, db: Session = Depends(get_db)):
    entry = db.get(StockEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Stock entry not found")
    tag = db.query(Tag).filter(Tag.name == data.name).first()
    if not tag:
        tag = Tag(name=data.name)
        db.add(tag)
        db.flush()
    if tag not in entry.tags:
        entry.tags.append(tag)
    db.commit()
    db.refresh(tag)
    return tag


@router.delete("/entries/{entry_id}/tags/{tag_name}", status_code=204)
def remove_tag_from_stock_entry(entry_id: int, tag_name: str, db: Session = Depends(get_db)):
    entry = db.get(StockEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Stock entry not found")
    tag = db.query(Tag).filter(Tag.name == tag_name).first()
    if tag and tag in entry.tags:
        entry.tags.remove(tag)
        db.commit()


@router.post("/entries/{entry_id}/stockids", response_model=StockEntryIdRead, status_code=201)
def add_stock_id(entry_id: int, data: StockEntryIdCreate, db: Session = Depends(get_db)):
    entry = db.get(StockEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Stock entry not found")
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


# ── Movement history / audit log ───────────────────────────────────────────────

@router.get("/movements/forecast", response_model=list[ConsumptionForecastItem])
def consumption_forecast(
    days: int = Query(90, ge=1, le=3650, description="Look-back window for the consumption rate"),
    product_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Per-product consumption rate and projected days of stock remaining.

    Rate = sum of outflows (negative deltas, undo excluded) over the window,
    divided by the window length. ``days_remaining = current_stock / rate``.
    Only products with measured consumption are returned, soonest-empty first.
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)

    stock_q = (
        db.query(StockEntry.product_id, func.sum(StockEntry.quantity).label("qty"))
        .group_by(StockEntry.product_id)
    )
    if product_id is not None:
        stock_q = stock_q.filter(StockEntry.product_id == product_id)
    current = {r.product_id: float(r.qty or 0.0) for r in stock_q.all()}

    cons_q = (
        db.query(StockMovement.product_id, func.sum(-StockMovement.delta).label("consumed"))
        .filter(
            StockMovement.delta < 0,
            StockMovement.reason != "undo",
            StockMovement.undone == 0,
            StockMovement.created_at >= since,
            StockMovement.product_id.isnot(None),
        )
        .group_by(StockMovement.product_id)
    )
    if product_id is not None:
        cons_q = cons_q.filter(StockMovement.product_id == product_id)
    consumed = {r.product_id: float(r.consumed or 0.0) for r in cons_q.all()}

    product_ids = set(current) | set(consumed)
    products = (
        {p.id: p for p in db.query(Product).filter(Product.id.in_(product_ids)).all()}
        if product_ids else {}
    )
    today = date.today()

    out: list[ConsumptionForecastItem] = []
    for pid in product_ids:
        p = products.get(pid)
        c = consumed.get(pid, 0.0)
        if p is None or c <= 0:
            continue
        stock = current.get(pid, 0.0)
        avg = c / days
        remaining = stock / avg if avg > 0 else None
        depletion = None
        if remaining is not None and remaining < 100_000:
            depletion = today + timedelta(days=int(round(remaining)))
        out.append(ConsumptionForecastItem(
            product_id=pid,
            product_name=p.name,
            vendor=p.vendor,
            unit=p.unit,
            current_stock=stock,
            window_days=days,
            consumed_in_window=c,
            avg_daily_consumption=avg,
            days_remaining=remaining,
            depletion_date=depletion,
        ))
    out.sort(key=lambda x: (x.days_remaining is None, x.days_remaining or 0.0))
    return out


@router.get("/movements", response_model=list[StockMovementRead])
def list_stock_movements(
    product_id: Optional[int] = Query(None),
    vault_id: Optional[int] = Query(None),
    stock_entry_id: Optional[int] = Query(None),
    reason: Optional[str] = Query(None),
    include_undone: bool = Query(True),
    skip: int = 0,
    limit: int = Query(200, ge=1, le=2000),
    db: Session = Depends(get_db),
):
    q = db.query(StockMovement)
    if product_id is not None:
        q = q.filter(StockMovement.product_id == product_id)
    if vault_id is not None:
        q = q.filter(StockMovement.vault_id == vault_id)
    if stock_entry_id is not None:
        q = q.filter(StockMovement.stock_entry_id == stock_entry_id)
    if reason:
        q = q.filter(StockMovement.reason == reason)
    if not include_undone:
        q = q.filter(StockMovement.undone == 0)
    rows = (
        q.order_by(StockMovement.created_at.desc(), StockMovement.id.desc())
        .offset(skip).limit(limit).all()
    )
    return _serialize_movements(db, rows)


@router.get("/entries/{entry_id}/movements", response_model=list[StockMovementRead])
def list_entry_movements(entry_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(StockMovement)
        .filter(StockMovement.stock_entry_id == entry_id)
        .order_by(StockMovement.created_at.desc(), StockMovement.id.desc())
        .all()
    )
    return _serialize_movements(db, rows)


@router.post("/movements/{movement_id}/undo", response_model=StockMovementRead)
def undo_movement(movement_id: int, db: Session = Depends(get_db)):
    """Reverse a single movement.

    * Entry still exists  → its quantity is moved back by ``-delta`` (the entry
      is removed instead if that lands it at zero).
    * Entry was removed   → it is recreated from the snapshot taken at deletion,
      re-attaching any stock IDs that are still free.

    A compensating ``undo`` movement is appended and the original is flagged.
    """
    mv = db.get(StockMovement, movement_id)
    if not mv:
        raise HTTPException(status_code=404, detail="Movement not found")
    if mv.undone:
        raise HTTPException(status_code=409, detail="Movement already undone")
    if mv.reason == "undo":
        raise HTTPException(status_code=409, detail="Cannot undo an undo")

    entry = db.get(StockEntry, mv.stock_entry_id) if mv.stock_entry_id else None

    if entry is not None:
        restored = entry.quantity - mv.delta
        if restored < 0:
            raise HTTPException(status_code=409, detail="Undo would produce a negative stock level")
        before = entry.quantity
        if restored == 0:
            snapshot = _entry_snapshot(entry)
            db.delete(entry)
            reversal = _record_movement(
                db, stock_entry_id=None, product_id=mv.product_id, vault_id=mv.vault_id,
                before=before, after=0.0, reason="undo",
                note=f"Rückgängig von #{mv.id}", snapshot=snapshot,
            )
        else:
            entry.quantity = restored
            reversal = _record_movement(
                db, stock_entry_id=entry.id, product_id=mv.product_id, vault_id=mv.vault_id,
                before=before, after=restored, reason="undo", note=f"Rückgängig von #{mv.id}",
            )
    elif mv.entry_snapshot:
        snap = mv.entry_snapshot
        if not db.get(Product, snap.get("product_id")) or not db.get(Vault, snap.get("vault_id")):
            raise HTTPException(status_code=409, detail="Product or vault no longer exists")
        entry = StockEntry(
            product_id=snap["product_id"],
            vault_id=snap["vault_id"],
            quantity=snap["quantity"],
            comment=snap.get("comment"),
            best_before_date=(
                date.fromisoformat(snap["best_before_date"]) if snap.get("best_before_date") else None
            ),
        )
        db.add(entry)
        db.flush()
        for code in snap.get("stock_ids", []):
            if not db.query(StockEntryId).filter(StockEntryId.code == code).first():
                db.add(StockEntryId(code=code, stock_entry_id=entry.id))
        reversal = _record_movement(
            db, stock_entry_id=entry.id, product_id=entry.product_id, vault_id=entry.vault_id,
            before=0.0, after=entry.quantity, reason="undo",
            note=f"Rückgängig von #{mv.id} (Eintrag wiederhergestellt)",
        )
    else:
        raise HTTPException(
            status_code=409,
            detail="Stock entry no longer exists and cannot be restored",
        )

    mv.undone = 1
    db.commit()
    db.refresh(reversal)
    return _serialize_movements(db, [reversal])[0]
