from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
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

    # Dies orientatius per estimar la caducitat segons la categoria.
    # Això dona compliment a RNF-EXP-01: el període queda reflectit a BBDD.
    dies_caducitat_estimats = Column(Integer, nullable=True)


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
    # Camps extra valors nutricionals (colors i percentatges)
    nutrient_levels = Column(JSON, nullable=True)
    nutriments_100g = Column(JSON, nullable=True)

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
    data_caducitat_estimada = Column(Boolean, default=False, nullable=False)

    # NUEVA COLUMNA:
    es_privat = Column(Boolean, default=False, nullable=False)

    # Camps propis de la compra / llar
    preu = Column(Numeric(10, 2), nullable=True)
    data_compra = Column(Date, nullable=True)

    # Usuari que ha pagat aquest producte.
    # Si el frontend no l'envia, es guarda l'usuari autenticat.
    paid_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
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
    paid_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)


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


class CostSettlement(Base):
    __tablename__ = "cost_settlements"

    id = Column(Integer, primary_key=True, autoincrement=True)

    home_id = Column(
        UUID(as_uuid=True),
        ForeignKey("homes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    from_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    to_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    amount = Column(Numeric(10, 2), nullable=False)

    # Rang opcional al qual aplica el pagament.
    # Si són null, el pagament aplica al balanç general.
    date_from = Column(Date, nullable=True)
    date_to = Column(Date, nullable=True)

    paid_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
