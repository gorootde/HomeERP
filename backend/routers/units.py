import math
from collections import deque
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..helpers import get_or_404, raise_if_exists
from ..models import Product, Unit, UnitConversion
from ..schemas import (
    UnitConversionCreate,
    UnitConversionRead,
    UnitCreate,
    UnitRead,
    UnitSuggestionRead,
    UnitUpdate,
)
from ..unit_inference import (
    canonical_token,
    category_dimension,
    guess_dimension_from_abbr,
    keyword_dimension,
    parse_size,
)

router = APIRouter()


@router.get("", response_model=list[UnitRead])
def list_units(db: Session = Depends(get_db)):
    return db.query(Unit).order_by(Unit.name).all()


@router.post("", response_model=UnitRead, status_code=201)
def create_unit(data: UnitCreate, db: Session = Depends(get_db)):
    raise_if_exists(db, Unit, "Unit name already exists", name=data.name)
    raise_if_exists(db, Unit, "Unit abbreviation already exists", abbreviation=data.abbreviation)
    unit = Unit(**data.model_dump())
    if unit.dimension is None:
        unit.dimension = (
            guess_dimension_from_abbr(data.abbreviation)
            or guess_dimension_from_abbr(data.name)
        )
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit


@router.get("/suggest", response_model=UnitSuggestionRead)
def suggest_unit(
    name: Optional[str] = None,
    size: Optional[str] = None,
    off_categories: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Best-effort pre-selection of a product's unit when adding a product.

    Runs a deterministic cascade over whatever signal is supplied: an explicit
    unit token in ``size`` (``"500 g"``), an OpenFoodFacts category tag list in
    ``off_categories`` (comma-separated), then a keyword in ``name``. The result
    is advisory — the client pre-selects it and never overrides a manual choice.
    """
    units = db.query(Unit).order_by(Unit.id).all()
    parsed = parse_size(size)
    size_value = parsed["value"]
    dimension = parsed["dimension"]
    source: Optional[str] = "size_token" if dimension else None
    token_unit = _unit_for_token(units, parsed["token"])

    # Dimension from the OpenFoodFacts category, then a product-name keyword.
    if not dimension and off_categories:
        dimension = category_dimension(off_categories.split(","))
        source = "off_category" if dimension else source
    if not dimension and name:
        dimension = keyword_dimension(name)
        source = "name_keyword" if dimension else source

    if not dimension:
        return UnitSuggestionRead(confidence="none")

    candidates = [u for u in units if u.dimension == dimension]
    if not candidates:
        if token_unit is not None:
            return UnitSuggestionRead(
                unit_id=token_unit.id,
                dimension=token_unit.dimension or dimension,
                confidence="exact",
                source="size_token",
                size_value=size_value,
            )
        return UnitSuggestionRead(
            dimension=dimension, confidence="none", source=source, size_value=size_value
        )

    chosen, confidence = _pick_unit(db, candidates, size_value, token_unit)
    return UnitSuggestionRead(
        unit_id=chosen.id,
        dimension=dimension,
        confidence=confidence,
        source="existing_products" if confidence == "learned" else source,
        size_value=size_value,
    )


@router.get("/{unit_id}", response_model=UnitRead)
def get_unit(unit_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, Unit, unit_id, "Unit not found")


@router.put("/{unit_id}", response_model=UnitRead)
def update_unit(unit_id: int, data: UnitUpdate, db: Session = Depends(get_db)):
    unit = get_or_404(db, Unit, unit_id, "Unit not found")
    fields = data.model_dump(exclude_unset=True)
    for field, value in fields.items():
        setattr(unit, field, value)
    # Re-infer only when the caller didn't touch dimension and it's still unknown.
    if "dimension" not in fields and unit.dimension is None:
        unit.dimension = (
            guess_dimension_from_abbr(unit.abbreviation)
            or guess_dimension_from_abbr(unit.name)
        )
    db.commit()
    db.refresh(unit)
    return unit


@router.delete("/{unit_id}", status_code=204)
def delete_unit(unit_id: int, db: Session = Depends(get_db)):
    unit = get_or_404(db, Unit, unit_id, "Unit not found")
    db.delete(unit)
    db.commit()


@router.post("/{unit_id}/conversions", response_model=UnitConversionRead, status_code=201)
def add_conversion(unit_id: int, data: UnitConversionCreate, db: Session = Depends(get_db)):
    get_or_404(db, Unit, unit_id, "Unit not found")
    get_or_404(db, Unit, data.to_unit_id, "Target unit not found")
    if unit_id == data.to_unit_id:
        raise HTTPException(status_code=400, detail="Cannot convert a unit to itself")
    def _upsert(from_id: int, to_id: int, factor: float):
        row = (
            db.query(UnitConversion)
            .filter(UnitConversion.from_unit_id == from_id, UnitConversion.to_unit_id == to_id)
            .first()
        )
        if row:
            row.factor = factor
        else:
            row = UnitConversion(from_unit_id=from_id, to_unit_id=to_id, factor=factor)
            db.add(row)
        return row

    conv = _upsert(unit_id, data.to_unit_id, data.factor)
    _upsert(data.to_unit_id, unit_id, 1.0 / data.factor)
    db.commit()
    db.refresh(conv)
    return conv


@router.delete("/{unit_id}/conversions/{conversion_id}", status_code=204)
def delete_conversion(unit_id: int, conversion_id: int, db: Session = Depends(get_db)):
    conv = db.query(UnitConversion).filter(
        UnitConversion.id == conversion_id,
        UnitConversion.from_unit_id == unit_id,
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversion not found")
    reverse = db.query(UnitConversion).filter(
        UnitConversion.from_unit_id == conv.to_unit_id,
        UnitConversion.to_unit_id == unit_id,
    ).first()
    db.delete(conv)
    if reverse:
        db.delete(reverse)
    db.commit()


# ── suggest_unit helpers ───────────────────────────────────────────────────

def _unit_for_token(units: list[Unit], token: Optional[str]) -> Optional[Unit]:
    """The user's unit whose abbreviation/name canonicalises to ``token``."""
    if not token:
        return None
    for u in units:
        if canonical_token(u.abbreviation) == token or canonical_token(u.name) == token:
            return u
    for u in units:
        if token in (u.abbreviation.strip().lower(), u.name.strip().lower()):
            return u
    return None


def _conversion_factor(
    edges: dict[int, list[tuple[int, float]]], from_id: int, to_id: int
) -> Optional[float]:
    """Factor f such that ``1 from_unit == f to_unit``, via the conversion graph."""
    if from_id == to_id:
        return 1.0
    queue = deque([(from_id, 1.0)])
    seen = {from_id}
    while queue:
        node, acc = queue.popleft()
        for nxt, factor in edges.get(node, []):
            if nxt == to_id:
                return acc * factor
            if nxt not in seen:
                seen.add(nxt)
                queue.append((nxt, acc * factor))
    return None


def _magnitude_score(amount: float) -> float:
    """0 when the amount reads nicely (1 ≤ x < 1000), else distance from that band."""
    if amount <= 0:
        return math.inf
    if 1 <= amount < 1000:
        return 0.0
    return abs(math.log10(amount)) if amount >= 1 else abs(math.log10(1 / amount))


def _pick_unit(
    db: Session,
    candidates: list[Unit],
    size_value: Optional[float],
    token_unit: Optional[Unit],
) -> tuple[Unit, str]:
    """Choose one unit of the target dimension. Returns (unit, confidence)."""
    # Known exact amount + a real token unit → pick the same-dimension unit the
    # amount reads best in (1000 g → kg, 330 ml → ml, 0.33 l → l).
    if size_value is not None and token_unit is not None:
        edges: dict[int, list[tuple[int, float]]] = {}
        for row in db.query(UnitConversion).all():
            edges.setdefault(row.from_unit_id, []).append((row.to_unit_id, row.factor))
        best: Optional[tuple[float, Unit]] = None
        for c in candidates:
            factor = _conversion_factor(edges, token_unit.id, c.id)
            if factor is None:
                continue
            score = _magnitude_score(size_value * factor)
            if best is None or score < best[0] or (score == best[0] and c.id < best[1].id):
                best = (score, c)
        if best is not None:
            return best[1], "exact"

    if token_unit is not None:
        return token_unit, "exact"

    # Fall back to what the user tends to use for products of this dimension.
    cand_ids = [c.id for c in candidates]
    counts = dict(
        db.query(Product.unit_id, func.count(Product.id))
        .filter(Product.unit_id.in_(cand_ids))
        .group_by(Product.unit_id)
        .all()
    )
    if counts:
        chosen = max(candidates, key=lambda c: (counts.get(c.id, 0), -c.id))
        if counts.get(chosen.id, 0) > 0:
            return chosen, "learned"
    return candidates[0], "dimension"
