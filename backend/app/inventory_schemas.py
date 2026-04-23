from pydantic import BaseModel


class ConsumeProductRequest(BaseModel):
    id_producte: str
    modificacio: int


class ConsumeProductResponseItem(BaseModel):
    id_producte: str
    nom: str
    quantitat_restant: int


class ConsumeProductResponse(BaseModel):
    code: str
    missatge: str
    producte: ConsumeProductResponseItem
