from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decoder_token
from app.models import models

securite = HTTPBearer()


def _decoder_ou_401(credentials: HTTPAuthorizationCredentials) -> dict:
    try:
        return decoder_token(credentials.credentials)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide ou expiré.")


def utilisateur_courant(credentials: HTTPAuthorizationCredentials = Depends(securite)) -> dict:
    """Décode le token sans imposer de rôle précis — utile quand plusieurs rôles sont acceptés."""
    return _decoder_ou_401(credentials)


def parent_courant(
    credentials: HTTPAuthorizationCredentials = Depends(securite),
    db: Session = Depends(get_db),
) -> models.Parent:
    payload = _decoder_ou_401(credentials)
    if payload.get("role") != "parent":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé aux parents.")
    parent = db.query(models.Parent).get(int(payload["sub"]))
    if not parent:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Compte introuvable.")
    return parent


def admin_ecole_courant(
    credentials: HTTPAuthorizationCredentials = Depends(securite),
    db: Session = Depends(get_db),
) -> models.AdminEcole:
    payload = _decoder_ou_401(credentials)
    if payload.get("role") != "admin_ecole":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé aux administrateurs d'école.")
    admin = db.query(models.AdminEcole).get(int(payload["sub"]))
    if not admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Compte introuvable.")
    return admin


def super_admin_courant(
    credentials: HTTPAuthorizationCredentials = Depends(securite),
    db: Session = Depends(get_db),
) -> models.SuperAdmin:
    payload = _decoder_ou_401(credentials)
    if payload.get("role") != "super_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé au super-administrateur.")
    superadmin = db.query(models.SuperAdmin).get(int(payload["sub"]))
    if not superadmin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Compte introuvable.")
    return superadmin


def verifier_ecole_correspond(id_ecole_cible: int, admin: models.AdminEcole = Depends(admin_ecole_courant)) -> models.AdminEcole:
    """Empêche un admin d'une école d'agir sur les données d'une autre école — le cloisonnement multi-écoles."""
    if admin.id_ecole != id_ecole_cible:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous n'avez pas accès à cette école.")
    return admin
