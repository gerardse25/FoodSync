from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Category(Base):
    __tablename__ = "categories"

    id_categoria = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nom = Column(String(50), nullable=False, unique=True)


class CatalogProduct(Base):
    __tablename__ = "productes_cataleg"

    id_producte_cataleg = Column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    codi_barres = Column(String(50), unique=True, nullable=True, index=True)
    nom = Column(String(100), nullable=False)
    marca = Column(String(100), nullable=True)
    id_categoria = Column(Integer, ForeignKey("categories.id_categoria"), nullable=True)
    imatge_url = Column(String(255), nullable=True)

    # Snapshot local d'Open Food Facts
    quantitat_envas = Column(String(64), nullable=True)  # ex: "200 g", "1 L"
    ingredients_text = Column(Text, nullable=True)
    allergens_text = Column(Text, nullable=True)
    nutriscore_grade = Column(String(1), nullable=True)
    nutriments_per_100g = Column(JSON, nullable=True)
    off_last_synced_at = Column(DateTime, nullable=True)

    categoria = relationship("Category")


class InventoryProduct(Base):
    __tablename__ = "productes_inventari"

    __table_args__ = (
        CheckConstraint(
            "quantitat >= 0 AND quantitat <= 99", name="check_quantitat_range"
        ),
    )

    id_inventari = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_llar = Column(UUID(as_uuid=True), ForeignKey("homes.id"), nullable=False)
    id_producte_cataleg = Column(
        Integer, ForeignKey("productes_cataleg.id_producte_cataleg"), nullable=False
    )

    quantitat = Column(Integer, default=1, nullable=False)
    data_caducitat = Column(Date, nullable=True)

    # Camps propis de la compra / llar
    preu = Column(Numeric(10, 2), nullable=True)
    data_compra = Column(Date, nullable=True)
    metode_registre = Column(
        String(16), nullable=False, default="manual"
    )  # manual|barcode|receipt

    data_registre = Column(DateTime, default=datetime.utcnow)

    producte_cataleg = relationship("CatalogProduct")
    owners = relationship(
        "InventoryProductOwner",
        back_populates="producte_inventari",
        cascade="all, delete-orphan",
    )


class InventoryProductOwner(Base):
    __tablename__ = "productes_inventari_propietaris"

    __table_args__ = (
        UniqueConstraint("id_inventari", "user_id", name="uq_inventory_product_owner"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_inventari = Column(
        Integer,
        ForeignKey("productes_inventari.id_inventari", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    producte_inventari = relationship("InventoryProduct", back_populates="owners")
    user = relationship("app.models.User")
