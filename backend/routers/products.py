import uuid
import urllib.request
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Product, EanCode, Tag, ProductUnitConversion
from ..schemas import (
    ProductCreate, ProductRead, ProductUpdate,
    EanCodeCreate, EanCodeRead,
    TagCreate, TagRead,
    ProductUnitConversionCreate, ProductUnitConversionRead,
)

UPLOADS_DIR = Path(__file__).parent.parent.parent / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_SIZE = 10 * 1024 * 1024  # 10 MB

router = APIRouter()


@router.get("/by-ean/{ean}", response_model=ProductRead)
def get_product_by_ean(ean: str, db: Session = Depends(get_db)):
    """Look up a product by one of its EAN codes. Used by the barcode scanner."""
    ean_code = db.query(EanCode).filter(EanCode.code == ean).first()
    if not ean_code:
        raise HTTPException(status_code=404, detail=f"EAN {ean} not found")
    return ean_code.product


@router.get("", response_model=list[ProductRead])
def list_products(
    search: Optional[str] = Query(None, description="Filter by name or vendor"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    q = db.query(Product)
    if search:
        pattern = f"%{search}%"
        q = q.filter(Product.name.ilike(pattern) | Product.vendor.ilike(pattern))
    return q.offset(skip).limit(limit).all()


@router.post("", response_model=ProductRead, status_code=201)
def create_product(data: ProductCreate, db: Session = Depends(get_db)):
    product = Product(vendor=data.vendor, name=data.name, size=data.size, unit_id=data.unit_id, category_id=data.category_id)
    db.add(product)
    db.flush()
    for code in data.ean_codes:
        existing = db.query(EanCode).filter(EanCode.code == code).first()
        if existing:
            raise HTTPException(status_code=409, detail=f"EAN {code} is already assigned to another product")
        db.add(EanCode(code=code, product_id=product.id))
    db.commit()
    db.refresh(product)
    return product


@router.get("/{product_id}", response_model=ProductRead)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.put("/{product_id}", response_model=ProductRead)
def update_product(product_id: int, data: ProductUpdate, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()


@router.post("/{product_id}/ean", response_model=EanCodeRead, status_code=201)
def add_ean(product_id: int, data: EanCodeCreate, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    existing = db.query(EanCode).filter(EanCode.code == data.code).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"EAN {data.code} is already assigned to another product")
    ean = EanCode(code=data.code, product_id=product_id)
    db.add(ean)
    db.commit()
    db.refresh(ean)
    return ean


@router.delete("/{product_id}/ean/{ean_id}", status_code=204)
def remove_ean(product_id: int, ean_id: int, db: Session = Depends(get_db)):
    ean = db.query(EanCode).filter(EanCode.id == ean_id, EanCode.product_id == product_id).first()
    if not ean:
        raise HTTPException(status_code=404, detail="EAN not found")
    db.delete(ean)
    db.commit()


@router.post("/{product_id}/image", response_model=ProductRead)
async def upload_image(product_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="Only JPEG, PNG, WebP and GIF images are allowed")
    data = await file.read()
    if len(data) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="Image must be smaller than 10 MB")
    suffix = Path(file.filename).suffix.lower() if file.filename else ".jpg"
    filename = f"{uuid.uuid4().hex}{suffix}"
    dest = UPLOADS_DIR / filename
    dest.write_bytes(data)
    # Remove old image if present
    if product.image_path:
        old = UPLOADS_DIR / Path(product.image_path).name
        if old.exists():
            old.unlink()
    product.image_path = f"/uploads/{filename}"
    db.commit()
    db.refresh(product)
    return product


@router.post("/{product_id}/tags", response_model=TagRead, status_code=201)
def add_tag_to_product(product_id: int, data: TagCreate, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    tag = db.query(Tag).filter(Tag.name == data.name).first()
    if not tag:
        tag = Tag(name=data.name)
        db.add(tag)
        db.flush()
    if tag not in product.tags:
        product.tags.append(tag)
    db.commit()
    db.refresh(tag)
    return tag


@router.delete("/{product_id}/tags/{tag_name}", status_code=204)
def remove_tag_from_product(product_id: int, tag_name: str, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    tag = db.query(Tag).filter(Tag.name == tag_name).first()
    if tag and tag in product.tags:
        product.tags.remove(tag)
        db.commit()


class _ImageUrlBody(BaseModel):
    url: str

@router.post("/{product_id}/image-from-url", response_model=ProductRead)
def image_from_url(product_id: int, body: _ImageUrlBody, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    try:
        req = urllib.request.Request(body.url, headers={"User-Agent": "HomeERP/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            content_type = resp.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
            image_data = resp.read(MAX_SIZE + 1)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Bild konnte nicht heruntergeladen werden: {exc}")
    if len(image_data) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="Image must be smaller than 10 MB")
    if content_type not in ALLOWED_TYPES:
        content_type = "image/jpeg"
    ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}.get(content_type, ".jpg")
    filename = f"{uuid.uuid4().hex}{ext}"
    dest = UPLOADS_DIR / filename
    dest.write_bytes(image_data)
    if product.image_path:
        old = UPLOADS_DIR / Path(product.image_path).name
        if old.exists():
            old.unlink()
    product.image_path = f"/uploads/{filename}"
    db.commit()
    db.refresh(product)
    return product


@router.get("/{product_id}/unit-conversions", response_model=list[ProductUnitConversionRead])
def list_product_unit_conversions(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product.unit_conversions


@router.post("/{product_id}/unit-conversions", response_model=ProductUnitConversionRead, status_code=201)
def add_product_unit_conversion(product_id: int, data: ProductUnitConversionCreate, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    existing = db.query(ProductUnitConversion).filter(
        ProductUnitConversion.product_id == product_id,
        ProductUnitConversion.unit_name == data.unit_name,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Einheit '{data.unit_name}' ist für dieses Produkt bereits definiert")
    conv = ProductUnitConversion(
        product_id=product_id,
        unit_name=data.unit_name,
        base_unit_id=data.base_unit_id,
        factor=data.factor,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


@router.delete("/{product_id}/unit-conversions/{conv_id}", status_code=204)
def delete_product_unit_conversion(product_id: int, conv_id: int, db: Session = Depends(get_db)):
    conv = db.query(ProductUnitConversion).filter(
        ProductUnitConversion.id == conv_id,
        ProductUnitConversion.product_id == product_id,
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversion not found")
    db.delete(conv)
    db.commit()


@router.delete("/{product_id}/image", status_code=204)
def delete_image(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.image_path:
        old = UPLOADS_DIR / Path(product.image_path).name
        if old.exists():
            old.unlink()
        product.image_path = None
        db.commit()
