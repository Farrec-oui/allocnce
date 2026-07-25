"""Authentification JWT + hachage des mots de passe.

Le hachage utilise `bcrypt` directement plutôt que passlib : passlib 1.7.4
(dernière version, 2020) est incompatible avec bcrypt >= 4.1 et lève une
ValueError au chargement du backend.
"""
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from database import get_db
from models import User

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 8

# bcrypt ignore silencieusement tout octet au-delà de 72 : on tronque
# explicitement pour que hachage et vérification restent cohérents.
_BCRYPT_MAX_BYTES = 72

_SECRET_FILE = Path(__file__).resolve().parent.parent / ".secret_key"


def _load_secret_key() -> str:
    """SECRET_KEY depuis l'env, sinon depuis un fichier local persistant.

    En dev le fichier évite d'invalider tous les tokens à chaque redémarrage
    d'uvicorn --reload. En production, définir SECRET_KEY dans l'environnement.
    """
    env = os.getenv("SECRET_KEY")
    if env:
        return env

    if _SECRET_FILE.exists():
        key = _SECRET_FILE.read_text().strip()
        if key:
            return key

    key = secrets.token_hex(32)
    _SECRET_FILE.write_text(key)
    _SECRET_FILE.chmod(0o600)
    logger.warning(
        "SECRET_KEY absent de l'environnement — clé générée dans %s. "
        "Définir SECRET_KEY en production.",
        _SECRET_FILE.name,
    )
    return key


SECRET_KEY = _load_secret_key()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ---------------------------------------------------------------------------
# Mots de passe
# ---------------------------------------------------------------------------

def _pw_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(_pw_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(_pw_bytes(plain_password), hashed_password.encode("utf-8"))
    except ValueError:
        # Hash malformé en base — on refuse sans faire tomber la requête.
        return False


# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> dict | None:
    """Décode un token. Retourne le payload, ou None si invalide/expiré."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# Dépendances FastAPI
# ---------------------------------------------------------------------------

_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Session invalide ou expirée, veuillez vous reconnecter",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = verify_token(token)
    if payload is None:
        raise _CREDENTIALS_EXC

    subject = payload.get("sub")
    if subject is None:
        raise _CREDENTIALS_EXC

    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        raise _CREDENTIALS_EXC

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise _CREDENTIALS_EXC
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce compte a été désactivé",
        )
    return user


def get_current_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs",
        )
    return user
