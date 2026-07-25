import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import get_db
from models import Allocation, User
from services.auth import get_current_user

UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

router = APIRouter(
    prefix="/files",
    tags=["files"],
    dependencies=[Depends(get_current_user)],
)

_UPLOAD_ROOT = os.path.realpath(UPLOAD_DIR)


def _resolve_owned_file(filename: str, db: Session, user: User) -> str:
    """Résout un nom de fichier vers un chemin sûr appartenant à l'utilisateur.

    Deux garde-fous :
    - le chemin résolu doit rester sous data/uploads (anti-traversée) ;
    - le fichier doit être référencé par une allocation de l'utilisateur,
      sinon n'importe quel compte pourrait lire les DOCX des autres en
      devinant un nom de fichier.
    """
    # basename neutralise "../" et les chemins absolus.
    safe_name = os.path.basename(filename)
    path = os.path.realpath(os.path.join(_UPLOAD_ROOT, safe_name))

    if os.path.commonpath([path, _UPLOAD_ROOT]) != _UPLOAD_ROOT:
        raise HTTPException(404, "Fichier introuvable")

    owned = (
        db.query(Allocation)
        .filter(Allocation.user_id == user.id)
        .filter(Allocation.docx_path.isnot(None))
        .all()
    )
    if not any(os.path.basename(a.docx_path) == safe_name for a in owned):
        raise HTTPException(404, "Fichier introuvable")

    if not os.path.exists(path):
        raise HTTPException(404, "Fichier introuvable")

    return path


@router.get("/download/{filename}")
def download_file(
    filename: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    path = _resolve_owned_file(filename, db, current_user)
    return FileResponse(path, filename=os.path.basename(path))


@router.get("/{filename}")
def serve_file(
    filename: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    path = _resolve_owned_file(filename, db, current_user)
    return FileResponse(path, filename=os.path.basename(path))
