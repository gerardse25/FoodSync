import re

from app.product_schemas import ProductCategory

# -----------------------------------------------------------------------------
# Estratègia:
# 1) Normalitzar tags d'OFF (llista o string)
# 2) Intentar match exacte sobre tags coneguts
# 3) Intentar match per sinònims/variants
# 4) Intentar match per keywords específiques
# 5) Si hi ha ambigüitat o res clar -> OTHER
#
# Objectiu: ser conservadors i reduir falsos positius.
# -----------------------------------------------------------------------------

LANG_PREFIX_RE = re.compile(r"^[a-z]{2,3}:")


def _strip_lang_prefix(value: str) -> str:
    return LANG_PREFIX_RE.sub("", value.strip().lower())


def _slugify(value: str) -> str:
    """
    Normalitza per comparar tags:
    - lowercase
    - espais -> guions
    - elimina caràcters estranys
    """
    value = _strip_lang_prefix(value)
    value = value.replace("_", "-").replace("/", "-")
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"[^a-z0-9\-]", "", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value


def _normalize_off_tags(off_tags: list[str] | str) -> list[str]:
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

    # treure duplicats mantenint ordre
    seen = set()
    result = []
    for tag in normalized:
        if tag not in seen:
            seen.add(tag)
            result.append(tag)
    return result


# -----------------------------------------------------------------------------
# 1) Match exacte: tags OFF o variants molt concretes
# -----------------------------------------------------------------------------
EXACT_TAG_MAP: dict[str, ProductCategory] = {
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
    "nut-butters": ProductCategory.NUT_BUTTER,
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


# -----------------------------------------------------------------------------
# 2) Sinònims i variants específiques
# -----------------------------------------------------------------------------
VARIANT_KEYWORDS: list[tuple[str, ProductCategory]] = [
    # específics primer
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
    ("nut-butter", ProductCategory.NUT_BUTTER),
]


# -----------------------------------------------------------------------------
# 3) Keywords genèriques però encara útils
# IMPORTANT: no hi posem termes massa amplis com "beverage", "fruit", "sweet",
# "meat", "vegetable", "sauce"... perquè generen massa falsos positius.
# -----------------------------------------------------------------------------
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


def map_off_to_internal_category(off_tags: list[str] | str) -> ProductCategory:
    tags = _normalize_off_tags(off_tags)
    if not tags:
        return ProductCategory.OTHER

    # 1) match exacte de tag
    for tag in tags:
        if tag in EXACT_TAG_MAP:
            return EXACT_TAG_MAP[tag]

    # 2) match per variants específiques
    for tag in tags:
        for keyword, category in VARIANT_KEYWORDS:
            if keyword in tag:
                return category

    # 3) match per keywords específiques
    for tag in tags:
        for keyword, category in SAFE_KEYWORDS:
            if keyword in tag:
                return category

    return ProductCategory.OTHER
