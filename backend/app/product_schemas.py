from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ProductCategory(str, Enum):
    FRESH_FRUIT = "FRESH_FRUIT"
    DRIED_FRUIT = "DRIED_FRUIT"
    FRESH_VEGETABLES = "FRESH_VEGETABLES"
    FRESH_SOUPS = "FRESH_SOUPS"
    DEHYDRATED_SOUPS = "DEHYDRATED_SOUPS"

    BREAD = "BREAD"
    BREAKFAST_CEREALS = "BREAKFAST_CEREALS"
    RICE = "RICE"
    PASTA = "PASTA"
    POTATOES = "POTATOES"
    LEGUMES = "LEGUMES"

    MILK = "MILK"
    YOGURT_AND_FERMENTED_MILK = "YOGURT_AND_FERMENTED_MILK"
    DAIRY_DESSERTS = "DAIRY_DESSERTS"
    ICE_CREAM = "ICE_CREAM"
    FRESH_CHEESE = "FRESH_CHEESE"
    SOFT_CHEESE = "SOFT_CHEESE"
    HARD_CHEESE = "HARD_CHEESE"
    BLUE_CHEESE = "BLUE_CHEESE"
    PROCESSED_CHEESE = "PROCESSED_CHEESE"

    EGGS = "EGGS"
    POULTRY = "POULTRY"
    RED_MEAT = "RED_MEAT"
    PROCESSED_MEAT = "PROCESSED_MEAT"
    OFFALS = "OFFALS"
    LEAN_FISH = "LEAN_FISH"
    FATTY_FISH = "FATTY_FISH"
    SMOKED_FISH = "SMOKED_FISH"
    SEAFOOD = "SEAFOOD"

    DARK_CHOCOLATE = "DARK_CHOCOLATE"
    MILK_CHOCOLATE = "MILK_CHOCOLATE"
    WHITE_CHOCOLATE = "WHITE_CHOCOLATE"
    SWEETS_AND_CANDIES = "SWEETS_AND_CANDIES"
    BISCUITS_AND_CAKES = "BISCUITS_AND_CAKES"
    PASTRIES = "PASTRIES"
    UNSALTED_NUTS = "UNSALTED_NUTS"
    SALTED_NUTS = "SALTED_NUTS"
    NUT_BUTTER = "NUT_BUTTER"
    SALTY_SNACKS = "SALTY_SNACKS"

    ANIMAL_FATS = "ANIMAL_FATS"
    VEGETABLE_OILS = "VEGETABLE_OILS"
    MARGARINES = "MARGARINES"
    DRESSINGS = "DRESSINGS"
    SAUCES = "SAUCES"

    PIZZA_QUICHE = "PIZZA_QUICHE"
    READY_MEALS = "READY_MEALS"
    SANDWICHES = "SANDWICHES"

    WATER_AND_FLAVORED_WATER = "WATER_AND_FLAVORED_WATER"
    FRUIT_JUICES = "FRUIT_JUICES"
    FRUIT_NECTARS = "FRUIT_NECTARS"
    SWEETENED_BEVERAGES = "SWEETENED_BEVERAGES"
    ARTIFICIALLY_SWEETENED_BEVERAGES = "ARTIFICIALLY_SWEETENED_BEVERAGES"
    UNSWEETENED_BEVERAGES = "UNSWEETENED_BEVERAGES"
    COFFEE_TEA_HERBAL_TEA = "COFFEE_TEA_HERBAL_TEA"
    PLANT_BASED_DRINKS = "PLANT_BASED_DRINKS"

    BEER = "BEER"
    FERMENTED_ALCOHOLIC_DRINKS = "FERMENTED_ALCOHOLIC_DRINKS"
    SPIRITS = "SPIRITS"
    PREMIXED_ALCOHOLIC_DRINKS = "PREMIXED_ALCOHOLIC_DRINKS"

    BABY_FOODS = "BABY_FOODS"
    BABY_MILKS = "BABY_MILKS"
    BABY_DRINKS = "BABY_DRINKS"
    BABY_DESSERTS_AND_SNACKS = "BABY_DESSERTS_AND_SNACKS"

    OTHER = "OTHER"


CATEGORY_LABELS_CA = {
    ProductCategory.FRESH_FRUIT: "Fruita fresca",
    ProductCategory.DRIED_FRUIT: "Fruita seca",
    ProductCategory.FRESH_VEGETABLES: "Verdura fresca",
    ProductCategory.FRESH_SOUPS: "Sopes fresques",
    ProductCategory.DEHYDRATED_SOUPS: "Sopes deshidratades",
    ProductCategory.BREAD: "Pa",
    ProductCategory.BREAKFAST_CEREALS: "Cereals d'esmorzar",
    ProductCategory.RICE: "Arròs",
    ProductCategory.PASTA: "Pasta",
    ProductCategory.POTATOES: "Patates",
    ProductCategory.LEGUMES: "Llegums",
    ProductCategory.MILK: "Llet",
    ProductCategory.YOGURT_AND_FERMENTED_MILK: "Iogurts i llets fermentades",
    ProductCategory.DAIRY_DESSERTS: "Postres làcties",
    ProductCategory.ICE_CREAM: "Gelats",
    ProductCategory.FRESH_CHEESE: "Formatge fresc",
    ProductCategory.SOFT_CHEESE: "Formatge tou",
    ProductCategory.HARD_CHEESE: "Formatge curat",
    ProductCategory.BLUE_CHEESE: "Formatge blau",
    ProductCategory.PROCESSED_CHEESE: "Formatge fos",
    ProductCategory.EGGS: "Ous",
    ProductCategory.POULTRY: "Carn d'au",
    ProductCategory.RED_MEAT: "Carn fresca",
    ProductCategory.PROCESSED_MEAT: "Carn processada / embotits",
    ProductCategory.OFFALS: "Menuts",
    ProductCategory.LEAN_FISH: "Peix blanc",
    ProductCategory.FATTY_FISH: "Peix blau",
    ProductCategory.SMOKED_FISH: "Peix fumat",
    ProductCategory.SEAFOOD: "Marisc",
    ProductCategory.DARK_CHOCOLATE: "Xocolata negra",
    ProductCategory.MILK_CHOCOLATE: "Xocolata amb llet",
    ProductCategory.WHITE_CHOCOLATE: "Xocolata blanca",
    ProductCategory.SWEETS_AND_CANDIES: "Caramels i llaminadures",
    ProductCategory.BISCUITS_AND_CAKES: "Galetes i pastissos",
    ProductCategory.PASTRIES: "Brioixeria",
    ProductCategory.UNSALTED_NUTS: "Fruits secs naturals",
    ProductCategory.SALTED_NUTS: "Fruits secs salats",
    ProductCategory.NUT_BUTTER: "Cremes de fruits secs",
    ProductCategory.SALTY_SNACKS: "Aperitius salats",
    ProductCategory.ANIMAL_FATS: "Greixos animals",
    ProductCategory.VEGETABLE_OILS: "Olis vegetals",
    ProductCategory.MARGARINES: "Margarines",
    ProductCategory.DRESSINGS: "Amaniments",
    ProductCategory.SAUCES: "Salses",
    ProductCategory.PIZZA_QUICHE: "Pizza, quiche i similars",
    ProductCategory.READY_MEALS: "Plats preparats",
    ProductCategory.SANDWICHES: "Entrepans",
    ProductCategory.WATER_AND_FLAVORED_WATER: "Aigua i aigües aromatitzades",
    ProductCategory.FRUIT_JUICES: "Sucs",
    ProductCategory.FRUIT_NECTARS: "Nèctars",
    ProductCategory.SWEETENED_BEVERAGES: "Begudes ensucrades",
    ProductCategory.ARTIFICIALLY_SWEETENED_BEVERAGES: "Begudes amb edulcorants",
    ProductCategory.UNSWEETENED_BEVERAGES: "Begudes sense sucre",
    ProductCategory.COFFEE_TEA_HERBAL_TEA: "Cafè, te i infusions",
    ProductCategory.PLANT_BASED_DRINKS: "Begudes vegetals",
    ProductCategory.BEER: "Cervesa",
    ProductCategory.FERMENTED_ALCOHOLIC_DRINKS: "Vi i altres fermentats alcohòlics",
    ProductCategory.SPIRITS: "Destil·lats i licors",
    ProductCategory.PREMIXED_ALCOHOLIC_DRINKS: "Begudes alcohòliques premesclades",
    ProductCategory.BABY_FOODS: "Menjar infantil",
    ProductCategory.BABY_MILKS: "Llets infantils",
    ProductCategory.BABY_DRINKS: "Begudes infantils",
    ProductCategory.BABY_DESSERTS_AND_SNACKS: "Postres i snacks infantils",
    ProductCategory.OTHER: "Altres",
}


class CreateManualProductSchema(BaseModel):
    name: Optional[str] = None
    price: Optional[Decimal] = None
    category: Optional[ProductCategory] = None
    quantity: Optional[int] = None
    purchase_date: Optional[date] = None
    expiration_date: Optional[date] = None
    owner_user_id: Optional[UUID] = None


class ProductResponse(BaseModel):
    id: str
    home_id: str
    created_by_user_id: str
    owner_user_id: Optional[str]
    is_private: bool
    name: str
    category: str
    category_label: str
    quantity: int
    price: str
    purchase_date: Optional[str]
    expiration_date: Optional[str]
    created_at: str


class CategoryOptionResponse(BaseModel):
    value: str
    label: str