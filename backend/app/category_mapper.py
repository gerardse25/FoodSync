import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from app.product_schemas import ProductCategory

# -----------------------------------------------------------------------------
# Estratègia millorada:
#
# 1) Acceptar tant una llista/string de tags com el product_data complet d'OFF.
# 2) Prioritzar camps més específics:
#    - ciqual_food_name_tags
#    - compared_to_category
#    - categories_tags
#    - categories_hierarchy
# 3) Usar food_groups_tags només com a fallback, perquè és més genèric.
# 4) Crear candidats amb confiança i escollir el millor.
# 5) Evitar que tags massa genèrics guanyin davant tags més concrets.
#
# Exemple Nutella:
# - food_groups_tags: sugary-snacks / sweets  -> massa genèric
# - categories_tags: cocoa-and-hazelnuts-spreads -> molt més precís
# - ciqual_food_name_tags: chocolate-spread-with-hazelnuts -> molt precís
# Resultat recomanat: ProductCategory.NUT_BUTTER
# -----------------------------------------------------------------------------


LANG_PREFIX_RE = re.compile(r"^[a-z]{2,3}:")
HTML_TAG_RE = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class CategoryMatch:
    category: ProductCategory
    confidence: float
    matched_tag: str
    source: str
    reason: str


def _strip_lang_prefix(value: str) -> str:
    return LANG_PREFIX_RE.sub("", value.strip().lower())


def _remove_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _slugify(value: str) -> str:
    """
    Normalitza valors d'Open Food Facts per comparar:
    - treu prefixos de llengua: en:, es:, fr:
    - lowercase
    - elimina accents
    - converteix espais, _, / en guions
    - elimina caràcters estranys
    """
    value = HTML_TAG_RE.sub(" ", str(value))
    value = _strip_lang_prefix(value)
    value = _remove_accents(value)
    value = value.replace("_", "-").replace("/", "-")
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"[^a-z0-9\-]", "", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value


def _normalize_off_tags(off_tags: list[str] | str | None) -> list[str]:
    if not off_tags:
        return []

    if isinstance(off_tags, list):
        raw_tags = off_tags
    else:
        raw_tags = str(off_tags).split(",")

    normalized = []
    for tag in raw_tags:
        cleaned = _slugify(tag)
        if cleaned:
            normalized.append(cleaned)

    seen = set()
    result = []
    for tag in normalized:
        if tag not in seen:
            seen.add(tag)
            result.append(tag)

    return result


def _as_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item]
    return [str(value)]


def extract_category_signals(product_data_or_tags: dict | list[str] | str) -> list[tuple[str, str]]:
    """
    Retorna tuples (source, tag_normalitzat).

    Si rep un dict complet d'OFF, aprofita els camps més fiables.
    Si rep list/str, manté compatibilitat amb el codi actual.
    """
    if not isinstance(product_data_or_tags, dict):
        return [("legacy_tags", tag) for tag in _normalize_off_tags(product_data_or_tags)]

    product_data = product_data_or_tags
    signals: list[tuple[str, str]] = []

    # 1) Camps més específics i útils per a mapping de categoria.
    prioritized_sources = [
        "ciqual_food_name_tags",
        "compared_to_category",
        "categories_tags",
        "categories_hierarchy",
    ]

    # 2) Camps útils però més genèrics.
    fallback_sources = [
        "food_groups_tags",
        "pnns_groups_2_tags",
        "pnns_groups_1_tags",
    ]

    # 3) Text lliure: només fallback.
    text_sources = [
        "categories",
        "generic_name",
        "product_name",
        "_keywords",
    ]

    for source in prioritized_sources:
        for raw in _as_list(product_data.get(source)):
            for tag in _normalize_off_tags(raw):
                signals.append((source, tag))

    for source in fallback_sources:
        for raw in _as_list(product_data.get(source)):
            for tag in _normalize_off_tags(raw):
                signals.append((source, tag))

    for source in text_sources:
        for raw in _as_list(product_data.get(source)):
            for tag in _normalize_off_tags(raw):
                signals.append((source, tag))

    # Treure duplicats mantenint ordre i font.
    seen = set()
    result = []
    for source, tag in signals:
        key = (source, tag)
        if key not in seen:
            seen.add(key)
            result.append((source, tag))

    return result


# -----------------------------------------------------------------------------
# 1) Match exacte: tags OFF o variants molt concretes
# -----------------------------------------------------------------------------

EXACT_TAG_MAP: dict[str, ProductCategory] = {
    # CASOS ESPECÍFICS DE CREMES / UNTABLES
    "chocolate-spread-with-hazelnuts": ProductCategory.NUT_BUTTER,
    "cocoa-and-hazelnuts-spreads": ProductCategory.NUT_BUTTER,
    "hazelnut-spreads": ProductCategory.NUT_BUTTER,
    "chocolate-spreads": ProductCategory.NUT_BUTTER,
    "nut-butters": ProductCategory.NUT_BUTTER,
    "peanut-butters": ProductCategory.NUT_BUTTER,
    "almond-butters": ProductCategory.NUT_BUTTER,

    # BEGUDES
    "waters": ProductCategory.WATER_AND_FLAVORED_WATER,
    "water": ProductCategory.WATER_AND_FLAVORED_WATER,
    "flavored-waters": ProductCategory.WATER_AND_FLAVORED_WATER,
    "fruit-juices": ProductCategory.FRUIT_JUICES,
    "juice": ProductCategory.FRUIT_JUICES,
    "juices": ProductCategory.FRUIT_JUICES,
    "fruit-nectars": ProductCategory.FRUIT_NECTARS,
    "nectar": ProductCategory.FRUIT_NECTARS,
    "sodas": ProductCategory.SWEETENED_BEVERAGES,
    "soft-drinks": ProductCategory.SWEETENED_BEVERAGES,
    "colas": ProductCategory.SWEETENED_BEVERAGES,
    "energy-drinks": ProductCategory.SWEETENED_BEVERAGES,
    "sugar-free-soft-drinks": ProductCategory.ARTIFICIALLY_SWEETENED_BEVERAGES,
    "diet-soft-drinks": ProductCategory.ARTIFICIALLY_SWEETENED_BEVERAGES,
    "teas": ProductCategory.COFFEE_TEA_HERBAL_TEA,
    "tea": ProductCategory.COFFEE_TEA_HERBAL_TEA,
    "coffee": ProductCategory.COFFEE_TEA_HERBAL_TEA,
    "coffees": ProductCategory.COFFEE_TEA_HERBAL_TEA,
    "herbal-teas": ProductCategory.COFFEE_TEA_HERBAL_TEA,
    "infusions": ProductCategory.COFFEE_TEA_HERBAL_TEA,
    "plant-based-drinks": ProductCategory.PLANT_BASED_DRINKS,
    "soy-milks": ProductCategory.PLANT_BASED_DRINKS,
    "almond-milks": ProductCategory.PLANT_BASED_DRINKS,

    # ALCOHOL
    "beers": ProductCategory.BEER,
    "beer": ProductCategory.BEER,
    "wines": ProductCategory.FERMENTED_ALCOHOLIC_DRINKS,
    "wine": ProductCategory.FERMENTED_ALCOHOLIC_DRINKS,
    "ciders": ProductCategory.FERMENTED_ALCOHOLIC_DRINKS,
    "spirits": ProductCategory.SPIRITS,
    "liqueurs": ProductCategory.SPIRITS,
    "cocktails": ProductCategory.PREMIXED_ALCOHOLIC_DRINKS,

    # LACTIS
    "milk": ProductCategory.MILK,
    "milks": ProductCategory.MILK,
    "yogurts": ProductCategory.YOGURT_AND_FERMENTED_MILK,
    "yoghurts": ProductCategory.YOGURT_AND_FERMENTED_MILK,
    "kefirs": ProductCategory.YOGURT_AND_FERMENTED_MILK,
    "dairy-desserts": ProductCategory.DAIRY_DESSERTS,
    "ice-creams": ProductCategory.ICE_CREAM,
    "sorbets": ProductCategory.ICE_CREAM,
    "fresh-cheeses": ProductCategory.FRESH_CHEESE,
    "soft-cheeses": ProductCategory.SOFT_CHEESE,
    "blue-cheeses": ProductCategory.BLUE_CHEESE,
    "processed-cheeses": ProductCategory.PROCESSED_CHEESE,
    "hard-cheeses": ProductCategory.HARD_CHEESE,
    "cheeses": ProductCategory.HARD_CHEESE,

    # CARN / PEIX / OUS
    "eggs": ProductCategory.EGGS,
    "poultries": ProductCategory.POULTRY,
    "poultry": ProductCategory.POULTRY,
    "chickens": ProductCategory.POULTRY,
    "turkeys": ProductCategory.POULTRY,
    "processed-meats": ProductCategory.PROCESSED_MEAT,
    "sausages": ProductCategory.PROCESSED_MEAT,
    "salamis": ProductCategory.PROCESSED_MEAT,
    "hams": ProductCategory.PROCESSED_MEAT,
    "cold-cuts": ProductCategory.PROCESSED_MEAT,
    "red-meats": ProductCategory.RED_MEAT,
    "offals": ProductCategory.OFFALS,
    "lean-fishes": ProductCategory.LEAN_FISH,
    "white-fishes": ProductCategory.LEAN_FISH,
    "fatty-fishes": ProductCategory.FATTY_FISH,
    "salmons": ProductCategory.FATTY_FISH,
    "tunas": ProductCategory.FATTY_FISH,
    "smoked-fishes": ProductCategory.SMOKED_FISH,
    "seafood": ProductCategory.SEAFOOD,
    "crustaceans": ProductCategory.SEAFOOD,
    "molluscs": ProductCategory.SEAFOOD,

    # FRUITA / VERDURA / LLEGUMS
    "fresh-fruits": ProductCategory.FRESH_FRUIT,
    "fruits": ProductCategory.FRESH_FRUIT,
    "dried-fruits": ProductCategory.DRIED_FRUIT,
    "fresh-vegetables": ProductCategory.FRESH_VEGETABLES,
    "vegetables": ProductCategory.FRESH_VEGETABLES,
    "legumes": ProductCategory.LEGUMES,
    "beans": ProductCategory.LEGUMES,
    "lentils": ProductCategory.LEGUMES,
    "fresh-soups": ProductCategory.FRESH_SOUPS,
    "soups": ProductCategory.FRESH_SOUPS,
    "dehydrated-soups": ProductCategory.DEHYDRATED_SOUPS,

    # CEREALS / FARINACIS
    "breakfast-cereals": ProductCategory.BREAKFAST_CEREALS,
    "mueslis": ProductCategory.BREAKFAST_CEREALS,
    "cereal-bars": ProductCategory.BREAKFAST_CEREALS,
    "rices": ProductCategory.RICE,
    "rice": ProductCategory.RICE,
    "pastas": ProductCategory.PASTA,
    "pasta": ProductCategory.PASTA,
    "noodles": ProductCategory.PASTA,
    "potatoes": ProductCategory.POTATOES,
    "breads": ProductCategory.BREAD,
    "bread": ProductCategory.BREAD,

    # DOLÇOS / SNACKS
    "dark-chocolates": ProductCategory.DARK_CHOCOLATE,
    "milk-chocolates": ProductCategory.MILK_CHOCOLATE,
    "white-chocolates": ProductCategory.WHITE_CHOCOLATE,
    "candies": ProductCategory.SWEETS_AND_CANDIES,
    "sweets": ProductCategory.SWEETS_AND_CANDIES,
    "biscuits": ProductCategory.BISCUITS_AND_CAKES,
    "cakes": ProductCategory.BISCUITS_AND_CAKES,
    "pastries": ProductCategory.PASTRIES,
    "viennoiseries": ProductCategory.PASTRIES,
    "unsalted-nuts": ProductCategory.UNSALTED_NUTS,
    "salted-nuts": ProductCategory.SALTED_NUTS,
    "salty-snacks": ProductCategory.SALTY_SNACKS,
    "chips": ProductCategory.SALTY_SNACKS,
    "crisps": ProductCategory.SALTY_SNACKS,

    # GREIXOS / SALSES
    "animal-fats": ProductCategory.ANIMAL_FATS,
    "lards": ProductCategory.ANIMAL_FATS,
    "vegetable-oils": ProductCategory.VEGETABLE_OILS,
    "olive-oils": ProductCategory.VEGETABLE_OILS,
    "margarines": ProductCategory.MARGARINES,
    "dressings": ProductCategory.DRESSINGS,
    "vinaigrettes": ProductCategory.DRESSINGS,
    "sauces": ProductCategory.SAUCES,
    "ketchups": ProductCategory.SAUCES,
    "mayonnaises": ProductCategory.SAUCES,

    # PREPARATS
    "pizzas": ProductCategory.PIZZA_QUICHE,
    "quiches": ProductCategory.PIZZA_QUICHE,
    "sandwiches": ProductCategory.SANDWICHES,
    "ready-meals": ProductCategory.READY_MEALS,
    "prepared-dishes": ProductCategory.READY_MEALS,

    # INFANTIL
    "baby-foods": ProductCategory.BABY_FOODS,
    "baby-milks": ProductCategory.BABY_MILKS,
    "baby-drinks": ProductCategory.BABY_DRINKS,
    "baby-desserts": ProductCategory.BABY_DESSERTS_AND_SNACKS,
    "baby-snacks": ProductCategory.BABY_DESSERTS_AND_SNACKS,
}


VARIANT_KEYWORDS: list[tuple[str, ProductCategory]] = [
    # Cremes / untables
    ("cocoa-and-hazelnut", ProductCategory.NUT_BUTTER),
    ("cocoa-and-hazelnuts", ProductCategory.NUT_BUTTER),
    ("chocolate-spread", ProductCategory.NUT_BUTTER),
    ("hazelnut-spread", ProductCategory.NUT_BUTTER),
    ("nut-spread", ProductCategory.NUT_BUTTER),
    ("peanut-butter", ProductCategory.NUT_BUTTER),
    ("almond-butter", ProductCategory.NUT_BUTTER),

    # Altres variants específiques
    ("corn-flakes", ProductCategory.BREAKFAST_CEREALS),
    ("breakfast-cereal", ProductCategory.BREAKFAST_CEREALS),
    ("muesli", ProductCategory.BREAKFAST_CEREALS),
    ("dark-chocolate", ProductCategory.DARK_CHOCOLATE),
    ("milk-chocolate", ProductCategory.MILK_CHOCOLATE),
    ("white-chocolate", ProductCategory.WHITE_CHOCOLATE),
    ("sugar-free-soft-drink", ProductCategory.ARTIFICIALLY_SWEETENED_BEVERAGES),
    ("diet-soda", ProductCategory.ARTIFICIALLY_SWEETENED_BEVERAGES),
    ("energy-drink", ProductCategory.SWEETENED_BEVERAGES),
    ("soft-drink", ProductCategory.SWEETENED_BEVERAGES),
    ("fresh-cheese", ProductCategory.FRESH_CHEESE),
    ("soft-cheese", ProductCategory.SOFT_CHEESE),
    ("blue-cheese", ProductCategory.BLUE_CHEESE),
    ("processed-cheese", ProductCategory.PROCESSED_CHEESE),
    ("hard-cheese", ProductCategory.HARD_CHEESE),
    ("fatty-fish", ProductCategory.FATTY_FISH),
    ("lean-fish", ProductCategory.LEAN_FISH),
    ("white-fish", ProductCategory.LEAN_FISH),
    ("smoked-fish", ProductCategory.SMOKED_FISH),
    ("plant-based-beverage", ProductCategory.PLANT_BASED_DRINKS),
    ("soy-milk", ProductCategory.PLANT_BASED_DRINKS),
    ("almond-milk", ProductCategory.PLANT_BASED_DRINKS),
    ("fruit-juice", ProductCategory.FRUIT_JUICES),
    ("fruit-nectar", ProductCategory.FRUIT_NECTARS),
    ("herbal-tea", ProductCategory.COFFEE_TEA_HERBAL_TEA),
    ("ice-cream", ProductCategory.ICE_CREAM),
    ("dairy-dessert", ProductCategory.DAIRY_DESSERTS),
    ("dehydrated-soup", ProductCategory.DEHYDRATED_SOUPS),
    ("fresh-soup", ProductCategory.FRESH_SOUPS),
    ("prepared-dish", ProductCategory.READY_MEALS),
    ("ready-meal", ProductCategory.READY_MEALS),
]


SAFE_KEYWORDS: list[tuple[str, ProductCategory]] = [
    ("yogurt", ProductCategory.YOGURT_AND_FERMENTED_MILK),
    ("yoghurt", ProductCategory.YOGURT_AND_FERMENTED_MILK),
    ("kefir", ProductCategory.YOGURT_AND_FERMENTED_MILK),
    ("sausage", ProductCategory.PROCESSED_MEAT),
    ("salami", ProductCategory.PROCESSED_MEAT),
    ("ham", ProductCategory.PROCESSED_MEAT),
    ("salmon", ProductCategory.FATTY_FISH),
    ("tuna", ProductCategory.FATTY_FISH),
    ("lentil", ProductCategory.LEGUMES),
    ("bean", ProductCategory.LEGUMES),
    ("bread", ProductCategory.BREAD),
    ("pasta", ProductCategory.PASTA),
    ("noodle", ProductCategory.PASTA),
    ("rice", ProductCategory.RICE),
    ("potato", ProductCategory.POTATOES),
    ("pizza", ProductCategory.PIZZA_QUICHE),
    ("quiche", ProductCategory.PIZZA_QUICHE),
    ("sandwich", ProductCategory.SANDWICHES),
    ("coffee", ProductCategory.COFFEE_TEA_HERBAL_TEA),
    ("tea", ProductCategory.COFFEE_TEA_HERBAL_TEA),
    ("infusion", ProductCategory.COFFEE_TEA_HERBAL_TEA),
    ("beer", ProductCategory.BEER),
    ("wine", ProductCategory.FERMENTED_ALCOHOLIC_DRINKS),
    ("cider", ProductCategory.FERMENTED_ALCOHOLIC_DRINKS),
]


# Tags genèrics: poden ser correctes, però no haurien de guanyar
# davant de tags més concrets.
BROAD_TAGS = {
    "snacks",
    "breakfasts",
    "spreads",
    "sweet-spreads",
    "sweets",
    "sugary-snacks",
    "festive-foods",
    "christmas-foods-and-drinks",
    "fruits",
    "vegetables",
    "cheeses",
    "soups",
    "bread",
    "pasta",
    "rice",
    "potatoes",
    "water",
    "waters",
}


SOURCE_WEIGHT = {
    "ciqual_food_name_tags": 0.18,
    "compared_to_category": 0.16,
    "categories_tags": 0.14,
    "categories_hierarchy": 0.12,
    "food_groups_tags": 0.04,
    "pnns_groups_2_tags": 0.03,
    "pnns_groups_1_tags": 0.02,
    "categories": 0.00,
    "generic_name": 0.00,
    "product_name": 0.00,
    "_keywords": -0.05,
    "legacy_tags": 0.00,
}


def _source_weight(source: str) -> float:
    return SOURCE_WEIGHT.get(source, 0.0)


def _is_broad_tag(tag: str) -> bool:
    return tag in BROAD_TAGS


def _build_match_candidates(signals: list[tuple[str, str]]) -> list[CategoryMatch]:
    candidates: list[CategoryMatch] = []

    for source, tag in signals:
        if tag in EXACT_TAG_MAP:
            confidence = 0.95 + _source_weight(source)

            if _is_broad_tag(tag):
                confidence -= 0.25

            candidates.append(
                CategoryMatch(
                    category=EXACT_TAG_MAP[tag],
                    confidence=confidence,
                    matched_tag=tag,
                    source=source,
                    reason="exact",
                )
            )

    for source, tag in signals:
        for keyword, category in VARIANT_KEYWORDS:
            if keyword in tag:
                confidence = 0.82 + _source_weight(source)

                candidates.append(
                    CategoryMatch(
                        category=category,
                        confidence=confidence,
                        matched_tag=tag,
                        source=source,
                        reason=f"variant:{keyword}",
                    )
                )

    for source, tag in signals:
        for keyword, category in SAFE_KEYWORDS:
            if keyword in tag:
                confidence = 0.62 + _source_weight(source)

                candidates.append(
                    CategoryMatch(
                        category=category,
                        confidence=confidence,
                        matched_tag=tag,
                        source=source,
                        reason=f"keyword:{keyword}",
                    )
                )

    return candidates


def map_off_to_internal_category_detailed(
    product_data_or_tags: dict | list[str] | str,
) -> CategoryMatch:
    signals = extract_category_signals(product_data_or_tags)

    if not signals:
        return CategoryMatch(
            category=ProductCategory.OTHER,
            confidence=0.0,
            matched_tag="",
            source="none",
            reason="no_tags",
        )

    candidates = _build_match_candidates(signals)

    if not candidates:
        return CategoryMatch(
            category=ProductCategory.OTHER,
            confidence=0.0,
            matched_tag="",
            source="none",
            reason="no_match",
        )

    # Triem:
    # 1) més confiança
    # 2) tag més llarg, perquè normalment és més específic
    # 3) millor font
    return max(
        candidates,
        key=lambda candidate: (
            candidate.confidence,
            len(candidate.matched_tag),
            _source_weight(candidate.source),
        ),
    )


def map_off_to_internal_category(
    product_data_or_tags: dict | list[str] | str,
) -> ProductCategory:
    """
    Funció compatible amb el codi actual.

    Abans rebia només categories_tags o un string.
    Ara també pot rebre el product_data complet d'Open Food Facts.
    """
    return map_off_to_internal_category_detailed(product_data_or_tags).category