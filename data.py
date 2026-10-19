"""Built-in datasets for the CGD gas-allocation simulator.

Every dataset is a dict with the same keys (see `empty_like`):
  settings, nodes, tiers, demand, sources, contract, supply, source_cost,
  prices, corridors, cap_factor, mitigation

Volumes are in the dataset's own unit (settings['unit']); money is ₹/SCM.
`settings['scm_per_unit']` converts the volume unit to SCM so that totals can be
shown in ₹ / ₹ crore.
"""
from __future__ import annotations

import io

import numpy as np
import pandas as pd

MCOLS = lambda T: [f"M{t}" for t in range(1, T + 1)]  # noqa: E731

SECTORS = ["PNG Households", "CNG Stations", "Commercial", "Industries"]


# --------------------------------------------------------------------------------------
# 1. MGL-based 24-month dataset (Jul-2024 .. Jun-2026)
# --------------------------------------------------------------------------------------
# Reported quarterly average sales volumes, MMSCMD (MGL incl. erstwhile UEPL), from MGL
# investor presentation Q2 FY26, Q3 FY26 earnings call, Q4 FY25 call and Q1 FY27 release.
MGL_QUARTERS = [
    # label,    CNG,   Domestic PNG, Industrial+Commercial
    ("Q2 FY25", 3.038, 0.530, 0.637),
    ("Q3 FY25", 3.098, 0.554, 0.659),
    ("Q4 FY25", 3.123, 0.609, 0.670),
    ("Q1 FY26", 3.185, 0.571, 0.698),
    ("Q2 FY26", 3.255, 0.582, 0.757),
    ("Q3 FY26", 3.281, 0.604, 0.735),
    ("Q4 FY26", 3.349, 0.605, 0.719),
    ("Q1 FY27", 3.496, 0.623, 0.648),
]
MGL_MONTHS = ["Jul-24", "Aug-24", "Sep-24", "Oct-24", "Nov-24", "Dec-24", "Jan-25", "Feb-25",
              "Mar-25", "Apr-25", "May-25", "Jun-25", "Jul-25", "Aug-25", "Sep-25", "Oct-25",
              "Nov-25", "Dec-25", "Jan-26", "Feb-26", "Mar-26", "Apr-26", "May-26", "Jun-26"]
MGL_DAYS = [31, 31, 30, 31, 30, 31, 31, 28, 31, 30, 31, 30,
            31, 31, 30, 31, 30, 31, 31, 28, 31, 30, 31, 30]

# Within-quarter seasonal shape (mean 1.0): CNG dips in monsoon, domestic PNG peaks in winter.
SEAS = {
    "CNG": [0.985, 0.990, 1.025, 1.005, 0.995, 1.000, 1.000, 0.995, 1.005, 0.995, 1.005, 1.000,
            0.985, 0.990, 1.025, 1.005, 0.995, 1.000, 1.000, 0.995, 1.005, 0.995, 1.005, 1.000],
    "DOM": [1.000, 0.990, 1.010, 0.985, 1.000, 1.015, 1.025, 1.000, 0.975, 0.990, 1.005, 1.005,
            1.000, 0.990, 1.010, 0.985, 1.000, 1.015, 1.025, 1.000, 0.975, 0.990, 1.005, 1.005],
    "IC": [0.995, 1.000, 1.005, 0.990, 1.000, 1.010, 1.005, 0.995, 1.000, 1.010, 1.000, 0.990,
           0.995, 1.000, 1.005, 0.990, 1.000, 1.010, 1.005, 0.995, 1.000, 1.010, 1.000, 0.990],
}

# Node split of segment volume (modelled; MGL does not publish zone-wise volumes)
NODE_SPLIT = {
    "A": ("CNG", 0.60), "B": ("CNG", 0.40),
    "P1": ("DOM", 0.30), "P2": ("DOM", 0.30), "P3": ("DOM", 0.22), "P4": ("DOM", 0.18),
    "I1": ("IC", 0.80), "I2": ("IC", 0.20),   # industrial ~13.5 % vs commercial ~3.4 % of sales
}


def _monthly_segment(seg_idx: int, key: str) -> np.ndarray:
    out = []
    for q, row in enumerate(MGL_QUARTERS):
        avg = row[seg_idx]
        for m in range(3):
            i = q * 3 + m
            out.append(avg * SEAS[key][i] * MGL_DAYS[i])
    return np.array(out)


def _q(vals_per_quarter):
    """Expand 8 quarterly MMSCMD values to 24 monthly MMSCM values."""
    return np.array([vals_per_quarter[i // 3] * MGL_DAYS[i] for i in range(24)])


def mgl_dataset() -> dict:
    T = 24
    M = MCOLS(T)
    seg = {"CNG": _monthly_segment(1, "CNG"), "DOM": _monthly_segment(2, "DOM"),
           "IC": _monthly_segment(3, "IC")}

    nodes = pd.DataFrame([
        ("A", "CNG cluster – Mumbai city & suburbs", "CNG Stations", 2),
        ("B", "CNG cluster – Thane / Navi Mumbai", "CNG Stations", 2),
        ("P1", "Domestic PNG – Mumbai island city", "PNG Households", 1),
        ("P2", "Domestic PNG – Mumbai suburbs", "PNG Households", 1),
        ("P3", "Domestic PNG – Thane & Mira-Bhayandar", "PNG Households", 1),
        ("P4", "Domestic PNG – Navi Mumbai & Raigad", "PNG Households", 1),
        ("I1", "Industrial PNG – Taloja / Raigad MIDC", "Industries", 4),
        ("I2", "Commercial PNG – hotels, hospitals, offices", "Commercial", 3),
    ], columns=["Node", "Name", "Sector", "Tier"])

    tiers = pd.DataFrame([
        (1, "PNG Households", 1.00, 1000.0, True),
        (2, "CNG Stations", 0.95, 25.0, False),
        (3, "Commercial", 0.90, 15.0, False),
        (4, "Industries", 0.80, 5.0, False),
    ], columns=["Tier", "Customer", "MinService", "Penalty", "NonCurtailable"])

    dem_rows = []
    for n, (key, share) in NODE_SPLIT.items():
        dem_rows.append([n] + list(np.round(seg[key] * share, 3)))
    demand = pd.DataFrame(dem_rows, columns=["Node"] + M)

    sources = pd.DataFrame([
        ("APM", "APM domestic gas (MoPNG allocation)", "GAIL (MoPNG/PPAC allocation)",
         "PNG Households;CNG Stations", 0.0, "PNG Households"),
        ("NWG", "New Well Gas (ONGC)", "GAIL / ONGC", "PNG Households;CNG Stations", 0.0, ""),
        ("HPHT", "HP-HT domestic gas", "RIL-BP / ONGC (via IGX & contracts)", "All", 0.8, ""),
        ("RLNG_T", "Term RLNG (Henry-Hub / Brent linked)", "GAIL / BPCL (term LNG)", "All", 0.8, ""),
        ("RLNG_S", "Spot RLNG / IGX", "Spot LNG traders / IGX", "All", 0.0, ""),
    ], columns=["Source", "Name", "Supplier", "Eligible", "TakeOrPay", "PriorityTo"])

    # MMSCMD by quarter (contracted / allocated). APM reflects the Oct & Nov-2024 cuts.
    apm = _q([2.45, 2.00, 1.92, 1.82, 1.80, 1.80, 1.80, 1.82])
    apm[3] = 2.20 * MGL_DAYS[3]  # Oct-24: first cut (16-Oct-2024)
    nwg = _q([0.00, 0.17, 0.25, 0.26, 0.27, 0.27, 0.28, 0.28])
    nwg[3] = 0.0
    hpht = _q([0.50, 0.55, 0.55, 0.58, 0.60, 0.60, 0.62, 0.62])
    rlt = _q([0.95, 1.05, 1.10, 1.30, 1.40, 1.45, 1.55, 1.65])
    rls = _q([0.80, 0.90, 0.90, 0.90, 0.90, 0.95, 0.95, 1.00])
    contract = pd.DataFrame([[s] + list(np.round(v, 3)) for s, v in
                             zip(sources.Source, [apm, nwg, hpht, rlt, rls])], columns=["Source"] + M)
    supply = contract.copy()

    # Landed cost at CGS, ₹/SCM (gas price + trunk tariff). Illustrative, see References.
    def path(*knots):  # knots: (month_index, value) piecewise constant
        v = np.zeros(T)
        for (i, val) in knots:
            v[i:] = val
        return v
    cost_apm = path((0, 25.5), (9, 26.5), (21, 27.0))
    cost_nwg = path((0, 33.0), (9, 32.0), (18, 31.5))
    cost_hpht = path((0, 37.0), (9, 36.0), (21, 38.0))
    cost_rlt = path((0, 38.5), (6, 40.0), (12, 38.0), (21, 41.5))
    cost_rls = path((0, 45.0), (6, 47.0), (12, 44.0), (21, 52.0))
    source_cost = pd.DataFrame([[s] + list(np.round(v, 2)) for s, v in
                                zip(sources.Source, [cost_apm, cost_nwg, cost_hpht, cost_rlt, cost_rls])],
                               columns=["Source"] + M)

    # Net realisation ₹/SCM (ex-VAT, net of dealer margin), from MGL retail price history.
    def cng_net(rs_kg):
        return round((rs_kg / 1.135 - 4.0) / 1.36, 2)
    cng_retail = path((0, 75.0), (4, 77.0), (9, 79.5), (14, 80.5), (19, 81.0), (22, 86.0))
    dom_retail = path((0, 48.0), (9, 49.0), (14, 49.5), (22, 52.0))
    prices = pd.DataFrame([
        ["PNG Households"] + [round(v / 1.03, 2) for v in dom_retail],
        ["CNG Stations"] + [cng_net(v) for v in cng_retail],
        ["Commercial"] + list(path((0, 66.0), (9, 67.0), (21, 72.0))),
        ["Industries"] + list(path((0, 57.0), (9, 56.0), (21, 61.0))),
    ], columns=["Sector"] + M)

    # 5 corridors exactly as in the problem-statement network (MMSCM/month)
    corridors = pd.DataFrame([
        (1, "G", "A", 1.20, 105.0),
        (2, "A", "B", 0.90, 41.8),
        (3, "G", "P1", 1.00, 19.6),
        (3, "G", "P2", 1.00, 19.6),
        (4, "P1", "P3", 0.80, 8.0),
        (4, "P1", "P4", 0.80, 8.0),
        (4, "P2", "P3", 0.80, 8.0),
        (4, "P2", "P4", 0.80, 8.0),
        (5, "G", "I1", 1.40, 22.0),
        (5, "G", "I2", 1.40, 22.0),
    ], columns=["Corridor", "From", "To", "Cost", "Capacity"])
    cap_factor = pd.DataFrame([[k] + [1.0] * T for k in range(1, 6)], columns=["Corridor"] + M)

    mitigation = pd.DataFrame([
        ("Emergency spot LNG cargo / IGX purchase", "supply", "G", 18.0, 56.0, True, "Supplier"),
        ("Gas swap / borrow from neighbouring CGD", "supply", "G", 6.0, 49.0, True, "Supplier"),
        ("Line-pack & pressure uplift (within MAOP, T4S)", "capacity", "all", 0.08, 2.5, True, "MGL"),
        ("Virtual pipeline: mobile cascades to CNG stations", "virtual", "A;B", 3.0, 7.0, True, "MGL"),
        ("LCNG skid injection into PNG DRS", "virtual", "P3;P4", 1.0, 10.0, True, "MGL"),
    ], columns=["Option", "Type", "Target", "MaxPerMonth", "Cost", "Enabled", "Side"])

    settings = {
        "name": "MGL 24-month data (Jul-2024 – Jun-2026)",
        "unit": "MMSCM/month", "scm_per_unit": 1e6, "opex": 5.0,
        "month_labels": MGL_MONTHS, "default_objective": "profit",
        "note": ("Segment volumes are MGL-reported quarterly averages (MMSCMD × days). Node split, "
                 "seasonal shape, corridor capacities and gas costs are modelled assumptions."),
    }
    return dict(settings=settings, nodes=nodes, tiers=tiers, demand=demand, sources=sources,
                contract=contract, supply=supply, source_cost=source_cost, prices=prices,
                corridors=corridors, cap_factor=cap_factor, mitigation=mitigation)


# --------------------------------------------------------------------------------------
# 2. Original problem-statement (poster) data, 12 months, SCM/month
# --------------------------------------------------------------------------------------
def _single_source_frames(T, avail, cost=30.0):
    M = MCOLS(T)
    sources = pd.DataFrame([("G", "City Gate supply", "GAIL (city-gate)", "All", 0.0, "")],
                           columns=["Source", "Name", "Supplier", "Eligible", "TakeOrPay", "PriorityTo"])
    contract = pd.DataFrame([["G"] + list(avail)], columns=["Source"] + M)
    supply = contract.copy()
    source_cost = pd.DataFrame([["G"] + [cost] * T], columns=["Source"] + M)
    prices = pd.DataFrame([
        ["PNG Households"] + [47.0] * T, ["CNG Stations"] + [50.0] * T,
        ["Commercial"] + [66.0] * T, ["Industries"] + [57.0] * T,
    ], columns=["Sector"] + M)
    cap_factor = pd.DataFrame([[k] + [1.0] * T for k in range(1, 6)], columns=["Corridor"] + M)
    return sources, contract, supply, source_cost, prices, cap_factor


def _three_tiers():
    return pd.DataFrame([
        (1, "PNG Households", 0.95, 20.0, False),
        (2, "CNG Stations", 0.90, 15.0, False),
        (3, "Industries", 0.80, 10.0, False),
    ], columns=["Tier", "Customer", "MinService", "Penalty", "NonCurtailable"])


def _nodes_basic():
    return pd.DataFrame([
        ("A", "CNG Stations A", "CNG Stations", 2), ("B", "CNG Stations B", "CNG Stations", 2),
        ("P1", "PNG node P1", "PNG Households", 1), ("P2", "PNG node P2", "PNG Households", 1),
        ("P3", "PNG node P3", "PNG Households", 1), ("P4", "PNG node P4", "PNG Households", 1),
        ("I1", "Industry I1", "Industries", 3), ("I2", "Industry I2", "Industries", 3),
    ], columns=["Node", "Name", "Sector", "Tier"])


def _corridors(caps, costs=(2.0, 1.5, 1.8, 1.2, 2.5)):
    c1, c2, c3, c4, c5 = caps
    k1, k2, k3, k4, k5 = costs
    return pd.DataFrame([
        (1, "G", "A", k1, c1), (2, "A", "B", k2, c2),
        (3, "G", "P1", k3, c3), (3, "G", "P2", k3, c3),
        (4, "P1", "P3", k4, c4), (4, "P1", "P4", k4, c4), (4, "P2", "P3", k4, c4), (4, "P2", "P4", k4, c4),
        (5, "G", "I1", k5, c5), (5, "G", "I2", k5, c5),
    ], columns=["Corridor", "From", "To", "Cost", "Capacity"])


def _mitigation_scaled(scale):
    return pd.DataFrame([
        ("Emergency spot LNG cargo / IGX purchase", "supply", "G", 0.06 * scale, 56.0, True, "Supplier"),
        ("Gas swap / borrow from neighbouring CGD", "supply", "G", 0.02 * scale, 49.0, True, "Supplier"),
        ("Line-pack & pressure uplift (within MAOP, T4S)", "capacity", "all", 0.08, 2.5, True, "MGL"),
        ("Virtual pipeline: mobile cascades to CNG stations", "virtual", "A;B", 0.01 * scale, 7.0, True, "MGL"),
        ("LCNG skid injection into PNG DRS", "virtual", "P3;P4", 0.004 * scale, 10.0, True, "MGL"),
    ], columns=["Option", "Type", "Target", "MaxPerMonth", "Cost", "Enabled", "Side"])


def original_dataset() -> dict:
    T = 12
    M = MCOLS(T)
    m1 = {"A": 2500, "B": 2000, "P1": 1800, "P2": 1600, "P3": 1700, "P4": 1400, "I1": 1500, "I2": 1000}
    m12 = {"A": 2700, "B": 2200, "P1": 2000, "P2": 1800, "P3": 1900, "P4": 1500, "I1": 1700, "I2": 1100}
    demand = pd.DataFrame([[n] + list(np.round(np.linspace(m1[n], m12[n], T))) for n in m1],
                          columns=["Node"] + M)
    avail = [11000, 11500, 11200, 11800, 12000, 12500, 12300, 11900, 11600, 11500, 11000, 10800]
    sources, contract, supply, source_cost, prices, cap_factor = _single_source_frames(T, avail)
    settings = {"name": "Original problem-statement data (12 months)", "unit": "SCM/month",
                "scm_per_unit": 1.0, "opex": 0.0,
                "month_labels": [f"M{t}" for t in range(1, T + 1)], "default_objective": "cost",
                "note": "Poster data. Month 2-11 demand interpolated linearly between Month 1 and Month 12."}
    return dict(settings=settings, nodes=_nodes_basic(), tiers=_three_tiers(), demand=demand,
                sources=sources, contract=contract, supply=supply, source_cost=source_cost,
                prices=prices, corridors=_corridors((10000, 8000, 12000, 9000, 6000)),
                cap_factor=cap_factor, mitigation=_mitigation_scaled(12000))


def demo_dataset() -> dict:
    """The 'corridors bind' demo set used by the earlier dashboard (from its export)."""
    T = 12
    M = MCOLS(T)
    dem = {
        "A": [2500, 2560, 2600, 2630, 2640, 2630, 2610, 2590, 2580, 2580, 2610, 2660],
        "B": [2000, 2050, 2090, 2120, 2130, 2120, 2110, 2100, 2090, 2100, 2130, 2170],
        "P1": [1800, 1850, 1880, 1910, 1920, 1920, 1910, 1900, 1890, 1900, 1930, 1970],
        "P2": [1600, 1640, 1680, 1700, 1720, 1720, 1710, 1700, 1700, 1710, 1740, 1770],
        "P3": [1700, 1740, 1780, 1810, 1820, 1820, 1810, 1800, 1800, 1810, 1830, 1870],
        "P4": [1400, 1430, 1460, 1470, 1470, 1470, 1450, 1440, 1430, 1440, 1450, 1480],
        "I1": [1500, 1540, 1580, 1600, 1610, 1610, 1610, 1600, 1600, 1610, 1640, 1670],
        "I2": [1000, 1020, 1040, 1060, 1060, 1060, 1050, 1050, 1040, 1050, 1060, 1080],
    }
    demand = pd.DataFrame([[n] + v for n, v in dem.items()], columns=["Node"] + M)
    avail = [14800, 14900, 15000, 14700, 14000, 13950, 14600, 14800, 14900, 14900, 14300, 14100]
    sources, contract, supply, source_cost, prices, cap_factor = _single_source_frames(T, avail)
    settings = {"name": "Demo data (corridors bind)", "unit": "SCM/month", "scm_per_unit": 1.0, "opex": 0.0,
                "month_labels": [f"M{t}" for t in range(1, T + 1)], "default_objective": "cost",
                "note": "Demo set from the earlier dashboard: corridor capacities set so corridors bind."}
    return dict(settings=settings, nodes=_nodes_basic(), tiers=_three_tiers(), demand=demand,
                sources=sources, contract=contract, supply=supply, source_cost=source_cost,
                prices=prices, corridors=_corridors((4700, 2080, 6850, 3200, 2650)),
                cap_factor=cap_factor, mitigation=_mitigation_scaled(14500))


def normalize(d: dict) -> dict:
    """Make every month column float so scenario shocks / edits never hit integer dtypes."""
    for key in ["demand", "contract", "supply", "source_cost", "prices", "cap_factor"]:
        cols = [c for c in d[key].columns if str(c).startswith("M") and str(c)[1:].isdigit()]
        d[key][cols] = d[key][cols].astype(float)
    for key, cols in [("corridors", ["Cost", "Capacity"]), ("tiers", ["MinService", "Penalty"]),
                      ("mitigation", ["MaxPerMonth", "Cost"]), ("sources", ["TakeOrPay"])]:
        d[key][cols] = d[key][cols].astype(float)
    return d


BUILTIN = {
    "MGL 24-month data (2024-26)": lambda: normalize(mgl_dataset()),
    "Original problem-statement data": lambda: normalize(original_dataset()),
    "Demo data (corridors bind)": lambda: normalize(demo_dataset()),
}

# --------------------------------------------------------------------------------------
# Excel template / upload
# --------------------------------------------------------------------------------------
SHEETS = ["Settings", "Nodes", "Tiers", "Demand", "Sources", "Contract", "Supply", "Source_Cost",
          "Prices", "Corridors", "Corridor_Cap_Factor", "Mitigation"]
KEYMAP = {"Nodes": "nodes", "Tiers": "tiers", "Demand": "demand", "Sources": "sources",
          "Contract": "contract", "Supply": "supply", "Source_Cost": "source_cost", "Prices": "prices",
          "Corridors": "corridors", "Corridor_Cap_Factor": "cap_factor", "Mitigation": "mitigation"}

README_ROWS = [
    ("Settings", "name, unit (label), opex (₹/SCM operating cost), scm_per_unit (1 for SCM, 1000000 for MMSCM), month_labels (comma separated), default_objective (profit/cost)"),
    ("Nodes", "Node id, Name, Sector (PNG Households / CNG Stations / Commercial / Industries), Tier"),
    ("Tiers", "Tier, Customer, MinService (0-1), Penalty (₹/SCM shortage), NonCurtailable (TRUE/FALSE)"),
    ("Demand", "Node, M1..MT demand per month"),
    ("Sources", "Source id, Name, Supplier, Eligible (sectors separated by ';' or 'All'), TakeOrPay (0-1), PriorityTo (sector served first from this source, e.g. APM → PNG Households)"),
    ("Contract", "Source, M1..MT contracted / allocated quantity"),
    ("Supply", "Source, M1..MT quantity actually delivered / available from supplier"),
    ("Source_Cost", "Source, M1..MT landed gas cost ₹/SCM"),
    ("Prices", "Sector, M1..MT net selling price ₹/SCM"),
    ("Corridors", "Corridor (1-5), From, To, Cost ₹/SCM, Capacity per month (shared by all rows of a corridor)"),
    ("Corridor_Cap_Factor", "Corridor, M1..MT availability factor (1 = full, 0.7 = 30 % outage)"),
    ("Mitigation", "Option, Type (supply/capacity/virtual), Target (G / all / corridor ids / nodes ';'), MaxPerMonth, Cost ₹/SCM, Enabled, Side (Supplier/MGL)"),
    ("Old format", "Files from the earlier dashboard (Input_nodes, Input_tiers, Input_demand, Input_supply, Input_corridors) are also accepted."),
]


def to_excel_bytes(data: dict) -> bytes:
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as xw:
        pd.DataFrame(README_ROWS, columns=["Sheet", "Columns / meaning"]).to_excel(xw, sheet_name="README", index=False)
        s = data["settings"]
        pd.DataFrame([
            ("name", s["name"]), ("unit", s["unit"]), ("scm_per_unit", s["scm_per_unit"]),
            ("opex", s.get("opex", 0.0)),
            ("month_labels", ",".join(s["month_labels"])), ("default_objective", s["default_objective"]),
        ], columns=["Key", "Value"]).to_excel(xw, sheet_name="Settings", index=False)
        for sheet, key in KEYMAP.items():
            data[key].to_excel(xw, sheet_name=sheet, index=False)
    return bio.getvalue()


def _norm(name: str) -> str:
    n = name.strip().lower().replace(" ", "_")
    return n[6:] if n.startswith("input_") else n


def from_excel(file) -> dict:
    xl = pd.ExcelFile(file)
    sheets = {_norm(s): s for s in xl.sheet_names}
    get = lambda k: xl.parse(sheets[k]) if k in sheets else None  # noqa: E731

    if "sources" not in sheets:  # ---- old single-source format
        nodes = get("nodes"); tiers = get("tiers"); demand = get("demand")
        sup = get("supply"); cor = get("corridors")
        if nodes is None or demand is None or sup is None or cor is None:
            raise ValueError("Workbook needs at least Nodes, Demand, Supply and Corridors sheets.")
        if "Sector" not in nodes.columns:
            nodes["Sector"] = nodes.get("Type", "Industries")
        if "Name" not in nodes.columns:
            nodes["Name"] = nodes["Node"]
        nodes = nodes[["Node", "Name", "Sector", "Tier"]]
        mcols = [c for c in demand.columns if c != "Node"]
        T = len(mcols)
        demand.columns = ["Node"] + MCOLS(T)
        avail = sup.iloc[:, -1].astype(float).tolist()[:T]
        sources, contract, supply, source_cost, prices, cap_factor = _single_source_frames(T, avail)
        if tiers is None:
            tiers = _three_tiers()
        if "NonCurtailable" not in tiers.columns:
            tiers["NonCurtailable"] = False
        scale = float(demand[MCOLS(T)].sum().mean())
        return normalize(dict(settings={"name": "Uploaded workbook (old format)", "unit": "SCM/month",
                              "scm_per_unit": 1.0, "opex": 0.0, "month_labels": [str(c) for c in mcols],
                              "default_objective": "cost", "note": "Uploaded by user."},
                    nodes=nodes, tiers=tiers, demand=demand, sources=sources, contract=contract,
                    supply=supply, source_cost=source_cost, prices=prices,
                    corridors=cor[["Corridor", "From", "To", "Cost", "Capacity"]],
                    cap_factor=cap_factor, mitigation=_mitigation_scaled(scale)))

    d = {}
    for sheet, key in KEYMAP.items():
        df = get(_norm(sheet))
        if df is None:
            raise ValueError(f"Sheet '{sheet}' is missing.")
        d[key] = df
    T = len([c for c in d["demand"].columns if c != "Node"])
    for key, idc in [("demand", "Node"), ("contract", "Source"), ("supply", "Source"),
                     ("source_cost", "Source"), ("prices", "Sector"), ("cap_factor", "Corridor")]:
        d[key].columns = [idc] + MCOLS(T)
    st = {"name": "Uploaded workbook", "unit": "units/month", "scm_per_unit": 1.0, "opex": 0.0,
          "month_labels": [f"M{t}" for t in range(1, T + 1)], "default_objective": "profit", "note": "Uploaded by user."}
    s = get("settings")
    if s is not None and len(s.columns) >= 2:
        kv = dict(zip(s.iloc[:, 0].astype(str), s.iloc[:, 1]))
        st["name"] = str(kv.get("name", st["name"]))
        st["unit"] = str(kv.get("unit", st["unit"]))
        st["scm_per_unit"] = float(kv.get("scm_per_unit", 1.0))
        st["opex"] = float(kv.get("opex", 0.0))
        labels = str(kv.get("month_labels", "")).split(",")
        if len(labels) == T:
            st["month_labels"] = [x.strip() for x in labels]
        st["default_objective"] = str(kv.get("default_objective", "profit")).strip().lower()
    d["settings"] = st
    d["tiers"]["NonCurtailable"] = d["tiers"]["NonCurtailable"].astype(bool)
    d["mitigation"]["Enabled"] = d["mitigation"]["Enabled"].astype(bool)
    if "PriorityTo" not in d["sources"].columns:
        d["sources"]["PriorityTo"] = ""
    d["sources"]["PriorityTo"] = d["sources"]["PriorityTo"].fillna("").astype(str)
    return normalize(d)
