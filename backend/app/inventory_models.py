import uuid
from datetime import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Category(Base):
    __tablename__ = "categories"

    id_categoria = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nom = Column(String(50), nullable=False)


class CatalogProduct(Base):
    __tablename__ = "productes_cataleg"

    id_producte_cataleg = Column(Integer, primary_key=True, index=True, autoincrement=True)
    codi_barres = Column(String(50), unique=True, nullable=True)
    nom = Column(String(100), nullable=False)
    marca = Column(String(100))
    id_categoria = Column(Integer, ForeignKey("categories.id_categoria"))
    imatge_url = Column(String(255))

    categoria = relationship("Category")


class InventoryProduct(Base):
    __tablename__ = "productes_inventari"

    id_inventari = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_llar = Column(UUID(as_uuid=True), ForeignKey("homes.id"), nullable=False)
    id_producte_cataleg = Column(Integer, ForeignKey("productes_cataleg.id_producte_cataleg"), nullable=False)
    quantitat = Column(Integer, default=1, nullable=False)
    data_caducitat = Column(Date)
    id_propietari_privat = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    data_registre = Column(DateTime, default=datetime.utcnow)

    producte_cataleg = relationship("CatalogProduct")
    propietari = relationship("app.models.User")
