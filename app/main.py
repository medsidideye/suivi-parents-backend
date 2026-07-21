from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import Base, engine
from app.models import models  # noqa: F401 — nécessaire pour enregistrer les tables
from app.routers import ecoles, parents, admin, eleves, auth

Base.metadata.create_all(bind=engine)

app = FastAPI(title="API — Suivi scolaire parents")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # à restreindre en production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ecoles.router)
app.include_router(auth.router)
app.include_router(parents.router)
app.include_router(admin.router)
app.include_router(eleves.router)


@app.get("/")
def racine():
    return {"message": "API suivi scolaire parents — en ligne."}
