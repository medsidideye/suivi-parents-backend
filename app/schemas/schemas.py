from datetime import date as date_type, time
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# --- Écoles ---

class EcoleCreation(BaseModel):
    nom: str
    adresse: Optional[str] = None


class EcoleLecture(BaseModel):
    id: int
    nom: str
    statut: str

    class Config:
        from_attributes = True


# --- Parents ---

class EnfantDeclare(BaseModel):
    nom: str
    prenom: str


class ParentInscription(BaseModel):
    nom: str
    numero_telephone: str
    mot_de_passe: str
    id_ecole: int
    enfants: list[EnfantDeclare]


class ParentConnexion(BaseModel):
    numero_telephone: str
    mot_de_passe: str


class ConnexionEmail(BaseModel):
    """Connexion par email — réservée aux comptes professionnels (admin école, super-admin)."""
    email: EmailStr
    mot_de_passe: str


class ChangementMotDePasse(BaseModel):
    ancien_mot_de_passe: str
    nouveau_mot_de_passe: str


class BootstrapSuperAdmin(BaseModel):
    secret: str
    nom: str
    email: EmailStr
    mot_de_passe: str


class AdminEcoleCreation(BaseModel):
    nom: str
    email: EmailStr


class DefinirMotDePasseAdmin(BaseModel):
    email: EmailStr
    code_verification: str
    nouveau_mot_de_passe: str


class EleveCreation(BaseModel):
    nom: str
    prenom: str
    id_classe: int
    numero_national: Optional[str] = None
    numero_rim: Optional[str] = None
    numero_appel: Optional[str] = None


# --- Élèves / classes / matières ---

class ClasseCreation(BaseModel):
    nom: str
    niveau: Optional[str] = None


class MatiereCreation(BaseModel):
    nom: str


class NoteCreation(BaseModel):
    id_eleve: int
    id_matiere: int
    valeur: float
    type_evaluation: str = "devoir"
    date: date_type = Field(default_factory=date_type.today)


class AbsenceCreation(BaseModel):
    id_eleve: int
    id_matiere: int
    date: date_type
    duree_heures: float
    justifiee: bool = False
    observation: Optional[str] = None


class CreneauCreation(BaseModel):
    id_classe: int
    id_matiere: int
    jour: str
    heure_debut: time
    heure_fin: time


class CreneauSansClasse(BaseModel):
    id_matiere: int
    jour: str
    heure_debut: time
    heure_fin: time



# --- Statistiques élève (calculées, jamais stockées) ---

class MatiereScore(BaseModel):
    matiere: str
    moyenne: float


class StatsEleve(BaseModel):
    eleve: str
    classe: str
    moyenne_generale: Optional[float]
    moyenne_classe: Optional[float]
    classement: Optional[int]
    effectif_classe: int
    points_forts: list[MatiereScore]
    points_faibles: list[MatiereScore]
    absences_mois: float
    absences_annee: float
