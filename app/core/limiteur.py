"""
Limiteur de tentatives simple, en mémoire — protège les routes de connexion et de
code de vérification contre les essais répétés automatisés.

Volontairement en mémoire (pas de base de données ni de service externe) : simple,
sans dépendance, et suffisant tant que le serveur tourne en un seul processus
(c'est le cas sur Render, WEB_CONCURRENCY=1 par défaut). Le compteur se remet à
zéro à chaque redémarrage du serveur — sans conséquence, un redémarrage n'est pas
un événement qu'un attaquant peut déclencher à volonté.
"""
import time
from fastapi import HTTPException

MAX_TENTATIVES = 8
FENETRE_SECONDES = 15 * 60  # 15 minutes

_tentatives: dict[str, list[float]] = {}


def verifier_limite(cle: str):
    """Lève une erreur 429 si trop de tentatives récentes pour cette clé
    (ex. adresse IP + route). À appeler AVANT de vérifier le mot de passe/code."""
    maintenant = time.time()
    historique = _tentatives.get(cle, [])
    historique = [t for t in historique if maintenant - t < FENETRE_SECONDES]

    if len(historique) >= MAX_TENTATIVES:
        raise HTTPException(
            status_code=429,
            detail="Trop de tentatives. Réessayez dans quelques minutes.",
        )

    historique.append(maintenant)
    _tentatives[cle] = historique


def reinitialiser_limite(cle: str):
    """À appeler après une tentative réussie, pour ne pas pénaliser l'utilisateur
    légitime lors de sa prochaine connexion."""
    _tentatives.pop(cle, None)
