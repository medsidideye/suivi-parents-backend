import os
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt

SECRET_KEY = os.environ.get("SECRET_KEY", "change-moi-en-production")
ALGORITHM = "HS256"
EXPIRATION_MINUTES = 60 * 24  # 24h

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hacher_mot_de_passe(mot_de_passe: str) -> str:
    return pwd_context.hash(mot_de_passe)


def verifier_mot_de_passe(mot_de_passe: str, hash_stocke: str) -> bool:
    return pwd_context.verify(mot_de_passe, hash_stocke)


def creer_token(donnees: dict) -> str:
    a_encoder = donnees.copy()
    expiration = datetime.utcnow() + timedelta(minutes=EXPIRATION_MINUTES)
    a_encoder.update({"exp": expiration})
    return jwt.encode(a_encoder, SECRET_KEY, algorithm=ALGORITHM)


def decoder_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def generer_mot_de_passe_temporaire() -> str:
    """Génère un mot de passe temporaire lisible (6 chiffres), à communiquer à l'utilisateur
    par l'école ou le super-admin — il devra idéalement le changer à sa prochaine connexion."""
    import secrets
    return "".join(secrets.choice("0123456789") for _ in range(6))

