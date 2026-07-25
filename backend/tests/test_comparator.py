"""Tests pour comparator.py.

PDFs de référence :
  workflow/FlightAllocationReport.pdf        → pré-alloc (J-1)
  workflow/FlightAllocationReport (1).pdf    → alloc finale
  workflow/Feuille de journee EASYJET MZS V19 - NEW_fr-fr.pdf → Feuille de journée
"""
from pathlib import Path

import pytest

from services.comparator import (
    parse_feuille_journee,
    compare_with_feuille_journee,
    compare_allocs,
)

_WORKFLOW = Path(__file__).resolve().parents[4] / "workflow"
PDF_FJ    = _WORKFLOW / "Feuille de journee EASYJET MZS V19 - NEW_fr-fr.pdf"
PDF_PRE   = _WORKFLOW / "FlightAllocationReport.pdf"
PDF_FINAL = _WORKFLOW / "FlightAllocationReport (1).pdf"


# ---------------------------------------------------------------------------
# Fixtures (module scope — PDF parsé une fois par fichier)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def fj_flights():
    assert PDF_FJ.exists(), f"PDF introuvable : {PDF_FJ}"
    return parse_feuille_journee(str(PDF_FJ))


@pytest.fixture(scope="module")
def pre_flights():
    from services.pdf_parser import parse_easyjet_allocation
    assert PDF_PRE.exists()
    return parse_easyjet_allocation(str(PDF_PRE))


@pytest.fixture(scope="module")
def final_flights():
    from services.pdf_parser import parse_easyjet_allocation
    assert PDF_FINAL.exists()
    return parse_easyjet_allocation(str(PDF_FINAL))


# ---------------------------------------------------------------------------
# Helpers synthétiques
# ---------------------------------------------------------------------------

def _flt(flt_no, dep, arr, std="06:00", sta="07:00", ac_reg="OE-AAA",
         ac_type="320", rot_no=None):
    """Flight dict pour tests unitaires."""
    d = {
        "flt_no": flt_no, "dep": dep, "arr": arr,
        "std": std, "sta": sta, "ac_reg": ac_reg,
        "ac_type": ac_type, "pax": 100, "crew": "FC-2 / CC-4",
        "dh": 0, "captain": None, "date": "27.06",
    }
    if rot_no is not None:
        d["rot_no"] = rot_no
    return d


def _fj(flt_no, dep, arr, rot_no, ac_type="320", std=None, sta=None):
    """Flight dict FJ pour tests unitaires."""
    return {
        "flt_no": flt_no, "dep": dep, "arr": arr,
        "std": std, "sta": sta, "ac_type": ac_type, "rot_no": rot_no,
    }


def _hl(flt_no, color_index):
    return {"flt_no": flt_no, "color_index": color_index}


def _flt_nos(highlights):
    return {h["flt_no"] for h in highlights}


# ===========================================================================
# parse_feuille_journee
# ===========================================================================

class TestParseFJ:
    def test_non_vide(self, fj_flights):
        assert len(fj_flights) > 0

    def test_cles_requises(self, fj_flights):
        required = {"flt_no", "dep", "arr", "ac_type", "rot_no"}
        for f in fj_flights:
            assert required <= f.keys()

    def test_flt_no_format(self, fj_flights):
        import re
        FLT_RE = re.compile(r'^[A-Z]{2,3}\d{4}$')
        for f in fj_flights:
            assert FLT_RE.match(f["flt_no"]), f"Mauvais format : {f['flt_no']}"

    def test_arrivees_arr_nce(self, fj_flights):
        arrs = [f for f in fj_flights if f["arr"] == "NCE"]
        assert len(arrs) > 0

    def test_departs_dep_nce(self, fj_flights):
        deps = [f for f in fj_flights if f["dep"] == "NCE"]
        assert len(deps) > 0

    def test_rot_no_numerique(self, fj_flights):
        for f in fj_flights:
            assert f["rot_no"].isdigit(), f"rot_no non numérique : {f['rot_no']}"

    def test_ac_type_normalise(self, fj_flights):
        for f in fj_flights:
            assert f["ac_type"] in {"319", "320", "321"}, \
                f"ac_type inattendu : {f['ac_type']}"

    def test_heure_format_hhmm(self, fj_flights):
        import re
        TIME_RE = re.compile(r'^\d{2}:\d{2}$')
        for f in fj_flights:
            if f["sta"] is not None:
                assert TIME_RE.match(f["sta"]), f"sta malformé : {f['sta']}"
            if f["std"] is not None:
                assert TIME_RE.match(f["std"]), f"std malformé : {f['std']}"

    def test_eju1642_present(self, fj_flights):
        """EJU1642 (BOD→NCE) doit apparaître comme arrivée."""
        eju = next((f for f in fj_flights if f["flt_no"] == "EJU1642"), None)
        assert eju is not None
        assert eju["arr"] == "NCE"

    def test_eju1642_rot_no_43(self, fj_flights):
        eju = next(f for f in fj_flights if f["flt_no"] == "EJU1642")
        assert eju["rot_no"] == "43"

    def test_eju1659_present(self, fj_flights):
        """EJU1659 (NCE→CAG) doit apparaître comme départ."""
        eju = next((f for f in fj_flights if f["flt_no"] == "EJU1659"), None)
        assert eju is not None
        assert eju["dep"] == "NCE"

    def test_eju1659_rot_no_43(self, fj_flights):
        """EJU1659 et EJU1642 partagent le rot_no 43."""
        eju = next(f for f in fj_flights if f["flt_no"] == "EJU1659")
        assert eju["rot_no"] == "43"

    def test_pas_de_header(self, fj_flights):
        for f in fj_flights:
            assert f["flt_no"] not in {"DATE", "FLT", "FROM", "TO"}

    def test_nb_paires_coherent(self, fj_flights):
        """Chaque rot_no doit avoir au plus 1 arrivée et 1 départ."""
        from collections import Counter
        arr_counts = Counter(f["rot_no"] for f in fj_flights if f["arr"] == "NCE")
        dep_counts = Counter(f["rot_no"] for f in fj_flights if f["dep"] == "NCE")
        for rot, cnt in arr_counts.items():
            assert cnt == 1, f"rot {rot}: {cnt} arrivées"
        for rot, cnt in dep_counts.items():
            assert cnt == 1, f"rot {rot}: {cnt} départs"


# ===========================================================================
# compare_with_feuille_journee — tests unitaires synthétiques
# ===========================================================================

class TestCompareWithFJSynthetique:
    def _alloc(self, pairs):
        """Crée une liste de vols pour une seule immat à partir de paires
        [(arr_flt_dep, arr_flt_arr, dep_flt_dep, dep_flt_arr), ...]."""
        flights = []
        std = 600
        for arr_no, arr_from, dep_no, dep_to in pairs:
            std_str = f"{std // 100:02d}:{std % 100:02d}"
            sta_str = f"{(std + 100) // 100:02d}:{(std + 100) % 100:02d}"
            flights.append(_flt(arr_no, arr_from, "NCE", std_str, sta_str))
            std += 120
            std2 = f"{std // 100:02d}:{std % 100:02d}"
            sta2 = f"{(std + 100) // 100:02d}:{(std + 100) % 100:02d}"
            flights.append(_flt(dep_no, "NCE", dep_to, std2, sta2))
            std += 200
        return flights

    def test_aucun_changement(self):
        alloc = self._alloc([("EJU0001", "BOD", "EJU0002", "BOD")])
        fj = [
            _fj("EJU0001", "BOD", "NCE", "1"),
            _fj("EJU0002", "NCE", "BOD", "1"),
        ]
        result = compare_with_feuille_journee(alloc, fj)
        assert result == []

    def test_un_changement_flagge_trois_vols(self):
        # alloc : EJU0001→NCE puis NCE→EJU0002
        # FJ    : EJU0001→NCE puis NCE→EJU0003
        alloc = self._alloc([("EJU0001", "BOD", "EJU0002", "ORY")])
        fj = [
            _fj("EJU0001", "BOD", "NCE", "1"),
            _fj("EJU0003", "NCE", "ORY", "1"),
        ]
        result = compare_with_feuille_journee(alloc, fj)
        flts = _flt_nos(result)
        assert "EJU0001" in flts   # arrivée changée
        assert "EJU0002" in flts   # nouveau départ alloc
        assert "EJU0003" in flts   # départ FJ (absent de l'alloc)
        assert all(h["color_index"] == 0 for h in result)

    def test_color_index_toujours_zero(self):
        alloc = self._alloc([("EJU0001", "BOD", "EJU0002", "ORY")])
        fj = [
            _fj("EJU0001", "BOD", "NCE", "1"),
            _fj("EJU0099", "NCE", "BER", "1"),
        ]
        result = compare_with_feuille_journee(alloc, fj)
        assert all(h["color_index"] == 0 for h in result)

    def test_fj_vide(self):
        alloc = self._alloc([("EJU0001", "BOD", "EJU0002", "ORY")])
        result = compare_with_feuille_journee(alloc, [])
        assert result == []

    def test_alloc_vide(self):
        fj = [_fj("EJU0001", "BOD", "NCE", "1"), _fj("EJU0002", "NCE", "ORY", "1")]
        result = compare_with_feuille_journee([], fj)
        assert result == []

    def test_pas_de_doublon_flt_no(self):
        alloc = self._alloc([
            ("EJU0001", "BOD", "EJU0002", "ORY"),
            ("EJU0003", "CDG", "EJU0004", "LYS"),
        ])
        fj = [
            _fj("EJU0001", "BOD", "NCE", "1"),
            _fj("EJU0099", "NCE", "BER", "1"),
            _fj("EJU0003", "CDG", "NCE", "2"),
            _fj("EJU0004", "NCE", "LYS", "2"),
        ]
        result = compare_with_feuille_journee(alloc, fj)
        flts = [h["flt_no"] for h in result]
        assert len(flts) == len(set(flts)), "Doublons dans les highlights"

    def test_plusieurs_changements_independants(self):
        alloc = [
            _flt("EJU0001", "BOD", "NCE", "06:00", "07:00", ac_reg="OE-AAA"),
            _flt("EJU0002", "NCE", "ORY", "08:00", "09:00", ac_reg="OE-AAA"),
            _flt("EJU0003", "CDG", "NCE", "06:00", "07:00", ac_reg="OE-BBB"),
            _flt("EJU0004", "NCE", "LYS", "08:00", "09:00", ac_reg="OE-BBB"),
        ]
        fj = [
            _fj("EJU0001", "BOD", "NCE", "1"),
            _fj("EJU0099", "NCE", "BER", "1"),  # changement pour EJU0001
            _fj("EJU0003", "CDG", "NCE", "2"),
            _fj("EJU0004", "NCE", "LYS", "2"),  # pas de changement pour EJU0003
        ]
        result = compare_with_feuille_journee(alloc, fj)
        flts = _flt_nos(result)
        assert "EJU0001" in flts
        assert "EJU0002" in flts
        assert "EJU0099" in flts
        assert "EJU0003" not in flts
        assert "EJU0004" not in flts


# ===========================================================================
# compare_with_feuille_journee — test d'intégration sur PDFs réels
# ===========================================================================

@pytest.fixture(scope="module")
def highlights_fj(final_flights, fj_flights):
    return compare_with_feuille_journee(final_flights, fj_flights)


class TestCompareWithFJReel:
    def test_non_vide(self, highlights_fj):
        assert len(highlights_fj) > 0

    def test_color_index_zero(self, highlights_fj):
        assert all(h["color_index"] == 0 for h in highlights_fj)

    def test_pas_de_doublon(self, highlights_fj):
        flts = [h["flt_no"] for h in highlights_fj]
        assert len(flts) == len(set(flts))

    def test_eju1642_flagge(self, highlights_fj):
        """Rotation 43 : EJU1642 change de partenaire (FJ=EJU1659, alloc=EJU4190)."""
        flts = _flt_nos(highlights_fj)
        assert "EJU1642" in flts

    def test_eju1659_flagge(self, highlights_fj):
        """EJU1659 était prévu dans la FJ après EJU1642 mais l'alloc lui substitue EJU4190."""
        flts = _flt_nos(highlights_fj)
        assert "EJU1659" in flts

    def test_eju4190_flagge(self, highlights_fj):
        """EJU4190 est le départ alloc qui remplace EJU1659."""
        flts = _flt_nos(highlights_fj)
        assert "EJU4190" in flts

    def test_ezs1401_flagge(self, highlights_fj):
        """HB-JYA swap : EZS1401 change de départ (FJ=EZS1402, alloc=EZS1056)."""
        flts = _flt_nos(highlights_fj)
        assert "EZS1401" in flts

    def test_ezs1055_flagge(self, highlights_fj):
        """HB-JZR swap : EZS1055 change de départ (FJ=EZS1056, alloc=EZS1402)."""
        flts = _flt_nos(highlights_fj)
        assert "EZS1055" in flts

    def test_nb_vols_changes_coherent(self, highlights_fj):
        """6 rotations changées → au moins 6 flights flaggés (possiblement plus
        si un vol apparaît dans plusieurs changements)."""
        assert len(highlights_fj) >= 6


# ===========================================================================
# compare_allocs — tests unitaires synthétiques
# ===========================================================================

class TestCompareAllocsSynthetique:
    def test_aucun_changement(self):
        flights = [
            _flt("EJU0001", "NCE", "BOD"),
            _flt("EJU0002", "BOD", "NCE", std="08:00", sta="09:00"),
        ]
        result = compare_allocs(flights, flights, [], 1)
        assert result["highlights"] == []

    def test_changement_immat(self):
        old = [_flt("EJU0001", "NCE", "BOD", ac_reg="OE-AAA")]
        new = [_flt("EJU0001", "NCE", "BOD", ac_reg="OE-BBB")]
        result = compare_allocs(new, old, [], 1)
        flts = _flt_nos(result["highlights"])
        assert "EJU0001" in flts
        assert all(h["color_index"] == 1 for h in result["highlights"])

    def test_changement_rotation(self):
        # old : EJU0001→NCE → EJU0002(NCE→BOD)
        # new : EJU0001→NCE → EJU0099(NCE→ORY)
        old = [
            _flt("EJU0001", "BOD", "NCE", "06:00", "07:00"),
            _flt("EJU0002", "NCE", "BOD", "08:00", "09:00"),
        ]
        new = [
            _flt("EJU0001", "BOD", "NCE", "06:00", "07:00"),
            _flt("EJU0099", "NCE", "ORY", "08:00", "09:00"),
        ]
        result = compare_allocs(new, old, [], 2)
        flts = _flt_nos(result["highlights"])
        assert "EJU0001" in flts
        assert "EJU0002" in flts
        assert "EJU0099" in flts
        assert all(h["color_index"] == 2 for h in result["highlights"])

    def test_fusion_highlights_existants_conserves(self):
        old = [_flt("EJU0001", "NCE", "BOD", ac_reg="OE-AAA")]
        new = [_flt("EJU0001", "NCE", "BOD", ac_reg="OE-AAA")]
        existing = [_hl("EJU9999", 0)]
        result = compare_allocs(new, old, existing, 1)
        flts_ci = {h["flt_no"]: h["color_index"] for h in result["highlights"]}
        assert flts_ci["EJU9999"] == 0  # conservé

    def test_fusion_color_override(self):
        """Un vol déjà highlighté qui change encore → color_index mis à jour."""
        old = [_flt("EJU0001", "NCE", "BOD", ac_reg="OE-AAA")]
        new = [_flt("EJU0001", "NCE", "BOD", ac_reg="OE-BBB")]
        existing = [_hl("EJU0001", 0)]  # couleur précédente = 0
        result = compare_allocs(new, old, existing, 1)
        flts_ci = {h["flt_no"]: h["color_index"] for h in result["highlights"]}
        assert flts_ci["EJU0001"] == 1  # écrasé par new_color_index

    def test_existing_highlights_none(self):
        old = [_flt("EJU0001", "NCE", "BOD", ac_reg="OE-AAA")]
        new = [_flt("EJU0001", "NCE", "BOD", ac_reg="OE-BBB")]
        result = compare_allocs(new, old, None, 1)
        flts = _flt_nos(result["highlights"])
        assert "EJU0001" in flts

    def test_flights_vides(self):
        result = compare_allocs([], [], [], 0)
        assert result["highlights"] == []
        assert result["cancelled"] == []

    def test_nouveau_vol_ignore(self):
        """Un vol présent dans new mais absent de old ne déclenche pas de highlight."""
        old = [_flt("EJU0001", "NCE", "BOD")]
        new = [_flt("EJU0001", "NCE", "BOD"), _flt("EJU0002", "NCE", "ORY")]
        result = compare_allocs(new, old, [], 1)
        flts = _flt_nos(result["highlights"])
        assert "EJU0002" not in flts

    def test_vol_supprime_dans_cancelled(self):
        """Un vol absent de new mais présent dans old apparaît dans cancelled."""
        old = [_flt("EJU0001", "NCE", "BOD"), _flt("EJU0002", "NCE", "ORY")]
        new = [_flt("EJU0001", "NCE", "BOD")]
        result = compare_allocs(new, old, [], 1)
        assert result["highlights"] == []
        cancelled_nos = {f["flt_no"] for f in result["cancelled"]}
        assert "EJU0002" in cancelled_nos

    def test_new_color_index_applique(self):
        old = [_flt("EJU0001", "NCE", "BOD", ac_reg="OE-AAA")]
        new = [_flt("EJU0001", "NCE", "BOD", ac_reg="OE-BBB")]
        for ci in range(4):
            result = compare_allocs(new, old, [], ci)
            assert result["highlights"][0]["color_index"] == ci

    def test_pas_de_doublon_flt_no(self):
        old = [
            _flt("EJU0001", "BOD", "NCE", "06:00", "07:00"),
            _flt("EJU0002", "NCE", "BOD", "08:00", "09:00"),
        ]
        new = [
            _flt("EJU0001", "BOD", "NCE", "06:00", "07:00"),
            _flt("EJU0099", "NCE", "ORY", "08:00", "09:00"),
        ]
        result = compare_allocs(new, old, [], 2)
        flts = [h["flt_no"] for h in result["highlights"]]
        assert len(flts) == len(set(flts))

    def test_immat_seule_partial_true(self):
        """Même FLT_NO, DEP, ARR, STD mais ac_reg différente → partial=True."""
        old = [_flt("EJU0001", "NCE", "BOD", std="06:00", ac_reg="OE-AAA")]
        new = [_flt("EJU0001", "NCE", "BOD", std="06:00", ac_reg="OE-BBB")]
        result = compare_allocs(new, old, [], 1)
        assert len(result["highlights"]) == 1
        h = result["highlights"][0]
        assert h["flt_no"] == "EJU0001"
        assert h["partial"] is True

    def test_immat_et_arr_changes_partial_false(self):
        """Même FLT_NO mais ARR différent (+ ac_reg) → partial=False."""
        old = [_flt("EJU0001", "NCE", "BOD", std="06:00", ac_reg="OE-AAA")]
        new = [_flt("EJU0001", "NCE", "ORY", std="06:00", ac_reg="OE-BBB")]
        result = compare_allocs(new, old, [], 1)
        assert len(result["highlights"]) == 1
        h = result["highlights"][0]
        assert h["flt_no"] == "EJU0001"
        assert h["partial"] is False

    def test_rotation_nce_partial_false(self):
        """Rotation NCE changée → partial=False pour tous les vols impliqués."""
        old = [
            _flt("EJU0001", "BOD", "NCE", "06:00", "07:00"),
            _flt("EJU0002", "NCE", "BOD", "08:00", "09:00"),
        ]
        new = [
            _flt("EJU0001", "BOD", "NCE", "06:00", "07:00"),
            _flt("EJU0099", "NCE", "ORY", "08:00", "09:00"),
        ]
        result = compare_allocs(new, old, [], 1)
        for h in result["highlights"]:
            assert h["partial"] is False

    def test_immat_seule_puis_rotation_override_partial(self):
        """Si un vol a une immat-only change mais est aussi dans une rotation
        changée, la rotation prime → partial=False."""
        old = [
            _flt("EJU0001", "BOD", "NCE", "06:00", "07:00", ac_reg="OE-AAA"),
            _flt("EJU0002", "NCE", "BOD", "08:00", "09:00", ac_reg="OE-AAA"),
        ]
        new = [
            # EJU0001 : même route, ac_reg différente → immat-only candidat
            _flt("EJU0001", "BOD", "NCE", "06:00", "07:00", ac_reg="OE-BBB"),
            # Rotation changée : EJU0001 est maintenant suivi de EJU0099 (pas EJU0002)
            _flt("EJU0099", "NCE", "ORY", "08:00", "09:00", ac_reg="OE-BBB"),
        ]
        result = compare_allocs(new, old, [], 1)
        h_map = {h["flt_no"]: h for h in result["highlights"]}
        # EJU0001 est dans la rotation changée → partial=False malgré l'immat-only
        assert h_map["EJU0001"]["partial"] is False


# ===========================================================================
# compare_allocs — test d'intégration : pré-alloc vs alloc finale
# ===========================================================================

@pytest.fixture(scope="module")
def highlights_allocs(pre_flights, final_flights):
    return compare_allocs(final_flights, pre_flights, [], 1)["highlights"]


class TestCompareAllocsReel:
    def test_retourne_liste(self, highlights_allocs):
        assert isinstance(highlights_allocs, list)

    def test_color_index_new(self, highlights_allocs):
        assert all(h["color_index"] == 1 for h in highlights_allocs)

    def test_pas_de_doublon(self, highlights_allocs):
        flts = [h["flt_no"] for h in highlights_allocs]
        assert len(flts) == len(set(flts))

    def test_changements_immat_ou_rotation_trouves(self, highlights_allocs):
        """Il doit y avoir au moins un changement entre pré-alloc et alloc finale."""
        assert len(highlights_allocs) > 0

    def test_fusion_avec_highlights_fj(self, pre_flights, final_flights, fj_flights):
        """Scénario complet : on part des highlights FJ (color=0) et on ajoute
        les changements pré→finale (color=1). Les vols qui ont changé dans les
        deux passes doivent avoir color=1."""
        hl_fj = compare_with_feuille_journee(final_flights, fj_flights)
        hl_merged = compare_allocs(final_flights, pre_flights, hl_fj, 1)["highlights"]

        flts_ci = {h["flt_no"]: h["color_index"] for h in hl_merged}

        # Toutes les couleurs sont 0 ou 1
        assert all(ci in {0, 1} for ci in flts_ci.values())
        # Au moins un vol a color=0 (FJ-only) et au moins un a color=1
        assert any(ci == 0 for ci in flts_ci.values())
        assert any(ci == 1 for ci in flts_ci.values())
