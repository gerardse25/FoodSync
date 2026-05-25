"""
app/ticket_schemas.py

Schemas per al flux OCR de tickets (RF-ING-02, RF-ING-04).

Disseny:
  - OcrDetectedProduct: cada producte detectat pel OCR, editable pel frontend.
  - OcrTicketResponse: resposta de POST /inventory/ticket/ocr (llista editable).
  - ConfirmTicketProductItem: cada producte que el frontend confirma.
  - ConfirmTicketRequest: cos de POST /inventory/ticket/confirm.
  - ConfirmTicketResponse: resposta de confirmació amb productes guardats.

RF-ING-04: els productes NO es guarden fins a l'endpoint de confirmació.
"""

from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.product_schemas import ProductCategory

# ── Producte detectat retornat pel OCR ───────────────────────────────────────


class OcrDetectedProduct(BaseModel):
    """
    Producte detectat al ticket.

    Tots els camps són opcionals perquè el OCR pot tenir reconeixement parcial.
    El frontend els edita/omple abans de confirmar.
    """

    # Identificació
    nom: Optional[str] = None
    marca: Optional[str] = None

    # Classificació
    categoria: Optional[ProductCategory] = None
    categoria_label: Optional[str] = None  # label llegible en català

    # Quantitat i preu (extrets del ticket)
    quantitat: Optional[int] = None
    preu: Optional[Decimal] = None

    # Dates
    data_caducitat: Optional[date] = None
    data_compra: Optional[date] = None
    data_caducitat_estimada: bool = False

    # Enriquiment OFF
    quantitat_envas: Optional[str] = None
    nutriscore: Optional[str] = None
    imatge_url: Optional[str] = None
    nutrient_levels: Optional[dict] = None
    nutriments_100g: Optional[dict] = None
    ingredients_text: Optional[str] = None
    allergens_text: Optional[str] = None
    nutriments_per_100g: Optional[dict] = None

    # Propietaris (opcional, assignació posterior)
    id_propietaris_privats: List[UUID] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


# ── Resposta OCR ─────────────────────────────────────────────────────────────


class OcrTicketResponse(BaseModel):
    """Resposta de POST /inventory/ticket/ocr."""

    code: str
    missatge: str
    productes: List[OcrDetectedProduct]


# ── Confirmació ───────────────────────────────────────────────────────────────


class ConfirmTicketProductItem(BaseModel):
    """
    Producte que el frontend envia per confirmar.

    Camps obligatoris (RF-ING-04):
      - nom
      - categoria
      - quantitat
      - preu

    Camps opcionals:
      - data_caducitat
      - data_compra
      - id_propietaris_privats
      - marca
      - quantitat_envas
      - nutriscore
      - imatge_url
      - nutrient_levels
      - nutriments_100g
    """

    nom: Optional[str] = None
    categoria: Optional[ProductCategory] = None
    quantitat: Optional[int] = None
    preu: Optional[Decimal] = None

    # Enriquiment OFF reenviat pel frontend des del preview OCR
    marca: Optional[str] = None
    quantitat_envas: Optional[str] = None
    nutriscore: Optional[str] = None
    imatge_url: Optional[str] = None
    nutrient_levels: Optional[dict] = None
    nutriments_100g: Optional[dict] = None
    ingredients_text: Optional[str] = None
    allergens_text: Optional[str] = None
    nutriments_per_100g: Optional[dict] = None

    data_caducitat: Optional[date] = None
    data_compra: Optional[date] = None
    data_caducitat_estimada: bool = False
    id_propietaris_privats: List[UUID] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class ConfirmTicketRequest(BaseModel):
    """Cos de POST /inventory/ticket/confirm."""

    paid_by_user_id: Optional[UUID] = None
    productes: List[ConfirmTicketProductItem]


class ConfirmedProductItem(BaseModel):
    """Resum d'un producte guardat a l'inventari."""

    id_producte: str
    id_producte_cataleg: str
    nom: str
    quantitat: int
    categoria: str
    preu: Optional[str] = None
    marca: Optional[str] = None
    quantitat_envas: Optional[str] = None
    nutriscore: Optional[str] = None
    imatge_url: Optional[str] = None
    nutrient_levels: Optional[dict] = None
    nutriments_100g: Optional[dict] = None
    ingredients_text: Optional[str] = None
    allergens_text: Optional[str] = None
    nutriments_per_100g: Optional[dict] = None
    data_compra: Optional[date] = None
    data_caducitat: Optional[date] = None
    data_caducitat_estimada: bool = False
    paid_by_user_id: Optional[str] = None
    metode_registre: str
    owner_user_ids: List[str] = Field(default_factory=list)


class ConfirmTicketResponse(BaseModel):
    """Resposta de POST /inventory/ticket/confirm."""

    code: str
    missatge: str
    productes_guardats: List[ConfirmedProductItem]
