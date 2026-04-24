from app.category_mapper import map_off_to_internal_category
import base64
import re

import requests

OFF_BASE_URL = "https://es.openfoodfacts.net"
OFF_API_URL = OFF_BASE_URL + "/api/v2/product/{barcode}.json"
OFF_TIMEOUT = 8.0

HEADERS = {
    "Authorization": "Basic " + base64.b64encode(b"off:off").decode("utf-8"),
    "User-Agent": "FoodSyncTicket/1.0 (contacto@tuapp.com)",
}

BARCODE_REGEX = re.compile(r"^\d{8,14}$")


def is_valid_barcode(barcode: str) -> bool:
    return bool(BARCODE_REGEX.match(barcode.strip()))


def _clean_text(value):
    if not value:
        return None
    value = str(value).strip()
    return value or None


def _extract_category(product_data: dict) -> str:
    raw_tags = product_data.get("categories_tags") or product_data.get("categories", "")
    internal_cat = map_off_to_internal_category(raw_tags)
    return internal_cat.value

def _extract_ingredients(product_data: dict) -> str | None:
    return (
        _clean_text(product_data.get("ingredients_text_es"))
        or _clean_text(product_data.get("ingredients_text"))
        or _clean_text(product_data.get("ingredients_text_en"))
        or _clean_text(product_data.get("ingredients_text_ca"))
    )

ALLERGEN_TAGS_ES = {
    "milk": "leche",
    "nuts": "frutos secos",
    "soybeans": "soja",
    "soy": "soja",
    "gluten": "gluten",
    "eggs": "huevos",
    "egg": "huevo",
    "peanuts": "cacahuetes",
    "peanut": "cacahuete",
    "sesame-seeds": "sésamo",
    "sesame": "sésamo",
    "mustard": "mostaza",
    "celery": "apio",
    "fish": "pescado",
    "crustaceans": "crustáceos",
    "molluscs": "moluscos",
    "sulphur-dioxide-and-sulphites": "sulfitos",
    "sulfites": "sulfitos",
    "lupin": "altramuces",
}

def _extract_allergens(product_data: dict) -> str | None:
    tags = (
        product_data.get("allergens_tags")
        or product_data.get("allergens_hierarchy")
        or []
    )

    if isinstance(tags, list) and tags:
        result = []
        seen = set()

        for tag in tags:
            tag = re.sub(r"^[a-z]{2,3}:", "", str(tag)).strip().lower()
            if not tag:
                continue

            label = ALLERGEN_TAGS_ES.get(tag)
            if not label:
                label = tag.replace("-", " ")

            if label not in seen:
                seen.add(label)
                result.append(label)

        if result:
            return ", ".join(result)

    # fallback: si no hi ha tags, mirar el camp textual
    raw_allergens = _clean_text(product_data.get("allergens"))
    if raw_allergens:
        parts = [p.strip() for p in raw_allergens.split(",") if p.strip()]
        result = []
        seen = set()

        for part in parts:
            part = re.sub(r"^[a-z]{2,3}:", "", part).strip().lower()
            label = ALLERGEN_TAGS_ES.get(part, part.replace("-", " "))
            if label not in seen:
                seen.add(label)
                result.append(label)

        if result:
            return ", ".join(result)

    return None


def _extract_nutriments_per_100g(product_data: dict) -> dict | None:
    nutriments = product_data.get("nutriments", {}) or {}

    result = {
        "energy_kcal": nutriments.get("energy-kcal_100g"),
        "fat": nutriments.get("fat_100g"),
        "saturated_fat": nutriments.get("saturated-fat_100g"),
        "carbohydrates": nutriments.get("carbohydrates_100g"),
        "sugars": nutriments.get("sugars_100g"),
        "fiber": nutriments.get("fiber_100g"),
        "proteins": nutriments.get("proteins_100g"),
        "salt": nutriments.get("salt_100g"),
        "sodium": nutriments.get("sodium_100g"),
    }

    if all(v is None for v in result.values()):
        return None

    return result


def _fetch_off_product(barcode: str) -> dict | None:
    url = OFF_API_URL.format(barcode=barcode.strip())
    print(f"[OFF] GET {url}")

    try:
        response = requests.get(url, headers=HEADERS, timeout=OFF_TIMEOUT)
        print(f"[OFF] status_code={response.status_code}")
        print(f"[OFF] response_text_start={response.text[:200]}")
    except requests.RequestException as exc:
        print(f"[OFF] request_exception={repr(exc)}")
        return None

    if response.status_code != 200:
        return None

    try:
        data = response.json()
        print(f"[OFF] status_field={data.get('status')}")
    except Exception as exc:
        print(f"[OFF] json_exception={repr(exc)}")
        return None

    if data.get("status") != 1:
        return {"found": False, "barcode": barcode}

    return {
        "found": True,
        "barcode": barcode,
        "product_data": data.get("product", {}) or {},
    }

def lookup_barcode(barcode: str) -> dict | None:
    """
    Lookup ràpid per autocompletar.
    """
    result = _fetch_off_product(barcode)
    if result is None or not result.get("found"):
        return result

    product_data = result["product_data"]

    name = (
        product_data.get("product_name")
        or product_data.get("product_name_en")
        or product_data.get("product_name_es")
        or None
    )
    image_url = product_data.get("image_front_url") or product_data.get("image_url") or None

    return {
        "found": True,
        "barcode": barcode,
        "name": _clean_text(name),
        "category": _extract_category(product_data),
        "image_url": _clean_text(image_url),
    }


def lookup_barcode_enriched(barcode: str) -> dict | None:
    """
    Lookup complet per guardar snapshot OFF al catàleg local.
    """
    result = _fetch_off_product(barcode)
    if result is None or not result.get("found"):
        return result

    product_data = result["product_data"]

    name = (
        product_data.get("product_name")
        or product_data.get("product_name_en")
        or product_data.get("product_name_es")
        or None
    )

    nutriscore = _clean_text(product_data.get("nutriscore_grade"))
    if nutriscore:
        nutriscore = nutriscore.upper()

    image_url = product_data.get("image_front_url") or product_data.get("image_url") or None

    return {
        "found": True,
        "barcode": barcode,
        "name": _clean_text(name),
        "brand": _clean_text(product_data.get("brands")),
        "category": _extract_category(product_data),
        "package_quantity_label": _clean_text(product_data.get("quantity")),
        "ingredients_text": _extract_ingredients(product_data),
        "allergens_text": _extract_allergens(product_data),
        "nutriscore_grade": nutriscore,
        "nutriments_per_100g": _extract_nutriments_per_100g(product_data),
        "image_url": _clean_text(image_url),
    }