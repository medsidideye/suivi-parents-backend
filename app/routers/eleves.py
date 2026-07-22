from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import utilisateur_courant
from app.models import models
from app.schemas import schemas

router = APIRouter(prefix="/eleves", tags=["élèves"])

SEUIL_POINT_FORT = 10.0
MAX_POINTS = 3


def _verifier_acces_eleve(db: Session, id_eleve: int, payload: dict) -> models.Eleve:
    """Autorise seulement : le parent validé de cet élève, ou l'admin de l'école de cet élève."""
    eleve = db.query(models.Eleve).get(id_eleve)
    if not eleve:
        raise HTTPException(status_code=404, detail="Élève introuvable.")

    role = payload.get("role")
    if role == "admin_ecole" and payload.get("id_ecole") == eleve.id_ecole:
        return eleve

    if role == "parent":
        lien = db.query(models.ParentEleve).filter(
            models.ParentEleve.id_parent == int(payload["sub"]),
            models.ParentEleve.id_eleve == id_eleve,
        ).first()
        if lien:
            return eleve

    raise HTTPException(status_code=403, detail="Vous n'avez pas accès à cet élève.")


def moyenne_eleve(db: Session, id_eleve: int) -> float | None:
    notes = db.query(models.Note).filter(models.Note.id_eleve == id_eleve).all()
    if not notes:
        return None
    return round(sum(n.valeur for n in notes) / len(notes), 2)


def moyennes_par_matiere(db: Session, id_eleve: int) -> list[schemas.MatiereScore]:
    notes = db.query(models.Note).filter(models.Note.id_eleve == id_eleve).all()
    par_matiere: dict[str, list[float]] = {}
    for n in notes:
        par_matiere.setdefault(n.matiere.nom, []).append(n.valeur)
    return [
        schemas.MatiereScore(matiere=nom, moyenne=round(sum(vals) / len(vals), 2))
        for nom, vals in par_matiere.items()
    ]


@router.get("/{id_eleve}/stats", response_model=schemas.StatsEleve)
def stats_eleve(id_eleve: int, db: Session = Depends(get_db), payload: dict = Depends(utilisateur_courant)):
    eleve = _verifier_acces_eleve(db, id_eleve, payload)

    moyenne = moyenne_eleve(db, id_eleve)
    scores = moyennes_par_matiere(db, id_eleve)
    forts = sorted([s for s in scores if s.moyenne > SEUIL_POINT_FORT], key=lambda s: -s.moyenne)[:MAX_POINTS]
    faibles = sorted([s for s in scores if s.moyenne <= SEUIL_POINT_FORT], key=lambda s: s.moyenne)[:MAX_POINTS]

    camarades = db.query(models.Eleve).filter(models.Eleve.id_classe == eleve.id_classe).all()
    moyennes_classe = []
    for camarade in camarades:
        m = moyenne_eleve(db, camarade.id)
        if m is not None:
            moyennes_classe.append((camarade.id, m))

    moyenne_classe = round(sum(m for _, m in moyennes_classe) / len(moyennes_classe), 2) if moyennes_classe else None

    classement = None
    if moyenne is not None and moyennes_classe:
        classes_triees = sorted(moyennes_classe, key=lambda t: -t[1])
        for rang, (id_c, _) in enumerate(classes_triees, start=1):
            if id_c == id_eleve:
                classement = rang
                break

    absences = db.query(models.Absence).filter(models.Absence.id_eleve == id_eleve).all()
    aujourd_hui = date.today()
    absences_mois = sum(a.duree_heures for a in absences if a.date.month == aujourd_hui.month and a.date.year == aujourd_hui.year)
    absences_annee = sum(a.duree_heures for a in absences if a.date.year == aujourd_hui.year)

    return schemas.StatsEleve(
        eleve=f"{eleve.prenom} {eleve.nom}",
        classe=eleve.classe.nom,
        moyenne_generale=moyenne,
        moyenne_classe=moyenne_classe,
        classement=classement,
        effectif_classe=len(camarades),
        points_forts=forts,
        points_faibles=faibles,
        absences_mois=absences_mois,
        absences_annee=absences_annee,
    )


@router.get("/{id_eleve}/profil", response_model=schemas.ProfilEleve)
def profil_eleve(id_eleve: int, db: Session = Depends(get_db), payload: dict = Depends(utilisateur_courant)):
    """Fiche d'identité de l'élève — numéros, classe, photo. Distinct des statistiques
    scolaires (moyenne, classement...), qui restent sur /stats."""
    eleve = _verifier_acces_eleve(db, id_eleve, payload)
    return schemas.ProfilEleve(
        eleve=f"{eleve.prenom} {eleve.nom}",
        classe=eleve.classe.nom,
        ecole=eleve.ecole.nom,
        numero_national=eleve.numero_national,
        numero_rim=eleve.numero_rim,
        numero_appel=eleve.numero_appel,
        photo_base64=eleve.photo_base64,
    )


@router.get("/{id_eleve}/notes", response_model=list[schemas.NoteDetail])
def notes_eleve(id_eleve: int, db: Session = Depends(get_db), payload: dict = Depends(utilisateur_courant)):
    """Liste détaillée des notes — le site la répartit ensuite entre les onglets
    Devoirs, Examens, et Derniers résultats (30 derniers jours)."""
    _verifier_acces_eleve(db, id_eleve, payload)
    notes = db.query(models.Note).filter(models.Note.id_eleve == id_eleve).order_by(models.Note.date.desc()).all()
    return [
        schemas.NoteDetail(matiere=n.matiere.nom, valeur=n.valeur, type=n.type.value, date=n.date)
        for n in notes
    ]


@router.get("/{id_eleve}/emploi-du-temps")
def emploi_du_temps_eleve(id_eleve: int, db: Session = Depends(get_db), payload: dict = Depends(utilisateur_courant)):
    eleve = _verifier_acces_eleve(db, id_eleve, payload)

    creneaux = db.query(models.CreneauEmploiDuTemps).filter(
        models.CreneauEmploiDuTemps.id_classe == eleve.id_classe
    ).order_by(models.CreneauEmploiDuTemps.jour, models.CreneauEmploiDuTemps.heure_debut).all()

    return [
        {"jour": c.jour, "heure_debut": c.heure_debut.strftime("%H:%M"),
         "heure_fin": c.heure_fin.strftime("%H:%M"), "matiere": c.matiere.nom}
        for c in creneaux
    ]
