import re
from collections import defaultdict

import pdfplumber

_FLT_RE = re.compile(r'^[A-Z]{2,3}\d{4}$')
_TIME_RE = re.compile(r'\d{2}:\d{2}')


def _normalize_ac_type(raw: str) -> str:
    if "321" in raw:
        return "321"
    if "319" in raw:
        return "319"
    return "320"


def _strip_time(raw: str) -> str | None:
    if not raw:
        return None
    m = _TIME_RE.search(raw)
    return m.group(0) if m else None


def _build_alloc_pairs(flights: list[dict]) -> dict[str, str]:
    """From a raw flight list, build {arr_flt_no: dep_flt_no} for consecutive
    same-aircraft NCE transitions (arr=NCE followed by dep=NCE)."""
    by_reg: dict[str, list[dict]] = defaultdict(list)
    for f in sorted(flights, key=lambda x: x["std"]):
        by_reg[f["ac_reg"]].append(f)

    pairs: dict[str, str] = {}
    for ac_flights in by_reg.values():
        for i in range(len(ac_flights) - 1):
            if ac_flights[i]["arr"] == "NCE" and ac_flights[i + 1]["dep"] == "NCE":
                pairs[ac_flights[i]["flt_no"]] = ac_flights[i + 1]["flt_no"]
    return pairs


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_feuille_journee(pdf_path: str) -> list[dict]:
    """Parse une Feuille de journée EasyJet NCE.

    Chaque ligne du tableau est soit une arrivée (col 0 remplie) soit un
    départ (col 13 remplie).  Les deux partagent le même rot_no (col 8).

    Retourne une liste de dicts avec les clés :
        flt_no, dep, arr, std (None si arrivée), sta (None si départ),
        ac_type, rot_no
    """
    flights: list[dict] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in (page.extract_tables() or []):
                for row in (table or []):
                    if len(row) < 14:
                        continue
                    c0  = (row[0]  or "").strip()   # arr flt_no
                    c2  = (row[2]  or "").strip()   # origin
                    c4  = (row[4]  or "").strip()   # ac_type
                    c5  = (row[5]  or "").strip()   # arr time (may have day prefix)
                    c8  = (row[8]  or "").strip()   # rot_no
                    c9  = (row[9]  or "").strip()   # dep time
                    c10 = (row[10] or "").strip()   # destination
                    c13 = (row[13] or "").strip()   # dep flt_no

                    if not (c8.isdigit() and c4):
                        continue

                    ac_type = _normalize_ac_type(c4)

                    if _FLT_RE.match(c0):
                        # Arrival row
                        flights.append({
                            "flt_no":  c0,
                            "dep":     c2 if c2 else None,
                            "arr":     "NCE",
                            "std":     None,
                            "sta":     _strip_time(c5),
                            "ac_type": ac_type,
                            "rot_no":  c8,
                        })

                    if _FLT_RE.match(c13):
                        # Departure row
                        flights.append({
                            "flt_no":  c13,
                            "dep":     "NCE",
                            "arr":     c10 if c10 else None,
                            "std":     _strip_time(c9),
                            "sta":     None,
                            "ac_type": ac_type,
                            "rot_no":  c8,
                        })

    return flights


def compare_with_feuille_journee(
    flights_alloc: list[dict],
    flights_fj: list[dict],
) -> list[dict]:
    """Détecte les rotations qui diffèrent entre l'allocation et la FJ.

    Retourne une liste de highlights (color_index=0/YELLOW) pour tous les
    numéros de vol impliqués dans un changement de rotation.
    """
    # Paires FJ : rot_no → (arr_flt, dep_flt) → {arr_flt: dep_flt}
    arr_by_rot: dict[str, str] = {}
    dep_by_rot: dict[str, str] = {}
    for f in flights_fj:
        rot = f.get("rot_no", "")
        if not rot:
            continue
        if f["arr"] == "NCE":
            arr_by_rot[rot] = f["flt_no"]
        if f["dep"] == "NCE":
            dep_by_rot[rot] = f["flt_no"]

    fj_pairs: dict[str, str] = {
        arr_by_rot[rot]: dep_by_rot[rot]
        for rot in arr_by_rot
        if rot in dep_by_rot
    }

    # Paires alloc : même avion, arrivée NCE → départ NCE
    alloc_pairs = _build_alloc_pairs(flights_alloc)

    # Différences
    changed_flts: set[str] = set()
    for arr_flt, dep_alloc in alloc_pairs.items():
        dep_fj = fj_pairs.get(arr_flt)
        if dep_fj is not None and dep_fj != dep_alloc:
            changed_flts.add(arr_flt)
            changed_flts.add(dep_fj)
            changed_flts.add(dep_alloc)

    return [{"flt_no": flt, "color_index": 0, "partial": False} for flt in sorted(changed_flts)]


def find_cancelled(flights_old: list[dict], flights_new: list[dict]) -> list[dict]:
    """Retourne les vols présents dans flights_old mais absents de flights_new."""
    new_flt_nos = {f["flt_no"] for f in flights_new}
    return [f for f in flights_old if f["flt_no"] not in new_flt_nos]


def compare_allocs(
    flights_new: list[dict],
    flights_old: list[dict],
    existing_highlights: list[dict],
    new_color_index: int,
) -> dict:
    """Détecte les changements entre deux versions d'une allocation.

    Détecte :
    - Changements d'immatriculation : même flt_no, ac_reg différent.
    - Changements de rotation : un vol arr=NCE est maintenant associé à un
      vol dep=NCE différent.
    - Vols annulés : présents dans flights_old, absents de flights_new.

    Retourne :
        {
            "highlights": [...],   # liste de dicts {flt_no, color_index, partial}
            "cancelled":  [...],   # liste de flight dicts annulés
        }
    """
    old_by_flt: dict[str, dict] = {f["flt_no"]: f for f in flights_old}
    new_by_flt: dict[str, dict] = {f["flt_no"]: f for f in flights_new}

    # Paires de rotation pour chaque version
    old_pairs = _build_alloc_pairs(flights_old)
    new_pairs = _build_alloc_pairs(flights_new)

    # partial_flts : seule l'immat change (DEP, ARR, STD identiques)
    # full_flts    : rotation changée, ou immat + route changées
    partial_flts: set[str] = set()
    full_flts: set[str] = set()

    # 1. Changements d'immat
    for flt_no, new_f in new_by_flt.items():
        old_f = old_by_flt.get(flt_no)
        if old_f is None or old_f["ac_reg"] == new_f["ac_reg"]:
            continue
        if (old_f["dep"] == new_f["dep"]
                and old_f["arr"] == new_f["arr"]
                and old_f["std"] == new_f["std"]):
            partial_flts.add(flt_no)
        else:
            full_flts.add(flt_no)

    # 2. Changements de rotation (NCE-based) — toujours full
    for arr_flt, dep_new in new_pairs.items():
        dep_old = old_pairs.get(arr_flt)
        if dep_old is not None and dep_old != dep_new:
            full_flts.add(arr_flt)
            full_flts.add(dep_new)
            full_flts.add(dep_old)

    # Un changement de rotation prime sur un changement d'immat seul
    partial_flts -= full_flts

    # Fusion avec les highlights existants
    hl_map: dict[str, tuple[int, bool]] = {
        h["flt_no"]: (h["color_index"], h.get("partial", False))
        for h in (existing_highlights or [])
    }
    for flt_no in partial_flts:
        hl_map[flt_no] = (new_color_index, True)
    for flt_no in full_flts:
        hl_map[flt_no] = (new_color_index, False)

    return {
        "highlights": [
            {"flt_no": flt, "color_index": ci, "partial": partial}
            for flt, (ci, partial) in hl_map.items()
        ],
        "cancelled": find_cancelled(flights_old, flights_new),
    }
