"""
Extraction Night Stop et First Wave à partir des vols bruts.
"""


def extract_night_stop(flights: list[dict]) -> list[dict]:
    """Retourne les avions dont le dernier vol de la journée arrive à NCE.

    Triés par ac_reg alphabétique.
    """
    by_reg: dict[str, list[dict]] = {}
    for f in flights:
        by_reg.setdefault(f["ac_reg"], []).append(f)

    result = []
    for ac_reg in sorted(by_reg):
        # Le dernier vol = celui dont la STA est la plus tardive
        last = max(by_reg[ac_reg], key=lambda x: x["sta"])
        if last["arr"] == "NCE":
            result.append({
                "ac_reg":   ac_reg,
                "last_arr": "NCE",
                "last_sta": last["sta"],
            })
    return result


def extract_first_wave(flights: list[dict]) -> list[dict]:
    """Retourne le premier départ NCE de chaque avion, trié par STD croissant.

    Seuls les avions dont le premier vol part de NCE sont inclus.
    """
    by_reg: dict[str, list[dict]] = {}
    for f in flights:
        by_reg.setdefault(f["ac_reg"], []).append(f)

    result = []
    for ac_reg, ac_flights in by_reg.items():
        first = min(ac_flights, key=lambda x: x["std"])
        if first["dep"] == "NCE":
            result.append({
                "flt_no":  first["flt_no"],
                "ac_reg":  ac_reg,
                "dep":     "NCE",
                "arr":     first["arr"],
                "std":     first["std"],
                "sta":     first["sta"],
                "ac_type": first["ac_type"],
                "date":    first["date"],
            })

    return sorted(result, key=lambda x: x["std"])


def extract_night_stop_per_aircraft(
    flights: list[dict],
    based_regs: list[str],
) -> dict[str, dict]:
    """Pour une liste de vols (alloc de la veille), retourne pour chaque immat basée
    son dernier vol arrivant à NCE.

    Retourne un dict :
        { "OE-ICI": {"flt_no": "EJU1704", "dep": "IBZ", "arr": "NCE",
                     "sta": "2105", "date": "26.06"}, ... }

    - Filtre uniquement les vols dont ARR == "NCE"
    - Pour chaque ac_reg, prend celui avec la STA la plus tardive
    - Ne retient que les ac_reg présentes dans based_regs
    """
    based_set = set(based_regs)
    by_reg: dict[str, list[dict]] = {}
    for f in flights:
        if f["arr"] == "NCE" and f["ac_reg"] in based_set:
            by_reg.setdefault(f["ac_reg"], []).append(f)

    result: dict[str, dict] = {}
    for ac_reg, ac_flights in by_reg.items():
        last = max(ac_flights, key=lambda x: x["sta"])
        result[ac_reg] = {
            "flt_no": last["flt_no"],
            "dep":    last["dep"],
            "arr":    last["arr"],
            "sta":    last["sta"],
            "date":   last["date"],
        }
    return result
