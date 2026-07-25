"""Tests unitaires pour parse_easyjet_allocation.

PDFs de référence :
  - workflow/FlightAllocationReport.pdf   → pré-alloc (sans ETD/ETA ni Captain)
  - workflow/FlightAllocationReport (1).pdf → alloc finale (avec ETD/ETA et Captain)
"""
from pathlib import Path
import pytest
from services.pdf_parser import parse_easyjet_allocation

_WORKFLOW = Path(__file__).resolve().parents[4] / "workflow"
PDF_PRE   = _WORKFLOW / "FlightAllocationReport.pdf"
PDF_FINAL = _WORKFLOW / "FlightAllocationReport (1).pdf"


# ---------------------------------------------------------------------------
# Fixtures (scope=module → le PDF n'est parsé qu'une seule fois par fichier)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def pre_flights():
    assert PDF_PRE.exists(), f"PDF introuvable : {PDF_PRE}"
    return parse_easyjet_allocation(str(PDF_PRE))


@pytest.fixture(scope="module")
def final_flights():
    assert PDF_FINAL.exists(), f"PDF introuvable : {PDF_FINAL}"
    return parse_easyjet_allocation(str(PDF_FINAL))


def _find(flights: list[dict], flt_no: str) -> dict | None:
    return next((f for f in flights if f["flt_no"] == flt_no), None)


# ---------------------------------------------------------------------------
# Pré-allocation : sans ETD/ETA, sans capitaine
# ---------------------------------------------------------------------------

def test_pre_non_vide(pre_flights):
    assert len(pre_flights) > 0

def test_pre_eju1687_present(pre_flights):
    assert _find(pre_flights, "EJU1687") is not None

def test_pre_eju1687_dep(pre_flights):
    assert _find(pre_flights, "EJU1687")["dep"] == "NCE"

def test_pre_eju1687_arr(pre_flights):
    assert _find(pre_flights, "EJU1687")["arr"] == "OLB"

def test_pre_eju1687_std(pre_flights):
    assert _find(pre_flights, "EJU1687")["std"] == "04:00"

def test_pre_eju1687_sta(pre_flights):
    assert _find(pre_flights, "EJU1687")["sta"] == "05:00"

def test_pre_eju1687_ac_reg(pre_flights):
    assert _find(pre_flights, "EJU1687")["ac_reg"] == "OE-IJR"

def test_pre_eju1687_ac_type(pre_flights):
    assert _find(pre_flights, "EJU1687")["ac_type"] == "320"

def test_pre_eju1687_pax(pre_flights):
    assert _find(pre_flights, "EJU1687")["pax"] == 186

def test_pre_eju1687_crew(pre_flights):
    assert _find(pre_flights, "EJU1687")["crew"] == "FC-2 / CC-4"

def test_pre_eju1687_dh(pre_flights):
    assert _find(pre_flights, "EJU1687")["dh"] == 0

def test_pre_eju1687_captain_absent(pre_flights):
    assert _find(pre_flights, "EJU1687")["captain"] is None

def test_pre_toutes_cles(pre_flights):
    required = {"date", "flt_no", "dep", "arr", "std", "sta",
                "ac_type", "ac_reg", "pax", "crew", "dh", "captain"}
    for f in pre_flights:
        assert required <= f.keys()

def test_pre_pas_header(pre_flights):
    assert not any(f["flt_no"] == "FLT" for f in pre_flights)


# ---------------------------------------------------------------------------
# Allocation finale : avec ETD/ETA et capitaines
# ---------------------------------------------------------------------------

def test_final_eju1687_captain(final_flights):
    assert _find(final_flights, "EJU1687")["captain"] == "DURENDEAU DAVID"

def test_final_captain_asterisques(final_flights):
    # PEZZO ALESSANDRA*** → nettoyé en "PEZZO ALESSANDRA"
    assert _find(final_flights, "EJU4859")["captain"] == "PEZZO ALESSANDRA"

def test_final_captain_wrap_tiret(final_flights):
    # DUBOIS-DIT- / BONCLAUDE JACQUES → soudé sans espace
    f = _find(final_flights, "EZS1401")
    assert f is not None
    assert "BONCLAUDE" in f["captain"]
    assert not f["captain"].startswith(" ")

def test_final_captain_wrap_sans_tiret(final_flights):
    # FRANCIS-NAYLOR + MICHAEL → joint avec espace
    assert _find(final_flights, "EZY3035")["captain"] == "FRANCIS-NAYLOR MICHAEL"

def test_final_captain_long(final_flights):
    # CHATZIKONSTANTINOU + PANOS
    assert _find(final_flights, "EJU1737")["captain"] == "CHATZIKONSTANTINOU PANOS"

def test_final_eju2979_std_sta(final_flights):
    # Ce vol a STD=10:25 ETD=10:30 STA=11:35 ETA=11:31 → on expose STD et STA
    f = _find(final_flights, "EJU2979")
    assert f["std"] == "10:25"
    assert f["sta"] == "11:35"

def test_final_dh_non_zero(final_flights):
    assert _find(final_flights, "EJU5145")["dh"] == 1
