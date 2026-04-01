from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
import httpx

from ..database import get_db
from ..models import StockEntry, Product, Vault, Tag, ProductCategory, StockEntryId, Setting
from ..schemas import (
    StockEntryCreate, StockEntryRead, StockEntryUpdate,
    StockSummaryItem, StockSummaryVaultQty,
    CategoryStockSummaryItem,
    StockEntryIdCreate, StockEntryIdRead,
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


@router.post("/entries", response_model=StockEntryRead, status_code=201)
def create_stock_entry(data: StockEntryCreate, db: Session = Depends(get_db)):
    if not db.get(Product, data.product_id):
        raise HTTPException(status_code=404, detail="Product not found")
    if not db.get(Vault, data.vault_id):
        raise HTTPException(status_code=404, detail="Vault not found")
    entry = StockEntry(**data.model_dump(exclude={"stock_id"}))
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
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/entries/{entry_id}", status_code=204)
def delete_stock_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.get(StockEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Stock entry not found")
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
