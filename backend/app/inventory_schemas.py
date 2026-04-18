from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class ProductOwnerSchema(BaseModel):
    id_usuari: str
    nom: str
    
    model_config = ConfigDict(from_attributes=True)


class InventoryProductSchema(BaseModel):
    id_producte: str
    nom: str
    quantitat: int
    categoria: str
    data_caducitat: Optional[date] = None
    es_privat: bool
    propietari: Optional[ProductOwnerSchema] = None
    
    model_config = ConfigDict(from_attributes=True)


class InventoryResponseSchema(BaseModel):
    missatge: str
    productes: List[InventoryProductSchema]
