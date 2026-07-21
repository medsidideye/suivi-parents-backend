"""
Réinitialise le mot de passe d'un compte super-admin existant, à partir de son email.
À utiliser si le super-admin oublie son mot de passe — s'exécute en local ou sur le
serveur, jamais via une route API publique.

Usage :
    python -m app.core.reinitialiser_super_admin
"""
import getpass
from app.core.database import SessionLocal
from app.core.security import hacher_mot_de_passe
from app.models import models


def main():
    db = SessionLocal()
    email = input("Email du super-admin : ")
    superadmin = db.query(models.SuperAdmin).filter(models.SuperAdmin.email == email).first()
    if not superadmin:
        print("Aucun super-admin avec cet email.")
        return

    nouveau_mot_de_passe = getpass.getpass("Nouveau mot de passe : ")
    superadmin.mot_de_passe_hash = hacher_mot_de_passe(nouveau_mot_de_passe)
    db.commit()
    print(f"Mot de passe de '{superadmin.nom}' réinitialisé avec succès.")


if __name__ == "__main__":
    main()
