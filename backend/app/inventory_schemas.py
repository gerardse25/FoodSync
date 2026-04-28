from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.product_schemas import ProductCategory


class ProductOwnerSchema(BaseModel):
    id_usuari: str
    nom: str

    model_config = ConfigDict(from_attributes=True)


# =========================
# INVENTARI - LLISTAT
# =========================


class InventoryProductSchema(BaseModel):
    id_producte: str
    nom: str
    quantitat: int
    categoria: str
    data_caducitat: Optional[date] = None
    es_privat: bool
    owner_user_ids: List[str] = []
    # Si vols l'objecte complex amb nom:
    propietaris: List[ProductOwnerSchema] = []

    model_config = ConfigDict(from_attributes=True)


class InventoryResponseSchema(BaseModel):
    code: str = "INVENTORY_RETRIEVED"
    missatge: str
    productes: List[InventoryProductSchema]


# =========================
# INVENTARI - DETALL
# =========================


class InventoryNutritionSchema(BaseModel):
    energy_kcal: Optional[float] = None
    fat: Optional[float] = None
    saturated_fat: Optional[float] = None
    carbohydrates: Optional[float] = None
    sugars: Optional[float] = None
    fiber: Optional[float] = None
    proteins: Optional[float] = None
    salt: Optional[float] = None
    sodium: Optional[float] = None


class InventoryProductDetailSchema(BaseModel):
    id_producte: str
    nom: str
    marca: Optional[str] = None

    quantitat_stock: int
    quantitat_envas: Optional[str] = None

    categoria: Optional[str] = None

    data_caducitat: Optional[date] = None
    data_compra: Optional[date] = None

    preu: Optional[str] = None

    es_privat: bool
    propietaris: List[ProductOwnerSchema] = []

    estat_stock: str

    nutriscore: Optional[str] = None
    informacio_nutricional_100g_ml: Optional[InventoryNutritionSchema] = None
    ingredients: Optional[str] = None
    allergens: Optional[str] = None

    imatge_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class InventoryProductDetailResponseSchema(BaseModel):
    code: str = "PRODUCT_DETAIL_RETRIEVED"
    missatge: str
    producte: InventoryProductDetailSchema


# =========================
# CREAR PRODUCTE MANUAL
# =========================


class CreateInventoryManualProductRequest(BaseModel):
    nom: Optional[str] = None
    categoria: Optional[ProductCategory] = None
    preu: Optional[Decimal] = None
    quantitat: Optional[int] = None
    data_compra: Optional[date] = None
    data_caducitat: Optional[date] = None
    id_propietaris_privats: List[UUID] = Field(default_factory=list)


class CreateInventoryProductResponseItem(BaseModel):
    id_producte: str
    id_producte_cataleg: str
    nom: str
    quantitat: int
    categoria: str
    preu: Optional[str] = None
    data_compra: Optional[date] = None
    data_caducitat: Optional[date] = None
    codi_barres: Optional[str] = None
    metode_registre: str
    owner_user_ids: List[str] = Field(default_factory=list)


class CreateInventoryProductResponse(BaseModel):
    code: str
    missatge: str
    producte: CreateInventoryProductResponseItem


# =========================
# LOOKUP BARCODE
# =========================


class BarcodeLookupProductSchema(BaseModel):
    nom: Optional[str] = None
    categoria: Optional[str] = None  # enum value, ex: BREAKFAST_CEREALS
    marca: Optional[str] = None
    quantitat_envas: Optional[str] = None
    nutriscore: Optional[str] = None
    imatge_url: Optional[str] = None


class BarcodeLookupResponseSchema(BaseModel):
    found: bool
    barcode: str
    source: str
    code: str
    product: Optional[BarcodeLookupProductSchema] = None
    message: Optional[str] = None


# =========================
# CONFIRMAR BARCODE
# =========================


class ConfirmBarcodeProductRequest(BaseModel):
    barcode: str
    nom: Optional[str] = None
    categoria: Optional[ProductCategory] = None
    preu: Optional[Decimal] = None
    quantitat: Optional[int] = None
    data_compra: Optional[date] = None
    data_caducitat: Optional[date] = None
    id_propietaris_privats: List[UUID] = Field(default_factory=list)


# =========================
# MODIFICAR / ELIMINAR
# =========================


class ConsumeProductRequest(BaseModel):
    id_producte: str
    modificacio: int


class ConsumeProductResponseItem(BaseModel):
    id_producte: str
    nom: str
    quantitat_restant: int


class ConsumeProductResponse(BaseModel):
    code: str
    missatge: str
    producte: ConsumeProductResponseItem


class DeleteProductRequest(BaseModel):
    id_producte: str


class DeleteProductResponse(BaseModel):
    code: str
    missatge: str


class UpdateProductOwnersRequest(BaseModel):
    id_producte: str
    owner_user_ids: List[UUID]


class UpdateProductOwnersResponse(BaseModel):
    code: str
    missatge: str
    id_producte: str
    es_privat: bool
    propietaris: List[ProductOwnerSchema]
