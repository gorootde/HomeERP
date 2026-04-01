from __future__ import annotations
from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


# ── Units ───────────────────────────────────────────────────────────────────

class UnitBase(BaseModel):
    name:         str = Field(..., min_length=1, max_length=64)
    abbreviation: str = Field(..., min_length=1, max_length=16)

class UnitCreate(UnitBase):
    pass

class UnitUpdate(BaseModel):
    name:         Optional[str] = Field(None, min_length=1, max_length=64)
    abbreviation: Optional[str] = Field(None, min_length=1, max_length=16)

class UnitConversionCreate(BaseModel):
    to_unit_id: int
    factor:     float = Field(..., gt=0)

class UnitSimple(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:           int
    name:         str
    abbreviation: str

class UnitConversionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:      int
    factor:  float
    to_unit: UnitSimple

class UnitRead(UnitBase):
    model_config = ConfigDict(from_attributes=True)
    id:          int
    conversions: list[UnitConversionRead] = []


# ── Settings ────────────────────────────────────────────────────────────────

class SettingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    key:   str
    value: str

class SettingWrite(BaseModel):
    value: str = Field(..., min_length=0, max_length=1024)


# ── Product Categories ──────────────────────────────────────────────────────

class ProductCategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    min_stock_quantity: Optional[float] = Field(None, gt=0)
    min_stock_unit_id: Optional[int] = None

class ProductCategoryCreate(ProductCategoryBase):
    pass

class ProductCategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    min_stock_quantity: Optional[float] = Field(None, gt=0)
    min_stock_unit_id: Optional[int] = None

class ProductCategoryRead(ProductCategoryBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    min_stock_unit: Optional[UnitSimple] = None


# ── Tags ────────────────────────────────────────────────────────────────────

class TagRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


# ── EAN Codes ──────────────────────────────────────────────────────────────────

class EanCodeBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=32)

class EanCodeCreate(EanCodeBase):
    pass

class EanCodeRead(EanCodeBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ── Products ───────────────────────────────────────────────────────────────────

class ProductBase(BaseModel):
    vendor: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
    size: Optional[float] = None
    unit_id: Optional[int] = None
    entry_unit_key: Optional[str] = Field(None, max_length=64)
    category_id: Optional[int] = None

class ProductCreate(ProductBase):
    ean_codes: list[str] = Field(default_factory=list)

class ProductUpdate(BaseModel):
    vendor: Optional[str] = Field(None, min_length=1, max_length=255)
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    size: Optional[float] = None
    unit_id: Optional[int] = None
    entry_unit_key: Optional[str] = Field(None, max_length=64)
    category_id: Optional[int] = None

class ProductUnitConversionCreate(BaseModel):
    unit_name:    str   = Field(..., min_length=1, max_length=64)
    base_unit_id: int
    factor:       float = Field(..., gt=0)

class ProductUnitConversionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:        int
    unit_name: str
    factor:    float
    base_unit: UnitSimple


class ProductRead(ProductBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    image_path: Optional[str] = None
    unit: Optional[UnitSimple] = None
    category: Optional[ProductCategoryRead] = None
    ean_codes: list[EanCodeRead] = []
    tags: list[TagRead] = []
    unit_conversions: list[ProductUnitConversionRead] = []


# ── Vaults ─────────────────────────────────────────────────────────────────────

class VaultBase(BaseModel):
    description: str = Field(..., min_length=1, max_length=512)

class VaultCreate(VaultBase):
    pass

class VaultUpdate(BaseModel):
    description: Optional[str] = Field(None, min_length=1, max_length=512)

class VaultRead(VaultBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tags: list[TagRead] = []


# ── Stock Entry IDs ────────────────────────────────────────────────────────────

class StockEntryIdCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=512)

class StockEntryIdRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:   int
    code: str


# ── Stock Entries ──────────────────────────────────────────────────────────────

class StockEntryBase(BaseModel):
    product_id: int
    vault_id: int
    quantity: float = Field(..., gt=0)
    comment: Optional[str] = None
    best_before_date: Optional[date] = None

class StockEntryCreate(StockEntryBase):
    stock_id: Optional[str] = Field(None, max_length=512)

class StockEntryUpdate(BaseModel):
    quantity: Optional[float] = Field(None, gt=0)
    comment: Optional[str] = None
    best_before_date: Optional[date] = None

class StockEntryRead(StockEntryBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product: ProductRead
    vault: VaultRead
    tags: list[TagRead] = []
    stock_ids: list[StockEntryIdRead] = []


# ── Tag operations ─────────────────────────────────────────────────────────────

class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)


# ── Aggregated ─────────────────────────────────────────────────────────────────

class StockSummaryVaultQty(BaseModel):
    vault_id: int
    vault_description: str
    total_quantity: float

class StockSummaryItem(BaseModel):
    product_id: int
    vendor: str
    product_name: str
    size: Optional[float] = None
    unit: Optional[UnitSimple] = None
    total_quantity: float
    by_vault: list[StockSummaryVaultQty]

class CategoryStockSummaryItem(BaseModel):
    category_id: Optional[int]
    category_name: str
    min_stock_quantity: Optional[float]
    min_stock_unit: Optional[UnitSimple]
    total_quantity: float
    product_count: int
