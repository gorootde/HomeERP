from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer

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
    unit_id: Optional[int] = None
    entry_unit_key: Optional[str] = Field(None, max_length=64)
    category_id: Optional[int] = None

class ProductCreate(ProductBase):
    ean_codes: list[str] = Field(default_factory=list)

class ProductUpdate(BaseModel):
    vendor: Optional[str] = Field(None, min_length=1, max_length=255)
    name: Optional[str] = Field(None, min_length=1, max_length=255)
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
    quantity: float = Field(..., gt=0)  # amount in the product's base unit
    # Unit picked at creation + raw amount typed, kept for display only ("1 Kasten (12 L)").
    # entry_unit_key: 'base' | 'puc_<id>' | 'global_<id>'; both null for base-unit / legacy entries.
    entry_unit_key: Optional[str] = Field(None, max_length=64)
    entry_quantity: Optional[float] = Field(None, gt=0)
    comment: Optional[str] = None
    best_before_date: Optional[date] = None

class StockEntryCreate(StockEntryBase):
    stock_id: Optional[str] = Field(None, max_length=512)
    # None → follow the global auto-print setting; False → don't print for this entry.
    print_label: Optional[bool] = None

class StockEntryUpdate(BaseModel):
    quantity: Optional[float] = Field(None, gt=0)
    entry_unit_key: Optional[str] = Field(None, max_length=64)
    entry_quantity: Optional[float] = Field(None, gt=0)
    comment: Optional[str] = None
    best_before_date: Optional[date] = None
    # Audit-log context; consumed by the router, not persisted on the entry.
    reason: Optional[str] = Field(None, max_length=32)
    note: Optional[str] = Field(None, max_length=255)

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


# ── Stock Movements (audit log) ────────────────────────────────────────────────

class StockMovementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    stock_entry_id: Optional[int] = None
    product_id: Optional[int] = None
    vault_id: Optional[int] = None
    product_name: Optional[str] = None
    vendor: Optional[str] = None
    unit: Optional[UnitSimple] = None
    vault_description: Optional[str] = None
    delta: float
    quantity_before: float
    quantity_after: float
    reason: str
    note: Optional[str] = None
    undone: bool = False
    can_undo: bool = False
    created_at: datetime

    @field_serializer("created_at")
    def _serialize_created_at(self, value: datetime) -> str:
        # Stored naive in UTC (SQLite drops tzinfo) — re-attach it so clients
        # don't parse the timestamp as local time.
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()


class ConsumptionForecastItem(BaseModel):
    product_id: int
    product_name: str
    vendor: Optional[str] = None
    unit: Optional[UnitSimple] = None
    current_stock: float
    window_days: int
    consumed_in_window: float
    avg_daily_consumption: float
    days_remaining: Optional[float] = None
    depletion_date: Optional[date] = None
