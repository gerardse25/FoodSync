from app.product_schemas import ProductCategory

# Heurística de mapatge: les claus més específiques van primer.
OFF_KEYWORD_MAP = {
    # --- BEVERAGES (Begudes) ---
    "water": ProductCategory.WATER_AND_FLAVORED_WATER,
    "nectar": ProductCategory.FRUIT_NECTARS,
    "juice": ProductCategory.FRUIT_JUICES,
    "energy-drink": ProductCategory.SWEETENED_BEVERAGES,
    "cola": ProductCategory.SWEETENED_BEVERAGES,
    "soda": ProductCategory.SWEETENED_BEVERAGES,
    "sugar-free-soft-drink": ProductCategory.ARTIFICIALLY_SWEETENED_BEVERAGES,
    "diet-soda": ProductCategory.ARTIFICIALLY_SWEETENED_BEVERAGES,
    "tea": ProductCategory.COFFEE_TEA_HERBAL_TEA,
    "coffee": ProductCategory.COFFEE_TEA_HERBAL_TEA,
    "infusion": ProductCategory.COFFEE_TEA_HERBAL_TEA,
    "plant-based-beverage": ProductCategory.PLANT_BASED_DRINKS,
    "soy-milk": ProductCategory.PLANT_BASED_DRINKS,
    "almond-milk": ProductCategory.PLANT_BASED_DRINKS,
    "beverage": ProductCategory.UNSWEETENED_BEVERAGES, # Fallback general de begudes

    # --- ALCOHOL ---
    "beer": ProductCategory.BEER,
    "wine": ProductCategory.FERMENTED_ALCOHOLIC_DRINKS,
    "cider": ProductCategory.FERMENTED_ALCOHOLIC_DRINKS,
    "spirit": ProductCategory.SPIRITS,
    "liquor": ProductCategory.SPIRITS,
    "cocktail": ProductCategory.PREMIXED_ALCOHOLIC_DRINKS,

    # --- DAIRY & DERIVATIVES (Lactis) ---
    "yogurt": ProductCategory.YOGURT_AND_FERMENTED_MILK,
    "kefir": ProductCategory.YOGURT_AND_FERMENTED_MILK,
    "dairy-dessert": ProductCategory.DAIRY_DESSERTS,
    "pudding": ProductCategory.DAIRY_DESSERTS,
    "ice-cream": ProductCategory.ICE_CREAM,
    "sorbet": ProductCategory.ICE_CREAM,
    "fresh-cheese": ProductCategory.FRESH_CHEESE,
    "soft-cheese": ProductCategory.SOFT_CHEESE,
    "blue-cheese": ProductCategory.BLUE_CHEESE,
    "processed-cheese": ProductCategory.PROCESSED_CHEESE,
    "cheese": ProductCategory.HARD_CHEESE, # La resta de formatges per defecte
    "milk": ProductCategory.MILK,

    # --- MEAT, FISH & EGGS (Proteïna) ---
    "poultry": ProductCategory.POULTRY,
    "chicken": ProductCategory.POULTRY,
    "turkey": ProductCategory.POULTRY,
    "ham": ProductCategory.PROCESSED_MEAT,
    "sausage": ProductCategory.PROCESSED_MEAT,
    "salami": ProductCategory.PROCESSED_MEAT,
    "cold-cuts": ProductCategory.PROCESSED_MEAT,
    "meat": ProductCategory.RED_MEAT,
    "offal": ProductCategory.OFFALS,
    "white-fish": ProductCategory.LEAN_FISH,
    "lean-fish": ProductCategory.LEAN_FISH,
    "fatty-fish": ProductCategory.FATTY_FISH,
    "salmon": ProductCategory.FATTY_FISH,
    "tuna": ProductCategory.FATTY_FISH,
    "smoked-fish": ProductCategory.SMOKED_FISH,
    "seafood": ProductCategory.SEAFOOD,
    "crustacean": ProductCategory.SEAFOOD,
    "mollusc": ProductCategory.SEAFOOD,
    "egg": ProductCategory.EGGS,

    # --- FRUITS, VEGGIES & LEGUMES ---
    "dried-fruit": ProductCategory.DRIED_FRUIT,
    "fruit": ProductCategory.FRESH_FRUIT,
    "vegetable": ProductCategory.FRESH_VEGETABLES,
    "legume": ProductCategory.LEGUMES,
    "bean": ProductCategory.LEGUMES,
    "lentil": ProductCategory.LEGUMES,
    "fresh-soup": ProductCategory.FRESH_SOUPS,
    "dehydrated-soup": ProductCategory.DEHYDRATED_SOUPS,
    "soup": ProductCategory.FRESH_SOUPS,

    # --- CEREALS & BAKERY (Farinacis) ---
    "breakfast-cereal": ProductCategory.BREAKFAST_CEREALS,
    "muesli": ProductCategory.BREAKFAST_CEREALS,
    "corn-flakes": ProductCategory.BREAKFAST_CEREALS,
    "rice": ProductCategory.RICE,
    "pasta": ProductCategory.PASTA,
    "noodle": ProductCategory.PASTA,
    "potato": ProductCategory.POTATOES,
    "bread": ProductCategory.BREAD,

    # --- SWEETS & SNACKS (Dolços i Aperitius) ---
    "dark-chocolate": ProductCategory.DARK_CHOCOLATE,
    "milk-chocolate": ProductCategory.MILK_CHOCOLATE,
    "white-chocolate": ProductCategory.WHITE_CHOCOLATE,
    "chocolate": ProductCategory.DARK_CHOCOLATE,
    "candy": ProductCategory.SWEETS_AND_CANDIES,
    "sweet": ProductCategory.SWEETS_AND_CANDIES,
    "biscuit": ProductCategory.BISCUITS_AND_CAKES,
    "cake": ProductCategory.BISCUITS_AND_CAKES,
    "pastry": ProductCategory.PASTRIES,
    "viennoiserie": ProductCategory.PASTRIES,
    "unsalted-nut": ProductCategory.UNSALTED_NUTS,
    "salted-nut": ProductCategory.SALTED_NUTS,
    "nut-butter": ProductCategory.NUT_BUTTER,
    "snack": ProductCategory.SALTY_SNACKS,
    "chips": ProductCategory.SALTY_SNACKS,

    # --- FATS & SAUCES ---
    "animal-fat": ProductCategory.ANIMAL_FATS,
    "lard": ProductCategory.ANIMAL_FATS,
    "vegetable-oil": ProductCategory.VEGETABLE_OILS,
    "olive-oil": ProductCategory.VEGETABLE_OILS,
    "margarine": ProductCategory.MARGARINES,
    "dressing": ProductCategory.DRESSINGS,
    "vinaigrette": ProductCategory.DRESSINGS,
    "sauce": ProductCategory.SAUCES,
    "ketchup": ProductCategory.SAUCES,
    "mayonnaise": ProductCategory.SAUCES,

    # --- READY MEALS ---
    "pizza": ProductCategory.PIZZA_QUICHE,
    "quiche": ProductCategory.PIZZA_QUICHE,
    "sandwich": ProductCategory.SANDWICHES,
    "ready-meal": ProductCategory.READY_MEALS,
    "prepared-dish": ProductCategory.READY_MEALS,

    # --- BABY FOOD ---
    "baby-milk": ProductCategory.BABY_MILKS,
    "baby-drink": ProductCategory.BABY_DRINKS,
    "baby-dessert": ProductCategory.BABY_DESSERTS_AND_SNACKS,
    "baby-food": ProductCategory.BABY_FOODS,
}

def map_off_to_internal_category(off_tags: list[str] | str) -> ProductCategory:
    if not off_tags:
        return ProductCategory.OTHER

    # Unifiquem tots els tags en un sol text per cercar paraules clau
    full_tags_text = ""
    if isinstance(off_tags, list):
        full_tags_text = "|".join(off_tags).lower()
    else:
        full_tags_text = off_tags.lower()

    # Ara iterem primer pel nostre diccionari (que està ordenat per especificitat)
    for keyword, category in OFF_KEYWORD_MAP.items():
        if keyword in full_tags_text:
            return category

    return ProductCategory.OTHER