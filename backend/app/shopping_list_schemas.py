from typing import Optional, Union
from uuid import UUID
from pydantic import BaseModel, Field

class AddShoppingListItemRequest(BaseModel):
    product_id: Union[int, str]
    quantity: int = Field(..., gt=0)
    notes: Optional[str] = None

class ShoppingListItemData(BaseModel):
    item_id: UUID
    product_id: str
    quantity: int
    is_new: Optional[bool] = None

class AddShoppingListItemResponse(BaseModel):
    message: str
    data: ShoppingListItemData

class UpdateShoppingListItemRequest(BaseModel):
    quantity: int

class ConsumeInventoryItemRequest(BaseModel):
    quantity_consumed: int = Field(..., gt=0)
    add_to_shopping_list: bool
    shopping_list_quantity: Optional[int] = Field(default=1, ge=0)

class ConsumeInventoryItemResponseData(BaseModel):
    inventory_status: str
    shopping_list_item: Optional[ShoppingListItemData] = None

class ConsumeInventoryItemResponse(BaseModel):
    message: str
    data: ConsumeInventoryItemResponseData

class ShoppingListProductDetails(BaseModel):
    item_id: UUID
    product_id: str
    name: str
    quantity: int
    notes: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    image_url: Optional[str] = None

class GetShoppingListResponse(BaseModel):
    code: str = "SHOPPING_LIST_RETRIEVED"
    message: str
    items: list[ShoppingListProductDetails]
