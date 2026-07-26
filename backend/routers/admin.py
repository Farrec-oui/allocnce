"""Endpoints d'administration.

Tous exigent `get_current_admin`, déclaré à la fois sur le router (filet de
sécurité si un endpoint est ajouté sans dépendance) et sur chaque handler qui a
besoin de l'objet admin courant.

Note de conception : les routes de prévisualisation et de téléchargement sont
dupliquées ici plutôt que d'ouvrir une dérogation admin dans le `_owned_or_404`
de `routers/allocations.py`. Cette dérogation aurait aussi donné aux admins le
droit de supprimer et d'écraser les allocations des autres via les routes
ordinaires. Le cloisonnement par utilisateur reste donc strictement intact, et
tous les pouvoirs d'administration sont regroupés dans ce fichier.
"""
import logging
import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import Allocation, User
from schemas import (
    AdminAllocationOut,
    AdminAllocationPage,
    AdminStats,
    AdminUserCreate,
    AdminUserOut,
    AdminUserUpdate,
    AllocsByType,
    TopUser,
)
from services.auth import get_current_admin, get_password_hash
from services.docx_preview import docx_to_html

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_admin)],
)

ALLOC_TYPES = ("creation", "prealloc", "alloc_finale", "maj")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _alloc_counts(db: Session) -> dict[int, int]:
    """{user_id: nombre d'allocations} en une seule requête groupée."""
    rows = (
        db.query(Allocation.user_id, func.count(Allocation.id))
        .filter(Allocation.user_id.isnot(None))
        .group_by(Allocation.user_id)
        .all()
    )
    return {user_id: count for user_id, count in rows}


def _to_admin_user(user: User, counts: dict[int, int]) -> AdminUserOut:
    return AdminUserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login=user.last_login,
        alloc_count=counts.get(user.id, 0),
    )


def _get_user_or_404(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Utilisateur introuvable")
    return user


def _get_alloc_or_404(db: Session, alloc_id: int) -> Allocation:
    alloc = db.query(Allocation).filter(Allocation.id == alloc_id).first()
    if not alloc:
        raise HTTPException(404, "Allocation introuvable")
    return alloc


def _remove_file(path: str | None) -> None:
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            logger.warning("Suppression impossible : %s", path)


# ---------------------------------------------------------------------------
# Utilisateurs
# ---------------------------------------------------------------------------

@router.get("/users", response_model=list[AdminUserOut])
def list_users(db: Session = Depends(get_db)):
    counts = _alloc_counts(db)
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [_to_admin_user(u, counts) for u in users]


@router.post("/users", response_model=AdminUserOut, status_code=201)
def create_user(payload: AdminUserCreate, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    if db.query(User).filter(func.lower(User.email) == email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Un compte existe déjà avec cet email")

    user = User(
        email=email,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name.strip(),
        role=payload.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("Compte créé par un admin — id=%s email=%s role=%s", user.id, user.email, user.role)
    return _to_admin_user(user, _alloc_counts(db))


@router.patch("/users/{user_id}", response_model=AdminUserOut)
def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = _get_user_or_404(db, user_id)

    # Un admin ne peut ni se retirer ses droits ni se désactiver : sans ce
    # garde-fou, le dernier admin pourrait verrouiller tout le monde dehors.
    if user.id == admin.id:
        if payload.role is not None and payload.role != user.role:
            raise HTTPException(400, "Vous ne pouvez pas modifier votre propre rôle")
        if payload.is_active is False:
            raise HTTPException(400, "Vous ne pouvez pas désactiver votre propre compte")

    if payload.full_name is not None:
        user.full_name = payload.full_name.strip()
    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.password is not None:
        user.hashed_password = get_password_hash(payload.password)

    db.commit()
    db.refresh(user)
    logger.info("Compte modifié par admin=%s — id=%s role=%s actif=%s",
                admin.id, user.id, user.role, user.is_active)
    return _to_admin_user(user, _alloc_counts(db))


@router.delete("/users/{user_id}", response_model=AdminUserOut)
def deactivate_user(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Désactivation (is_active=False), jamais une suppression en base :
    les allocations de l'utilisateur référencent son id."""
    user = _get_user_or_404(db, user_id)
    if user.id == admin.id:
        raise HTTPException(400, "Vous ne pouvez pas désactiver votre propre compte")

    user.is_active = False
    db.commit()
    db.refresh(user)
    logger.info("Compte désactivé par admin=%s — id=%s", admin.id, user.id)
    return _to_admin_user(user, _alloc_counts(db))


# ---------------------------------------------------------------------------
# Statistiques
# ---------------------------------------------------------------------------

@router.get("/stats", response_model=AdminStats)
def get_stats(db: Session = Depends(get_db)):
    total_users  = db.query(func.count(User.id)).scalar() or 0
    active_users = db.query(func.count(User.id)).filter(User.is_active.is_(True)).scalar() or 0
    total_allocs = db.query(func.count(Allocation.id)).scalar() or 0

    since = datetime.utcnow() - timedelta(days=7)
    allocs_last_7_days = (
        db.query(func.count(Allocation.id))
        .filter(Allocation.created_at >= since)
        .scalar() or 0
    )

    type_rows = (
        db.query(Allocation.type, func.count(Allocation.id))
        .group_by(Allocation.type)
        .all()
    )
    by_type = {t: 0 for t in ALLOC_TYPES}
    for alloc_type, count in type_rows:
        if alloc_type in by_type:
            by_type[alloc_type] = count

    counts = _alloc_counts(db)
    top = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:5]
    top_ids = [user_id for user_id, _ in top]
    users_by_id = {
        u.id: u for u in db.query(User).filter(User.id.in_(top_ids)).all()
    } if top_ids else {}

    top_users = [
        TopUser(full_name=users_by_id[uid].full_name,
                email=users_by_id[uid].email,
                alloc_count=count)
        for uid, count in top
        if uid in users_by_id
    ]

    return AdminStats(
        total_users=total_users,
        active_users=active_users,
        total_allocs=total_allocs,
        allocs_last_7_days=allocs_last_7_days,
        allocs_by_type=AllocsByType(**by_type),
        top_users=top_users,
    )


# ---------------------------------------------------------------------------
# Allocations (toutes, tous utilisateurs confondus)
# ---------------------------------------------------------------------------

@router.get("/allocations", response_model=AdminAllocationPage)
def list_allocations(
    user_id: int | None = Query(default=None),
    date: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Allocation, User).outerjoin(User, Allocation.user_id == User.id)
    if user_id is not None:
        query = query.filter(Allocation.user_id == user_id)
    if date:
        query = query.filter(Allocation.date == date)

    total = query.count()
    rows = (
        query.order_by(Allocation.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    items = [
        AdminAllocationOut(
            id=alloc.id,
            label=alloc.label,
            date=alloc.date,
            type=alloc.type,
            user_email=user.email if user else None,
            user_name=user.full_name if user else None,
            created_at=alloc.created_at,
            docx_path=alloc.docx_path,
        )
        for alloc, user in rows
    ]
    return AdminAllocationPage(total=total, limit=limit, offset=offset, items=items)


@router.get("/allocations/{alloc_id}/preview", response_class=HTMLResponse)
def preview_allocation(alloc_id: int, db: Session = Depends(get_db)):
    alloc = _get_alloc_or_404(db, alloc_id)
    if not alloc.docx_path or not os.path.exists(alloc.docx_path):
        raise HTTPException(404, "Le fichier DOCX n'est plus disponible sur le disque")
    try:
        return docx_to_html(alloc.docx_path)
    except Exception as exc:
        logger.exception("Aperçu admin impossible pour id=%s", alloc_id)
        raise HTTPException(500, "Impossible de générer l'aperçu") from exc


@router.get("/allocations/{alloc_id}/download")
def download_allocation(alloc_id: int, db: Session = Depends(get_db)):
    alloc = _get_alloc_or_404(db, alloc_id)
    if not alloc.docx_path or not os.path.exists(alloc.docx_path):
        raise HTTPException(404, "Le fichier DOCX n'est plus disponible sur le disque")
    return FileResponse(
        alloc.docx_path,
        media_type=(
            "application/vnd.openxmlformats-officedocument"
            ".wordprocessingml.document"
        ),
        filename=f"{alloc.label}.docx",
    )


@router.delete("/allocations/{alloc_id}", status_code=204)
def delete_allocation(
    alloc_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    alloc = _get_alloc_or_404(db, alloc_id)
    logger.info("Suppression par admin=%s — allocation id=%s label=%s",
                admin.id, alloc.id, alloc.label)
    _remove_file(alloc.docx_path)
    _remove_file(alloc.source_pdf_path)
    db.delete(alloc)
    db.commit()
