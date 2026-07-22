import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import hacher_mot_de_passe
from app.core.limiteur import verifier_limite
from app.models import models
from app.schemas import schemas

router = APIRouter(prefix="/bootstrap", tags=["démarrage"])


@router.post("/creer-super-admin")
def creer_super_admin_bootstrap(donnees: schemas.BootstrapSuperAdmin, db: Session = Depends(get_db)):
    """Crée le tout premier super-admin sans avoir besoin d'un accès Shell —
    utile sur les hébergeurs (comme Render en plan gratuit) qui ne le proposent pas.

    Protégé par un secret défini via la variable d'environnement SETUP_SECRET, et se
    désactive automatiquement dès qu'un super-admin existe déjà — utilisable une seule
    fois, sans danger de laisser cette route active en permanence."""
    verifier_limite("bootstrap-super-admin")

    secret_attendu = os.environ.get("SETUP_SECRET")
    if not secret_attendu:
        raise HTTPException(status_code=403, detail="SETUP_SECRET n'est pas configuré sur ce serveur.")
    if donnees.secret != secret_attendu:
        raise HTTPException(status_code=403, detail="Secret incorrect.")

    if db.query(models.SuperAdmin).first():
        raise HTTPException(status_code=403, detail="Un super-admin existe déjà — cette route ne peut plus être utilisée.")

    superadmin = models.SuperAdmin(
        nom=donnees.nom,
        email=donnees.email,
        mot_de_passe_hash=hacher_mot_de_passe(donnees.mot_de_passe),
    )
    db.add(superadmin)
    db.commit()
    return {"message": f"Super-admin '{donnees.nom}' créé avec succès."}
