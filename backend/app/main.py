from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

import app.home_models
import app.inventory_models
import app.models
from app.database import Base, engine
from app.home_routes import router as home_router
from app.inventory_delete_product import router as inventory_delete_router
from app.inventory_modify import router as inventory_modify_router
from app.inventory_routes import router as inventory_router
from app.routes import router

app = FastAPI()

Base.metadata.create_all(bind=engine)

app.include_router(router)
app.include_router(home_router)
app.include_router(inventory_router)
app.include_router(inventory_modify_router)
app.include_router(inventory_delete_router)

# IMPORTANT:
# product_router queda fora del main en aquesta branca per evitar
# tenir dos sistemes de productes en paral·lel.
# Els fitxers product_* els pots conservar temporalment al repo,
# però ja no són el flux principal.


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail,
        )

    if exc.status_code in (401, 403):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "code": "AUTH_REQUIRED",
            },
        )

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.get("/")
def root():
    return {"message": "API funcionando 🚀"}
