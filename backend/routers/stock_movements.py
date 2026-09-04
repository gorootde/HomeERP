from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..helpers import get_or_404
from ..models import Product, StockEntry, StockEntryId, StockMovement, Vault
from ..schemas import ConsumptionForecastItem, StockMovementRead
from ..services.stock_movements import (
    entry_snapshot,
    record_movement,
    serialize_movements,
)

router = APIRouter()


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
    return serialize_movements(db, rows)


@router.get("/entries/{entry_id}/movements", response_model=list[StockMovementRead])
def list_entry_movements(entry_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(StockMovement)
        .filter(StockMovement.stock_entry_id == entry_id)
        .order_by(StockMovement.created_at.desc(), StockMovement.id.desc())
        .all()
    )
    return serialize_movements(db, rows)


@router.post("/movements/{movement_id}/undo", response_model=StockMovementRead)
def undo_movement(movement_id: int, db: Session = Depends(get_db)):
    """Reverse a single movement.

    * Entry still exists  → its quantity is moved back by ``-delta`` (the entry
      is removed instead if that lands it at zero).
    * Entry was removed   → it is recreated from the snapshot taken at deletion,
      re-attaching any stock IDs that are still free.

    A compensating ``undo`` movement is appended and the original is flagged.
    """
    mv = get_or_404(db, StockMovement, movement_id, "Movement not found")
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
            snapshot = entry_snapshot(entry)
            db.delete(entry)
            reversal = record_movement(
                db, stock_entry_id=None, product_id=mv.product_id, vault_id=mv.vault_id,
                before=before, after=0.0, reason="undo",
                note=f"Rückgängig von #{mv.id}", snapshot=snapshot,
            )
        else:
            entry.quantity = restored
            reversal = record_movement(
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
        reversal = record_movement(
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
    return serialize_movements(db, [reversal])[0]
