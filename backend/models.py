from sqlalchemy import Column, Integer, String, Float, Date, Text, ForeignKey, UniqueConstraint, Table
from sqlalchemy.orm import relationship
from .database import Base


# ── Association tables ──────────────────────────────────────────────────────

product_tags = Table(
    "product_tags",
    Base.metadata,
    Column("product_id", Integer, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)

vault_tags = Table(
    "vault_tags",
    Base.metadata,
    Column("vault_id", Integer, ForeignKey("vaults.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)

stock_entry_tags = Table(
    "stock_entry_tags",
    Base.metadata,
    Column("stock_entry_id", Integer, ForeignKey("stock_entries.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


# ── Models ──────────────────────────────────────────────────────────────────

class Unit(Base):
    __tablename__ = "units"

    id           = Column(Integer, primary_key=True, index=True)
    name         = Column(String(64), nullable=False, unique=True)
    abbreviation = Column(String(16), nullable=False, unique=True)

    conversions = relationship(
        "UnitConversion",
        foreign_keys="UnitConversion.from_unit_id",
        back_populates="from_unit",
        cascade="all, delete-orphan",
    )


class UnitConversion(Base):
    __tablename__ = "unit_conversions"
    __table_args__ = (UniqueConstraint("from_unit_id", "to_unit_id", name="uq_unit_conversion"),)

    id           = Column(Integer, primary_key=True, index=True)
    from_unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)
    to_unit_id   = Column(Integer, ForeignKey("units.id"), nullable=False)
    factor       = Column(Float, nullable=False)  # 1 from_unit = factor to_unit

    from_unit = relationship("Unit", foreign_keys=[from_unit_id], back_populates="conversions")
    to_unit   = relationship("Unit", foreign_keys=[to_unit_id])


class Setting(Base):
    __tablename__ = "settings"

    key   = Column(String(128), primary_key=True)
    value = Column(String(1024), nullable=False)


class ProductCategory(Base):
    __tablename__ = "product_categories"

    id                  = Column(Integer, primary_key=True, index=True)
    name                = Column(String(128), nullable=False, unique=True)
    min_stock_quantity  = Column(Float, nullable=True)
    min_stock_unit_id   = Column(Integer, ForeignKey("units.id"), nullable=True)

    min_stock_unit = relationship("Unit")
    products = relationship("Product", back_populates="category")


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), nullable=False, unique=True, index=True)


class Product(Base):
    __tablename__ = "products"

    id          = Column(Integer, primary_key=True, index=True)
    vendor      = Column(String(255), nullable=False)
    name        = Column(String(255), nullable=False)
    size        = Column(Float, nullable=True)
    unit_id         = Column(Integer, ForeignKey("units.id"), nullable=True)
    entry_unit_key  = Column(String(64), nullable=True)   # 'base' | 'puc_<id>' | 'global_<id>'
    category_id     = Column(Integer, ForeignKey("product_categories.id"), nullable=True)
    image_path      = Column(String(512), nullable=True)

    unit     = relationship("Unit")
    category = relationship("ProductCategory", back_populates="products")
    ean_codes        = relationship("EanCode", back_populates="product", cascade="all, delete-orphan")
    stock_entries    = relationship("StockEntry", back_populates="product", cascade="all, delete-orphan")
    tags             = relationship("Tag", secondary=product_tags)
    unit_conversions = relationship("ProductUnitConversion", back_populates="product", cascade="all, delete-orphan")


class ProductUnitConversion(Base):
    __tablename__ = "product_unit_conversions"
    __table_args__ = (UniqueConstraint("product_id", "unit_name", name="uq_product_unit_name"),)

    id           = Column(Integer, primary_key=True, index=True)
    product_id   = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    unit_name    = Column(String(64), nullable=False)   # z.B. "Flasche"
    base_unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)
    factor       = Column(Float, nullable=False)        # 1 unit_name = factor base_unit

    product   = relationship("Product", back_populates="unit_conversions")
    base_unit = relationship("Unit")


class EanCode(Base):
    __tablename__ = "ean_codes"
    __table_args__ = (UniqueConstraint("code", name="uq_ean_code"),)

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(32), nullable=False, unique=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    product = relationship("Product", back_populates="ean_codes")


class StockEntryId(Base):
    __tablename__ = "stock_entry_qr_codes"

    id             = Column(Integer, primary_key=True, index=True)
    code           = Column(String(512), nullable=False, index=True)
    stock_entry_id = Column(Integer, ForeignKey("stock_entries.id"), nullable=False)

    stock_entry = relationship("StockEntry", back_populates="stock_ids")


class Vault(Base):
    __tablename__ = "vaults"

    id = Column(Integer, primary_key=True, index=True)
    description = Column(String(512), nullable=False)

    stock_entries = relationship("StockEntry", back_populates="vault", cascade="all, delete-orphan")
    tags = relationship("Tag", secondary=vault_tags)


class StockEntry(Base):
    __tablename__ = "stock_entries"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    vault_id = Column(Integer, ForeignKey("vaults.id"), nullable=False)
    quantity = Column(Float, nullable=False, default=1.0)
    comment = Column(Text, nullable=True)
    best_before_date = Column(Date, nullable=True)

    product  = relationship("Product", back_populates="stock_entries")
    vault    = relationship("Vault", back_populates="stock_entries")
    tags     = relationship("Tag", secondary=stock_entry_tags)
    stock_ids = relationship("StockEntryId", back_populates="stock_entry", cascade="all, delete-orphan")
