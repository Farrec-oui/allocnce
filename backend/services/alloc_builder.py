import re

HIGHLIGHT_SEQUENCE = ["YELLOW", "BRIGHT_GREEN", "CYAN", "PINK"]

_VER_RE = re.compile(r'^(.*) v(\d+)$')

CAPACITY: dict[str, int] = {"319": 156, "320": 186, "321": 220}

_MONTHS: dict[str, str] = {
    "01": "JAN", "02": "FEB", "03": "MAR", "04": "APR",
    "05": "MAY", "06": "JUN", "07": "JUL", "08": "AUG",
    "09": "SEP", "10": "OCT", "11": "NOV", "12": "DEC",
}

_CREW_RE = re.compile(r"FC-(\d+)\s*/\s*CC-(\d+)")


# ---------------------------------------------------------------------------
# Public helpers (used by other services)
# ---------------------------------------------------------------------------

def get_highlight_color(index: int) -> str:
    return HIGHLIGHT_SEQUENCE[index % len(HIGHLIGHT_SEQUENCE)]


def generate_label(
    date: str,
    alloc_type: str,
    parent_label: str | None = None,
) -> str:
    """Génère le nom d'une allocation.

    - creation / alloc_finale → "Allocation {date}"
    - prealloc               → "Pre-Allocation {date}"
    - maj                    → label parent sans "Pre-", incrémente le suffixe vN
    """
    if alloc_type == "prealloc":
        return f"Pre-Allocation {date}"
    if alloc_type in ("creation", "alloc_finale"):
        return f"Allocation {date}"
    if alloc_type == "maj":
        base = (parent_label or f"Allocation {date}").removeprefix("Pre-")
        m = _VER_RE.match(base)
        if m:
            return f"{m.group(1)} v{int(m.group(2)) + 1}"
        return f"{base} v2"
    return f"Allocation {date}"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _format_date(raw: str) -> str:
    """'27.06' → '27 JUN'"""
    try:
        day, month = raw.split(".")
        return f"{int(day):02d} {_MONTHS[month]}"
    except (ValueError, KeyError):
        return raw


def _crew_str(crew: str, dh: int) -> str:
    """'FC-2 / CC-4', dh=0  →  '2+4/0'"""
    m = _CREW_RE.match(crew.strip())
    if not m:
        return crew
    return f"{m.group(1)}+{m.group(2)}/{dh}"


def _classify(flights: list[dict]) -> tuple[str, bool]:
    """Return (category, new_based) for a sorted list of flights for one ac_reg.

    Categories: 'based' | 'autres_rotations' | 'ferry'
    Swap is no longer a separate category: swap aircraft land in 'autres_rotations'
    and are identified via swap_refs in build_allocation().
    new_based is True only when category == 'based' and the aircraft did not
    start the day at NCE (i.e. it returns to NCE in the evening).
    """
    first_dep = flights[0]["dep"]
    last_arr  = flights[-1]["arr"]

    is_based  = (first_dep == "NCE") or (last_arr == "NCE")
    new_based = is_based and (first_dep != "NCE")

    if is_based:
        return "based", new_based

    has_nce_dep = any(f["dep"] == "NCE" for f in flights)
    has_nce_arr = any(f["arr"] == "NCE" for f in flights)

    if has_nce_dep and has_nce_arr:
        return "autres_rotations", False

    # One-directional NCE touch (or no NCE touch at all) → ferry
    return "ferry", False


def _enrich(flights: list[dict]) -> list[dict]:
    """Add capacity, crew_str, crew_change_before to each flight dict."""
    out = []
    for i, f in enumerate(flights):
        prev = flights[i - 1] if i > 0 else None
        captain_changed = bool(
            prev
            and f.get("captain")
            and prev.get("captain")
            and f["captain"] != prev["captain"]
        )
        out.append({
            "date":              f["date"],
            "flt_no":            f["flt_no"],
            "dep":               f["dep"],
            "arr":               f["arr"],
            "std":               f["std"],
            "sta":               f["sta"],
            "ac_reg":            f["ac_reg"],
            "ac_type":           f["ac_type"],
            "capacity":          CAPACITY.get(f["ac_type"], 0),
            "pax":               f["pax"],
            "crew_str":          _crew_str(f["crew"], f["dh"]),
            "captain":           f.get("captain"),
            "crew_change_before": captain_changed,
        })
    return out


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def build_allocation(flights: list[dict]) -> dict:
    """Organise une liste de vols parsés en structure d'allocation.

    Args:
        flights: sortie de parse_easyjet_allocation()

    Returns:
        dict with keys: date, based, autres_rotations, swap_refs, ferry
        swap_refs: list of ac_reg present in autres_rotations whose
                   first flight dep != last flight arr (asymmetric routing through NCE)
    """
    empty: dict = {"date": "", "based": [], "autres_rotations": [], "swap_refs": [], "ferry": []}
    if not flights:
        return empty

    # 1. Tri global : STD croissant, puis ac_reg alphabétique à STD égal
    all_sorted = sorted(flights, key=lambda f: (f["std"], f["ac_reg"]))

    date_str = _format_date(all_sorted[0]["date"])

    # 2. Grouper par ac_reg (l'ordre à l'intérieur de chaque groupe est déjà STD-croissant)
    by_reg: dict[str, list[dict]] = {}
    for f in all_sorted:
        by_reg.setdefault(f["ac_reg"], []).append(f)

    # 3. Classifier et construire les entrées
    buckets: dict[str, list] = {
        "based": [], "autres_rotations": [], "ferry": []
    }

    for ac_reg in sorted(by_reg):          # tri alpha des immatriculations
        ac_flights = by_reg[ac_reg]
        category, new_based = _classify(ac_flights)
        buckets[category].append({
            "ac_reg":    ac_reg,
            "new_based": new_based,
            "flights":   _enrich(ac_flights),
        })

    # 4. Identifier les swaps parmi autres_rotations :
    #    premier vol dep != dernier vol arr → routing asymétrique passant par NCE
    swap_refs: list[str] = [
        entry["ac_reg"]
        for entry in buckets["autres_rotations"]
        if entry["flights"][0]["dep"] != entry["flights"][-1]["arr"]
    ]

    return {
        "date":             date_str,
        "based":            buckets["based"],
        "autres_rotations": buckets["autres_rotations"],
        "swap_refs":        swap_refs,
        "ferry":            buckets["ferry"],
    }
