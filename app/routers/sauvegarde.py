from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import super_admin_courant
from app.models import models

router = APIRouter(prefix="/sauvegarde", tags=["sauvegarde"])


@router.get("/export")
def exporter_toutes_les_donnees(db: Session = Depends(get_db), _: models.SuperAdmin = Depends(super_admin_courant)):
    """Export complet de toutes les données métier (hors mots de passe et codes de
    vérification, jamais inclus dans un export) — à télécharger et conserver en lieu
    sûr régulièrement, indépendamment de Neon. En cas de restauration nécessaire,
    ces données permettent de recréer l'état de l'application (les comptes devront
    être réactivés via réinitialisation de mot de passe, par sécurité)."""

    def ecole_vers_dict(e):
        return {"id": e.id, "nom": e.nom, "adresse": e.adresse, "statut": e.statut.value}

    def admin_vers_dict(a):
        return {"id": a.id, "nom": a.nom, "email": a.email, "id_ecole": a.id_ecole, "compte_active": a.mot_de_passe_hash is not None}

    def parent_vers_dict(p):
        return {"id": p.id, "nom": p.nom, "numero_telephone": p.numero_telephone}

    def classe_vers_dict(c):
        return {"id": c.id, "nom": c.nom, "niveau": c.niveau, "id_ecole": c.id_ecole}

    def matiere_vers_dict(m):
        return {"id": m.id, "nom": m.nom, "id_ecole": m.id_ecole}

    def eleve_vers_dict(e):
        return {
            "id": e.id, "nom": e.nom, "prenom": e.prenom, "id_classe": e.id_classe, "id_ecole": e.id_ecole,
            "numero_national": e.numero_national, "numero_rim": e.numero_rim, "numero_appel": e.numero_appel,
        }

    def parent_eleve_vers_dict(pe):
        return {"id_parent": pe.id_parent, "id_eleve": pe.id_eleve}

    def demande_vers_dict(d):
        return {
            "id": d.id, "id_parent": d.id_parent, "id_ecole": d.id_ecole,
            "nom_enfant_indique": d.nom_enfant_indique, "prenom_enfant_indique": d.prenom_enfant_indique,
            "statut": d.statut.value,
        }

    def note_vers_dict(n):
        return {"id_eleve": n.id_eleve, "id_matiere": n.id_matiere, "valeur": n.valeur, "type": n.type.value, "numero": n.numero, "date": str(n.date)}

    def absence_vers_dict(a):
        return {
            "id_eleve": a.id_eleve, "id_matiere": a.id_matiere, "date": str(a.date),
            "duree_heures": a.duree_heures, "justifiee": a.justifiee, "observation": a.observation,
        }

    def creneau_vers_dict(c):
        return {
            "id_classe": c.id_classe, "id_matiere": c.id_matiere, "jour": c.jour,
            "heure_debut": str(c.heure_debut), "heure_fin": str(c.heure_fin),
        }

    return {
        "ecoles": [ecole_vers_dict(x) for x in db.query(models.Ecole).all()],
        "admins_ecole": [admin_vers_dict(x) for x in db.query(models.AdminEcole).all()],
        "parents": [parent_vers_dict(x) for x in db.query(models.Parent).all()],
        "classes": [classe_vers_dict(x) for x in db.query(models.Classe).all()],
        "matieres": [matiere_vers_dict(x) for x in db.query(models.Matiere).all()],
        "eleves": [eleve_vers_dict(x) for x in db.query(models.Eleve).all()],
        "parent_eleve": [parent_eleve_vers_dict(x) for x in db.query(models.ParentEleve).all()],
        "demandes_attribution": [demande_vers_dict(x) for x in db.query(models.DemandeAttribution).all()],
        "notes": [note_vers_dict(x) for x in db.query(models.Note).all()],
        "absences": [absence_vers_dict(x) for x in db.query(models.Absence).all()],
        "creneaux_emploi_du_temps": [creneau_vers_dict(x) for x in db.query(models.CreneauEmploiDuTemps).all()],
    }
