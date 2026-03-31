from fastapi import FastAPI

import app.models
import app.home_models
from app.database import Base, engine
from app.routes import router
from app.home_routes import router as home_router

app = FastAPI()

Base.metadata.create_all(bind=engine)

app.include_router(router)
app.include_router(home_router)


@app.get("/")
def root():
    return {"message": "API funcionando 🚀"}
