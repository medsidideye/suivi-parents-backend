"""
Crée le compte super-admin initial. À exécuter une seule fois, en local ou sur le serveur,
JAMAIS via une route API publique (sinon n'importe qui pourrait s'auto-nommer super-admin).

Usage :
    python -m app.core.creer_super_admin
"""
import getpass
from app.core.database import SessionLocal, Base, engine
from app.core.security import hacher_mot_de_passe
from app.models import models

Base.metadata.create_all(bind=engine)


def main():
    db = SessionLocal()
    nom = input("Nom : ")
    email = input("Email : ")
    mot_de_passe = getpass.getpass("Mot de passe : ")

    if db.query(models.SuperAdmin).filter(models.SuperAdmin.email == email).first():
        print("Un compte avec cet email existe déjà.")
        return

    superadmin = models.SuperAdmin(nom=nom, email=email, mot_de_passe_hash=hacher_mot_de_passe(mot_de_passe))
    db.add(superadmin)
    db.commit()
    print(f"Super-admin '{nom}' créé avec succès.")


if __name__ == "__main__":
    main()
