from pydantic import BaseModel


class DeleteProductRequest(BaseModel):
    id_producte: str


class DeleteProductResponse(BaseModel):
    code: str
    missatge: str
