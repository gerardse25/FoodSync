from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

import app.home_models
import app.models
from app.database import Base, engine
from app.home_routes import router as home_router
from app.routes import router

app = FastAPI()

Base.metadata.create_all(bind=engine)

app.include_router(router)
app.include_router(home_router)

# ==================== EXCEPTION HANDLERS ====================


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    # Si ja té format correcte amb code → respectar-lo
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail,
        )

    # Errors d'autenticació
    if exc.status_code in (401, 403):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "code": "AUTH_REQUIRED",
            },
        )


@app.get("/")
def root():
    return {"message": "API funcionando 🚀"}
