"""Tests unitaires pour build_allocation.

Fixtures synthétiques — pas de dépendance au PDF.
"""
import pytest
from services.alloc_builder import build_allocation, _format_date, _crew_str, CAPACITY


# ---------------------------------------------------------------------------
# Factory helper
# ---------------------------------------------------------------------------

def flt(
    flt_no, dep, arr, std, sta="09:00",
    ac_reg="OE-AAA", ac_type="320",
    pax=150, crew="FC-2 / CC-4", dh=0,
    captain=None, date="27.06",
):
    return {
        "date": date, "flt_no": flt_no, "dep": dep, "arr": arr,
        "std": std, "sta": sta, "ac_reg": ac_reg, "ac_type": ac_type,
        "pax": pax, "crew": crew, "dh": dh, "captain": captain,
    }


# ---------------------------------------------------------------------------
# Helpers unitaires
# ---------------------------------------------------------------------------

class TestFormatDate:
    def test_juin(self):
        assert _format_date("27.06") == "27 JUN"

    def test_zero_pad(self):
        assert _format_date("03.01") == "03 JAN"

    def test_decembre(self):
        assert _format_date("31.12") == "31 DEC"

    def test_mauvais_format(self):
        # Ne doit pas lever d'exception
        assert _format_date("invalid") == "invalid"


class TestCrewStr:
    def test_2_4(self):
        assert _crew_str("FC-2 / CC-4", 0) == "2+4/0"

    def test_2_5(self):
        assert _crew_str("FC-2 / CC-5", 0) == "2+5/0"

    def test_1_4(self):
        assert _crew_str("FC-1 / CC-4", 0) == "1+4/0"

    def test_dh_non_zero(self):
        assert _crew_str("FC-3 / CC-4", 1) == "3+4/1"

    def test_espaces_variables(self):
        assert _crew_str("FC-2 / CC-4", 0) == "2+4/0"


class TestCapacity:
    def test_319(self):
        assert CAPACITY["319"] == 156

    def test_320(self):
        assert CAPACITY["320"] == 186

    def test_321(self):
        assert CAPACITY["321"] == 220


# ---------------------------------------------------------------------------
# build_allocation — cas vide
# ---------------------------------------------------------------------------

def test_vide():
    r = build_allocation([])
    assert r["date"] == ""
    assert r["based"] == []
    assert r["autres_rotations"] == []
    assert r["swap_refs"] == []
    assert r["ferry"] == []


# ---------------------------------------------------------------------------
# Catégorie BASED
# ---------------------------------------------------------------------------

class TestBased:
    def _flights(self):
        return [
            flt("EJU1001", "NCE", "OLB", "06:00", ac_reg="OE-IJR"),
            flt("EJU1002", "OLB", "NCE", "07:30", ac_reg="OE-IJR"),
            flt("EJU1003", "NCE", "PMI", "10:00", ac_reg="OE-IJR"),
            flt("EJU1004", "PMI", "NCE", "12:00", ac_reg="OE-IJR"),
        ]

    def test_dans_based(self):
        r = build_allocation(self._flights())
        assert len(r["based"]) == 1
        assert r["based"][0]["ac_reg"] == "OE-IJR"

    def test_new_based_false(self):
        r = build_allocation(self._flights())
        assert r["based"][0]["new_based"] is False

    def test_nb_vols(self):
        r = build_allocation(self._flights())
        assert len(r["based"][0]["flights"]) == 4

    def test_ordre_std(self):
        # Vols mélangés en entrée → resortis par STD
        shuffled = [
            flt("EJU1004", "PMI", "NCE", "12:00", ac_reg="OE-IJR"),
            flt("EJU1001", "NCE", "OLB", "06:00", ac_reg="OE-IJR"),
            flt("EJU1003", "NCE", "PMI", "10:00", ac_reg="OE-IJR"),
            flt("EJU1002", "OLB", "NCE", "07:30", ac_reg="OE-IJR"),
        ]
        r = build_allocation(shuffled)
        stds = [f["std"] for f in r["based"][0]["flights"]]
        assert stds == sorted(stds)

    def test_capacity_injectee(self):
        r = build_allocation(self._flights())
        assert r["based"][0]["flights"][0]["capacity"] == 186  # type 320

    def test_crew_str_format(self):
        r = build_allocation(self._flights())
        assert r["based"][0]["flights"][0]["crew_str"] == "2+4/0"

    def test_pas_dans_autres_categories(self):
        r = build_allocation(self._flights())
        assert r["autres_rotations"] == []
        assert r["swap_refs"] == []
        assert r["ferry"] == []


class TestNewBased:
    """Avion qui n'était pas à NCE le matin mais y revient le soir."""

    def _flights(self):
        return [
            flt("EZY0001", "LGW", "NCE", "05:00", ac_reg="G-UZHF"),
            flt("EZY0002", "NCE", "OLB", "08:00", ac_reg="G-UZHF"),
            flt("EZY0003", "OLB", "NCE", "10:00", ac_reg="G-UZHF"),
        ]

    def test_dans_based(self):
        r = build_allocation(self._flights())
        assert len(r["based"]) == 1

    def test_new_based_true(self):
        r = build_allocation(self._flights())
        assert r["based"][0]["new_based"] is True

    def test_pas_dans_autres(self):
        r = build_allocation(self._flights())
        assert r["autres_rotations"] == [] and r["swap_refs"] == []


# ---------------------------------------------------------------------------
# Catégorie AUTRES_ROTATIONS
# ---------------------------------------------------------------------------

class TestAutresRotations:
    """LGW→NCE→LGW : rotation complète, non basé."""

    def _flights(self):
        return [
            flt("EZY8417", "LGW", "NCE", "05:00", ac_reg="G-UZHF"),
            flt("EZY8418", "NCE", "LGW", "07:40", ac_reg="G-UZHF"),
        ]

    def test_dans_autres_rotations(self):
        r = build_allocation(self._flights())
        assert len(r["autres_rotations"]) == 1
        assert r["autres_rotations"][0]["ac_reg"] == "G-UZHF"

    def test_new_based_false(self):
        r = build_allocation(self._flights())
        assert r["autres_rotations"][0]["new_based"] is False

    def test_pas_dans_based(self):
        r = build_allocation(self._flights())
        assert r["based"] == []

    def test_multi_rotations_meme_avion(self):
        """PMI→NCE→PMI→NCE→PMI : première et dernière arrivée identiques."""
        flights = [
            flt("EJU7293", "PMI", "NCE", "12:00", ac_reg="OE-LQQ"),
            flt("EJU7294", "NCE", "PMI", "14:10", ac_reg="OE-LQQ"),
        ]
        r = build_allocation(flights)
        assert len(r["autres_rotations"]) == 1
        assert len(r["autres_rotations"][0]["flights"]) == 2

    def test_tri_alpha_multi_avions(self):
        """Plusieurs avions non basés → triés alphabétiquement."""
        flights = [
            flt("E001", "LGW", "NCE", "05:00", ac_reg="G-ZZZZ"),
            flt("E002", "NCE", "LGW", "08:00", ac_reg="G-ZZZZ"),
            flt("E003", "LGW", "NCE", "06:00", ac_reg="G-AAAA"),
            flt("E004", "NCE", "LGW", "09:00", ac_reg="G-AAAA"),
        ]
        r = build_allocation(flights)
        regs = [e["ac_reg"] for e in r["autres_rotations"]]
        assert regs == sorted(regs)


# ---------------------------------------------------------------------------
# Catégorie SWAP (référencé dans swap_refs, vol dans autres_rotations)
# ---------------------------------------------------------------------------

class TestSwap:
    """GVA→NCE→BSL : passe par NCE, premier dep ≠ dernier arr → swap."""

    def _flights(self):
        return [
            flt("EZS1393", "GVA", "NCE", "04:25", ac_reg="HB-JYA"),
            flt("EZS1058", "NCE", "BSL", "06:30", ac_reg="HB-JYA"),
        ]

    def test_dans_autres_rotations(self):
        r = build_allocation(self._flights())
        assert len(r["autres_rotations"]) == 1
        assert r["autres_rotations"][0]["ac_reg"] == "HB-JYA"

    def test_dans_swap_refs(self):
        r = build_allocation(self._flights())
        assert r["swap_refs"] == ["HB-JYA"]

    def test_pas_dans_based_ferry(self):
        r = build_allocation(self._flights())
        assert r["based"] == [] and r["ferry"] == []

    def test_swap_3_vols_new_based(self):
        """MAN→NCE→LHR→NCE : last_arr=NCE → based (new_based), pas swap."""
        flights = [
            flt("X001", "MAN", "NCE", "07:00", ac_reg="G-SWAP"),
            flt("X002", "NCE", "LHR", "09:00", ac_reg="G-SWAP"),
            flt("X003", "LHR", "NCE", "12:00", ac_reg="G-SWAP"),
        ]
        r = build_allocation(flights)
        assert r["based"][0]["ac_reg"] == "G-SWAP"
        assert r["based"][0]["new_based"] is True
        assert r["swap_refs"] == []

    def test_swap_3_vols_asymetrique(self):
        """LHR→NCE→MAD→FCO : first_dep≠last_arr, passe par NCE → swap_refs."""
        flights = [
            flt("X001", "LHR", "NCE", "07:00", ac_reg="G-SWAP"),
            flt("X002", "NCE", "MAD", "09:00", ac_reg="G-SWAP"),
            flt("X003", "MAD", "FCO", "12:00", ac_reg="G-SWAP"),
        ]
        r = build_allocation(flights)
        assert r["swap_refs"] == ["G-SWAP"]
        assert r["autres_rotations"][0]["ac_reg"] == "G-SWAP"

    def test_rotation_symetrique_pas_swap(self):
        """GVA→NCE→GVA : first_dep == last_arr → dans autres_rotations, PAS dans swap_refs."""
        flights = [
            flt("EZS1001", "GVA", "NCE", "05:00", ac_reg="HB-JYA"),
            flt("EZS1002", "NCE", "GVA", "07:00", ac_reg="HB-JYA"),
        ]
        r = build_allocation(flights)
        assert r["autres_rotations"][0]["ac_reg"] == "HB-JYA"
        assert r["swap_refs"] == []

    def test_deux_swaps_dans_refs(self):
        """Deux avions en swap → swap_refs trié alphabétiquement."""
        flights = [
            flt("EZS1055", "BSL", "NCE", "04:35", ac_reg="HB-JZR"),
            flt("EZS1402", "NCE", "GVA", "06:30", ac_reg="HB-JZR"),
            flt("EZS1393", "GVA", "NCE", "04:25", ac_reg="HB-JYA"),
            flt("EZS1056", "NCE", "BSL", "06:30", ac_reg="HB-JYA"),
        ]
        r = build_allocation(flights)
        assert sorted(r["swap_refs"]) == ["HB-JYA", "HB-JZR"]
        regs = [e["ac_reg"] for e in r["autres_rotations"]]
        assert "HB-JYA" in regs and "HB-JZR" in regs


# ---------------------------------------------------------------------------
# Catégorie FERRY
# ---------------------------------------------------------------------------

class TestFerry:
    """Avion sans contact avec NCE → ferry (cas de repli)."""

    def test_ferry_sans_nce(self):
        flights = [flt("X999", "LHR", "BER", "08:00", ac_reg="G-FERR")]
        r = build_allocation(flights)
        assert len(r["ferry"]) == 1
        assert r["ferry"][0]["ac_reg"] == "G-FERR"

    def test_ferry_pas_dans_autres(self):
        flights = [flt("X999", "LHR", "BER", "08:00", ac_reg="G-FERR")]
        r = build_allocation(flights)
        assert r["based"] == [] and r["autres_rotations"] == [] and r["swap_refs"] == []


# ---------------------------------------------------------------------------
# Crew change
# ---------------------------------------------------------------------------

class TestCrewChange:
    def _flights_same_captain(self):
        return [
            flt("EJU1001", "NCE", "OLB", "06:00", ac_reg="OE-IJR",
                captain="DURAND PIERRE"),
            flt("EJU1002", "OLB", "NCE", "08:00", ac_reg="OE-IJR",
                captain="DURAND PIERRE"),
        ]

    def _flights_diff_captain(self):
        return [
            flt("EJU1001", "NCE", "OLB", "06:00", ac_reg="OE-IJR",
                captain="DURAND PIERRE"),
            flt("EJU1002", "OLB", "NCE", "08:00", ac_reg="OE-IJR",
                captain="MARTIN JEAN"),
        ]

    def test_pas_de_changement(self):
        r = build_allocation(self._flights_same_captain())
        flights = r["based"][0]["flights"]
        assert flights[0]["crew_change_before"] is False
        assert flights[1]["crew_change_before"] is False

    def test_changement_detecte(self):
        r = build_allocation(self._flights_diff_captain())
        flights = r["based"][0]["flights"]
        assert flights[0]["crew_change_before"] is False   # premier vol : pas de précédent
        assert flights[1]["crew_change_before"] is True    # deuxième vol : capitaine différent

    def test_pas_de_changement_si_captain_none(self):
        """Sans info capitaine (pré-alloc), on ne marque pas de crew change."""
        flights = [
            flt("EJU1001", "NCE", "OLB", "06:00", ac_reg="OE-IJR", captain=None),
            flt("EJU1002", "OLB", "NCE", "08:00", ac_reg="OE-IJR", captain=None),
        ]
        r = build_allocation(flights)
        assert not any(f["crew_change_before"] for f in r["based"][0]["flights"])

    def test_pas_de_changement_si_un_seul_captain_connu(self):
        """Un des deux capitaines inconnu → pas de marqueur."""
        flights = [
            flt("EJU1001", "NCE", "OLB", "06:00", ac_reg="OE-IJR", captain=None),
            flt("EJU1002", "OLB", "NCE", "08:00", ac_reg="OE-IJR", captain="MARTIN JEAN"),
        ]
        r = build_allocation(flights)
        assert r["based"][0]["flights"][1]["crew_change_before"] is False


# ---------------------------------------------------------------------------
# Tri global et multi-avions
# ---------------------------------------------------------------------------

class TestTriGlobal:
    def test_std_croissant_inter_avions(self):
        """Vols de deux avions mélangés : vérifier que chaque groupe est trié."""
        flights = [
            flt("A004", "PMI", "NCE", "12:00", ac_reg="OE-IJR"),
            flt("A001", "NCE", "OLB", "06:00", ac_reg="OE-IJR"),
            flt("B002", "LGW", "NCE", "07:00", ac_reg="G-UZHF"),
            flt("A002", "OLB", "NCE", "07:30", ac_reg="OE-IJR"),
            flt("B001", "NCE", "LGW", "09:00", ac_reg="G-UZHF"),  # STD APRES B002
            flt("A003", "NCE", "PMI", "10:00", ac_reg="OE-IJR"),
        ]
        r = build_allocation(flights)
        # OE-IJR est basé NCE
        oe_stds = [f["std"] for f in r["based"][0]["flights"]]
        assert oe_stds == sorted(oe_stds)
        # G-UZHF est autres_rotations
        g_stds = [f["std"] for f in r["autres_rotations"][0]["flights"]]
        assert g_stds == sorted(g_stds)

    def test_ac_reg_alpha_a_std_egal(self):
        """À STD égal, l'ordre est déterminé par ac_reg alphabétique."""
        flights = [
            flt("Z001", "NCE", "OLB", "06:00", ac_reg="OE-ZZZ"),
            flt("A001", "NCE", "LGW", "06:00", ac_reg="OE-AAA"),
        ]
        r = build_allocation(flights)
        regs = [e["ac_reg"] for e in r["based"]]
        assert regs == ["OE-AAA", "OE-ZZZ"]

    def test_date_extraite(self):
        flights = [flt("EJU1001", "NCE", "OLB", "06:00")]
        assert build_allocation(flights)["date"] == "27 JUN"


# ---------------------------------------------------------------------------
# Intégration avec données réelles
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def real_result():
    from pathlib import Path
    from services.pdf_parser import parse_easyjet_allocation
    pdf = Path(__file__).resolve().parents[4] / "workflow" / "FlightAllocationReport (1).pdf"
    return build_allocation(parse_easyjet_allocation(str(pdf)))


def test_integ_date(real_result):
    assert real_result["date"] == "27 JUN"

def test_integ_nb_based(real_result):
    assert len(real_result["based"]) == 5

def test_integ_based_tri_alpha(real_result):
    regs = [e["ac_reg"] for e in real_result["based"]]
    assert regs == sorted(regs)

def test_integ_oe_ijr_est_based(real_result):
    assert "OE-IJR" in [e["ac_reg"] for e in real_result["based"]]

def test_integ_oe_ijr_8_vols(real_result):
    entry = next(e for e in real_result["based"] if e["ac_reg"] == "OE-IJR")
    assert len(entry["flights"]) == 8

def test_integ_nb_autres_rotations(real_result):
    # Les 2 avions en swap (HB-JYA, HB-JZR) sont désormais dans autres_rotations
    assert len(real_result["autres_rotations"]) == 30

def test_integ_autres_rotations_tri_alpha(real_result):
    regs = [e["ac_reg"] for e in real_result["autres_rotations"]]
    assert regs == sorted(regs)

def test_integ_nb_swap_refs(real_result):
    assert len(real_result["swap_refs"]) == 2

def test_integ_swap_refs_regs(real_result):
    assert sorted(real_result["swap_refs"]) == ["HB-JYA", "HB-JZR"]

def test_integ_swaps_dans_autres_rotations(real_result):
    regs = {e["ac_reg"] for e in real_result["autres_rotations"]}
    assert "HB-JYA" in regs and "HB-JZR" in regs

def test_integ_ferry_vide(real_result):
    assert real_result["ferry"] == []

def test_integ_capacity(real_result):
    for cat in ("based", "autres_rotations"):
        for entry in real_result[cat]:
            for f in entry["flights"]:
                assert f["capacity"] in (156, 186, 220)

def test_integ_crew_str_format(real_result):
    import re
    pat = re.compile(r"^\d+\+\d+/\d+$")
    for cat in ("based", "autres_rotations"):
        for entry in real_result[cat]:
            for f in entry["flights"]:
                assert pat.match(f["crew_str"]), f["crew_str"]

def test_integ_captain_oe_ijr(real_result):
    entry = next(e for e in real_result["based"] if e["ac_reg"] == "OE-IJR")
    assert entry["flights"][0]["captain"] == "DURENDEAU DAVID"

def test_integ_premier_vol_jamais_crew_change(real_result):
    for cat in ("based", "autres_rotations"):
        for entry in real_result[cat]:
            assert entry["flights"][0]["crew_change_before"] is False
