from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verifier_mot_de_passe, creer_token, hacher_mot_de_passe
from app.core.deps import super_admin_courant
from app.core.limiteur import verifier_limite, reinitialiser_limite
from app.models import models
from app.schemas import schemas

router = APIRouter(prefix="/auth", tags=["authentification"])


@router.post("/admin-ecole/connexion")
def connexion_admin_ecole(donnees: schemas.ConnexionEmail, db: Session = Depends(get_db)):
    cle = f"admin-connexion:{donnees.email.lower()}"
    verifier_limite(cle)
    admin = db.query(models.AdminEcole).filter(models.AdminEcole.email == donnees.email).first()
    if not admin or not admin.mot_de_passe_hash or not verifier_mot_de_passe(donnees.mot_de_passe, admin.mot_de_passe_hash):
        raise HTTPException(status_code=401, detail="Identifiants invalides.")
    reinitialiser_limite(cle)
    token = creer_token({"sub": str(admin.id), "role": "admin_ecole", "id_ecole": admin.id_ecole})
    return {"token": token, "id_ecole": admin.id_ecole}


@router.post("/admin-ecole/definir-mot-de-passe")
def definir_mot_de_passe_admin_ecole(donnees: schemas.DefinirMotDePasseAdmin, db: Session = Depends(get_db)):
    """Utilisé à la fois pour la première activation du compte (avec le code donné par le
    super-admin à la création) et pour une réinitialisation après oubli (avec le nouveau
    code régénéré par le super-admin) — le mécanisme est identique dans les deux cas."""
    cle = f"admin-code:{donnees.email.lower()}"
    verifier_limite(cle)
    admin = db.query(models.AdminEcole).filter(models.AdminEcole.email == donnees.email).first()
    if not admin or not admin.code_verification_hash or not verifier_mot_de_passe(donnees.code_verification, admin.code_verification_hash):
        raise HTTPException(status_code=401, detail="Code de vérification invalide.")
    reinitialiser_limite(cle)
    admin.mot_de_passe_hash = hacher_mot_de_passe(donnees.nouveau_mot_de_passe)
    admin.code_verification_hash = None
    db.commit()
    return {"message": "Mot de passe défini avec succès. Vous pouvez maintenant vous connecter."}


@router.post("/super-admin/connexion")
def connexion_super_admin(donnees: schemas.ConnexionEmail, db: Session = Depends(get_db)):
    cle = f"super-admin-connexion:{donnees.email.lower()}"
    verifier_limite(cle)
    superadmin = db.query(models.SuperAdmin).filter(models.SuperAdmin.email == donnees.email).first()
    if not superadmin or not verifier_mot_de_passe(donnees.mot_de_passe, superadmin.mot_de_passe_hash):
        raise HTTPException(status_code=401, detail="Identifiants invalides.")
    reinitialiser_limite(cle)
    token = creer_token({"sub": str(superadmin.id), "role": "super_admin"})
    return {"token": token}
