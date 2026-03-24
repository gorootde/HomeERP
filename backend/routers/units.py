from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Unit, UnitConversion
from ..schemas import UnitCreate, UnitUpdate, UnitRead, UnitConversionCreate, UnitConversionRead

router = APIRouter()


@router.get("", response_model=list[UnitRead])
def list_units(db: Session = Depends(get_db)):
    return db.query(Unit).order_by(Unit.name).all()


@router.post("", response_model=UnitRead, status_code=201)
def create_unit(data: UnitCreate, db: Session = Depends(get_db)):
    if db.query(Unit).filter(Unit.name == data.name).first():
        raise HTTPException(400, "Unit name already exists")
    if db.query(Unit).filter(Unit.abbreviation == data.abbreviation).first():
        raise HTTPException(400, "Unit abbreviation already exists")
    unit = Unit(**data.model_dump())
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit


@router.get("/{unit_id}", response_model=UnitRead)
def get_unit(unit_id: int, db: Session = Depends(get_db)):
    unit = db.get(Unit, unit_id)
    if not unit:
        raise HTTPException(404, "Unit not found")
    return unit


@router.put("/{unit_id}", response_model=UnitRead)
def update_unit(unit_id: int, data: UnitUpdate, db: Session = Depends(get_db)):
    unit = db.get(Unit, unit_id)
    if not unit:
        raise HTTPException(404, "Unit not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(unit, field, value)
    db.commit()
    db.refresh(unit)
    return unit


@router.delete("/{unit_id}", status_code=204)
def delete_unit(unit_id: int, db: Session = Depends(get_db)):
    unit = db.get(Unit, unit_id)
    if not unit:
        raise HTTPException(404, "Unit not found")
    db.delete(unit)
    db.commit()


@router.post("/{unit_id}/conversions", response_model=UnitConversionRead, status_code=201)
def add_conversion(unit_id: int, data: UnitConversionCreate, db: Session = Depends(get_db)):
    if not db.get(Unit, unit_id):
        raise HTTPException(404, "Unit not found")
    if not db.get(Unit, data.to_unit_id):
        raise HTTPException(404, "Target unit not found")
    if unit_id == data.to_unit_id:
        raise HTTPException(400, "Cannot convert a unit to itself")
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
        raise HTTPException(404, "Conversion not found")
    reverse = db.query(UnitConversion).filter(
        UnitConversion.from_unit_id == conv.to_unit_id,
        UnitConversion.to_unit_id == unit_id,
    ).first()
    db.delete(conv)
    if reverse:
        db.delete(reverse)
    db.commit()
