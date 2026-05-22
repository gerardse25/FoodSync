from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field

class AddShoppingListItemRequest(BaseModel):
    product_name: str = Field(..., min_length=1)
    quantity: int = Field(..., gt=0)
    notes: Optional[str] = None

class ShoppingListItemData(BaseModel):
    item_id: UUID
    product_name: str
    quantity: int
    is_new: Optional[bool] = None

class AddShoppingListItemResponse(BaseModel):
    message: str
    data: ShoppingListItemData

class UpdateShoppingListItemRequest(BaseModel):
    quantity: int

class ShoppingListProductDetails(BaseModel):
    item_id: UUID
    product_name: str
    quantity: int
    notes: Optional[str] = None

class GetShoppingListResponse(BaseModel):
    code: str = "SHOPPING_LIST_RETRIEVED"
    message: str
    items: list[ShoppingListProductDetails]
