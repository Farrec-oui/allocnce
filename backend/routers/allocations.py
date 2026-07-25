import logging
import os
import uuid
from datetime import date as _date
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import Allocation, User
from schemas import AllocationOut, AllocationUpdate
from services.alloc_builder import build_allocation, generate_label
from services.auth import get_current_user
from services.comparator import (
    compare_allocs,
    compare_with_feuille_journee,
    parse_feuille_journee,
)
from services.docx_generator import generate_docx
from services.docx_preview import docx_to_html
from services.pdf_parser import parse_easyjet_allocation

logger = logging.getLogger(__name__)

# La dépendance au niveau du router garantit qu'aucun endpoint ajouté plus tard
# ne soit exposé par oubli. FastAPI met en cache la dépendance sur la requête :
# la déclarer aussi en paramètre de handler ne coûte pas une seconde résolution.
router = APIRouter(
    prefix="/allocations",
    tags=["allocations"],
    dependencies=[Depends(get_current_user)],
)

UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _save_upload(upload: UploadFile, suffix: str = "") -> str:
    path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}{suffix}")
    with open(path, "wb") as f:
        f.write(upload.file.read())
    return path


def _docx_url(path: str) -> str:
    return f"/files/{os.path.basename(path)}"


def _make_docx_path(label: str) -> str:
    safe = label.replace("/", "-").replace("\\", "-")
    path = os.path.join(UPLOAD_DIR, f"{safe}.docx")
    if not os.path.exists(path):
        return path
    n = 2
    while os.path.exists(os.path.join(UPLOAD_DIR, f"{safe}_{n}.docx")):
        n += 1
    return os.path.join(UPLOAD_DIR, f"{safe}_{n}.docx")


def _highlights(alloc: Allocation) -> list[dict]:
    return alloc.highlights_json or []


def _owned(db: Session, alloc_id: int, user: User) -> Allocation | None:
    """Récupère une allocation appartenant à l'utilisateur, sinon None."""
    return (
        db.query(Allocation)
        .filter(Allocation.id == alloc_id, Allocation.user_id == user.id)
        .first()
    )


def _owned_or_404(db: Session, alloc_id: int, user: User) -> Allocation:
    """Comme _owned, mais lève 404 si absente ou détenue par quelqu'un d'autre.

    On renvoie 404 et non 403 : un 403 confirmerait l'existence de
    l'allocation d'un autre utilisateur.
    """
    alloc = _owned(db, alloc_id, user)
    if not alloc:
        raise HTTPException(404, "L'allocation de référence n'existe plus")
    return alloc


def _load_previous_flights(
    previous_day_alloc_id: int | None, db: Session, user: User
) -> list[dict] | None:
    """Charge les vols bruts de l'alloc de la veille pour les tableaux NS/FW."""
    if not previous_day_alloc_id:
        return None
    ref = _owned(db, previous_day_alloc_id, user)
    if not ref or not ref.source_pdf_path or not os.path.exists(ref.source_pdf_path):
        logger.warning("Alloc de la veille id=%s introuvable ou sans PDF", previous_day_alloc_id)
        return None
    try:
        flights = _parse_alloc_pdf(ref.source_pdf_path)
        logger.info("Vols J-1 chargés — %d vols depuis alloc id=%s", len(flights), previous_day_alloc_id)
        return flights
    except HTTPException:
        logger.warning("Impossible de parser le PDF de la veille id=%s", previous_day_alloc_id)
        return None


def _remove_file(path: str | None) -> None:
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


_MONTH_NAMES = {
    1: "JAN", 2: "FEB", 3: "MAR", 4: "APR", 5: "MAY", 6: "JUN",
    7: "JUL", 8: "AUG", 9: "SEP", 10: "OCT", 11: "NOV", 12: "DEC",
}


def _extract_date_from_flights(flights: list[dict]) -> str:
    """Derive DDMONYY date string from the first parsed flight's 'DD.MM' date field."""
    if not flights:
        raise HTTPException(422, "Impossible d'extraire la date du PDF")
    try:
        day_s, month_s = flights[0]["date"].split(".")
        day, month = int(day_s), int(month_s)
        mon = _MONTH_NAMES[month]
        today = _date.today()
        year = today.year
        # If the candidate date is more than 30 days in the past, it's likely next year
        try:
            candidate = _date(year, month, day)
            if (today - candidate).days > 30:
                year += 1
        except ValueError:
            year += 1
        return f"{day_s}{mon}{str(year)[2:]}"
    except (ValueError, KeyError, IndexError) as exc:
        raise HTTPException(422, "Impossible d'extraire la date du PDF") from exc


def _parse_alloc_pdf(path: str) -> list[dict]:
    """Parse un PDF EasyJet avec messages d'erreur en français."""
    try:
        flights = parse_easyjet_allocation(path)
    except Exception as exc:
        logger.warning("Échec du parsing PDF %s : %s", path, exc)
        raise HTTPException(
            422, "Le PDF fourni n'est pas un rapport EasyJet valide"
        ) from exc
    if not flights:
        raise HTTPException(422, "Aucun vol trouvé dans ce PDF")
    return flights


def _parse_fj_pdf(path: str) -> list[dict]:
    """Parse une feuille de journée avec messages d'erreur en français."""
    try:
        return parse_feuille_journee(path)
    except Exception as exc:
        logger.warning("Échec du parsing FJ %s : %s", path, exc)
        raise HTTPException(
            422, "Le PDF de feuille de journée n'est pas lisible"
        ) from exc


def _get_parent(parent_id: int, db: Session, user: User) -> Allocation:
    parent = _owned_or_404(db, parent_id, user)
    if not parent.source_pdf_path or not os.path.exists(parent.source_pdf_path):
        raise HTTPException(400, "L'allocation de référence n'a plus de PDF source sur le disque")
    return parent


# ---------------------------------------------------------------------------
# GET /allocations/stats
# ---------------------------------------------------------------------------

@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    allocs = db.query(Allocation).filter(Allocation.user_id == current_user.id).all()
    by_type: dict[str, int] = {}
    last_date: str | None = None
    for a in allocs:
        by_type[a.type] = by_type.get(a.type, 0) + 1
        if last_date is None or a.date > last_date:
            last_date = a.date
    return {
        "total": len(allocs),
        "by_type": by_type,
        "last_date": last_date,
    }


# ---------------------------------------------------------------------------
# GET /allocations
# ---------------------------------------------------------------------------

@router.get("/")
def list_allocations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    allocs = (
        db.query(Allocation)
        .filter(Allocation.user_id == current_user.id)
        .order_by(Allocation.date.desc(), Allocation.created_at.desc())
        .all()
    )
    groups: dict[str, list] = {}
    for a in allocs:
        groups.setdefault(a.date, []).append({
            "id":                    a.id,
            "label":                 a.label,
            "date":                  a.date,
            "type":                  a.type,
            "docx_url":              _docx_url(a.docx_path) if a.docx_path else None,
            "highlight_color_index": a.highlight_color_index,
            "changes_count":         a.changes_count if a.changes_count is not None else len(_highlights(a)),
            "parent_id":             a.parent_id,
            "parent_label":          None,  # filled below
            "created_at":            a.created_at,
        })

    # Fill parent_label
    id_to_label = {a.id: a.label for a in allocs}
    for group in groups.values():
        for entry in group:
            if entry["parent_id"]:
                entry["parent_label"] = id_to_label.get(entry["parent_id"])

    return [{"date": date, "allocs": al} for date, al in groups.items()]


# ---------------------------------------------------------------------------
# POST /allocations/create
# ---------------------------------------------------------------------------

@router.post("/create", status_code=201)
async def create_allocation(
    pdf: UploadFile = File(...),
    date: Optional[str] = Form(default=None),
    previous_day_alloc_id: Optional[int] = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pdf_path = _save_upload(pdf, ".pdf")
    try:
        flights    = _parse_alloc_pdf(pdf_path)
        logger.info("Parsing OK — %d vols extraits", len(flights))
        if not date:
            date = _extract_date_from_flights(flights)
        alloc_data = build_allocation(flights)
        label      = generate_label(date, "creation")
        docx_path  = _make_docx_path(label)
        prev_flights = _load_previous_flights(previous_day_alloc_id, db, current_user)
        generate_docx(alloc_data, [], docx_path, previous_alloc_flights=prev_flights)
        logger.info("DOCX généré : %s", os.path.basename(docx_path))

        alloc = Allocation(
            date=date, label=label, type="creation",
            docx_path=docx_path, source_pdf_path=pdf_path,
            highlight_color_index=0, highlights_json=[], changes_count=0,
            user_id=current_user.id,
        )
        db.add(alloc); db.commit(); db.refresh(alloc)
    except HTTPException:
        _remove_file(pdf_path)
        raise
    except Exception as exc:
        _remove_file(pdf_path)
        logger.exception("Erreur inattendue dans create_allocation")
        raise HTTPException(500, "Erreur interne lors de la création") from exc

    return {
        "id": alloc.id, "label": alloc.label, "date": alloc.date,
        "docx_url": _docx_url(docx_path), "created_at": alloc.created_at,
    }


# ---------------------------------------------------------------------------
# POST /allocations/prealloc
# ---------------------------------------------------------------------------

@router.post("/prealloc", status_code=201)
async def create_prealloc(
    pdf_alloc: UploadFile = File(...),
    date: Optional[str] = Form(default=None),
    pdf_fj: Optional[UploadFile] = File(default=None),
    previous_day_alloc_id: Optional[int] = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pdf_alloc_path = _save_upload(pdf_alloc, ".pdf")
    pdf_fj_path: str | None = None
    try:
        flights_alloc = _parse_alloc_pdf(pdf_alloc_path)
        logger.info("Parsing alloc OK — %d vols", len(flights_alloc))
        if not date:
            date = _extract_date_from_flights(flights_alloc)
        highlights: list[dict] = []

        if pdf_fj and pdf_fj.filename:
            pdf_fj_path = _save_upload(pdf_fj, ".pdf")
            flights_fj = _parse_fj_pdf(pdf_fj_path)
            logger.info("Parsing FJ OK — %d vols FJ", len(flights_fj))
            highlights = compare_with_feuille_journee(flights_alloc, flights_fj)
            logger.info("Comparaison FJ — %d vols surlignés", len(highlights))

        alloc_data = build_allocation(flights_alloc)
        label      = generate_label(date, "prealloc")
        docx_path  = _make_docx_path(label)
        prev_flights = _load_previous_flights(previous_day_alloc_id, db, current_user)
        generate_docx(alloc_data, highlights, docx_path, previous_alloc_flights=prev_flights)
        logger.info("DOCX généré : %s", os.path.basename(docx_path))

        alloc = Allocation(
            date=date, label=label, type="prealloc",
            docx_path=docx_path, source_pdf_path=pdf_alloc_path,
            highlight_color_index=0, highlights_json=highlights,
            changes_count=len(highlights),
            user_id=current_user.id,
        )
        db.add(alloc); db.commit(); db.refresh(alloc)
    except HTTPException:
        _remove_file(pdf_alloc_path)
        _remove_file(pdf_fj_path)
        raise
    except Exception as exc:
        _remove_file(pdf_alloc_path)
        _remove_file(pdf_fj_path)
        logger.exception("Erreur inattendue dans create_prealloc")
        raise HTTPException(500, "Erreur interne lors de la création de la pré-allocation") from exc

    return {
        "id": alloc.id, "label": alloc.label, "date": alloc.date,
        "docx_url": _docx_url(docx_path),
        "changes_count": len(highlights),
        "created_at": alloc.created_at,
    }


# ---------------------------------------------------------------------------
# POST /allocations/finale
# ---------------------------------------------------------------------------

@router.post("/finale", status_code=201)
async def create_finale(
    pdf_new: UploadFile = File(...),
    parent_id: int = Form(...),
    date: Optional[str] = Form(default=None),
    previous_day_alloc_id: Optional[int] = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    parent = _get_parent(parent_id, db, current_user)

    pdf_new_path = _save_upload(pdf_new, ".pdf")
    try:
        flights_new = _parse_alloc_pdf(pdf_new_path)
        flights_old = _parse_alloc_pdf(parent.source_pdf_path)
        logger.info("Parsing OK — new=%d vols, old=%d vols", len(flights_new), len(flights_old))
        if not date:
            date = _extract_date_from_flights(flights_new)
        existing    = _highlights(parent)

        cmp_result     = compare_allocs(flights_new, flights_old, existing, 1)
        all_highlights = cmp_result["highlights"]
        cancelled      = cmp_result["cancelled"]
        logger.info("Comparaison — %d vols surlignés, %d annulés", len(all_highlights), len(cancelled))

        alloc_data = build_allocation(flights_new)
        label      = generate_label(date, "alloc_finale")
        docx_path  = _make_docx_path(label)
        prev_flights = _load_previous_flights(previous_day_alloc_id, db, current_user)
        generate_docx(alloc_data, all_highlights, docx_path, previous_alloc_flights=prev_flights, cancelled=cancelled)
        logger.info("DOCX généré : %s", os.path.basename(docx_path))

        alloc = Allocation(
            date=date, label=label, type="alloc_finale",
            docx_path=docx_path, source_pdf_path=pdf_new_path,
            parent_id=parent_id, highlight_color_index=1,
            highlights_json=all_highlights, changes_count=len(all_highlights),
            user_id=current_user.id,
        )
        db.add(alloc); db.commit(); db.refresh(alloc)
    except HTTPException:
        _remove_file(pdf_new_path)
        raise
    except Exception as exc:
        _remove_file(pdf_new_path)
        logger.exception("Erreur inattendue dans create_finale")
        raise HTTPException(500, "Erreur interne lors de la création de l'allocation finale") from exc

    return {
        "id": alloc.id, "label": alloc.label, "date": alloc.date,
        "docx_url": _docx_url(docx_path),
        "changes_count": len(all_highlights),
        "created_at": alloc.created_at,
    }


# ---------------------------------------------------------------------------
# POST /allocations/{alloc_id}/update
# ---------------------------------------------------------------------------

@router.post("/{alloc_id}/update", status_code=201)
async def update_with_pdf(
    alloc_id: int,
    pdf_new: UploadFile = File(...),
    previous_day_alloc_id: Optional[int] = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info("update_with_pdf — alloc_id=%s, fichier=%s", alloc_id, pdf_new.filename)
    alloc = _owned_or_404(db, alloc_id, current_user)
    if not alloc.source_pdf_path or not os.path.exists(alloc.source_pdf_path):
        raise HTTPException(400, "L'allocation de référence n'a plus de PDF source sur le disque")

    new_color = (alloc.highlight_color_index + 1) % 4
    label     = generate_label(alloc.date, "maj", alloc.label)

    pdf_new_path = _save_upload(pdf_new, ".pdf")
    try:
        flights_new = _parse_alloc_pdf(pdf_new_path)
        flights_old = _parse_alloc_pdf(alloc.source_pdf_path)
        logger.info("Parsing OK — new=%d vols, old=%d vols", len(flights_new), len(flights_old))
        existing    = _highlights(alloc)

        cmp_result     = compare_allocs(flights_new, flights_old, existing, new_color)
        all_highlights = cmp_result["highlights"]
        cancelled      = cmp_result["cancelled"]
        logger.info("Comparaison MAJ — %d vols surlignés, %d annulés", len(all_highlights), len(cancelled))

        alloc_data = build_allocation(flights_new)
        docx_path  = _make_docx_path(label)
        prev_flights = _load_previous_flights(previous_day_alloc_id, db, current_user)
        generate_docx(alloc_data, all_highlights, docx_path, previous_alloc_flights=prev_flights, cancelled=cancelled)
        logger.info("DOCX MAJ généré : %s", os.path.basename(docx_path))

        new_alloc = Allocation(
            date=alloc.date, label=label, type="maj",
            docx_path=docx_path, source_pdf_path=pdf_new_path,
            parent_id=alloc_id, highlight_color_index=new_color,
            highlights_json=all_highlights, changes_count=len(all_highlights),
            user_id=current_user.id,
        )
        db.add(new_alloc); db.commit(); db.refresh(new_alloc)
    except HTTPException:
        _remove_file(pdf_new_path)
        raise
    except Exception as exc:
        _remove_file(pdf_new_path)
        logger.exception("Erreur inattendue dans update_with_pdf")
        raise HTTPException(500, "Erreur interne lors de la mise à jour") from exc

    return {
        "id": new_alloc.id, "label": new_alloc.label, "date": new_alloc.date,
        "docx_url": _docx_url(docx_path),
        "changes_count": len(all_highlights),
        "created_at": new_alloc.created_at,
    }


# ---------------------------------------------------------------------------
# GET /allocations/{alloc_id}/preview
# ---------------------------------------------------------------------------

@router.get("/{alloc_id}/preview", response_class=HTMLResponse)
def preview_allocation(
    alloc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    alloc = _owned_or_404(db, alloc_id, current_user)
    if not alloc.docx_path or not os.path.exists(alloc.docx_path):
        raise HTTPException(404, "Le fichier DOCX n'est plus disponible sur le disque")
    try:
        return docx_to_html(alloc.docx_path)
    except Exception as exc:
        logger.exception("Erreur lors de la génération de l'aperçu id=%s", alloc_id)
        raise HTTPException(500, "Impossible de générer l'aperçu") from exc


# ---------------------------------------------------------------------------
# GET /allocations/{alloc_id}
# ---------------------------------------------------------------------------

@router.get("/{alloc_id}", response_model=AllocationOut)
def get_allocation(
    alloc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _owned_or_404(db, alloc_id, current_user)


# ---------------------------------------------------------------------------
# GET /allocations/{alloc_id}/download
# ---------------------------------------------------------------------------

@router.get("/{alloc_id}/download")
def download_docx(
    alloc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    alloc = _owned_or_404(db, alloc_id, current_user)
    if not alloc.docx_path or not os.path.exists(alloc.docx_path):
        raise HTTPException(404, "Le fichier DOCX n'est plus disponible sur le disque")
    filename = f"{alloc.label}.docx"
    return FileResponse(
        alloc.docx_path,
        media_type=(
            "application/vnd.openxmlformats-officedocument"
            ".wordprocessingml.document"
        ),
        filename=filename,
    )


# ---------------------------------------------------------------------------
# PATCH /allocations/{alloc_id}
# ---------------------------------------------------------------------------

@router.patch("/{alloc_id}", response_model=AllocationOut)
def patch_allocation(
    alloc_id: int,
    payload: AllocationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    alloc = _owned_or_404(db, alloc_id, current_user)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(alloc, field, value)
    db.commit(); db.refresh(alloc)
    return alloc


# ---------------------------------------------------------------------------
# DELETE /allocations/{alloc_id}
# ---------------------------------------------------------------------------

@router.delete("/{alloc_id}", status_code=204)
def delete_allocation(
    alloc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    alloc = _owned_or_404(db, alloc_id, current_user)
    logger.info("Suppression allocation id=%s label=%s", alloc.id, alloc.label)
    _remove_file(alloc.docx_path)
    _remove_file(alloc.source_pdf_path)
    db.delete(alloc)
    db.commit()
