from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import hacher_mot_de_passe, verifier_mot_de_passe, creer_token
from app.core.deps import parent_courant
from app.core.limiteur import verifier_limite, reinitialiser_limite
from app.models import models
from app.schemas import schemas

router = APIRouter(prefix="/parents", tags=["parents"])


@router.post("/inscription")
def inscrire_parent(donnees: schemas.ParentInscription, db: Session = Depends(get_db)):
    """Le parent crée son compte et indique le nom d'un ou plusieurs enfants à titre indicatif.
    Aucune fiche élève n'est créée ici — l'école recherchera et attribuera elle-même
    chaque élève exact dans sa propre liste, déjà existante."""
    if not donnees.enfants:
        raise HTTPException(status_code=422, detail="Indiquez au moins un enfant.")

    existant = db.query(models.Parent).filter(models.Parent.numero_telephone == donnees.numero_telephone).first()
    if existant:
        parent = existant
    else:
        parent = models.Parent(
            nom=donnees.nom,
            numero_telephone=donnees.numero_telephone,
            mot_de_passe_hash=hacher_mot_de_passe(donnees.mot_de_passe),
        )
        db.add(parent)
        db.flush()

    for enfant in donnees.enfants:
        db.add(models.DemandeAttribution(
            id_parent=parent.id,
            id_ecole=donnees.id_ecole,
            nom_enfant_indique=enfant.nom,
            prenom_enfant_indique=enfant.prenom,
            statut=models.StatutDemande.en_attente,
        ))
    db.commit()

    return {"message": "Compte créé, en attente d'attribution par l'école.", "id_parent": parent.id}


@router.post("/connexion")
def connexion_parent(donnees: schemas.ParentConnexion, db: Session = Depends(get_db)):
    cle = f"parent-connexion:{donnees.numero_telephone}"
    verifier_limite(cle)
    parent = db.query(models.Parent).filter(models.Parent.numero_telephone == donnees.numero_telephone).first()
    if not parent or not verifier_mot_de_passe(donnees.mot_de_passe, parent.mot_de_passe_hash):
        raise HTTPException(status_code=401, detail="Identifiants invalides.")
    reinitialiser_limite(cle)
    token = creer_token({"sub": str(parent.id), "role": "parent"})
    return {"token": token}


@router.get("/moi/enfants")
def mes_enfants(db: Session = Depends(get_db), parent: models.Parent = Depends(parent_courant)):
    """Le parent connecté ne voit que les enfants que l'école lui a explicitement attribués."""
    liens = db.query(models.ParentEleve).filter(models.ParentEleve.id_parent == parent.id).all()
    return [
        {"id_eleve": lien.eleve.id, "nom": lien.eleve.nom, "prenom": lien.eleve.prenom,
         "classe": lien.eleve.classe.nom, "ecole": lien.eleve.ecole.nom}
        for lien in liens
    ]


@router.post("/moi/changer-mot-de-passe")
def changer_mot_de_passe(donnees: schemas.ChangementMotDePasse, db: Session = Depends(get_db), parent: models.Parent = Depends(parent_courant)):
    if not verifier_mot_de_passe(donnees.ancien_mot_de_passe, parent.mot_de_passe_hash):
        raise HTTPException(status_code=401, detail="Mot de passe actuel incorrect.")
    parent.mot_de_passe_hash = hacher_mot_de_passe(donnees.nouveau_mot_de_passe)
    db.commit()
    return {"message": "Mot de passe changé avec succès."}
