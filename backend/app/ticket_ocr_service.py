"""
app/ticket_ocr_service.py

Servei OCR per a tickets de compra (RF-ING-02).

Responsabilitats:
  - Validar la imatge rebuda (MIME type, mida).
  - Executar PaddleOCR sobre la imatge en memòria.
  - Extreure línies de text rellevants.
  - Parsear productes (nom, unitats, preu) del text OCR.
  - Enriquir productes via Open Food Facts (reutilitza barcode_service.py).
  - Retornar llista de OcrDetectedProduct sense persistir res a la BD.

NO fa:
  - Persistència a BD (responsabilitat de ticket_routes.py + confirm).
  - Autenticació (responsabilitat del router).
  - Lògica de negoci d'inventari.
"""

from __future__ import annotations

import io
import logging
import os
import re
import time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from itertools import combinations
from typing import Optional

import requests

from app.barcode_service import HEADERS as OFF_HEADERS
from app.category_mapper import map_off_to_internal_category
from app.product_schemas import CATEGORY_LABELS_CA

logger = logging.getLogger(__name__)

# ── Constants de validació ────────────────────────────────────────────────────

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png"}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

# ── Constants parsing ─────────────────────────────────────────────────────────

_PRICE_RE = re.compile(r"^\d+[.,]\d{2}$")
_UNIT_NAME_RE = re.compile(r"^(\d+)?\s*(.+)$")
_JUNK_DIGITS_RE = re.compile(r"\d+[Xx]?\d*")
_MULTI_SPACE_RE = re.compile(r"\s+")

_SKIP_TOKENS = frozenset({
    "descripcion", "descripcio", "total", "subtotal", "iva",
    "ticket", "factura", "importe", "import", "cantidad", "quantitat",
    "unidad", "unitat", "precio", "preu", "nif", "cif", "fecha",
    "data", "gracias", "gracies", "obrigado",
})

# ── Constants OFF ─────────────────────────────────────────────────────────────

_OFF_SEARCH_URL = "https://es.openfoodfacts.net/cgi/search.pl"
_OFF_SEARCH_TIMEOUT = 8.0
_OFF_SEARCH_PAGE_SIZE = 3
_OFF_SEARCH_DELAY = 0.4


# ── Validació d'imatge ────────────────────────────────────────────────────────


@dataclass
class ImageValidationError(Exception):
    code: str
    message: str
    status_code: int = 400


def validate_image(content_type: str | None, size: int) -> None:
    if content_type not in ALLOWED_MIME_TYPES:
        raise ImageValidationError(
            code="UNSUPPORTED_IMAGE_FORMAT",
            message="Format de imatge no suportat. Utilitza JPEG o PNG.",
            status_code=415,
        )
    if size > MAX_FILE_SIZE_BYTES:
        raise ImageValidationError(
            code="IMAGE_TOO_LARGE",
            message="La imatge supera el límit de 5 MB.",
            status_code=413,
        )


# ── Helpers de ruta de models ─────────────────────────────────────────────────


def _models_base_dir() -> str:
    """Directori de models OCR, fora de ~/.paddleocr i amb ruta ASCII a Windows."""
    env_dir = os.getenv("PADDLEOCR_MODEL_DIR")
    if env_dir:
        return env_dir

    if os.name == "nt":
        public_dir = os.getenv("PUBLIC", r"C:\Users\Public")
        return os.path.join(public_dir, "FoodSyncPaddleOCR")

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(project_root, ".paddleocr_models")


def _resolve_model_dir(base: str) -> str:
    """
    PaddleOCR descomprimeix el tar dins de `base` en una subcarpeta,
    p. ex.:  det/en_PP-OCRv3_det_infer/inference.pdmodel

    Lògica:
      1. Si `base` ja conté inference.pdmodel → retorna `base`.
      2. Si existeix una subcarpeta amb inference.pdmodel → la retorna.
      3. Si no hi ha res (primera execució) → retorna `base` i PaddleOCR
         descarregarà i extraurà els models automàticament.

    Així funciona tant en la primera crida com en les posteriors sense
    cap canvi de codi.
    """
    os.makedirs(base, exist_ok=True)

    # Cas 1: model directament a base
    if os.path.isfile(os.path.join(base, "inference.pdmodel")):
        return base

    # Cas 2: buscar subcarpeta extreta
    try:
        entries = os.listdir(base)
    except OSError:
        return base

    for entry in entries:
        candidate = os.path.join(base, entry)
        if os.path.isdir(candidate) and os.path.isfile(
            os.path.join(candidate, "inference.pdmodel")
        ):
            logger.debug("[OcrEngine] Model dir resolt: %s", candidate)
            return candidate

    # Cas 3: carpeta buida → PaddleOCR descarregarà
    return base


# ── Motor OCR (singleton) ─────────────────────────────────────────────────────


class OcrEngine:
    """
    Wrapper sobre PaddleOCR.

    - Singleton: el model es carrega una sola vegada per procés.
    - Models fora de ~/.paddleocr; a Windows usa una ruta ASCII per evitar
      problemes amb PaddlePaddle i noms d'usuari amb accents.
    - extract_lines() propaga excepcions; el router decideix com tractar-les.
    """

    _instance: "OcrEngine | None" = None

    def __init__(self) -> None:
        try:
            import numpy as np  # noqa: F401
            from PIL import Image  # noqa: F401
            from paddleocr import PaddleOCR

            base = _models_base_dir()
            det_dir = _resolve_model_dir(os.path.join(base, "det"))
            rec_dir = _resolve_model_dir(os.path.join(base, "rec"))
            cls_dir = _resolve_model_dir(os.path.join(base, "cls"))

            logger.info(
                "[OcrEngine] Inicialitzant PaddleOCR\n  det=%s\n  rec=%s\n  cls=%s",
                det_dir, rec_dir, cls_dir,
            )
            
            self._ocr = PaddleOCR(
                use_angle_cls=True,
                lang="en",
                use_gpu=False,
                show_log=False,
                det_model_dir=det_dir,
                rec_model_dir=rec_dir,
                cls_model_dir=cls_dir,
            )
            logger.info("[OcrEngine] PaddleOCR llest.")

        except ImportError as exc:
            raise RuntimeError(
                "Dependències OCR no instal·lades. "
                "Executa: pip install paddlepaddle paddleocr pillow numpy"
            ) from exc
        except Exception as exc:
            raise RuntimeError(f"Error inicialitzant PaddleOCR: {exc}") from exc

    @classmethod
    def get(cls) -> "OcrEngine":
        """Singleton: només assigna _instance si __init__ té èxit."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @staticmethod
    def _to_numpy(image_bytes: bytes):
        """
        Bytes → numpy RGB array.
        PaddleOCR NO accepta bytes crus; necessita ndarray o ruta de fitxer.
        """
        import numpy as np
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        return np.array(img)

    def extract_lines(self, image_bytes: bytes) -> list[str]:
        """
        Executa OCR i retorna línies de text.
        Propaga excepcions (no les silencia) per a tractament al router.
        """
        img_array = self._to_numpy(image_bytes)
        resultado = self._ocr.ocr(img_array, cls=True)

        if not resultado or resultado[0] is None:
            return []

        lines: list[str] = []
        for bloque in resultado:
            if not bloque:
                continue
            for linea in bloque:
                if not linea or len(linea) < 2:
                    continue
                text_info = linea[1]
                if not text_info or not text_info[0]:
                    continue
                text = str(text_info[0]).strip()
                if text:
                    lines.append(text)
        return lines


# ── Parsing de línies del ticket ──────────────────────────────────────────────


@dataclass
class RawTicketProduct:
    nom: str
    unitats: int = 1
    preu: Optional[Decimal] = None


def _clean_product_name(name: str) -> str:
    cleaned = _JUNK_DIGITS_RE.sub("", name)
    return _MULTI_SPACE_RE.sub(" ", cleaned).strip()


def _is_skip_line(line: str) -> bool:
    normalized = line.strip().lower()
    return any(token in normalized for token in _SKIP_TOKENS)


def _find_section_start(lines: list[str]) -> int:
    for i, line in enumerate(lines):
        if "descripcion" in line.lower() or "descripcio" in line.lower():
            return i + 1
    return 0


def parse_ticket_lines(lines: list[str]) -> list[RawTicketProduct]:
    """
    Funció pura: parseja línies OCR → llista de RawTicketProduct.
    Adaptada d'ocr_funciona.py, ara retorna dataclasses.
    """
    if not lines:
        return []

    start = _find_section_start(lines)
    results: list[RawTicketProduct] = []
    price_temp: Optional[Decimal] = None
    name_temp: Optional[str] = None
    units_temp: int = 1

    def _flush(name: str, units: int, price: Optional[Decimal]) -> None:
        clean = _clean_product_name(name)
        if clean:
            results.append(RawTicketProduct(nom=clean, unitats=units, preu=price))

    for raw_line in lines[start:]:
        line = raw_line.strip().replace(",", ".")
        if not line or _is_skip_line(line):
            continue

        if _PRICE_RE.match(line):
            try:
                price_temp = Decimal(line)
            except InvalidOperation:
                price_temp = None
            if name_temp:
                _flush(name_temp, units_temp, price_temp)
                name_temp = None
                units_temp = 1
                price_temp = None
            continue

        m = _UNIT_NAME_RE.match(line)
        if m:
            units_temp = int(m.group(1)) if m.group(1) else 1
            name_temp = (m.group(2) or "").strip()
            if price_temp is not None:
                _flush(name_temp, units_temp, price_temp)
                name_temp = None
                units_temp = 1
                price_temp = None

    if name_temp:
        _flush(name_temp, units_temp, price_temp)

    return results


# ── Enriquiment OFF ───────────────────────────────────────────────────────────


def _search_off_by_name(name: str) -> list[dict]:
    params = {
        "search_terms": name,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": _OFF_SEARCH_PAGE_SIZE,
        "fields": (
            "product_name,brands,nutrition_grades,categories_tags,"
            "quantity,image_front_url,image_url"
        ),
    }
    try:
        resp = requests.get(
            _OFF_SEARCH_URL, params=params,
            headers=OFF_HEADERS, timeout=_OFF_SEARCH_TIMEOUT,
        )
        if resp.status_code != 200:
            return []
        return resp.json().get("products", []) or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("[OFF search] Error: %s", exc)
        return []


def _name_combinations(name: str) -> list[str]:
    words = name.split()
    seen: set[frozenset] = set()
    result: list[str] = []
    for length in range(len(words) - 1, 0, -1):
        for combo in combinations(words, length):
            key = frozenset(combo)
            if key not in seen:
                seen.add(key)
                result.append(" ".join(combo))
    return result


def enrich_product_off(raw: RawTicketProduct) -> dict:
    """Enriqueix RawTicketProduct amb dades OFF. Retorna dict parcial."""
    off_products = _search_off_by_name(raw.nom)
    time.sleep(_OFF_SEARCH_DELAY)

    if not off_products:
        for term in _name_combinations(raw.nom):
            off_products = _search_off_by_name(term)
            time.sleep(_OFF_SEARCH_DELAY)
            if off_products:
                break

    if not off_products:
        return {}

    best = off_products[0]
    enriched: dict = {}

    off_name = (best.get("product_name") or "").strip()
    if off_name:
        enriched["nom_off"] = off_name

    enriched["marca"] = (best.get("brands") or "").strip() or None

    ns = (best.get("nutrition_grades") or "").strip().upper()
    enriched["nutriscore"] = ns or None

    enriched["imatge_url"] = (
        best.get("image_front_url") or best.get("image_url") or None
    )

    cat_tags = best.get("categories_tags") or []
    category_enum = map_off_to_internal_category(cat_tags)
    enriched["categoria"] = category_enum
    enriched["categoria_label"] = CATEGORY_LABELS_CA.get(category_enum)
    enriched["quantitat_envas"] = (best.get("quantity") or "").strip() or None

    return enriched


# ── Punt d'entrada ────────────────────────────────────────────────────────────


def process_ticket_image(image_bytes: bytes) -> list[dict]:
    """
    Pipeline: OCR → parsing → enriquiment OFF.
    Propaga RuntimeError si el motor falla.
    Retorna llista buida si no es detecten productes (no és error).
    """
    engine = OcrEngine.get()
    lines = engine.extract_lines(image_bytes)

    if not lines:
        logger.info("[ticket_ocr] OCR: cap línia detectada.")
        return []

    raw_products = parse_ticket_lines(lines)
    if not raw_products:
        logger.info("[ticket_ocr] Parsing: cap producte extret.")
        return []

    result = []
    for raw in raw_products:
        enriched = enrich_product_off(raw)
        nom_final = enriched.pop("nom_off", None) or raw.nom
        item: dict = {"nom": nom_final, "quantitat": raw.unitats, "preu": raw.preu}
        item.update(enriched)
        result.append(item)

    return result
