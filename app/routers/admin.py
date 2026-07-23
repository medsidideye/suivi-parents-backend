import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import admin_ecole_courant
from app.core.security import hacher_mot_de_passe, generer_mot_de_passe_temporaire, verifier_mot_de_passe
from app.models import models
from app.schemas import schemas

router = APIRouter(prefix="/admin", tags=["admin école"])


def _verifier_eleve_dans_ecole(db: Session, id_eleve: int, id_ecole: int) -> models.Eleve:
    eleve = db.query(models.Eleve).get(id_eleve)
    if not eleve or eleve.id_ecole != id_ecole:
        raise HTTPException(status_code=404, detail="Élève introuvable dans votre école.")
    return eleve


def _verifier_classe_dans_ecole(db: Session, id_classe: int, id_ecole: int) -> models.Classe:
    classe = db.query(models.Classe).get(id_classe)
    if not classe or classe.id_ecole != id_ecole:
        raise HTTPException(status_code=404, detail="Classe introuvable dans votre école.")
    return classe


def _verifier_matiere_dans_ecole(db: Session, id_matiere: int, id_ecole: int) -> models.Matiere:
    matiere = db.query(models.Matiere).get(id_matiere)
    if not matiere or matiere.id_ecole != id_ecole:
        raise HTTPException(status_code=404, detail="Matière introuvable dans votre école.")
    return matiere


# --- Structure (classes, matières, élèves) ---

@router.post("/moi/changer-mot-de-passe")
def changer_mon_mot_de_passe(donnees: schemas.ChangementMotDePasse, db: Session = Depends(get_db), admin: models.AdminEcole = Depends(admin_ecole_courant)):
    """L'admin école change lui-même son mot de passe, sans passer par le super-admin —
    utile pour un changement volontaire, à ne pas confondre avec la réinitialisation
    en cas d'oubli (qui elle nécessite le super-admin, puisqu'un mot de passe oublié
    ne peut par définition pas être vérifié)."""
    if not verifier_mot_de_passe(donnees.ancien_mot_de_passe, admin.mot_de_passe_hash):
        raise HTTPException(status_code=401, detail="Mot de passe actuel incorrect.")
    admin.mot_de_passe_hash = hacher_mot_de_passe(donnees.nouveau_mot_de_passe)
    db.commit()
    return {"message": "Mot de passe changé avec succès."}


@router.post("/classes")
def creer_classe(donnees: schemas.ClasseCreation, db: Session = Depends(get_db), admin: models.AdminEcole = Depends(admin_ecole_courant)):
    classe = models.Classe(nom=donnees.nom, niveau=donnees.niveau, id_ecole=admin.id_ecole)
    db.add(classe)
    db.commit()
    db.refresh(classe)
    return classe


@router.post("/matieres")
def creer_matiere(donnees: schemas.MatiereCreation, db: Session = Depends(get_db), admin: models.AdminEcole = Depends(admin_ecole_courant)):
    matiere = models.Matiere(nom=donnees.nom, id_ecole=admin.id_ecole)
    db.add(matiere)
    db.commit()
    db.refresh(matiere)
    return matiere


@router.post("/eleves")
def creer_eleve(donnees: schemas.EleveCreation, db: Session = Depends(get_db), admin: models.AdminEcole = Depends(admin_ecole_courant)):
    """L'école inscrit ses élèves dans le système, indépendamment de tout compte parent."""
    _verifier_classe_dans_ecole(db, donnees.id_classe, admin.id_ecole)
    eleve = models.Eleve(
        nom=donnees.nom, prenom=donnees.prenom, id_classe=donnees.id_classe, id_ecole=admin.id_ecole,
        numero_national=donnees.numero_national, numero_rim=donnees.numero_rim, numero_appel=donnees.numero_appel,
        photo_base64=donnees.photo_base64,
    )
    db.add(eleve)
    db.commit()
    db.refresh(eleve)
    return eleve


@router.get("/eleves/{id_eleve}")
def obtenir_eleve(id_eleve: int, db: Session = Depends(get_db), admin: models.AdminEcole = Depends(admin_ecole_courant)):
    """Fiche complète d'un élève — pour l'écran de consultation/modification."""
    eleve = _verifier_eleve_dans_ecole(db, id_eleve, admin.id_ecole)
    return {
        "id": eleve.id, "nom": eleve.nom, "prenom": eleve.prenom,
        "id_classe": eleve.id_classe, "classe": eleve.classe.nom,
        "numero_national": eleve.numero_national, "numero_rim": eleve.numero_rim,
        "numero_appel": eleve.numero_appel, "photo_base64": eleve.photo_base64,
    }


@router.patch("/eleves/{id_eleve}")
def modifier_eleve(id_eleve: int, donnees: schemas.EleveModification, db: Session = Depends(get_db), admin: models.AdminEcole = Depends(admin_ecole_courant)):
    """Modifie uniquement les champs fournis — les autres restent inchangés.
    Permet de changer le nom, la classe, les numéros ou la photo d'un élève déjà créé."""
    eleve = _verifier_eleve_dans_ecole(db, id_eleve, admin.id_ecole)
    valeurs = donnees.model_dump(exclude_unset=True)

    if "id_classe" in valeurs and valeurs["id_classe"] is not None:
        _verifier_classe_dans_ecole(db, valeurs["id_classe"], admin.id_ecole)

    for cle, valeur in valeurs.items():
        setattr(eleve, cle, valeur)

    db.commit()
    db.refresh(eleve)
    return {
        "id": eleve.id, "nom": eleve.nom, "prenom": eleve.prenom,
        "id_classe": eleve.id_classe, "classe": eleve.classe.nom,
        "numero_national": eleve.numero_national, "numero_rim": eleve.numero_rim,
        "numero_appel": eleve.numero_appel, "photo_base64": eleve.photo_base64,
    }


def _cle_tri_numero_appel(eleve: models.Eleve):
    """Tri 'naturel' sur le numéro d'appel (ex. 6A-2 avant 6A-10) — un simple tri
    alphabétique classerait 6A-10 avant 6A-2. Les élèves sans numéro d'appel sont
    placés à la fin."""
    texte = eleve.numero_appel or ""
    correspondance = re.search(r"(\d+)\s*$", texte)
    if correspondance:
        return (0, int(correspondance.group(1)), texte)
    if texte:
        return (1, 0, texte)
    return (2, 0, "")


@router.get("/classes/{id_classe}/eleves")
def lister_eleves_classe(id_classe: int, db: Session = Depends(get_db), admin: models.AdminEcole = Depends(admin_ecole_courant)):
    """Liste des élèves d'une classe, avec leur photo — pour l'écran d'identification
    visuelle et pour la saisie des notes. Volontairement séparé du listing général
    (plus léger, sans photo), car limité à une classe à la fois."""
    _verifier_classe_dans_ecole(db, id_classe, admin.id_ecole)
    eleves = db.query(models.Eleve).filter(models.Eleve.id_classe == id_classe).all()
    eleves = sorted(eleves, key=_cle_tri_numero_appel)
    return [
        {"id": e.id, "nom": e.nom, "prenom": e.prenom, "classe": e.classe.nom,
         "numero_appel": e.numero_appel, "photo_base64": e.photo_base64}
        for e in eleves
    ]


@router.get("/classes")
def lister_classes(db: Session = Depends(get_db), admin: models.AdminEcole = Depends(admin_ecole_courant)):
    classes = db.query(models.Classe).filter(models.Classe.id_ecole == admin.id_ecole).order_by(models.Classe.nom).all()
    return [{"id": c.id, "nom": c.nom, "niveau": c.niveau} for c in classes]


@router.get("/matieres")
def lister_matieres(db: Session = Depends(get_db), admin: models.AdminEcole = Depends(admin_ecole_courant)):
    matieres = db.query(models.Matiere).filter(models.Matiere.id_ecole == admin.id_ecole).order_by(models.Matiere.nom).all()
    return [{"id": m.id, "nom": m.nom} for m in matieres]


@router.get("/eleves")
def lister_eleves(db: Session = Depends(get_db), admin: models.AdminEcole = Depends(admin_ecole_courant)):
    eleves = db.query(models.Eleve).filter(models.Eleve.id_ecole == admin.id_ecole).order_by(models.Eleve.nom).all()
    return [
        {"id": e.id, "nom": e.nom, "prenom": e.prenom, "classe": e.classe.nom, "id_classe": e.id_classe,
         "numero_national": e.numero_national, "numero_rim": e.numero_rim, "numero_appel": e.numero_appel,
         "a_une_photo": e.photo_base64 is not None}
        for e in eleves
    ]


@router.get("/eleves/recherche")
def rechercher_eleves(q: str, db: Session = Depends(get_db), admin: models.AdminEcole = Depends(admin_ecole_courant)):
    """Recherche par nom/prénom, restreinte aux élèves de l'école de l'admin connecté."""
    motif = f"%{q}%"
    eleves = db.query(models.Eleve).filter(
        models.Eleve.id_ecole == admin.id_ecole,
    ).filter(
        (models.Eleve.nom.ilike(motif)) | (models.Eleve.prenom.ilike(motif))
    ).all()
    return [
        {"id": e.id, "nom": e.nom, "prenom": e.prenom, "classe": e.classe.nom, "a_une_photo": e.photo_base64 is not None}
        for e in eleves
    ]


@router.post("/eleves/{id_eleve}/photo")
def definir_photo_eleve(id_eleve: int, donnees: schemas.PhotoEleve, db: Session = Depends(get_db), admin: models.AdminEcole = Depends(admin_ecole_courant)):
    """Ajoute ou remplace la photo d'un élève — envoyée encodée en base64 depuis le site
    (déjà redimensionnée côté navigateur pour rester légère)."""
    eleve = _verifier_eleve_dans_ecole(db, id_eleve, admin.id_ecole)
    eleve.photo_base64 = donnees.photo_base64
    db.commit()
    return {"message": "Photo enregistrée."}


@router.delete("/eleves/{id_eleve}/photo")
def supprimer_photo_eleve(id_eleve: int, db: Session = Depends(get_db), admin: models.AdminEcole = Depends(admin_ecole_courant)):
    eleve = _verifier_eleve_dans_ecole(db, id_eleve, admin.id_ecole)
    eleve.photo_base64 = None
    db.commit()
    return {"message": "Photo supprimée."}


# --- Demandes d'attribution parent <-> élève ---

@router.get("/demandes-en-attente")
def demandes_en_attente(db: Session = Depends(get_db), admin: models.AdminEcole = Depends(admin_ecole_courant)):
    demandes = db.query(models.DemandeAttribution).filter(
        models.DemandeAttribution.id_ecole == admin.id_ecole,
        models.DemandeAttribution.statut == models.StatutDemande.en_attente,
    ).all()
    return [
        {"id_demande": d.id, "id_parent": d.id_parent, "parent": d.parent.nom, "telephone_parent": d.parent.numero_telephone,
         "enfant_indique": f"{d.prenom_enfant_indique} {d.nom_enfant_indique}"}
        for d in demandes
    ]


@router.post("/demandes/{id_demande}/attribuer")
def attribuer_eleve(id_demande: int, id_eleve: int, db: Session = Depends(get_db), admin: models.AdminEcole = Depends(admin_ecole_courant)):
    """L'école choisit explicitement l'élève exact à rattacher au parent — c'est le seul moyen de créer le lien."""
    demande = db.query(models.DemandeAttribution).get(id_demande)
    if not demande or demande.id_ecole != admin.id_ecole:
        raise HTTPException(status_code=404, detail="Demande introuvable.")

    eleve = _verifier_eleve_dans_ecole(db, id_eleve, admin.id_ecole)

    lien_existant = db.query(models.ParentEleve).filter(
        models.ParentEleve.id_parent == demande.id_parent,
        models.ParentEleve.id_eleve == eleve.id,
    ).first()
    if not lien_existant:
        db.add(models.ParentEleve(id_parent=demande.id_parent, id_eleve=eleve.id))

    demande.statut = models.StatutDemande.traitee
    db.commit()
    return {"message": f"{eleve.prenom} {eleve.nom} attribué au parent.", "id_parent": demande.id_parent}


@router.post("/demandes/{id_demande}/refuser")
def refuser_demande(id_demande: int, db: Session = Depends(get_db), admin: models.AdminEcole = Depends(admin_ecole_courant)):
    demande = db.query(models.DemandeAttribution).get(id_demande)
    if not demande or demande.id_ecole != admin.id_ecole:
        raise HTTPException(status_code=404, detail="Demande introuvable.")
    demande.statut = models.StatutDemande.traitee
    db.commit()
    return {"message": "Demande refusée."}


# --- Parents connus de l'école (au-delà des demandes) : ajouter un enfant à tout moment ---

@router.get("/parents/recherche")
def rechercher_parents(q: str, db: Session = Depends(get_db), admin: models.AdminEcole = Depends(admin_ecole_courant)):
    """Recherche parmi les parents déjà connus de cette école (via une demande ou un enfant déjà
    attribué) — jamais parmi tous les parents de la plateforme, pour rester cloisonné par école."""
    motif = f"%{q}%"
    ids_via_demandes = db.query(models.DemandeAttribution.id_parent).filter(models.DemandeAttribution.id_ecole == admin.id_ecole)
    ids_via_enfants = db.query(models.ParentEleve.id_parent).join(models.Eleve).filter(models.Eleve.id_ecole == admin.id_ecole)
    ids_connus = {row[0] for row in ids_via_demandes.union(ids_via_enfants).all()}

    if not ids_connus:
        return []

    parents = db.query(models.Parent).filter(
        models.Parent.id.in_(ids_connus),
    ).filter(
        (models.Parent.nom.ilike(motif)) | (models.Parent.numero_telephone.ilike(motif))
    ).all()
    return [{"id": p.id, "nom": p.nom, "telephone": p.numero_telephone} for p in parents]


@router.get("/parents/{id_parent}/enfants")
def enfants_du_parent(id_parent: int, db: Session = Depends(get_db), admin: models.AdminEcole = Depends(admin_ecole_courant)):
    """Enfants déjà attribués à ce parent, limités à ceux de l'école de l'admin connecté."""
    liens = db.query(models.ParentEleve).join(models.Eleve).filter(
        models.ParentEleve.id_parent == id_parent,
        models.Eleve.id_ecole == admin.id_ecole,
    ).all()
    return [{"id_eleve": lien.eleve.id, "nom": lien.eleve.nom, "prenom": lien.eleve.prenom, "classe": lien.eleve.classe.nom} for lien in liens]


@router.post("/parents/{id_parent}/attribuer")
def attribuer_enfant_supplementaire(id_parent: int, id_eleve: int, db: Session = Depends(get_db), admin: models.AdminEcole = Depends(admin_ecole_courant)):
    """Rattache un enfant supplémentaire à un parent déjà connu de l'école — utilisable à tout
    moment, avant ou après le traitement d'une demande, sans repasser par une nouvelle inscription."""
    parent = db.query(models.Parent).get(id_parent)
    if not parent:
        raise HTTPException(status_code=404, detail="Parent introuvable.")
    eleve = _verifier_eleve_dans_ecole(db, id_eleve, admin.id_ecole)

    lien_existant = db.query(models.ParentEleve).filter(
        models.ParentEleve.id_parent == id_parent,
        models.ParentEleve.id_eleve == eleve.id,
    ).first()
    if lien_existant:
        return {"message": f"{eleve.prenom} {eleve.nom} était déjà rattaché à ce parent."}

    db.add(models.ParentEleve(id_parent=id_parent, id_eleve=eleve.id))
    db.commit()
    return {"message": f"{eleve.prenom} {eleve.nom} rattaché au parent."}


@router.delete("/parents/{id_parent}/enfants/{id_eleve}")
def detacher_enfant(id_parent: int, id_eleve: int, db: Session = Depends(get_db), admin: models.AdminEcole = Depends(admin_ecole_courant)):
    """Retire le lien entre un parent et un enfant — utile en cas de rattachement fait
    par erreur. Ne supprime jamais l'élève ni le parent, seulement le lien entre eux."""
    eleve = _verifier_eleve_dans_ecole(db, id_eleve, admin.id_ecole)
    lien = db.query(models.ParentEleve).filter(
        models.ParentEleve.id_parent == id_parent,
        models.ParentEleve.id_eleve == eleve.id,
    ).first()
    if not lien:
        raise HTTPException(status_code=404, detail="Ce lien n'existe pas.")
    db.delete(lien)
    db.commit()
    return {"message": f"{eleve.prenom} {eleve.nom} détaché de ce parent."}


@router.post("/parents/{id_parent}/reinitialiser-mot-de-passe")
def reinitialiser_mot_de_passe_parent(id_parent: int, db: Session = Depends(get_db), admin: models.AdminEcole = Depends(admin_ecole_courant)):
    """Génère un nouveau mot de passe temporaire pour un parent connu de cette école —
    à communiquer de vive voix ou par SMS manuel. Réservé aux parents ayant au moins un
    enfant ou une demande dans l'école de l'admin connecté (cloisonnement)."""
    connu = db.query(models.ParentEleve).join(models.Eleve).filter(
        models.ParentEleve.id_parent == id_parent, models.Eleve.id_ecole == admin.id_ecole,
    ).first() or db.query(models.DemandeAttribution).filter(
        models.DemandeAttribution.id_parent == id_parent, models.DemandeAttribution.id_ecole == admin.id_ecole,
    ).first()
    if not connu:
        raise HTTPException(status_code=404, detail="Ce parent n'est pas connu de votre école.")

    parent = db.query(models.Parent).get(id_parent)
    nouveau_mot_de_passe = generer_mot_de_passe_temporaire()
    parent.mot_de_passe_hash = hacher_mot_de_passe(nouveau_mot_de_passe)
    db.commit()
    return {"message": "Mot de passe réinitialisé.", "nouveau_mot_de_passe": nouveau_mot_de_passe}


# --- Notes, absences, emploi du temps ---

@router.post("/notes")
def ajouter_note(donnees: schemas.NoteCreation, db: Session = Depends(get_db), admin: models.AdminEcole = Depends(admin_ecole_courant)):
    _verifier_eleve_dans_ecole(db, donnees.id_eleve, admin.id_ecole)
    valeurs = donnees.model_dump()
    valeurs["type"] = valeurs.pop("type_evaluation")
    note = models.Note(**valeurs)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.get("/notes/numeros")
def lister_numeros_notes(
    id_classe: int, id_matiere: int, type_evaluation: str,
    db: Session = Depends(get_db), admin: models.AdminEcole = Depends(admin_ecole_courant),
):
    """Numéros déjà utilisés pour cette classe/matière/type (ex. [1, 2] si un 1er et un
    2e devoir existent déjà) — permet au site de proposer de reprendre une saisie en
    cours, ou de suggérer le numéro suivant."""
    _verifier_classe_dans_ecole(db, id_classe, admin.id_ecole)
    _verifier_matiere_dans_ecole(db, id_matiere, admin.id_ecole)
    numeros = db.query(models.Note.numero).join(models.Eleve).filter(
        models.Eleve.id_classe == id_classe,
        models.Note.id_matiere == id_matiere,
        models.Note.type == type_evaluation,
    ).distinct().all()
    return sorted({n[0] for n in numeros})


@router.get("/notes/grille")
def lire_grille_notes(
    id_classe: int, id_matiere: int, type_evaluation: str, numero: int,
    db: Session = Depends(get_db), admin: models.AdminEcole = Depends(admin_ecole_courant),
):
    """Notes déjà saisies pour cette évaluation précise — permet de pré-remplir la
    grille si l'admin reprend une saisie commencée plus tôt."""
    _verifier_classe_dans_ecole(db, id_classe, admin.id_ecole)
    _verifier_matiere_dans_ecole(db, id_matiere, admin.id_ecole)
    notes = db.query(models.Note).join(models.Eleve).filter(
        models.Eleve.id_classe == id_classe,
        models.Note.id_matiere == id_matiere,
        models.Note.type == type_evaluation,
        models.Note.numero == numero,
    ).all()
    return [{"id_eleve": n.id_eleve, "valeur": n.valeur} for n in notes]


@router.post("/notes/grille")
def enregistrer_grille_notes(
    donnees: schemas.NoteGrilleEnregistrement,
    db: Session = Depends(get_db), admin: models.AdminEcole = Depends(admin_ecole_courant),
):
    """Enregistre (ou met à jour) les notes de plusieurs élèves en une fois, pour une
    évaluation précise (classe + matière + type + numéro). Peut être appelé plusieurs
    fois de suite — chaque élève déjà noté est mis à jour, les autres sont ajoutés,
    sans jamais dupliquer une note pour le même élève sur la même évaluation."""
    _verifier_classe_dans_ecole(db, donnees.id_classe, admin.id_ecole)
    _verifier_matiere_dans_ecole(db, donnees.id_matiere, admin.id_ecole)

    compte = 0
    for entree in donnees.notes:
        _verifier_eleve_dans_ecole(db, entree.id_eleve, admin.id_ecole)
        existante = db.query(models.Note).filter(
            models.Note.id_eleve == entree.id_eleve,
            models.Note.id_matiere == donnees.id_matiere,
            models.Note.type == donnees.type_evaluation,
            models.Note.numero == donnees.numero,
        ).first()
        if existante:
            existante.valeur = entree.valeur
        else:
            db.add(models.Note(
                id_eleve=entree.id_eleve, id_matiere=donnees.id_matiere,
                valeur=entree.valeur, type=donnees.type_evaluation, numero=donnees.numero,
            ))
        compte += 1

    db.commit()
    return {"message": f"{compte} note(s) enregistrée(s)."}


@router.post("/absences")
def ajouter_absence(donnees: schemas.AbsenceCreation, db: Session = Depends(get_db), admin: models.AdminEcole = Depends(admin_ecole_courant)):
    _verifier_eleve_dans_ecole(db, donnees.id_eleve, admin.id_ecole)
    _verifier_matiere_dans_ecole(db, donnees.id_matiere, admin.id_ecole)
    absence = models.Absence(**donnees.model_dump())
    db.add(absence)
    db.commit()
    db.refresh(absence)
    return absence


@router.get("/classes/{id_classe}/emploi-du-temps")
def lire_emploi_du_temps_classe(id_classe: int, db: Session = Depends(get_db), admin: models.AdminEcole = Depends(admin_ecole_courant)):
    _verifier_classe_dans_ecole(db, id_classe, admin.id_ecole)
    creneaux = db.query(models.CreneauEmploiDuTemps).filter(
        models.CreneauEmploiDuTemps.id_classe == id_classe
    ).order_by(models.CreneauEmploiDuTemps.jour, models.CreneauEmploiDuTemps.heure_debut).all()
    return [
        {"id": c.id, "id_matiere": c.id_matiere, "matiere": c.matiere.nom, "jour": c.jour,
         "heure_debut": c.heure_debut.strftime("%H:%M"), "heure_fin": c.heure_fin.strftime("%H:%M")}
        for c in creneaux
    ]


@router.post("/classes/{id_classe}/emploi-du-temps")
def enregistrer_emploi_du_temps_classe(
    id_classe: int,
    creneaux: list[schemas.CreneauSansClasse],
    db: Session = Depends(get_db),
    admin: models.AdminEcole = Depends(admin_ecole_courant),
):
    """Remplace tout l'emploi du temps de la classe en une fois — l'école construit sa semaine
    complète puis enregistre en un seul geste, plutôt que créneau par créneau."""
    _verifier_classe_dans_ecole(db, id_classe, admin.id_ecole)

    db.query(models.CreneauEmploiDuTemps).filter(models.CreneauEmploiDuTemps.id_classe == id_classe).delete()

    for c in creneaux:
        db.add(models.CreneauEmploiDuTemps(
            id_classe=id_classe, id_matiere=c.id_matiere, jour=c.jour,
            heure_debut=c.heure_debut, heure_fin=c.heure_fin,
        ))
    db.commit()
    return {"message": f"{len(creneaux)} créneau(x) enregistré(s)."}
