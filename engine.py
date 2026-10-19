"""PuLP optimisation engine for CGD gas allocation under scarcity.

Formulation (extends the problem-statement LP; all months t = 1..T):

  Sets      t months, s gas sources (contracts), n demand nodes, (j,n) pipe arcs, k corridors
  Decision  x[j,n,t]  flow on arc                 y[n,t]  shortage (unmet demand)
            g[s,n,t]  gas of source s allotted to node n (contractual / eligibility accounting)
            v[n,t]    breach below service floor   u[s,t]  take-or-pay shortfall
            z, w      mitigation (capacity uplift, virtual pipeline), extra mitigation sources

  Cost mode (problem statement):  min Σ c·x + Σ p·y  (+ floor penalties, + mitigation cost)
  Profit mode (regulated):        max Σ price·(D−y) − Σ gascost·g − Σ c·x − ToP − mitigation
                                       − Σ p·y − floor penalties
  s.t.  source availability  Σ_n g[s,n,t] ≤ A[s,t]                (only eligible sectors)
        node balance         Σ_in x − Σ_out x + w + y = D
        gas accounting       Σ_s g[s,n,t] + y = D
        corridor capacity    Σ_(j,n)∈k x ≤ u_k·f_k,t + z_k,t
        service floor        y − v ≤ (1−α_n)·D                    (soft, heavy penalty)
        non-negativity
"""
from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import pulp as pl

BIG = 1e9


# --------------------------------------------------------------------------------------
# Parameters (sidebar levers)
# --------------------------------------------------------------------------------------
def default_params(objective="profit") -> dict:
    return dict(objective=objective, supply=1.0, demand=1.0, cap=1.0, cost=1.0, pen=1.0,
                svc_shift=0.0, svc_all=None, floor_pen=500.0, nc_pen=5000.0,
                price=1.0, gascost=1.0, opex=None, dem_node={}, cap_corr={}, src_mult={},
                mitigation=False, t_from=1, t_to=None,
                # diagnosis switches
                diag_supplier_full=False, diag_unlimited_gas=False, diag_unlimited_cap=False,
                physical=False)


def months_of(data):
    return [c for c in data["demand"].columns if c != "Node"]


# --------------------------------------------------------------------------------------
# Scenario library (5 real CGD scarcity situations)
# --------------------------------------------------------------------------------------
SCENARIOS = {
    "S1": dict(
        title="S1 · Base case – business as usual",
        side="Reference",
        problem="Normal operations on the reported 2-year MGL volume path. APM allocation is already "
                "lower after the Oct/Nov-2024 cuts; the balance comes from HP-HT, term RLNG and spot LNG. "
                "Strong CNG and I&C growth in FY26-27 pushes CNG and I&C corridors close to full.",
        real="MGL volumes grew ~7-9 % YoY in FY26 with APM + NWG at ~45 % of sales (Q3 FY26 call).",
        ops=[]),
    "S2": dict(
        title="S2 · APM allocation cut by MoPNG / GAIL (supplier-side)",
        side="Supplier",
        problem="The Government reduces domestic (APM) gas supplied to CGD for CNG(T) as domestic fields "
                "decline. MGL's contracted allocation is not delivered in full for ~9 months; domestic PNG "
                "must still be served 100 %.",
        real="16-Oct-2024 and 16-Nov-2024 APM cuts (~20 % for CNG) – MGL Reg-30 disclosure, CRISIL.",
        ops=[dict(kind="supply", match=["APM", "G"], factor=0.75, window=(0.17, 0.55)),
             dict(kind="supply", match=["NWG"], factor=0.60, window=(0.17, 0.55))]),
    "S3": dict(
        title="S3 · Global LNG disruption & price spike (supplier-side)",
        side="Supplier",
        problem="A geopolitical event (e.g. West-Asia crisis, shipping disruption) causes term LNG cargoes "
                "to be deferred and spot LNG to become scarce and expensive for 4 months.",
        real="2022 Europe crisis and the 2026 West-Asia crisis – MGL raised CNG prices citing spot RLNG cost.",
        ops=[dict(kind="supply", match=["RLNG_T", "G"], factor=0.60, window=(0.84, 1.0)),
             dict(kind="supply", match=["RLNG_S"], factor=0.45, window=(0.84, 1.0)),
             dict(kind="cost", match=["RLNG_T"], factor=1.25, window=(0.84, 1.0)),
             dict(kind="cost", match=["RLNG_S"], factor=1.70, window=(0.84, 1.0))]),
    "S4": dict(
        title="S4 · MGL network outage – CGS / steel pipeline (MGL-side)",
        side="MGL",
        problem="A third-party damage on the steel trunk line feeding PNG zones plus planned CGS / "
                "compressor maintenance reduces throughput of corridors 3, 4 and 1 for 2 months. Gas is "
                "available at the city gate but cannot reach customers.",
        real="Pipeline hits by Metro / road works are the most frequent cause of PNG outages in Mumbai.",
        ops=[dict(kind="cap", match=[3], factor=0.82, window=(0.42, 0.50)),
             dict(kind="cap", match=[4], factor=0.85, window=(0.42, 0.50)),
             dict(kind="cap", match=[1], factor=0.85, window=(0.46, 0.50))]),
    "S5": dict(
        title="S5 · Demand surge beyond contracted gas (MGL-side planning)",
        side="MGL",
        problem="CNG fleet conversion (taxis, buses, LCVs) and new industrial connections grow demand faster "
                "than MGL's gas contracts and network augmentation in the last 9 months. Suppliers deliver "
                "everything contracted – the gap is MGL's own procurement/network planning.",
        real="CNG volumes +10 % YoY in Q1 FY27; MGL relies increasingly on spot RLNG for CNG growth.",
        ops=[dict(kind="demand", match=["CNG Stations"], factor=1.10, window=(0.63, 1.0)),
             dict(kind="demand", match=["Industries", "Commercial"], factor=1.15, window=(0.63, 1.0)),
             dict(kind="supply", match=["RLNG_S"], factor=0.80, window=(0.63, 1.0))]),
}


def _window(T, w):
    a = max(1, int(math.floor(w[0] * T)) + 1)
    b = max(a, int(math.ceil(w[1] * T)))
    return list(range(a, min(T, b) + 1))


def apply_scenario(data: dict, key: str) -> dict:
    d = copy.deepcopy(data)
    if key not in SCENARIOS:
        return d
    for tbl in ["demand", "supply", "source_cost", "cap_factor"]:
        mc = [c for c in d[tbl].columns if str(c).startswith("M") and str(c)[1:].isdigit()]
        d[tbl][mc] = d[tbl][mc].astype(float)
    M = months_of(d)
    T = len(M)
    for op in SCENARIOS[key]["ops"]:
        cols = [f"M{t}" for t in _window(T, op["window"])]
        f = op["factor"]
        if op["kind"] in ("supply", "cost"):
            tbl = "supply" if op["kind"] == "supply" else "source_cost"
            ids = d[tbl]["Source"].astype(str).tolist()
            hit = [s for s in ids if s in op["match"]]
            if not hit and len(ids) == 1:          # single-source datasets
                hit = ids if any(m == "G" for m in op["match"]) else []
            mask = d[tbl]["Source"].astype(str).isin(hit)
            d[tbl].loc[mask, cols] = d[tbl].loc[mask, cols].astype(float) * f
        elif op["kind"] == "cap":
            mask = d["cap_factor"]["Corridor"].astype(int).isin(op["match"])
            d["cap_factor"].loc[mask, cols] = d["cap_factor"].loc[mask, cols].astype(float) * f
        elif op["kind"] == "demand":
            nodes = d["nodes"][d["nodes"]["Sector"].isin(op["match"])]["Node"].tolist()
            mask = d["demand"]["Node"].isin(nodes)
            d["demand"].loc[mask, cols] = d["demand"].loc[mask, cols].astype(float) * f
    return d


# --------------------------------------------------------------------------------------
# Instance preparation
# --------------------------------------------------------------------------------------
def _elig(eligible: str, sector: str) -> bool:
    e = str(eligible).strip()
    if e.lower() in ("all", "", "nan"):
        return True
    return sector in [x.strip() for x in e.split(";")]


def prepare(data: dict, p: dict) -> dict:
    M = months_of(data)
    T_all = len(M)
    t_to = p.get("t_to") or T_all
    T = [t for t in range(1, T_all + 1) if p.get("t_from", 1) <= t <= t_to]
    nodes = data["nodes"].copy()
    nodes["Node"] = nodes["Node"].astype(str)
    tiers = data["tiers"].set_index("Tier")
    N = nodes["Node"].tolist()
    sector = dict(zip(nodes.Node, nodes.Sector))
    tier = dict(zip(nodes.Node, nodes.Tier.astype(int)))

    dem = data["demand"].copy()
    dem["Node"] = dem["Node"].astype(str)
    dem = dem.set_index("Node")
    D = {(n, t): float(dem.loc[n, f"M{t}"]) * p["demand"] * p["dem_node"].get(n, 1.0) for n in N for t in T}

    # service floors & penalties
    alpha, pen, noncurt = {}, {}, {}
    for n in N:
        tr = tiers.loc[tier[n]]
        a = float(tr["MinService"])
        nc = bool(tr.get("NonCurtailable", False))
        if p.get("svc_all") is not None and not nc:
            a = float(p["svc_all"])
        a = min(1.0, max(0.0, a + p.get("svc_shift", 0.0) / 100.0)) if not nc else a
        alpha[n] = a
        pen[n] = float(tr["Penalty"]) * p["pen"]
        noncurt[n] = nc

    prices = data["prices"].set_index("Sector")
    price = {(n, t): (float(prices.loc[sector[n], f"M{t}"]) if sector[n] in prices.index else 0.0) * p["price"]
             for n in N for t in T}

    src = data["sources"].copy()
    src["Source"] = src["Source"].astype(str)
    S = src["Source"].tolist()
    con = data["contract"].assign(Source=data["contract"]["Source"].astype(str)).set_index("Source")
    sup = data["supply"].assign(Source=data["supply"]["Source"].astype(str)).set_index("Source")
    scost = data["source_cost"].assign(Source=data["source_cost"]["Source"].astype(str)).set_index("Source")
    A, C, GC, ToP, elig, prio_to = {}, {}, {}, {}, {}, {}
    for _, r in src.iterrows():
        s = r["Source"]
        mult = p["supply"] * p["src_mult"].get(s, 1.0)
        ToP[s] = float(r.get("TakeOrPay", 0.0) or 0.0)
        pt = str(r.get("PriorityTo", "") or "").strip()
        if pt and pt.lower() != "nan":
            prio_to[s] = pt
        for t in T:
            c = float(con.loc[s, f"M{t}"]) * mult
            a = float(sup.loc[s, f"M{t}"]) * mult
            if p.get("diag_supplier_full"):
                a = max(a, c)
            A[(s, t)] = a
            C[(s, t)] = c
            GC[(s, t)] = float(scost.loc[s, f"M{t}"]) * p["gascost"]
        for n in N:
            elig[(s, n)] = _elig(r.get("Eligible", "All"), sector[n])

    # mitigation sources
    mit = data["mitigation"].copy()
    mit_on = p.get("mitigation", False)
    mit_sup, mit_cap, mit_vir = [], [], []
    if mit_on:
        for i, r in mit.iterrows():
            if not bool(r["Enabled"]):
                continue
            typ = str(r["Type"]).strip().lower()
            if typ == "supply":
                sid = f"MIT{i}"
                S.append(sid)
                ToP[sid] = 0.0
                for t in T:
                    A[(sid, t)] = float(r["MaxPerMonth"]); C[(sid, t)] = 0.0
                    GC[(sid, t)] = float(r["Cost"]) * p["gascost"]
                for n in N:
                    elig[(sid, n)] = True
                mit_sup.append((sid, r["Option"]))
            elif typ == "capacity":
                tgt = str(r["Target"]).strip().lower()
                ks = None if tgt in ("all", "") else [int(float(x)) for x in tgt.split(";")]
                mit_cap.append((i, r["Option"], ks, float(r["MaxPerMonth"]), float(r["Cost"])))
            elif typ == "virtual":
                tg = [x.strip() for x in str(r["Target"]).split(";") if x.strip() in N]
                for n in tg:
                    mit_vir.append((i, r["Option"], n, float(r["MaxPerMonth"]), float(r["Cost"])))
    if p.get("diag_unlimited_gas"):
        S.append("UNC")
        ToP["UNC"] = 0.0
        for t in T:
            A[("UNC", t)] = BIG; C[("UNC", t)] = 0.0; GC[("UNC", t)] = 0.0
        for n in N:
            elig[("UNC", n)] = True

    cor = data["corridors"].copy()
    cor["Corridor"] = cor["Corridor"].astype(int)
    cor["From"] = cor["From"].astype(str); cor["To"] = cor["To"].astype(str)
    arcs = [(i, int(r.Corridor), r.From, r.To, float(r.Cost) * p["cost"]) for i, r in enumerate(cor.itertuples())]
    K = sorted(cor["Corridor"].unique().tolist())
    capf = data["cap_factor"].assign(Corridor=data["cap_factor"]["Corridor"].astype(int)).set_index("Corridor")
    base_cap = cor.groupby("Corridor")["Capacity"].first().astype(float).to_dict()
    U = {}
    for k in K:
        for t in T:
            f = float(capf.loc[k, f"M{t}"]) if k in capf.index else 1.0
            U[(k, t)] = BIG if p.get("diag_unlimited_cap") else base_cap[k] * p["cap"] * p["cap_corr"].get(k, 1.0) * f

    opex = p.get("opex")
    if opex is None:
        opex = float(data["settings"].get("opex", 0.0))
    return dict(T=T, N=N, S=S, K=K, arcs=arcs, D=D, opex=opex, prio_to=prio_to, alpha=alpha, pen=pen, noncurt=noncurt,
                price=price, A=A, C=C, GC=GC, ToP=ToP, elig=elig, U=U, base_cap=base_cap,
                sector=sector, tier=tier, mit_sup=mit_sup, mit_cap=mit_cap, mit_vir=mit_vir,
                labels=data["settings"]["month_labels"], src_names=dict(zip(src.Source, src.Name)),
                supplier=dict(zip(src.Source, src.Supplier)))


# --------------------------------------------------------------------------------------
# Solve
# --------------------------------------------------------------------------------------
def solve(data: dict, p: dict) -> dict:
    I = prepare(data, p)
    T, N, S, K, arcs = I["T"], I["N"], I["S"], I["K"], I["arcs"]
    mode = "physical" if p.get("physical") else p.get("objective", "profit")
    prob = pl.LpProblem("CGD_Gas_Allocation", pl.LpMinimize)

    x = {(a[0], t): pl.LpVariable(f"x_{a[0]}_{t}", lowBound=0) for a in arcs for t in T}
    y = {(n, t): pl.LpVariable(f"y_{n}_{t}", lowBound=0, upBound=I["D"][(n, t)]) for n in N for t in T}
    v = {(n, t): pl.LpVariable(f"v_{n}_{t}", lowBound=0) for n in N for t in T}
    g = {(s, n, t): pl.LpVariable(f"g_{s}_{n}_{t}", lowBound=0)
         for s in S for n in N for t in T if I["elig"][(s, n)]}
    u = {(s, t): pl.LpVariable(f"u_{s}_{t}", lowBound=0) for s in S for t in T if I["ToP"].get(s, 0) > 0}
    z = {}
    for (i, name, ks, frac, c) in I["mit_cap"]:
        for k in (ks or K):
            for t in T:
                z[(i, k, t)] = pl.LpVariable(f"z_{i}_{k}_{t}", lowBound=0,
                                             upBound=min(frac * I["U"][(k, t)], BIG))
    w = {}
    for (i, name, n, mx, c) in I["mit_vir"]:
        for t in T:
            w[(i, n, t)] = pl.LpVariable(f"w_{i}_{n}_{t}", lowBound=0, upBound=mx)

    # ---------------- objective
    transport = pl.lpSum(a[4] * x[(a[0], t)] for a in arcs for t in T)
    shortage_pen = pl.lpSum(I["pen"][n] * y[(n, t)] for n in N for t in T)
    floor_pen = pl.lpSum((p["nc_pen"] if I["noncurt"][n] else p["floor_pen"]) * v[(n, t)] for n in N for t in T)
    mit_cost = (pl.lpSum(c * z[(i, k, t)] for (i, name, ks, frac, c) in I["mit_cap"] for k in (ks or K) for t in T)
                + pl.lpSum(c * w[(i, n, t)] for (i, name, n, mx, c) in I["mit_vir"] for t in T))
    gas_cost = pl.lpSum(I["GC"][(s, t)] * g[(s, n, t)] for (s, n, t) in g)
    top_cost = pl.lpSum(I["GC"][(s, t)] * u[(s, t)] for (s, t) in u)
    lost_rev = pl.lpSum((I["price"][(n, t)] - I["opex"]) * y[(n, t)] for n in N for t in T)
    if mode == "physical":
        prio = {n: 10.0 ** (5 - min(I["tier"][n], 4)) for n in N}
        obj = pl.lpSum(prio[n] * y[(n, t)] for n in N for t in T) + 1e-3 * transport
    elif mode == "cost":
        obj = transport + shortage_pen + floor_pen + mit_cost + 1e-4 * gas_cost
    else:  # profit: min (lost revenue + costs + penalties)  ≡  max profit − penalties
        obj = lost_rev + gas_cost + top_cost + transport + mit_cost + shortage_pen + floor_pen
    prob += obj

    # ---------------- constraints
    for t in T:
        for s in S:
            prob += (pl.lpSum(g[(s, n, t)] for n in N if (s, n, t) in g) <= I["A"][(s, t)], f"sup_{s}_{t}")
            if (s, t) in u:
                prob += (u[(s, t)] + pl.lpSum(g[(s, n, t)] for n in N if (s, n, t) in g)
                         >= I["ToP"][s] * min(I["C"][(s, t)], I["A"][(s, t)]), f"top_{s}_{t}")
        for s, sec in I["prio_to"].items():   # regulatory allocation order (e.g. APM → domestic PNG first)
            dn = [n for n in N if I["sector"][n] == sec and (s, n, t) in g]
            if dn:
                need = min(I["A"][(s, t)], sum(I["D"][(n, t)] for n in dn))
                prob += (pl.lpSum(g[(s, n, t)] + y[(n, t)] for n in dn) >= need, f"prio_{s}_{t}")
        for k in K:
            extra = pl.lpSum(z[key] for key in z if key[1] == k and key[2] == t)
            prob += (pl.lpSum(x[(a[0], t)] for a in arcs if a[1] == k) - extra <= I["U"][(k, t)], f"cap_{k}_{t}")
        for n in N:
            inflow = pl.lpSum(x[(a[0], t)] for a in arcs if a[3] == n)
            outflow = pl.lpSum(x[(a[0], t)] for a in arcs if a[2] == n)
            virt = pl.lpSum(w[key] for key in w if key[1] == n and key[2] == t)
            prob += (inflow - outflow + virt + y[(n, t)] == I["D"][(n, t)], f"bal_{n}_{t}")
            prob += (pl.lpSum(g[(s, n, t)] for s in S if (s, n, t) in g) + y[(n, t)] == I["D"][(n, t)],
                     f"alloc_{n}_{t}")
            prob += (y[(n, t)] - v[(n, t)] <= (1 - I["alpha"][n]) * I["D"][(n, t)], f"floor_{n}_{t}")

    prob.solve(pl.PULP_CBC_CMD(msg=False))
    status = pl.LpStatus[prob.status]
    R = dict(status=status, mode=mode, I=I)
    if status != "Optimal":
        return R

    val = lambda e: float(pl.value(e) or 0.0)  # noqa: E731
    lab = lambda t: I["labels"][t - 1] if t - 1 < len(I["labels"]) else f"M{t}"  # noqa: E731

    # deliveries
    rows = []
    for t in T:
        for n in N:
            Dn = I["D"][(n, t)]
            yn = y[(n, t)].varValue or 0.0
            yn = 0.0 if abs(yn) < 1e-7 else yn
            rows.append(dict(Month=t, Label=lab(t), Node=n, Sector=I["sector"][n], Tier=I["tier"][n],
                             Demand=Dn, Delivered=Dn - yn, Shortage=yn, Required=I["alpha"][n] * Dn,
                             Floor_Violation=max(0.0, v[(n, t)].varValue or 0.0),
                             Fill_Rate=(Dn - yn) / Dn if Dn > 0 else 1.0,
                             Price=I["price"][(n, t)], Revenue=I["price"][(n, t)] * (Dn - yn)))
    deliv = pd.DataFrame(rows)

    flows = pd.DataFrame([dict(Month=t, Label=lab(t), Arc=a[0], Corridor=a[1], From=a[2], To=a[3],
                               Flow=x[(a[0], t)].varValue or 0.0, Cost=a[4],
                               Transport_Cost=a[4] * (x[(a[0], t)].varValue or 0.0))
                          for a in arcs for t in T])

    util = []
    for t in T:
        for k in K:
            fl = flows[(flows.Month == t) & (flows.Corridor == k)].Flow.sum()
            up = sum((z[key].varValue or 0.0) for key in z if key[1] == k and key[2] == t)
            cap = I["U"][(k, t)]
            util.append(dict(Month=t, Label=lab(t), Corridor=k, Flow=fl, Capacity=cap, Uplift=up,
                             Design_Capacity=I["base_cap"][k] * p["cap"] * p["cap_corr"].get(k, 1.0),
                             Utilization=fl / cap if 0 < cap < BIG / 10 else 0.0))
    util = pd.DataFrame(util)

    alloc = pd.DataFrame([dict(Month=t, Label=lab(t), Source=s, Node=n, Sector=I["sector"][n],
                               Volume=g[(s, n, t)].varValue or 0.0, Unit_Cost=I["GC"][(s, t)],
                               Cost=I["GC"][(s, t)] * (g[(s, n, t)].varValue or 0.0))
                          for (s, n, t) in g])
    alloc = alloc[alloc.Volume > 1e-9]

    srows = []
    for t in T:
        for s in S:
            used = sum((g[(s, n, t)].varValue or 0.0) for n in N if (s, n, t) in g)
            srows.append(dict(Month=t, Label=lab(t), Source=s, Contract=I["C"][(s, t)],
                              Available=min(I["A"][(s, t)], BIG), Used=used,
                              Shortfall_vs_Contract=max(0.0, I["C"][(s, t)] - I["A"][(s, t)]),
                              ToP_Unused=(u[(s, t)].varValue or 0.0) if (s, t) in u else 0.0,
                              Unit_Cost=I["GC"][(s, t)]))
    src_use = pd.DataFrame(srows)

    mrows = []
    for (sid, name) in I["mit_sup"]:
        for t in T:
            vol = src_use[(src_use.Source == sid) & (src_use.Month == t)].Used.sum()
            if vol > 1e-9:
                mrows.append(dict(Month=t, Label=lab(t), Option=name, Where="City gate", Volume=vol,
                                  Cost=vol * I["GC"][(sid, t)], Side="Supplier"))
    for (i, name, ks, frac, c) in I["mit_cap"]:
        for k in (ks or K):
            for t in T:
                vol = z[(i, k, t)].varValue or 0.0
                if vol > 1e-9:
                    mrows.append(dict(Month=t, Label=lab(t), Option=name, Where=f"Corridor {k}", Volume=vol,
                                      Cost=vol * c, Side="MGL"))
    for (i, name, n, mx, c) in I["mit_vir"]:
        for t in T:
            vol = w[(i, n, t)].varValue or 0.0
            if vol > 1e-9:
                mrows.append(dict(Month=t, Label=lab(t), Option=name, Where=f"Node {n}", Volume=vol,
                                  Cost=vol * c, Side="MGL"))
    mitig = pd.DataFrame(mrows, columns=["Month", "Label", "Option", "Where", "Volume", "Cost", "Side"])

    # shadow prices (PuLP/CBC: pi = dObj/dRHS for the minimisation)
    sh = []
    cons = prob.constraints
    for t in T:
        for s in S:
            if s == "UNC":
                continue
            c = cons[f"sup_{s}_{t}"]
            nm = I["src_names"].get(s, dict(I["mit_sup"]).get(s, s))
            sh.append(dict(Type="Source availability", Item=s, Name=nm, Month=t, Label=lab(t),
                           Shadow_Price=-(c.pi or 0.0), Slack=c.slack))
        for k in K:
            c = cons[f"cap_{k}_{t}"]
            sh.append(dict(Type="Corridor capacity", Item=f"Corridor {k}", Name=f"Corridor {k}", Month=t,
                           Label=lab(t), Shadow_Price=-(c.pi or 0.0), Slack=c.slack))
        for n in N:
            cb, ca, cf = cons[f"bal_{n}_{t}"], cons[f"alloc_{n}_{t}"], cons[f"floor_{n}_{t}"]
            sh.append(dict(Type="Node demand (marginal cost)", Item=n, Name=n, Month=t, Label=lab(t),
                           Shadow_Price=(cb.pi or 0) + (ca.pi or 0) + (1 - I["alpha"][n]) * (cf.pi or 0),
                           Slack=0.0))
            sh.append(dict(Type="Service-level floor", Item=n, Name=n, Month=t, Label=lab(t),
                           Shadow_Price=-(cf.pi or 0.0), Slack=cf.slack))
    shadow = pd.DataFrame(sh)
    shadow["Shadow_Price"] = shadow["Shadow_Price"].round(6) + 0.0
    shadow["Binding"] = shadow["Shadow_Price"].abs() > 1e-6

    # summary (money in ₹ per unit·₹/SCM; convert with scm_per_unit when displaying)
    revenue = float((deliv.Delivered * deliv.Price).sum())
    s_gas = val(gas_cost); s_top = val(top_cost); s_tr = val(transport); s_mit = val(mit_cost)
    s_pen = val(shortage_pen); s_fp = val(floor_pen)
    s_opex = I["opex"] * float(deliv.Delivered.sum())
    profit = revenue - s_gas - s_top - s_tr - s_mit - s_opex
    tot_d = float(deliv.Demand.sum()); tot_y = float(deliv.Shortage.sum())
    sector_fill = deliv.groupby("Sector").apply(lambda d: d.Delivered.sum() / d.Demand.sum() if d.Demand.sum() else 1.0)
    summary = dict(Status=status, Objective_mode=mode, Objective=val(obj), Revenue=revenue, Gas_Cost=s_gas,
                   TakeOrPay_Cost=s_top, Opex=s_opex, Transport_Cost=s_tr, Mitigation_Cost=s_mit, Shortage_Penalty=s_pen,
                   Floor_Penalty=s_fp, Total_Cost=s_tr + s_pen + s_fp + s_mit, Profit=profit,
                   Total_Demand=tot_d, Total_Shortage=tot_y, Fill_Rate=1 - tot_y / tot_d if tot_d else 1.0,
                   Floor_Violation=float(deliv.Floor_Violation.sum()),
                   **{f"Fill_{k}": float(v_) for k, v_ in sector_fill.items()})
    R.update(summary=summary, deliveries=deliv, flows=flows, util=util, alloc=alloc, sources=src_use,
             mitigation=mitig, shadow=shadow)
    return R


# --------------------------------------------------------------------------------------
# Economics helpers
# --------------------------------------------------------------------------------------
def sector_pnl(R) -> pd.DataFrame:
    """Revenue, gas cost (allocated), transport (allocated by node share) and margin by sector."""
    d = R["deliveries"]; a = R["alloc"]
    rev = d.groupby("Sector").Revenue.sum()
    vol = d.groupby("Sector").Delivered.sum()
    gas = a[~a.Source.eq("UNC")].groupby("Sector").Cost.sum() if len(a) else pd.Series(dtype=float)
    tr_total = R["summary"]["Transport_Cost"] + R["summary"]["Mitigation_Cost"]
    share = vol / vol.sum() if vol.sum() else vol
    out = pd.DataFrame({"Volume": vol, "Revenue": rev, "Gas_Cost": gas}).fillna(0.0)
    out["Network_Cost"] = share * tr_total
    out["Opex"] = out.Volume * R["I"]["opex"]
    out["Margin"] = out.Revenue - out.Gas_Cost - out.Network_Cost - out.Opex
    out["Margin_per_SCM"] = out.Margin / out.Volume.replace(0, np.nan)
    out["Avg_Price"] = out.Revenue / out.Volume.replace(0, np.nan)
    out["Avg_Gas_Cost"] = out.Gas_Cost / out.Volume.replace(0, np.nan)
    return out.reset_index()


def monthly_pnl(R) -> pd.DataFrame:
    d = R["deliveries"].groupby(["Month", "Label"]).agg(Demand=("Demand", "sum"), Delivered=("Delivered", "sum"),
                                                        Shortage=("Shortage", "sum"), Revenue=("Revenue", "sum")).reset_index()
    gas = R["alloc"].groupby("Month").Cost.sum()
    tr = R["flows"].groupby("Month").Transport_Cost.sum()
    mit = R["mitigation"].groupby("Month").Cost.sum() if len(R["mitigation"]) else pd.Series(dtype=float)
    top = (R["sources"].ToP_Unused * R["sources"].Unit_Cost).groupby(R["sources"].Month).sum()
    d["Gas_Cost"] = d.Month.map(gas).fillna(0); d["Transport"] = d.Month.map(tr).fillna(0)
    d["Mitigation"] = d.Month.map(mit).fillna(0); d["TakeOrPay"] = d.Month.map(top).fillna(0)
    d["Opex"] = d.Delivered * R["I"]["opex"]
    d["Profit"] = d.Revenue - d.Gas_Cost - d.Transport - d.Mitigation - d.TakeOrPay - d.Opex
    return d


def headline(R, p):
    """The objective-specific KPI: total cost (cost mode) or profit (profit mode)."""
    s = R["summary"]
    return s["Total_Cost"] if p.get("objective") == "cost" else s["Profit"]


# --------------------------------------------------------------------------------------
# Scarcity diagnosis: supplier (GAIL etc.) vs MGL (procurement / network)
# --------------------------------------------------------------------------------------
def diagnose(data: dict, p: dict) -> dict:
    """Attribute physical shortage to the supplier (e.g. GAIL) or to MGL (procurement / network).

    Step 1 – Shapley split between GAS (unlimited gas at city gate) and NETWORK (unlimited corridors).
    Step 2 – the GAS share is split into SUPPLIER (contracted gas not delivered) and
             MGL PROCUREMENT (gas never contracted), by restoring the contract first.
    All runs use 'physical' mode (maximise service by priority, no mitigation).
    """
    base = dict(p, physical=True, mitigation=False)

    def short(**kw):
        r = solve(data, dict(base, **kw))
        if r["status"] != "Optimal":
            raise RuntimeError("Diagnosis solve failed: " + r["status"])
        return r, r["deliveries"].groupby("Month").Shortage.sum()

    base_run, s00 = short()
    _, s10 = short(diag_unlimited_gas=True)
    _, s01 = short(diag_unlimited_cap=True)
    _, s11 = short(diag_unlimited_gas=True, diag_unlimited_cap=True)
    _, sS0 = short(diag_supplier_full=True)
    gas = 0.5 * ((s00 - s10) + (s01 - s11))
    net = 0.5 * ((s00 - s01) + (s10 - s11))
    sup_raw = (s00 - sS0).clip(lower=0)
    proc_raw = (sS0 - s10).clip(lower=0)
    den = (sup_raw + proc_raw).replace(0, np.nan)
    sup = (gas * sup_raw / den).fillna(0.0)
    proc = (gas - sup).clip(lower=0)
    tab = pd.DataFrame({"Supplier": sup.clip(lower=0), "MGL procurement": proc, "MGL network": net.clip(lower=0)})
    tab["Total_shortage"] = s00
    tab["Residual"] = s11
    tab["Label"] = [base_run["I"]["labels"][t - 1] for t in tab.index]
    tot = tab[["Supplier", "MGL procurement", "MGL network"]].sum()
    total = float(tot.sum())
    share = (tot / total) if total > 1e-9 else tot * 0
    sup_share = float(share["Supplier"]); mgl_share = float(share["MGL procurement"] + share["MGL network"])
    if total <= 1e-6:
        verdict = "none"
    elif sup_share >= 0.6:
        verdict = "supplier"
    elif mgl_share >= 0.6:
        verdict = "mgl"
    else:
        verdict = "both"

    # which suppliers fell short, which corridors bind
    srcs = base_run["sources"]
    short_by_src = (srcs.groupby("Source").Shortfall_vs_Contract.sum()
                    .rename(index=lambda s: f"{s} – {base_run['I']['supplier'].get(s, '')}"))
    short_by_src = short_by_src[short_by_src > 1e-9]
    sh = base_run["shadow"]
    corr = (sh[sh.Type == "Corridor capacity"].groupby("Item").agg(Months_binding=("Binding", "sum"))
            .join(base_run["util"].assign(Item=lambda d: "Corridor " + d.Corridor.astype(str))
                  .groupby("Item").Utilization.max().rename("Peak_util")))
    dem_tot = base_run["deliveries"].groupby("Month").Demand.sum()
    con_tot = srcs.groupby("Month").Contract.sum()
    proc_gap = (dem_tot - con_tot).clip(lower=0)
    return dict(table=tab, totals=tot, total=total, supplier_share=sup_share, mgl_share=mgl_share,
                verdict=verdict, short_by_src=short_by_src, corridors=corr, proc_gap=proc_gap,
                base_physical=base_run)


def response_plan(data: dict, p: dict, diag: dict | None = None) -> dict:
    """Optimised response, always in regulated profit mode.

    before         – no mitigation levers (what happens if we do nothing new)
    profit_first   – levers allowed, shortage penalties above the floors switched off: only actions
                     that add profit are taken, regulatory floors (domestic 100 %, CNG 90-95 %) still hold
    service_first  – levers allowed with the shortage penalties as set (customer-service priority)
    supplier_full  – counterfactual: supplier delivers the full contract (value of the shortfall)
    """
    q = dict(p, objective="profit", physical=False)
    before = solve(data, dict(q, mitigation=False))
    profit_first = solve(data, dict(q, mitigation=True, pen=0.0))
    service_first = solve(data, dict(q, mitigation=True))
    cf = solve(data, dict(q, mitigation=False, diag_supplier_full=True))
    return dict(before=before, profit_first=profit_first, service_first=service_first, supplier_full=cf)


PLAYBOOK = {
    "supplier": [
        ("Notify & claim", "Issue a supply-shortfall notice to the supplier (GAIL / LNG seller) and invoke the "
         "shortfall / 'supply-or-pay' clause of the Gas Sale Agreement for compensation.", "GSA terms"),
        ("Seek restoration of priority gas", "Represent to MoPNG / PPAC / GAIL for restoration of APM / NWG "
         "allocation to CNG(T) and PNG(D), which are priority sectors under the domestic-gas allocation policy.",
         "MoPNG CNG(T)/PNG(D) priority guidelines"),
        ("Protect domestic PNG first", "Re-assign the remaining cheap APM/NWG gas to domestic PNG (100 %) and "
         "then CNG(T); never curtail households.", "MoPNG guidelines; PNGRB QoS regulations"),
        ("Replace volumes at least cost", "Buy replacement gas in merit order: HP-HT / IGX → term RLNG → spot "
         "cargo → swap with neighbouring CGD, only up to the volume where margin stays positive.", "Optimiser output"),
        ("Curtail interruptible load", "Curtail industrial and then commercial PNG within their contractual "
         "interruptible clauses, with advance notice to customers.", "Customer contracts; PNGRB QoS"),
        ("Protect margin", "Pass through the higher weighted gas cost: revise CNG and I&C prices (market-determined); "
         "consider domestic PNG revision as allowed. Track EBITDA/SCM so no segment runs at a loss.", "Pricing policy"),
        ("Report", "Keep PNGRB and customers informed; record the event under the ERDMP / incident reporting system.",
         "PNGRB ERDMP regulations"),
    ],
    "mgl": [
        ("Declare internal constraint", "The shortage is created inside MGL (network capacity and/or "
         "under-contracting). Escalate to Operations, Gas Sourcing and Projects.", "Internal"),
        ("Re-route & line-pack", "Use line-pack and raise operating pressure within MAOP on the bottleneck "
         "corridor; re-route through parallel feeders; reschedule maintenance to low-demand months.",
         "PNGRB T4S & IMS regulations (MAOP, integrity)"),
        ("Virtual pipeline", "Supply CNG stations by mobile cascades (mother–daughter) and inject LCNG into "
         "PNG DRS for isolated areas until the line is restored.", "T4S (CNG cascade / LCNG)"),
        ("Fix procurement", "Nominate higher DCQ, sign term / mid-term contracts, buy on IGX ahead of the peak "
         "and keep a spot window open.", "Gas sourcing policy"),
        ("Invest where the shadow price is high", "Augment the corridor with the highest shadow price × binding "
         "months first (looping / new CGS / compressor).", "PNGRB capacity determination regulations"),
        ("Protect households", "Even for internal problems, domestic PNG is served first; curtail industrial, "
         "then commercial, then CNG down to its 90-95 % floor.", "MoPNG / PNGRB priority"),
        ("Report", "Log the outage, root cause and restoration under ERDMP & IMS; inform PNGRB if service "
         "standards are breached.", "PNGRB ERDMP & QoS regulations"),
    ],
}


# --------------------------------------------------------------------------------------
# Sensitivity helpers
# --------------------------------------------------------------------------------------
def shadow_impact(data, p, base, pct=0.10):
    rows = []
    sh = base["shadow"]
    base_obj = base["summary"]["Objective"]
    items = [("Source availability", s) for s in base["I"]["S"] if s in data["sources"]["Source"].astype(str).tolist()]
    items += [("Corridor capacity", f"Corridor {k}") for k in base["I"]["K"]]
    for typ, item in items:
        sp = sh[(sh.Type == typ) & (sh.Item == item)]
        if typ == "Source availability":
            extra = {t: base["I"]["A"][(item, t)] * pct for t in base["I"]["T"]}
            q = dict(p, src_mult={**p.get("src_mult", {}), item: p.get("src_mult", {}).get(item, 1.0) * (1 + pct)})
            label = f"{item} supply"
        else:
            k = int(item.split()[-1])
            extra = {t: base["I"]["U"][(k, t)] * pct for t in base["I"]["T"]}
            q = dict(p, cap_corr={**p.get("cap_corr", {}), k: p.get("cap_corr", {}).get(k, 1.0) * (1 + pct)})
            label = item
            ut = base["util"][base["util"].Corridor == k]
        est = float(sum(r.Shadow_Price * extra[r.Month] for r in sp.itertuples()))
        r2 = solve(data, q)
        act = base_obj - r2["summary"]["Objective"] if r2["status"] == "Optimal" else np.nan
        rows.append({"Constraint": label, "Avg shadow (₹/SCM)": sp.Shadow_Price.mean(),
                     "Max shadow (₹/SCM)": sp.Shadow_Price.max(), "Months binding": int(sp.Binding.sum()),
                     "Avg util": ut.Utilization.mean() if typ != "Source availability" else np.nan,
                     "Peak util": ut.Utilization.max() if typ != "Source availability" else np.nan,
                     "Extra per month": float(np.mean(list(extra.values()))),
                     "Est. objective gain (linear)": est, "Actual objective gain (re-solve)": act,
                     "Change in profit": (r2["summary"]["Profit"] - base["summary"]["Profit"]) if r2["status"] == "Optimal" else np.nan,
                     "Change in total cost": (r2["summary"]["Total_Cost"] - base["summary"]["Total_Cost"]) if r2["status"] == "Optimal" else np.nan,
                     "Change in shortage": (r2["summary"]["Total_Shortage"] - base["summary"]["Total_Shortage"]) if r2["status"] == "Optimal" else np.nan})
    return pd.DataFrame(rows)


def demand_impact(data, p, base, pct=0.10):
    rows = []
    d0 = base["deliveries"]
    for n in base["I"]["N"]:
        q = dict(p, dem_node={**p.get("dem_node", {}), n: p.get("dem_node", {}).get(n, 1.0) * (1 + pct)})
        r = solve(data, q)
        if r["status"] != "Optimal":
            continue
        extra = d0[d0.Node == n].Demand.sum() * pct
        s0, s1 = base["summary"], r["summary"]
        real0 = s0["Gas_Cost"] + s0["Transport_Cost"] + s0["Mitigation_Cost"] + s0["TakeOrPay_Cost"]
        real1 = s1["Gas_Cost"] + s1["Transport_Cost"] + s1["Mitigation_Cost"] + s1["TakeOrPay_Cost"]
        rows.append({"Node": n, "Sector": base["I"]["sector"][n],
                     "Base demand / month": d0[d0.Node == n].Demand.mean(), "Extra / month": extra / len(base["I"]["T"]),
                     "Change in objective": s1["Objective"] - s0["Objective"],
                     "Change in real cost (gas+network)": real1 - real0,
                     "Change in profit": s1["Profit"] - s0["Profit"],
                     "Change in shortage": s1["Total_Shortage"] - s0["Total_Shortage"],
                     "Extra served (share)": 1 - (s1["Total_Shortage"] - s0["Total_Shortage"]) / extra if extra else np.nan,
                     "Marginal profit ₹/extra SCM": (s1["Profit"] - s0["Profit"]) / extra if extra else np.nan})
    return pd.DataFrame(rows)


def service_sweep(data, p, levels=(0.70, 0.75, 0.80, 0.85, 0.90, 0.95)):
    rows, prev = [], None
    for a in levels:
        r = solve(data, dict(p, svc_all=a))
        if r["status"] != "Optimal":
            rows.append({"Service floor": a, "Feasible": "No"}); continue
        s = r["summary"]; d = r["deliveries"]
        row = {"Service floor": a, "Objective": s["Objective"], "Total cost": s["Total_Cost"], "Profit": s["Profit"],
               "Transport": s["Transport_Cost"], "Gas cost": s["Gas_Cost"], "Shortage penalty": s["Shortage_Penalty"],
               "Shortage": s["Total_Shortage"], "Fill rate": s["Fill_Rate"], "Floor breach": s["Floor_Violation"],
               "Feasible": "Yes" if s["Floor_Violation"] < 1e-6 else "Only with breach",
               "Objective vs previous": (s["Objective"] - prev) if prev is not None else 0.0}
        for sec, g_ in d.groupby("Sector"):
            row[f"Fill {sec}"] = g_.Delivered.sum() / g_.Demand.sum()
        rows.append(row); prev = s["Objective"]
    return pd.DataFrame(rows)


TORNADO_PARAMS = {
    "Gas supply": ("supply", None), "Demand": ("demand", None), "All corridor capacity": ("cap", None),
    "Transport cost": ("cost", None), "Shortage penalty": ("pen", None), "Selling price": ("price", None),
    "Gas purchase cost": ("gascost", None),
    "Corridor 1 capacity": ("cap_corr", 1), "Corridor 2 capacity": ("cap_corr", 2),
    "Corridor 3 capacity": ("cap_corr", 3), "Corridor 4 capacity": ("cap_corr", 4),
    "Corridor 5 capacity": ("cap_corr", 5),
}


def with_param(p, name, mult):
    key, sub = TORNADO_PARAMS[name]
    q = dict(p)
    if sub is None:
        q[key] = p.get(key, 1.0) * mult
    else:
        q[key] = {**p.get(key, {}), sub: p.get(key, {}).get(sub, 1.0) * mult}
    return q


def tornado(data, p, pct):
    base = solve(data, p)
    b = headline(base, p)
    rows = []
    for name in TORNADO_PARAMS:
        lo = solve(data, with_param(p, name, 1 - pct)); hi = solve(data, with_param(p, name, 1 + pct))
        if lo["status"] != "Optimal" or hi["status"] != "Optimal":
            continue
        rows.append({"Parameter": name, "Low (−)": headline(lo, p) - b, "High (+)": headline(hi, p) - b,
                     "Swing": abs(headline(hi, p) - headline(lo, p))})
    return b, pd.DataFrame(rows).sort_values("Swing")


def sweep(data, p, name, lo, hi, steps=9):
    rows = []
    for m in np.linspace(lo, hi, steps):
        r = solve(data, with_param(p, name, m))
        if r["status"] != "Optimal":
            continue
        s = r["summary"]
        rows.append({"Multiplier": m, "Headline": headline(r, p), "Profit": s["Profit"], "Total cost": s["Total_Cost"],
                     "Shortage": s["Total_Shortage"], "Fill rate": s["Fill_Rate"]})
    return pd.DataFrame(rows)


def heatmap(data, p, grid=(0.8, 0.9, 1.0, 1.1, 1.2)):
    Z = np.full((len(grid), len(grid)), np.nan)
    F = np.full((len(grid), len(grid)), np.nan)
    for i, dm in enumerate(grid):
        for j, sm in enumerate(grid):
            r = solve(data, dict(p, demand=p["demand"] * dm, supply=p["supply"] * sm))
            if r["status"] == "Optimal":
                Z[i, j] = headline(r, p); F[i, j] = r["summary"]["Fill_Rate"]
    return Z, F


def compare_scenarios(data, p):
    rows = []
    for key, sc in SCENARIOS.items():
        d = apply_scenario(data, key)
        r = solve(d, p)
        if r["status"] != "Optimal":
            rows.append({"Scenario": sc["title"], "Status": r["status"]}); continue
        s = r["summary"]
        rows.append({"Key": key, "Scenario": sc["title"], "Expected side": sc["side"], "Status": s["Status"],
                     "Profit": s["Profit"], "Total cost": s["Total_Cost"], "Revenue": s["Revenue"],
                     "Gas cost": s["Gas_Cost"], "Shortage": s["Total_Shortage"], "Fill rate": s["Fill_Rate"],
                     **{k: v for k, v in s.items() if k.startswith("Fill_") and k != "Fill_Rate"}})
    return pd.DataFrame(rows)


def compliance(R) -> pd.DataFrame:
    """Regulatory compliance check of an allocation result."""
    d = R["deliveries"]
    rows = []
    for sec, g_ in d.groupby("Sector"):
        fill = g_.Delivered.sum() / g_.Demand.sum()
        worst = g_.Fill_Rate.min()
        req = g_.Required.sum() / g_.Demand.sum()
        months_below = int((g_.groupby("Month").apply(lambda x: x.Delivered.sum() / x.Demand.sum()) < req - 1e-6).sum())
        rows.append({"Sector": sec, "Floor": req, "Fill (period)": fill, "Worst node-month": worst,
                     "Months below floor": months_below,
                     "Status": "✅ Compliant" if months_below == 0 else "❌ Breach"})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------
# Route status (for the control-tower network diagram)
# --------------------------------------------------------------------------------------
def route_status(R, month="avg") -> pd.DataFrame:
    """Per arc: flow, corridor utilisation, shadow price and status (Optimal / Bottleneck / Spare)."""
    fl, ut, sh = R["flows"], R["util"], R["shadow"]
    cs = sh[sh.Type == "Corridor capacity"].copy()
    cs["Corridor"] = cs.Item.str.split().str[-1].astype(int)
    if month == "avg":
        f = fl.groupby(["Arc", "Corridor", "From", "To", "Cost"], as_index=False).Flow.mean()
        u = ut.groupby("Corridor").agg(Utilization=("Utilization", "mean"), Peak=("Utilization", "max"),
                                       Capacity=("Capacity", "mean"), CFlow=("Flow", "mean"))
        s = cs.groupby("Corridor").agg(Shadow=("Shadow_Price", "mean"), Binding=("Binding", "sum"))
    else:
        f = fl[fl.Month == month][["Arc", "Corridor", "From", "To", "Cost", "Flow"]]
        u = ut[ut.Month == month].set_index("Corridor")[["Utilization", "Capacity", "Flow"]].rename(columns={"Flow": "CFlow"})
        u["Peak"] = u["Utilization"]
        s = cs[cs.Month == month].set_index("Corridor")[["Shadow_Price", "Binding"]].rename(columns={"Shadow_Price": "Shadow"})
        s["Binding"] = s["Binding"].astype(int)
    f = f.merge(u, left_on="Corridor", right_index=True, how="left").merge(s, left_on="Corridor", right_index=True, how="left")
    tot = f.groupby("Corridor").Flow.transform("max").replace(0, np.nan)

    def status(r):
        if r.Flow <= 1e-9:
            return "Spare"
        if (r.Shadow or 0) > 1e-6 and (r.Peak or 0) >= 0.995:
            return "Bottleneck"
        return "Optimal"
    f["Status"] = f.apply(status, axis=1)
    f["Share_of_corridor"] = (f.Flow / tot).fillna(0)
    return f


# --------------------------------------------------------------------------------------
# 2-year demand–supply outlook
# --------------------------------------------------------------------------------------
def outlook(data: dict, g1=0.08, g2=0.112, apm_decline=0.05, horizon=24) -> dict:
    """Project the last 12 months of demand by sector and contracted supply by source forward."""
    M = months_of(data)
    T = len(M)
    last = M[-12:] if T >= 12 else M
    sec = dict(zip(data["nodes"].Node.astype(str), data["nodes"].Sector))
    dem = data["demand"].assign(Sector=data["demand"].Node.astype(str).map(sec)).groupby("Sector")[last].sum()
    con = data["contract"].assign(Source=data["contract"].Source.astype(str)).set_index("Source")[last]
    lab0 = data["settings"]["month_labels"]
    import datetime as _dt
    try:
        d0 = _dt.datetime.strptime(lab0[-1], "%b-%y")
        labels = []
        y, m = d0.year, d0.month
        for _ in range(horizon):
            m += 1
            if m > 12:
                m, y = 1, y + 1
            labels.append(_dt.date(y, m, 1).strftime("%b-%y"))
    except Exception:  # noqa: BLE001
        labels = [f"F{i + 1}" for i in range(horizon)]
    drows, srows = [], []
    for i in range(horizon):
        base_col = last[i % len(last)]
        yr = i // 12
        gf = (1 + g1) if yr == 0 else (1 + g1) * (1 + g2)
        for sct, v in dem[base_col].items():
            drows.append({"i": i, "Label": labels[i], "Sector": sct, "Demand": float(v) * gf})
        for s, v in con[base_col].items():
            f = (1 - apm_decline) ** (yr + 1) if s.upper().startswith(("APM", "NWG")) else 1.0
            if s.upper().startswith(("RLNG_S", "SPOT")):
                continue      # spot is not contracted supply
            srows.append({"i": i, "Label": labels[i], "Source": s, "Supply": float(v) * f})
    D = pd.DataFrame(drows); Sdf = pd.DataFrame(srows)
    tot = D.groupby(["i", "Label"], as_index=False).Demand.sum().merge(
        Sdf.groupby(["i", "Label"], as_index=False).Supply.sum(), on=["i", "Label"], how="left").fillna(0)
    tot["Gap"] = (tot.Demand - tot.Supply).clip(lower=0)
    return dict(demand=D, supply=Sdf, total=tot)


# --------------------------------------------------------------------------------------
# Multi-case comparison
# --------------------------------------------------------------------------------------
def case_summary(data: dict, p: dict, key: str, optimise=True) -> dict:
    d = apply_scenario(data, key)
    base = solve(d, dict(p, mitigation=False))
    out = {"key": key, "base": base, "opt": None, "diag": None, "rec": None}
    if base["status"] != "Optimal":
        return out
    if optimise:
        rp = response_plan(d, p)
        pf, sf = rp["profit_first"], rp["service_first"]
        ok = lambda r: r["status"] == "Optimal" and (compliance(r)["Status"] == "✅ Compliant").all()  # noqa: E731
        out["opt"], out["rec"] = (pf, "Profit-first") if ok(pf) else ((sf, "Service-first") if ok(sf) else (pf, "Profit-first"))
    try:
        out["diag"] = diagnose(d, p)
    except Exception:  # noqa: BLE001
        out["diag"] = None
    return out
