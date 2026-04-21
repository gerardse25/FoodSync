"""
Servei d'integració amb Open Food Facts (OFF).

Responsabilitat:
  - Consultar l'API pública d'OFF a partir d'un codi EAN/UPC.
  - Normalitzar la resposta al format intern del projecte.
  - Aïllar la dependència externa per facilitar mocking en tests.

Decisions tècniques:
  - Timeout curt (5 s) per no bloquejar la request del client.
  - Cap dada s'emmagatzema: l'endpoint és només de consulta/autocompletat.
  - La categoria es mapeja des del camp `categories` d'OFF, agafant
    el primer valor normalitzat. Si no n'hi ha, retorna "General".
"""
from app.category_mapper import map_off_to_internal_category
import base64
import re

import requests

OFF_BASE_URL = "https://es.openfoodfacts.net"
OFF_API_URL = OFF_BASE_URL + "/api/v2/product/{barcode}.json"
OFF_TIMEOUT = 5.0

HEADERS = {
    "Authorization": "Basic " + base64.b64encode(b"off:off").decode("utf-8"),
    "User-Agent": "FoodSyncTicket/1.0 (contacto@tuapp.com)",
}

BARCODE_REGEX = re.compile(r"^\d{8,14}$")


def is_valid_barcode(barcode: str) -> bool:
    return bool(BARCODE_REGEX.match(barcode.strip()))


# def _extract_category(product_data: dict) -> str:
#     """
#     Extreu la primera categoria llegible d'OFF.
#     OFF retorna categories com 'en:beverages,en:juices' o
#     'Begudes,Sucs' depenent de l'idioma.
#     """
#     # Intentem el camp localitzat primer, després el genèric
#     raw = (
#         product_data.get("categories_tags")
#         or product_data.get("categories", "")
#     )

#     if isinstance(raw, list) and raw:
#         # Eliminem el prefix de llengua ('en:', 'ca:', etc.)
#         first = raw[0]
#         category = re.sub(r"^[a-z]{2}:", "", first)
#         return category.strip().capitalize() or "General"

#     if isinstance(raw, str) and raw:
#         first = raw.split(",")[0]
#         category = re.sub(r"^[a-z]{2}:", "", first)
#         return category.strip().capitalize() or "General"

#     return "General"

def _extract_category(product_data: dict) -> str:
    """
    Utilitza el mapejador per retornar una categoria vàlida del projecte.
    """
    raw_tags = (
        product_data.get("categories_tags")
        or product_data.get("categories", "")
    )
    
    # Obtenim la categoria del nostre Enum
    internal_cat = map_off_to_internal_category(raw_tags)
    
    # Retornem el valor (string) de l'Enum per a la resposta JSON
    return internal_cat.value

def lookup_barcode(barcode: str) -> dict | None:
    """
    Consulta Open Food Facts pel codi de barres donat.

    Retorna un dict amb els camps autocompletables si el producte
    existeix, o None si no es troba o hi ha error de xarxa.

    Camps retornats (tots opcionals/nullable):
      - name: str | None
      - category: str
      - barcode: str
      - image_url: str | None
      - found: bool
    """
    url = OFF_API_URL.format(barcode=barcode.strip())

    try:
        response = requests.get(
            url, 
            headers=HEADERS, 
            timeout=OFF_TIMEOUT
            )
    except requests.RequestException:
        return None

    if response.status_code != 200:
        return None

    try:
        data = response.json()
    except Exception:
        return None

    # OFF retorna status=0 si el producte no existeix
    if data.get("status") != 1:
        return {"found": False, "barcode": barcode}

    product_data = data.get("product", {})

    name = (
        product_data.get("product_name")
        or product_data.get("product_name_en")
        or product_data.get("product_name_es")
        or None
    )

    if name:
        name = name.strip() or None

    image_url = (
        product_data.get("image_front_url")
        or product_data.get("image_url")
        or None
    )

    return {
        "found": True,
        "barcode": barcode,
        "name": name,
        "category": _extract_category(product_data),
        "image_url": image_url,
    }
