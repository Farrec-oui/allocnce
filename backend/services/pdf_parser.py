import re
import pdfplumber
from typing import Optional

# DATE  FLT No  DEP  ARR  STD  [ETD]  STA  [ETA]  A/C Type  A/C Reg  PAX  Crew  DH  [Captain]
_FLIGHT_RE = re.compile(
    r'^(\d{2}\.\d{2})\s+'           # date
    r'([A-Z]{2,3}\d{4})\s+'         # flt_no
    r'([A-Z]{3})\s+'                # dep
    r'([A-Z]{3})\s+'                # arr
    r'(\d{2}:\d{2})\s+'             # std
    r'(?:(\d{2}:\d{2})\s+)?'        # etd  (absent si pas d'actual time)
    r'(\d{2}:\d{2})\s+'             # sta
    r'(?:(\d{2}:\d{2})\s+)?'        # eta  (absent si pas d'actual time)
    r'(3(?:19|20|21))\s+'           # ac_type
    r'([A-Z]{1,2}-[A-Z0-9]+)\s+'   # ac_reg
    r'(\d+)\s+'                      # pax
    r'(FC-\d+\s*/\s*CC-\d+)'        # crew_count
    r'(?:\s+(\d+))?'                 # dh (optionnel — absent si ligne coupée en fin de page)
    r'(?:\s+(.+))?$'                 # captain (optionnel)
)

# Ligne de continuation de capitaine : uniquement majuscules, espaces, tirets, parenthèses, *
_CAPTAIN_CONT_RE = re.compile(r'^[A-Z][A-Z\s\-\*\(\)]+$')

_HEADER_RE = re.compile(r'^DATE\s+FLT')


def _clean_captain(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    raw = raw.strip()
    raw = re.sub(r'\*+$', '', raw).strip()   # retire *** de fin
    return raw or None


def parse_easyjet_allocation(pdf_path: str) -> list[dict]:
    """Parse un FlightAllocationReport EasyJet et retourne la liste des vols.

    Gère les variantes :
    - Avec ou sans colonnes ETD / ETA
    - Avec ou sans colonne Captain (in-line ou wrappé sur la ligne suivante)
    - Noms coupés avec tiret en fin de ligne (DUBOIS-DIT- / BONCLAUDE JACQUES)
    - Suffixes *** (deadhead marker)
    """
    flights: list[dict] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for raw_line in (page.extract_text() or "").splitlines():
                line = raw_line.strip()
                if not line or _HEADER_RE.match(line):
                    continue

                m = _FLIGHT_RE.match(line)
                if m:
                    (date, flt_no, dep, arr, std, _etd, sta, _eta,
                     ac_type, ac_reg, pax, crew, dh_raw, captain_raw) = m.groups()

                    flights.append({
                        "date":    date,
                        "flt_no":  flt_no,
                        "dep":     dep,
                        "arr":     arr,
                        "std":     std,
                        "sta":     sta,
                        "ac_type": ac_type,
                        "ac_reg":  ac_reg,
                        "pax":     int(pax),
                        "crew":    re.sub(r'\s+', ' ', crew).strip(),
                        "dh":      int(dh_raw) if dh_raw is not None else 0,
                        "captain": _clean_captain(captain_raw),
                    })

                elif flights and _CAPTAIN_CONT_RE.match(line):
                    # Nom de capitaine wrappé sur la ligne suivante
                    last = flights[-1]
                    fragment = line.strip()
                    if last["captain"]:
                        # Tiret de césure → coller sans espace ; sinon ajouter espace
                        sep = "" if last["captain"].endswith("-") else " "
                        last["captain"] = _clean_captain(last["captain"] + sep + fragment)
                    else:
                        last["captain"] = _clean_captain(fragment)

    return flights


# ---------------------------------------------------------------------------
# Fonctions utilitaires génériques conservées
# ---------------------------------------------------------------------------

def extract_tables_from_pdf(pdf_path: str) -> list[dict]:
    """Extrait toutes les tables d'un PDF (usage générique)."""
    results = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            for table in page.extract_tables():
                if not table:
                    continue
                headers = table[0]
                for row in table[1:]:
                    if any(cell for cell in row):
                        results.append({
                            "page": page_num,
                            **{str(headers[i]): row[i] for i in range(len(headers))},
                        })
    return results


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extrait le texte brut de toutes les pages d'un PDF."""
    return "\n".join(
        page.extract_text() or ""
        for page in pdfplumber.open(pdf_path).pages
    )
