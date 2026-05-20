import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base

class ShoppingListItem(Base):
    __tablename__ = "shopping_list_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    home_id = Column(UUID(as_uuid=True), ForeignKey("homes.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("productes_cataleg.id_producte_cataleg"), nullable=False, index=True)
    quantity = Column(Integer, default=1, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    product = relationship("CatalogProduct")
