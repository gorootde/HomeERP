"""Stock-movement audit log: recording, snapshotting and serialization.

Shared by ``routers/stock.py`` (which appends a movement on every create/edit/
delete) and ``routers/stock_movements.py`` (which lists/undoes them) — split
out per the refactoring plan, section 2, so neither router needs to import
private helpers from the other.
"""
from typing import Optional

from sqlalchemy.orm import Session

from ..models import Product, StockEntry, StockMovement, Vault
from ..schemas import StockMovementRead

MOVEMENT_REASONS = {"create", "edit", "consume", "adjust", "delete", "undo", "import"}


def record_movement(db: Session, *, stock_entry_id: Optional[int], product_id: Optional[int],
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
        reason=reason if reason in MOVEMENT_REASONS else "edit",
        note=(note or None),
        entry_snapshot=snapshot,
    )
    db.add(mv)
    return mv


def entry_snapshot(entry: StockEntry) -> dict:
    """Enough state to recreate an entry that a mis-scan removed."""
    return {
        "product_id": entry.product_id,
        "vault_id": entry.vault_id,
        "quantity": entry.quantity,
        "comment": entry.comment,
        "best_before_date": entry.best_before_date.isoformat() if entry.best_before_date else None,
        "stock_ids": [s.code for s in entry.stock_ids],
    }


def movement_can_undo(mv: StockMovement) -> bool:
    if mv.undone or mv.reason == "undo":
        return False
    # Reversible if the entry still exists, or we kept a snapshot to rebuild it.
    return mv.stock_entry_id is not None or bool(mv.entry_snapshot)


def serialize_movements(db: Session, rows: list[StockMovement]) -> list[StockMovementRead]:
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
        can_undo = movement_can_undo(r) and (
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
