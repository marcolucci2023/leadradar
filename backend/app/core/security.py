from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings

# Algorithme de chiffrement du JWT
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """
    Transforme un mot de passe en clair en une empreinte illisible.
    Exemple : 'monmotdepasse' → '$2b$12$K8x...'
    Même mot de passe = empreinte différente à chaque fois (grâce au 'salt').
    """
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Vérifie si un mot de passe en clair correspond à l'empreinte stockée.
    Renvoie True si ça matche, False sinon.
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def create_access_token(data: dict) -> str:
    """
    Crée un token JWT qui contient l'identité de l'utilisateur.
    Le token expire après ACCESS_TOKEN_EXPIRE_MINUTES (24h par défaut).
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """
    Décode un token JWT et renvoie les données qu'il contient.
    Lève une erreur si le token est invalide ou expiré.
    """
    payload = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[ALGORITHM],
    )
    return payload