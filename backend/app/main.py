from fastapi import FastAPI
from app.database import Base, engine
import app.models
from app.routes import router

app = FastAPI()

# Crear tablas
Base.metadata.create_all(bind=engine)

# Rutas
app.include_router(router)


@app.get("/")
def root():
    return {"message": "API funcionando 🚀"}