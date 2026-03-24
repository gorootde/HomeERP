from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ProductCategory
from ..schemas import ProductCategoryCreate, ProductCategoryRead, ProductCategoryUpdate

router = APIRouter()


@router.get("", response_model=list[ProductCategoryRead])
def list_categories(db: Session = Depends(get_db)):
    return db.query(ProductCategory).order_by(ProductCategory.name).all()


@router.post("", response_model=ProductCategoryRead, status_code=201)
def create_category(data: ProductCategoryCreate, db: Session = Depends(get_db)):
    existing = db.query(ProductCategory).filter(ProductCategory.name == data.name).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Kategorie '{data.name}' existiert bereits")
    category = ProductCategory(**data.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.get("/{category_id}", response_model=ProductCategoryRead)
def get_category(category_id: int, db: Session = Depends(get_db)):
    category = db.get(ProductCategory, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Kategorie nicht gefunden")
    return category


@router.put("/{category_id}", response_model=ProductCategoryRead)
def update_category(category_id: int, data: ProductCategoryUpdate, db: Session = Depends(get_db)):
    category = db.get(ProductCategory, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Kategorie nicht gefunden")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=204)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    category = db.get(ProductCategory, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Kategorie nicht gefunden")
    db.delete(category)
    db.commit()
