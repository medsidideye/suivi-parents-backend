from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import hacher_mot_de_passe, generer_mot_de_passe_temporaire, verifier_mot_de_passe
from app.core.deps import super_admin_courant
from app.models import models
from app.schemas import schemas

router = APIRouter(prefix="/ecoles", tags=["écoles"])


@router.post("/moi/changer-mot-de-passe")
def changer_mon_mot_de_passe_super_admin(donnees: schemas.ChangementMotDePasse, db: Session = Depends(get_db), superadmin: models.SuperAdmin = Depends(super_admin_courant)):
    """Changement volontaire, différent du script CLI qui sert à la récupération en cas d'oubli."""
    if not verifier_mot_de_passe(donnees.ancien_mot_de_passe, superadmin.mot_de_passe_hash):
        raise HTTPException(status_code=401, detail="Mot de passe actuel incorrect.")
    superadmin.mot_de_passe_hash = hacher_mot_de_passe(donnees.nouveau_mot_de_passe)
    db.commit()
    return {"message": "Mot de passe changé avec succès."}


@router.get("/", response_model=list[schemas.EcoleLecture])
def lister_ecoles(db: Session = Depends(get_db)):
    """Route publique — alimente la liste déroulante du formulaire d'inscription parent."""
    return db.query(models.Ecole).filter(
        models.Ecole.statut == models.StatutEcole.actif
    ).all()


@router.get("/toutes")
def lister_toutes_les_ecoles(db: Session = Depends(get_db), _: models.SuperAdmin = Depends(super_admin_courant)):
    """Réservé au super-admin — inclut aussi les écoles non actives, avec quelques compteurs."""
    ecoles = db.query(models.Ecole).all()
    return [
        {"id": e.id, "nom": e.nom, "statut": e.statut, "nb_classes": len(e.classes), "nb_eleves": len(e.eleves)}
        for e in ecoles
    ]


@router.post("/", response_model=schemas.EcoleLecture)
def creer_ecole(
    donnees: schemas.EcoleCreation,
    db: Session = Depends(get_db),
    _: models.SuperAdmin = Depends(super_admin_courant),
):
    ecole = models.Ecole(nom=donnees.nom, adresse=donnees.adresse, statut=models.StatutEcole.actif)
    db.add(ecole)
    db.commit()
    db.refresh(ecole)
    return ecole


@router.post("/{id_ecole}/admins")
def creer_admin_ecole(
    id_ecole: int,
    donnees: schemas.AdminEcoleCreation,
    db: Session = Depends(get_db),
    _: models.SuperAdmin = Depends(super_admin_courant),
):
    """Le super-admin crée le compte (nom + email) mais PAS le mot de passe — un code de
    vérification est généré, à communiquer à l'école. Elle l'utilisera pour définir
    elle-même son mot de passe à sa première connexion."""
    code = generer_mot_de_passe_temporaire()
    admin = models.AdminEcole(
        nom=donnees.nom,
        email=donnees.email,
        mot_de_passe_hash=None,
        code_verification_hash=hacher_mot_de_passe(code),
        id_ecole=id_ecole,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return {"id": admin.id, "nom": admin.nom, "email": admin.email, "id_ecole": admin.id_ecole, "code_verification": code}


@router.get("/{id_ecole}/admins")
def lister_admins_ecole(id_ecole: int, db: Session = Depends(get_db), _: models.SuperAdmin = Depends(super_admin_courant)):
    admins = db.query(models.AdminEcole).filter(models.AdminEcole.id_ecole == id_ecole).all()
    return [
        {"id": a.id, "nom": a.nom, "email": a.email, "compte_active": a.mot_de_passe_hash is not None}
        for a in admins
    ]


@router.post("/admins/{id_admin}/reinitialiser-mot-de-passe")
def reinitialiser_mot_de_passe_admin(id_admin: int, db: Session = Depends(get_db), _: models.SuperAdmin = Depends(super_admin_courant)):
    """Génère un nouveau code de vérification pour un admin d'école — à communiquer.
    L'ancien mot de passe reste valide tant que l'admin n'a pas utilisé ce code pour
    en définir un nouveau, pour ne pas le bloquer entre-temps."""
    admin = db.query(models.AdminEcole).get(id_admin)
    if not admin:
        raise HTTPException(status_code=404, detail="Admin introuvable.")
    code = generer_mot_de_passe_temporaire()
    admin.code_verification_hash = hacher_mot_de_passe(code)
    db.commit()
    return {"message": "Code de vérification généré.", "code_verification": code}
