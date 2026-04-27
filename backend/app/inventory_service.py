"""
app/inventory_service.py

Servei de filtrat de productes de l'inventari (RF-INV-02).

Responsabilitats:
  - Aplicar filtres combinables (AND) sobre la query de l'inventari.
  - Mantenir la lògica fora del router per facilitar tests i extensió.
  - Deixar preparat el codi per a filtres futurs (nutriscore, caducitat).

NO fa:
  - Accés a la BD directament (rep la query ja iniciada).
  - Autenticació ni gestió de membres.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Query
from uuid import UUID

from app.inventory_models import CatalogProduct, Category, InventoryProduct, InventoryProductOwner

@dataclass
class InventoryFilterParams:
    """
    Agrupa tots els paràmetres de filtratge acceptats per l'endpoint.

    Camps actius (implementats):
      search        → cerca parcial i case-insensitive per nom de producte
      categoria     → filtre exacte per nom de categoria
      min_quantity  → quantitat mínima (inclusiva)
      max_quantity  → quantitat màxima (inclusiva)

    Camps preparats per a implementació futura (acceptats, ignorats):
      nutrition_score → filtre per nutriscore (A, B, C, D, E)
      expiry_filter   → filtre per caducitat (expired, expiring_soon, ok)
    """

    search: Optional[str] = None
    categoria: Optional[str] = None
    min_quantity: Optional[int] = None
    max_quantity: Optional[int] = None
    owner_user_id: Optional[str] = None

    # Futurs — acceptats però no aplicats encara
    nutrition_score: Optional[str] = None
    expiry_filter: Optional[str] = None


def apply_active_filters(
    query: Query,
    filters: InventoryFilterParams,
) -> Query:
    """
    Aplica els filtres actius sobre la query en l'ordre definit:
      1. search (nom, coincidència parcial, case-insensitive)
      2. categoria (exacta)
      3. min_quantity / max_quantity
      4. propietari
    """
    if filters.search:
        term = filters.search.strip()
        if term:
            query = query.filter(CatalogProduct.nom.ilike(f"%{term}%"))

    if filters.categoria:
        query = query.filter(Category.nom == filters.categoria)

    if filters.min_quantity is not None:
        query = query.filter(InventoryProduct.quantitat >= filters.min_quantity)

    if filters.max_quantity is not None:
        query = query.filter(InventoryProduct.quantitat <= filters.max_quantity)
    
    if filters.owner_user_id:
        # query = query.filter(
        #     InventoryProduct.owners.any(
        #         InventoryProductOwner.user_id == filters.owner_user_id
        #     )
        # )
        try:
            owner_uuid = UUID(filters.owner_user_id) if isinstance(filters.owner_user_id, str) else filters.owner_user_id
            query = query.join(InventoryProductOwner).filter(
                InventoryProductOwner.user_id == owner_uuid
            )
        except ValueError:
            # Opcional: gestionar si el string no és un UUID vàlid
            pass

    return query


def apply_future_filters(
    query: Query,
    nutrition_score: Optional[str],
    expiry_filter: Optional[str],
) -> Query:
    """
    Placeholder per a filtres pendents d'implementació (RF-INV-02 futur).
    Els paràmetres s'accepten però no s'apliquen encara.
    """

    # TODO: nutrition_score — filtrar per CatalogProduct.nutriscore_grade
    # Exemple d'implementació futura:
    # if nutrition_score:
    #     query = query.filter(
    #         CatalogProduct.nutriscore_grade == nutrition_score.lower()
    #     )

    # TODO: expiry_filter — filtrar per InventoryProduct.data_caducitat
    # Valors possibles: 'expired', 'expiring_soon', 'ok'
    # Exemple d'implementació futura:
    # if expiry_filter:
    #     from datetime import date, timedelta
    #     today = date.today()
    #     if expiry_filter == "expired":
    #         query = query.filter(InventoryProduct.data_caducitat < today)
    #     elif expiry_filter == "expiring_soon":
    #         soon = today + timedelta(days=7)
    #         query = query.filter(
    #             InventoryProduct.data_caducitat >= today,
    #             InventoryProduct.data_caducitat <= soon,
    #         )
    #     elif expiry_filter == "ok":
    #         query = query.filter(InventoryProduct.data_caducitat > today)

    return query


def get_filtered_products(
    db,
    home_id,
    filters: InventoryFilterParams,
    base_query=None,
):
    """
    Punt d'entrada principal del servei.

    Construeix la query base si no es passa una externament
    (per facilitar tests unitaris amb mocks).

    Retorna la llista de tuples (InventoryProduct, CatalogProduct, Category).
    """
    if base_query is None:
        base_query = (
            db.query(InventoryProduct, CatalogProduct, Category)
            .join(
                CatalogProduct,
                InventoryProduct.id_producte_cataleg
                == CatalogProduct.id_producte_cataleg,
            )
            .outerjoin(
                Category,
                CatalogProduct.id_categoria == Category.id_categoria,
            )
            .filter(InventoryProduct.id_llar == home_id)
        )

    query = apply_active_filters(base_query, filters)
    query = apply_future_filters(query, filters.nutrition_score, filters.expiry_filter)

    return query.all()