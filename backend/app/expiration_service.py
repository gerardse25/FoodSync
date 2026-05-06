from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.product_schemas import ProductCategory

DEFAULT_TIMEZONE = ZoneInfo("Europe/Madrid")


class ExpirationDateBeforePurchaseDate(Exception):
    """Raised when expiration date is earlier than purchase date."""


@dataclass(frozen=True)
class ExpirationResolution:
    data_compra: date | None
    data_caducitat: date
    data_caducitat_estimada: bool
    dies_caducitat_estimats: int | None


# Estimacions MVP per productes comprats i encara sense obrir.
# Són valors orientatius pensats per FoodSync, no substitueixen la data real
# de caducitat/consum preferent indicada pel fabricant.
# Si l'usuari coneix la data real, sempre pot enviar data_caducitat i aquesta preval.
EXPIRATION_DAYS_BY_CATEGORY: dict[ProductCategory, int] = {
    # FRUITA / VERDURA / SOPES
    ProductCategory.FRESH_FRUIT: 7,
    ProductCategory.DRIED_FRUIT: 180,
    ProductCategory.FRESH_VEGETABLES: 7,
    ProductCategory.FRESH_SOUPS: 5,
    ProductCategory.DEHYDRATED_SOUPS: 365,

    # CEREALS / FARINACIS / SECS
    ProductCategory.BREAD: 5,
    ProductCategory.BREAKFAST_CEREALS: 180,
    ProductCategory.RICE: 365,
    ProductCategory.PASTA: 365,
    ProductCategory.POTATOES: 30,
    ProductCategory.LEGUMES: 365,

    # LACTIS
    # Assumim producte sense obrir. En el cas de la llet, es prioritza l'escenari
    # més habitual de brick/UHT. Si és llet fresca refrigerada, l'usuari pot corregir.
    ProductCategory.MILK: 90,
    ProductCategory.YOGURT_AND_FERMENTED_MILK: 21,
    ProductCategory.DAIRY_DESSERTS: 21,
    ProductCategory.ICE_CREAM: 180,
    ProductCategory.FRESH_CHEESE: 14,
    ProductCategory.SOFT_CHEESE: 21,
    ProductCategory.HARD_CHEESE: 90,
    ProductCategory.BLUE_CHEESE: 45,
    ProductCategory.PROCESSED_CHEESE: 90,

    # OUS / CARN / PEIX
    ProductCategory.EGGS: 28,
    ProductCategory.POULTRY: 2,
    ProductCategory.RED_MEAT: 3,
    ProductCategory.PROCESSED_MEAT: 21,
    ProductCategory.OFFALS: 1,
    ProductCategory.LEAN_FISH: 2,
    ProductCategory.FATTY_FISH: 2,
    ProductCategory.SMOKED_FISH: 21,
    ProductCategory.SEAFOOD: 1,

    # DOLÇOS / SNACKS / FRUITS SECS
    ProductCategory.DARK_CHOCOLATE: 365,
    ProductCategory.MILK_CHOCOLATE: 270,
    ProductCategory.WHITE_CHOCOLATE: 180,
    ProductCategory.SWEETS_AND_CANDIES: 365,
    ProductCategory.BISCUITS_AND_CAKES: 180,
    ProductCategory.PASTRIES: 4,
    ProductCategory.UNSALTED_NUTS: 180,
    ProductCategory.SALTED_NUTS: 180,
    ProductCategory.NUT_BUTTER: 180,
    ProductCategory.SALTY_SNACKS: 150,

    # GREIXOS / SALSES / AMANIMENTS
    ProductCategory.ANIMAL_FATS: 90,
    ProductCategory.VEGETABLE_OILS: 365,
    ProductCategory.MARGARINES: 120,
    ProductCategory.DRESSINGS: 180,
    ProductCategory.SAUCES: 180,

    # PREPARATS
    ProductCategory.PIZZA_QUICHE: 5,
    ProductCategory.READY_MEALS: 5,
    ProductCategory.SANDWICHES: 1,

    # BEGUDES NO ALCOHÒLIQUES
    ProductCategory.WATER_AND_FLAVORED_WATER: 365,
    ProductCategory.FRUIT_JUICES: 90,
    ProductCategory.FRUIT_NECTARS: 180,
    ProductCategory.SWEETENED_BEVERAGES: 180,
    ProductCategory.ARTIFICIALLY_SWEETENED_BEVERAGES: 180,
    ProductCategory.UNSWEETENED_BEVERAGES: 180,
    ProductCategory.COFFEE_TEA_HERBAL_TEA: 365,
    ProductCategory.PLANT_BASED_DRINKS: 120,

    # ALCOHOL
    ProductCategory.BEER: 180,
    ProductCategory.FERMENTED_ALCOHOLIC_DRINKS: 365,
    ProductCategory.SPIRITS: 3650,
    ProductCategory.PREMIXED_ALCOHOLIC_DRINKS: 365,

    # INFANTIL
    ProductCategory.BABY_FOODS: 180,
    ProductCategory.BABY_MILKS: 180,
    ProductCategory.BABY_DRINKS: 180,
    ProductCategory.BABY_DESSERTS_AND_SNACKS: 90,

    # FALLBACK CONSERVADOR
    ProductCategory.OTHER: 30,
}


def get_default_expiration_days(category: ProductCategory) -> int:
    return EXPIRATION_DAYS_BY_CATEGORY.get(
        category,
        EXPIRATION_DAYS_BY_CATEGORY[ProductCategory.OTHER],
    )


def estimate_expiration_date(
    category: ProductCategory,
    purchase_date: date,
) -> date:
    days = get_default_expiration_days(category)
    return purchase_date + timedelta(days=days)


def _get_default_purchase_date() -> date:
    """
    Retorna la data actual que s'utilitzarà quan l'usuari no informa data_compra.
    Es fixa Europe/Madrid per evitar diferències si el servidor corre en UTC.
    """
    return datetime.now(DEFAULT_TIMEZONE).date()


def resolve_expiration_fields(
    category: ProductCategory,
    purchase_date: date | None,
    provided_expiration_date: date | None,
) -> ExpirationResolution:
    """
    Regla comuna per manual, barcode i OCR/tíquet:

    - Si l'usuari proporciona data_compra, es respecta.
    - Si no proporciona data_compra, s'assumeix la data actual.
    - Si l'usuari proporciona data_caducitat, es respecta i no es marca com estimada.
    - Si no proporciona data_caducitat, es calcula segons categoria + data_compra efectiva.
    """
    effective_purchase_date = purchase_date or _get_default_purchase_date()

    if provided_expiration_date is not None:
        if provided_expiration_date < effective_purchase_date:
            raise ExpirationDateBeforePurchaseDate()

        return ExpirationResolution(
            data_compra=effective_purchase_date,
            data_caducitat=provided_expiration_date,
            data_caducitat_estimada=False,
            dies_caducitat_estimats=None,
        )

    estimated_days = get_default_expiration_days(category)

    return ExpirationResolution(
        data_compra=effective_purchase_date,
        data_caducitat=effective_purchase_date + timedelta(days=estimated_days),
        data_caducitat_estimada=True,
        dies_caducitat_estimats=estimated_days,
    )