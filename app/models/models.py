import enum
from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Date, DateTime,
    ForeignKey, Enum, Time, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class StatutEcole(str, enum.Enum):
    actif = "actif"
    en_attente = "en_attente"
    suspendu = "suspendu"


class StatutValidation(str, enum.Enum):
    en_attente = "en_attente"
    valide = "valide"
    refuse = "refuse"


class TypeNote(str, enum.Enum):
    devoir = "devoir"
    examen = "examen"


# --- Comptes ---

class SuperAdmin(Base):
    __tablename__ = "super_admins"
    id = Column(Integer, primary_key=True)
    nom = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    mot_de_passe_hash = Column(String, nullable=False)
    cree_le = Column(DateTime, default=datetime.utcnow)


class Ecole(Base):
    __tablename__ = "ecoles"
    id = Column(Integer, primary_key=True)
    nom = Column(String, nullable=False)
    adresse = Column(String, nullable=True)
    statut = Column(Enum(StatutEcole), default=StatutEcole.en_attente)
    cree_le = Column(DateTime, default=datetime.utcnow)

    admins = relationship("AdminEcole", back_populates="ecole", cascade="all, delete-orphan")
    classes = relationship("Classe", back_populates="ecole", cascade="all, delete-orphan")
    eleves = relationship("Eleve", back_populates="ecole", cascade="all, delete-orphan")
    matieres = relationship("Matiere", back_populates="ecole", cascade="all, delete-orphan")


class AdminEcole(Base):
    __tablename__ = "admins_ecole"
    id = Column(Integer, primary_key=True)
    nom = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    mot_de_passe_hash = Column(String, nullable=True)
    code_verification_hash = Column(String, nullable=True)
    id_ecole = Column(Integer, ForeignKey("ecoles.id"), nullable=False)
    cree_le = Column(DateTime, default=datetime.utcnow)

    ecole = relationship("Ecole", back_populates="admins")


class Parent(Base):
    __tablename__ = "parents"
    id = Column(Integer, primary_key=True)
    nom = Column(String, nullable=False)
    numero_telephone = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=True, index=True)
    mot_de_passe_hash = Column(String, nullable=False)
    cree_le = Column(DateTime, default=datetime.utcnow)

    liens_eleves = relationship("ParentEleve", back_populates="parent", cascade="all, delete-orphan")


# --- Structure scolaire ---

class Classe(Base):
    __tablename__ = "classes"
    id = Column(Integer, primary_key=True)
    nom = Column(String, nullable=False)          # ex: "6e A"
    niveau = Column(String, nullable=True)         # ex: "6e"
    id_ecole = Column(Integer, ForeignKey("ecoles.id"), nullable=False)

    ecole = relationship("Ecole", back_populates="classes")
    eleves = relationship("Eleve", back_populates="classe")
    creneaux = relationship("CreneauEmploiDuTemps", back_populates="classe", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("nom", "id_ecole", name="uq_classe_nom_ecole"),)


class Matiere(Base):
    __tablename__ = "matieres"
    id = Column(Integer, primary_key=True)
    nom = Column(String, nullable=False)           # ex: "Histoire-géo"
    id_ecole = Column(Integer, ForeignKey("ecoles.id"), nullable=False)

    ecole = relationship("Ecole", back_populates="matieres")

    __table_args__ = (UniqueConstraint("nom", "id_ecole", name="uq_matiere_nom_ecole"),)


class Eleve(Base):
    __tablename__ = "eleves"
    id = Column(Integer, primary_key=True)
    nom = Column(String, nullable=False)
    prenom = Column(String, nullable=False)
    id_classe = Column(Integer, ForeignKey("classes.id"), nullable=False)
    id_ecole = Column(Integer, ForeignKey("ecoles.id"), nullable=False)
    numero_national = Column(String, nullable=True)
    numero_rim = Column(String, nullable=True)
    numero_appel = Column(String, nullable=True)
    photo_base64 = Column(Text, nullable=True)

    classe = relationship("Classe", back_populates="eleves")
    ecole = relationship("Ecole", back_populates="eleves")
    notes = relationship("Note", back_populates="eleve", cascade="all, delete-orphan")
    absences = relationship("Absence", back_populates="eleve", cascade="all, delete-orphan")
    liens_parents = relationship("ParentEleve", back_populates="eleve", cascade="all, delete-orphan")


class ParentEleve(Base):
    """Table de liaison parent <-> élève, créée uniquement quand l'école attribue explicitement un élève."""
    __tablename__ = "parent_eleve"
    id = Column(Integer, primary_key=True)
    id_parent = Column(Integer, ForeignKey("parents.id"), nullable=False)
    id_eleve = Column(Integer, ForeignKey("eleves.id"), nullable=False)
    attribue_le = Column(DateTime, default=datetime.utcnow)

    parent = relationship("Parent", back_populates="liens_eleves")
    eleve = relationship("Eleve", back_populates="liens_parents")

    __table_args__ = (UniqueConstraint("id_parent", "id_eleve", name="uq_parent_eleve"),)


class StatutDemande(str, enum.Enum):
    en_attente = "en_attente"
    traitee = "traitee"


class DemandeAttribution(Base):
    """Demande déposée par un parent à l'inscription : nom d'enfant donné à titre indicatif,
    l'école recherche et attribue elle-même l'élève exact — jamais de création automatique."""
    __tablename__ = "demandes_attribution"
    id = Column(Integer, primary_key=True)
    id_parent = Column(Integer, ForeignKey("parents.id"), nullable=False)
    id_ecole = Column(Integer, ForeignKey("ecoles.id"), nullable=False)
    nom_enfant_indique = Column(String, nullable=False)
    prenom_enfant_indique = Column(String, nullable=False)
    statut = Column(Enum(StatutDemande), default=StatutDemande.en_attente)
    cree_le = Column(DateTime, default=datetime.utcnow)

    parent = relationship("Parent")
    ecole = relationship("Ecole")


# --- Pédagogie ---

class Note(Base):
    __tablename__ = "notes"
    id = Column(Integer, primary_key=True)
    id_eleve = Column(Integer, ForeignKey("eleves.id"), nullable=False)
    id_matiere = Column(Integer, ForeignKey("matieres.id"), nullable=False)
    valeur = Column(Float, nullable=False)          # note sur 20
    type = Column(Enum(TypeNote), default=TypeNote.devoir)
    numero = Column(Integer, nullable=False, default=1)   # 1er, 2e, 3e... devoir/examen de cette matière
    date = Column(Date, default=date.today)

    eleve = relationship("Eleve", back_populates="notes")
    matiere = relationship("Matiere")


class Absence(Base):
    __tablename__ = "absences"
    id = Column(Integer, primary_key=True)
    id_eleve = Column(Integer, ForeignKey("eleves.id"), nullable=False)
    id_matiere = Column(Integer, ForeignKey("matieres.id"), nullable=True)
    date = Column(Date, nullable=False)
    duree_heures = Column(Float, nullable=False)
    justifiee = Column(Boolean, default=False)
    observation = Column(Text, nullable=True)

    eleve = relationship("Eleve", back_populates="absences")
    matiere = relationship("Matiere")


class CreneauEmploiDuTemps(Base):
    __tablename__ = "creneaux_emploi_du_temps"
    id = Column(Integer, primary_key=True)
    id_classe = Column(Integer, ForeignKey("classes.id"), nullable=False)
    id_matiere = Column(Integer, ForeignKey("matieres.id"), nullable=False)
    jour = Column(String, nullable=False)           # "lundi", "mardi", ...
    heure_debut = Column(Time, nullable=False)
    heure_fin = Column(Time, nullable=False)

    classe = relationship("Classe", back_populates="creneaux")
    matiere = relationship("Matiere")
