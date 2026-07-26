import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import User
from schemas import (
    Token,
    UserOut,
    UserRegister,
    UserSelfUpdate,
)
from services.auth import (
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _issue_token(user: User) -> Token:
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return Token(access_token=token, token_type="bearer", user=UserOut.model_validate(user))


# ---------------------------------------------------------------------------
# POST /auth/register
# ---------------------------------------------------------------------------

@router.post("/register", response_model=Token, status_code=201)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    email = _normalize_email(payload.email)

    exists = db.query(User).filter(func.lower(User.email) == email).first()
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Un compte existe déjà avec cet email")

    user = User(
        email=email,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name.strip(),
        role="user",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("Nouveau compte créé — id=%s email=%s", user.id, user.email)

    return _issue_token(user)


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------

@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    email = _normalize_email(form_data.username)
    user = db.query(User).filter(func.lower(User.email) == email).first()

    # Message identique dans les deux cas : ne pas révéler quels emails existent.
    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.info("Échec de connexion pour %s", email)
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Email ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Ce compte a été désactivé")

    user.last_login = datetime.utcnow()
    db.commit()
    db.refresh(user)
    logger.info("Connexion — id=%s email=%s", user.id, user.email)

    return _issue_token(user)


# ---------------------------------------------------------------------------
# POST /auth/logout
# ---------------------------------------------------------------------------

@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    """Les JWT sont sans état : la déconnexion effective consiste à supprimer
    le token côté client. Cet endpoint existe pour journaliser l'événement."""
    logger.info("Déconnexion — id=%s", current_user.id)
    return {"detail": "Déconnecté"}


# ---------------------------------------------------------------------------
# GET /auth/me  —  PATCH /auth/me
# ---------------------------------------------------------------------------

@router.get("/me", response_model=UserOut)
def read_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserOut)
def update_me(
    payload: UserSelfUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.full_name is not None:
        current_user.full_name = payload.full_name.strip()
    if payload.password is not None:
        current_user.hashed_password = get_password_hash(payload.password)

    db.commit()
    db.refresh(current_user)
    return current_user


# La gestion des comptes par un administrateur vit désormais dans
# routers/admin.py (/admin/users), avec le comptage d'allocations et la
# création de comptes.
