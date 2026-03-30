from fastapi import FastAPI

import app.models
from app.database import Base, engine
from app.routes import router

app = FastAPI()

Base.metadata.create_all(bind=engine)

app.include_router(router)


@app.get("/")
def root():
    return {"message": "API funcionando 🚀"}