"""CGD Gas Allocation under Scarcity – LP website & simulator (Streamlit + PuLP).

Run locally:   streamlit run app.py
"""
from __future__ import annotations

import io
import os

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import content as C
import data as D
import engine as E

st.set_page_config(page_title="GAS-OPTIC – Gas Allocation Control Tower", page_icon="⛽", layout="wide")

SECTOR_COLORS = {"PNG Households": "#F28E2B", "CNG Stations": "#4E79A7", "Commercial": "#B07AA1",
                 "Industries": "#59A14F"}
SIDE_COLORS = {"Supplier": "#E15759", "MGL procurement": "#F1CE63", "MGL network": "#4E79A7"}
PAGES = ["🏠 Home", "🧮 Model & formulation", "⚙️ Simulator", "🧪 Scenarios (5)", "🆚 Compare scenarios",
         "🔎 Scarcity diagnosis & response", "🏛 Priority & regulations", "🚀 Future expansion & outlook",
         "📖 Terminology", "📚 References"]
GREEN = "background-color: rgba(46,204,113,0.32)"
RED = "background-color: rgba(231,76,60,0.28)"
SL_OPTS = ["Tier-wise (policy default)", "70%", "75%", "80%", "85%", "90%", "92.5%", "95%", "97.5%", "100%"]
HERE = os.path.dirname(os.path.abspath(__file__))


# ======================================================================================
# Cached wrappers
# ======================================================================================
@st.cache_data(show_spinner=False)
def load_builtin(name):
    return D.BUILTIN[name]()


@st.cache_data(show_spinner=False)
def load_upload(content: bytes):
    return D.from_excel(io.BytesIO(content))


@st.cache_data(show_spinner=False)
def c_solve(data, params):
    return E.solve(data, params)


@st.cache_data(show_spinner=False)
def c_diag(data, params):
    return E.diagnose(data, params)


@st.cache_data(show_spinner=False)
def c_response(data, params):
    return E.response_plan(data, params)


@st.cache_data(show_spinner=False)
def c_shadow_impact(data, params, pct):
    return E.shadow_impact(data, params, E.solve(data, params), pct)


@st.cache_data(show_spinner=False)
def c_demand_impact(data, params, pct):
    return E.demand_impact(data, params, E.solve(data, params), pct)


@st.cache_data(show_spinner=False)
def c_service(data, params):
    return E.service_sweep(data, params)


@st.cache_data(show_spinner=False)
def c_compare(data, params):
    return E.compare_scenarios(data, params)


@st.cache_data(show_spinner=False)
def c_compare_diag(data, params):
    rows = []
    for key, sc in E.SCENARIOS.items():
        dg = E.diagnose(E.apply_scenario(data, key), params)
        t = dg["totals"]
        rows.append({"Key": key, "Scenario": sc["title"], "Diagnosed": dg["verdict"],
                     "Physical shortage": dg["total"], "Supplier": t["Supplier"],
                     "MGL procurement": t["MGL procurement"], "MGL network": t["MGL network"],
                     "Supplier share": dg["supplier_share"]})
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def c_case(data, params, key, optimise):
    return E.case_summary(data, params, key, optimise)


@st.cache_data(show_spinner=False)
def c_outlook(data, g1, g2, apm):
    return E.outlook(data, g1, g2, apm)


@st.cache_data(show_spinner=False)
def c_tornado(data, params, pct):
    return E.tornado(data, params, pct)


@st.cache_data(show_spinner=False)
def c_sweep(data, params, name, lo, hi):
    return E.sweep(data, params, name, lo, hi, 11)


@st.cache_data(show_spinner=False)
def c_heat(data, params):
    return E.heatmap(data, params)


# ======================================================================================
# Formatting helpers
# ======================================================================================
def money(v, scm_per_unit):
    """v is in (₹/SCM × volume unit). Show ₹ crore / lakh / ₹."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "–"
    r = v * scm_per_unit
    a = abs(r)
    if a >= 1e7:
        return f"₹{r / 1e7:,.1f} Cr"
    if a >= 1e5:
        return f"₹{r / 1e5:,.2f} L"
    return f"₹{r:,.0f}"


def money_unit(scm_per_unit):
    return ("₹ Cr", 1e7) if scm_per_unit >= 1e5 else ("₹", 1.0)


def to_money(series, scm_per_unit):
    lab, div = money_unit(scm_per_unit)
    return series * scm_per_unit / div


def pct(x):
    return "–" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.1%}"


def show(df, **kw):
    st.dataframe(df, width="stretch", hide_index=True, **kw)


def chart(fig, h=380):
    fig.update_layout(height=h, margin=dict(l=10, r=10, t=40, b=10), legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig, width="stretch")


def rec(msg):
    """One-line recommendation box (green)."""
    st.markdown("<div style='border-left:6px solid #2ECC71;background:rgba(46,204,113,0.12);padding:8px 12px;"
                f"border-radius:6px;margin:6px 0 14px 0'>💡 <b>Recommendation:</b> {msg}</div>", unsafe_allow_html=True)


def paint(styler, good=(), bad=()):
    """Highlight whole rows: index labels in `good` green (recommended), in `bad` red."""
    good, bad = set(good), set(bad)
    return styler.apply(lambda r: [GREEN if r.name in good else (RED if r.name in bad else "")] * len(r), axis=1)


def credits_html(compact=False):
    c = C.CREDITS
    if compact:
        return (f"<div style='font-size:0.8em;opacity:0.8'>FDP: {c['FDP Course']}<br>{c['Organiser']}<br>"
                f"{' · '.join(a.split(',')[0] for a in c['Authors'])}<br>Mentor: {c['Supervisor cum Mentor']}</div>")
    authors = "".join(f"<li>{a}</li>" for a in c["Authors"])
    return ("<div style='border:1px solid rgba(127,127,127,0.35);border-radius:10px;padding:12px 18px;margin:4px 0 18px 0;"
            "background:rgba(127,127,127,0.07)'>"
            f"<b>FDP Course:</b> {c['FDP Course']}<br><b>Organiser:</b> {c['Organiser']}<br>"
            f"<b>Authors:</b><ul style='margin:2px 0 4px 0'>{authors}</ul>"
            f"<b>Supervisor cum Mentor:</b> {c['Supervisor cum Mentor']}</div>")


# ======================================================================================
# Sidebar – navigation, data, scenario and levers (same structure as the earlier dashboard)
# ======================================================================================
st.sidebar.markdown("## ⛽ GAS-OPTIC")
st.sidebar.caption("Gas Allocation and Supply Optimization through Intelligent Control Tower")
page = st.sidebar.radio("Go to", PAGES, label_visibility="collapsed")

st.sidebar.markdown("### 1 · Data")
src_choice = st.sidebar.radio("Source", list(D.BUILTIN.keys()) + ["Upload Excel"], index=0)
base_data, ds_name = None, src_choice
if src_choice == "Upload Excel":
    up = st.sidebar.file_uploader("Workbook (.xlsx)", type=["xlsx"])
    if up is not None:
        try:
            base_data = load_upload(up.getvalue())
            ds_name = f"upload:{up.name}:{len(up.getvalue())}"
        except Exception as ex:  # noqa: BLE001
            st.sidebar.error(f"Could not read workbook: {ex}")
    if base_data is None:
        st.sidebar.info("Upload a workbook (use the template below). Showing MGL data meanwhile.")
        base_data, ds_name = load_builtin("MGL 24-month data (2024-26)"), "MGL 24-month data (2024-26)"
else:
    base_data = load_builtin(src_choice)

st.sidebar.download_button("⬇ Download sample-data template (.xlsx)", D.to_excel_bytes(load_builtin("MGL 24-month data (2024-26)")),
                           file_name="cgd_sample_data_template.xlsx", width="stretch")

# user edits from the Inputs tab (kept per dataset)
edits = st.session_state.setdefault("edits", {})
work = {k: (v.copy() if isinstance(v, pd.DataFrame) else dict(v)) for k, v in base_data.items()}
for k, v in edits.get(ds_name, {}).items():
    work[k] = v.copy()
S_ = work["settings"]
UNIT, SPU = S_["unit"], float(S_["scm_per_unit"])
UNIT_SHORT = UNIT.split("/")[0]
T_ALL = len(E.months_of(work))
LABELS = S_["month_labels"]

st.sidebar.markdown("### 2 · Scarcity scenario")
scen_opts = ["S1", "S2", "S3", "S4", "S5"]
scen = st.sidebar.selectbox("Scenario", scen_opts, format_func=lambda k: E.SCENARIOS[k]["title"], index=0)

st.sidebar.markdown("### 3 · Objective")
obj_default = 0 if S_.get("default_objective", "profit") == "profit" else 1
objective = st.sidebar.radio("Optimise for", ["profit", "cost"], index=obj_default, horizontal=True,
                             format_func=lambda x: {"profit": "Max regulated profit",
                                                    "cost": "Min cost (problem statement)"}[x])

st.sidebar.markdown("### 4 · Scenario levers")
lv = {}
lv["supply"] = st.sidebar.slider("Gas supply ×", 0.5, 1.5, 1.0, 0.05)
lv["demand"] = st.sidebar.slider("Demand ×", 0.5, 1.5, 1.0, 0.05)
lv["cap"] = st.sidebar.slider("All corridor capacity ×", 0.5, 1.5, 1.0, 0.05)
lv["cost"] = st.sidebar.slider("Transport cost ×", 0.5, 2.0, 1.0, 0.05)
lv["pen"] = st.sidebar.slider("Shortage penalty ×", 0.0, 3.0, 1.0, 0.1)
lv["price"] = st.sidebar.slider("Selling price ×", 0.7, 1.3, 1.0, 0.01)
lv["gascost"] = st.sidebar.slider("Gas purchase cost ×", 0.5, 2.0, 1.0, 0.05)
lv["svc_shift"] = st.sidebar.slider("Service-level shift (pts)", -20.0, 10.0, 0.0, 1.0,
                                    help="Moves every curtailable tier floor up/down. Domestic PNG stays non-curtailable.")
fsel = st.sidebar.selectbox("🎯 Required service level (all outputs)", SL_OPTS, index=0,
                            help="Minimum service level applied to every curtailable customer in all outputs. "
                                 "Tier-wise = policy floors from the Tiers table. Domestic PNG always stays at 100 %.")
lv["svc_all"] = None if fsel.startswith("Tier") else float(fsel[:-1]) / 100
lv["floor_pen"] = st.sidebar.number_input("Penalty for breaching a service floor (₹/SCM)", 0.0, 100000.0, 500.0, 50.0)
lv["mitigation"] = st.sidebar.checkbox("Allow mitigation levers (spot cargo, line-pack, virtual pipeline …)", value=False)
if T_ALL > 1:
    t_rng = st.sidebar.select_slider("Months", options=list(range(1, T_ALL + 1)), value=(1, T_ALL),
                                     format_func=lambda t: LABELS[t - 1] if t - 1 < len(LABELS) else f"M{t}")
else:
    t_rng = (1, 1)
lv["t_from"], lv["t_to"] = int(t_rng[0]), int(t_rng[1])
with st.sidebar.expander("Per-node demand ×"):
    lv["dem_node"] = {n: st.slider(f"{n}", 0.5, 1.5, 1.0, 0.05, key=f"dn_{n}") for n in work["nodes"]["Node"].astype(str)}
with st.sidebar.expander("Per-corridor capacity ×"):
    lv["cap_corr"] = {int(k): st.slider(f"Corridor {k}", 0.5, 1.5, 1.0, 0.05, key=f"cc_{k}")
                      for k in sorted(work["corridors"]["Corridor"].astype(int).unique())}
lv["dem_node"] = {k: v for k, v in lv["dem_node"].items() if v != 1.0}
lv["cap_corr"] = {k: v for k, v in lv["cap_corr"].items() if v != 1.0}

params = E.default_params(objective)
params.update(lv)
DATA = E.apply_scenario(work, scen)
HEAD = "Profit" if objective == "profit" else "Total cost"
st.sidebar.caption(f"Dataset: **{S_['name']}** · unit: {UNIT}")


def solve_now():
    with st.spinner("Solving LP with PuLP / CBC …"):
        return c_solve(DATA, params)


def need_ok(R):
    if R["status"] != "Optimal":
        st.error(f"Solver status: {R['status']}. Check the inputs (negative values, missing nodes or corridors).")
        st.stop()


def kpi_row(R):
    s = R["summary"]
    c = st.columns(6)
    if objective == "profit":
        c[0].metric("Profit (EBITDA)", money(s["Profit"], SPU))
        c[1].metric("Revenue", money(s["Revenue"], SPU))
        c[2].metric("Gas purchase cost", money(s["Gas_Cost"], SPU))
    else:
        c[0].metric("Total cost", money(s["Total_Cost"], SPU))
        c[1].metric("Transport", money(s["Transport_Cost"], SPU))
        c[2].metric("Shortage penalty", money(s["Shortage_Penalty"], SPU))
    c[3].metric(f"Total shortage ({UNIT_SHORT})", f"{s['Total_Shortage']:,.2f}")
    c[4].metric("Fill rate", pct(s["Fill_Rate"]))
    c[5].metric("Domestic PNG fill", pct(s.get("Fill_PNG Households", np.nan)))


# ======================================================================================
# Page: Home
# ======================================================================================
def shadow_summary(R):
    sh = R["shadow"]
    t = (sh[sh.Type.isin(["Source availability", "Corridor capacity"])]
         .groupby(["Type", "Item", "Name"], as_index=False)
         .agg(**{"Avg shadow (₹/SCM)": ("Shadow_Price", "mean"), "Max shadow (₹/SCM)": ("Shadow_Price", "max"),
                 "Months binding": ("Binding", "sum")}))
    return t.sort_values("Avg shadow (₹/SCM)", ascending=False).reset_index(drop=True)


def shadow_rec_text(t):
    if not len(t) or t["Avg shadow (₹/SCM)"].iloc[0] <= 1e-6:
        return "No supply or corridor limit is binding – adding gas or capacity would not change the plan."
    r = t.iloc[0]
    what = "buy more of this gas" if r.Type == "Source availability" else "add capacity on this corridor"
    return (f"<b>{r.Name}</b> is the most valuable limit: ₹{r['Avg shadow (₹/SCM)']:.2f}/SCM on average "
            f"(max ₹{r['Max shadow (₹/SCM)']:.2f}, binding {int(r['Months binding'])} months) – {what} first, "
            f"if it costs less than its shadow price.")


VERDICT_TXT = {"supplier": "🔴 Supplier-side scarcity", "mgl": "🔵 MGL-side scarcity (our problem)",
               "both": "🟠 Mixed (supplier + MGL)", "none": "🟢 No physical scarcity"}


def page_home():
    st.title(f"⛽ {C.TITLE}")
    st.markdown(f"#### {C.SUBTITLE}")
    st.markdown(f"<div style='font-size:1.05em;margin-bottom:6px'>{C.TITLE} = {C.ACRONYM_HTML}</div>", unsafe_allow_html=True)
    st.markdown(credits_html(), unsafe_allow_html=True)

    st.subheader("1 · Motivation")
    cols = st.columns(4)
    for col, (big, small) in zip(cols, C.MOTIVATION_TILES):
        col.metric(small, big)
    a, b = st.columns([3, 2])
    with a:
        st.markdown(C.MOTIVATION_BACKGROUND)
        st.markdown(C.MOTIVATION_OPPORTUNITY)
    with b:
        st.markdown("**Importance / business case**")
        x = st.columns(2)
        for i, (big, small) in enumerate(C.BUSINESS_TILES):
            x[i % 2].metric(small, big)
        for i, (t, d) in enumerate(C.BUSINESS_WHY, 1):
            st.markdown(f"**{i}. {t}** – {d}")
    st.markdown(C.MOTIVATION)
    st.caption(C.MOTIVATION_SRC)

    st.subheader("2 · Problem statement")
    st.markdown("**As given by the platform (project brief):**")
    st.markdown(f"> {C.PROBLEM_PLATFORM}")
    st.markdown("**Our project statement (what the model does):**")
    st.markdown(C.PROBLEM)

    st.subheader("3 · Objectives of the project")
    cols = st.columns(3)
    for i, (t, d) in enumerate(C.OBJECTIVES):
        with cols[i % 3]:
            st.markdown(f"**{i + 1}. {t}**  \n{d}")

    st.markdown("##### 3a · Shadow prices – what they tell us")
    cols = st.columns(4)
    for col, (t, d) in zip(cols, C.SHADOW_EXPLAINER):
        col.markdown(f"**{t}**  \n{d}")
    R = c_solve(DATA, params)
    if R["status"] == "Optimal":
        t = shadow_summary(R)
        st.caption(f"Live shadow prices – scenario **{E.SCENARIOS[scen]['title']}**, service level **{fsel}**")
        show(paint(t.style.format({"Avg shadow (₹/SCM)": "{:.2f}", "Max shadow (₹/SCM)": "{:.2f}"}),
                   good=[0] if t["Avg shadow (₹/SCM)"].iloc[0] > 1e-6 else []))
        rec(shadow_rec_text(t))

    st.markdown("##### 3b · Output of each scenario (click to select)")
    key = st.radio("Scenario", list(E.SCENARIOS), horizontal=True, label_visibility="collapsed",
                   format_func=lambda k: E.SCENARIOS[k]["title"].split(" (")[0])
    sc = E.SCENARIOS[key]
    st.markdown(f"**{sc['title']}** – {sc['problem']}")
    with st.spinner("Solving and diagnosing …"):
        dk = E.apply_scenario(work, key)
        Rk = c_solve(dk, params)
        dg = c_diag(dk, params)
    if Rk["status"] == "Optimal":
        s = Rk["summary"]
        c = st.columns(5)
        c[0].metric("Profit (EBITDA)" if objective == "profit" else "Total cost",
                    money(s["Profit"] if objective == "profit" else s["Total_Cost"], SPU))
        c[1].metric(f"Shortage ({UNIT_SHORT})", f"{s['Total_Shortage']:,.2f}")
        c[2].metric("Fill rate", pct(s["Fill_Rate"]))
        c[3].metric("Domestic PNG fill", pct(s.get("Fill_PNG Households", np.nan)))
        c[4].metric("Scarcity created by", VERDICT_TXT[dg["verdict"]].split(" ", 1)[1].replace(" scarcity", ""))
        tk = shadow_summary(Rk)
        side = {"supplier": "follow the supplier-side playbook (claim shortfall, replace gas at least cost, curtail I&C first)",
                "mgl": "fix MGL's own constraint (line-pack / virtual pipeline now, augment the bottleneck corridor next)",
                "both": "apply both playbooks", "none": "keep the current plan and maximise margin"}[dg["verdict"]]
        rec(f"{VERDICT_TXT[dg['verdict']]} – {side}. {shadow_rec_text(tk)} "
            f"See <i>Scarcity diagnosis & response</i> for the optimised plan.")

    st.subheader("4 · Sustainable Development Goals addressed")
    cols = st.columns(3)
    for i, (num, name, col, why, url) in enumerate(C.SDGS):
        with cols[i % 3]:
            st.markdown(
                f"<div style='border-left:8px solid {col};padding:8px 12px;margin-bottom:10px;"
                f"background:rgba(127,127,127,0.08);border-radius:6px'>"
                f"<b style='color:{col}'>SDG {num}</b> · <b>{name}</b><br><span style='font-size:0.9em'>{why}</span><br>"
                f"<a href='{url}' target='_blank'>UN SDG {num} ↗</a></div>", unsafe_allow_html=True)
    st.subheader("5 · How to use this simulator")
    st.markdown("""
1. **Simulator** – edit the inputs, move the sidebar levers and the **🎯 Required service level** dropdown, and see allocation, the control-tower network, corridors, shadow prices, service levels and sensitivity. Export everything to Excel.
2. **Scenarios (5)** – five real CGD scarcity situations; **Compare scenarios** – pick 2 or more and compare their optimised results side by side.
3. **Scarcity diagnosis & response** – find out whether a shortage comes from the **supplier (GAIL / LNG seller)** or from **MGL itself**, and get the optimised, regulation-compliant, profit-maximising response.
4. **Priority & regulations** – the curtailment order (domestic PNG is never cut) and a compliance check of the current plan.
5. **Future expansion & outlook** – scalability options, price escalation trend & forecast, uncertainties and the 2-year demand–supply outlook.
6. **Terminology** and **References** – plain-language glossary; PNGRB (incl. T4S), MoPNG, GAIL, MGL sources, SDGs and standard books.

Every output carries a green 💡 recommendation; recommended rows in tables are highlighted **green**.
""")
    st.info(C.DATA_NOTE)


# ======================================================================================
# Page: Model
# ======================================================================================
def page_model():
    st.title("🧮 Model & formulation")
    img = os.path.join(HERE, "assets", "problem_statement.jpg")
    if os.path.exists(img):
        with st.expander("Problem-statement poster (original formulation)", expanded=False):
            st.image(img, width="stretch")
    st.markdown("#### Index sets")
    st.markdown(r"""
- $t$ : months $\{1,\dots,T\}$ (12 for the poster data, 24 for MGL data)
- $s$ : gas sources / contracts at the city gate $G$ (APM, NWG, HP-HT, term RLNG, spot RLNG)
- $n$ : demand nodes $\{A, B, P1, P2, P3, P4, I1, I2\}$
- $k$ : corridors $\{1,2,3,4,5\}$; each corridor groups one or more pipe arcs $(j,n)$
""")
    st.markdown("#### Parameters")
    st.markdown(r"""
$A_{s,t}$ available (delivered) gas · $Q_{s,t}$ contracted gas · $D_{n,t}$ demand · $c_{jn}$ transport cost (₹/SCM) ·
$u_k$ corridor capacity · $f_{k,t}$ availability factor · $\alpha_n$ minimum service level · $p_n$ shortage penalty ·
$\pi_{n,t}$ selling price · $\gamma_{s,t}$ landed gas cost · $o$ operating cost/SCM · $e_{s,n}\in\{0,1\}$ eligibility
""")
    st.markdown("#### 1 · Problem-statement objective (min cost) — unchanged")
    st.latex(r"\min Z=\sum_{t=1}^{T}\Big(\sum_{(j,n)} c_{jn}\,x_{jn,t}+\sum_{n} p_n\,y_{n,t}\Big)")
    st.markdown("#### 2 · Extended objective (max regulated profit)")
    st.latex(r"\max \;\sum_{t}\Big[\sum_n (\pi_{n,t}-o)(D_{n,t}-y_{n,t})-\sum_{s,n}\gamma_{s,t}\,g_{s,n,t}-\sum_{(j,n)}c_{jn}x_{jn,t}-\sum_n p_n y_{n,t}-M\,v_{n,t}\Big]")
    st.markdown("#### Constraints")
    st.latex(r"\text{(1) Source availability}\quad \sum_n g_{s,n,t}\le A_{s,t}\qquad \forall s,t")
    st.latex(r"\text{(2) Node balance}\quad \sum_j x_{jn,t}-\sum_m x_{nm,t}+y_{n,t}=D_{n,t}\qquad \forall n,t")
    st.latex(r"\text{(3) Corridor capacity}\quad \sum_{(j,n)\in k}x_{jn,t}\le u_k f_{k,t}\qquad \forall k,t")
    st.latex(r"\text{(4) Service level}\quad \frac{D_{n,t}-y_{n,t}}{D_{n,t}}\ge \alpha_n\;\;(\text{soft: }+v_{n,t})\qquad \forall n,t")
    st.latex(r"\text{(5) Non-negativity}\quad x,\;y,\;g,\;v\ge 0")
    st.markdown("#### Regulatory extensions")
    st.latex(r"\text{(6) Gas accounting \& eligibility}\quad \sum_s g_{s,n,t}+y_{n,t}=D_{n,t},\qquad g_{s,n,t}=0 \text{ if } e_{s,n}=0")
    st.latex(r"\text{(7) Domestic first from APM}\quad \sum_{n\in PNG(D)} (g_{APM,n,t}+y_{n,t})\ge \min\big(A_{APM,t},\textstyle\sum_{n\in PNG(D)} D_{n,t}\big)")
    st.markdown(r"""
- **Domestic PNG** has $\alpha=100\%$ and is *non-curtailable* (very high breach penalty).
- **Take-or-pay:** unused contracted gas below the ToP % is paid for anyway.
- **Mitigation levers** (optional): emergency spot cargo, gas swap, line-pack/pressure uplift within MAOP (extra corridor capacity), virtual pipelines (cascades/LCNG) direct to nodes.
""")
    st.markdown("#### Scarcity diagnosis (supplier vs MGL)")
    st.markdown(r"""
The model is re-solved in *maximum-service* mode under four what-ifs: unlimited gas, unlimited corridors, both, and
*supplier delivers the full contract* ($A=Q$).
1. A Shapley split of the shortage between **gas** and **network** removes order bias.
2. The gas share is split into **Supplier** (contracted gas not delivered, $Q>A$) and **MGL procurement** (gas never contracted).

If ≥ 60 % of the shortage is supplier-caused, the verdict is *supplier-side*. If ≥ 60 % is MGL-caused, it is *MGL-side*. Otherwise both share the blame.
""")
    st.markdown("#### Shadow prices")
    st.markdown("Dual values from CBC show the change in objective per extra SCM of a constraint's right-hand side. "
                "For example, a corridor's shadow price is the ₹/SCM gain from one more SCM of capacity in that month.")

    st.markdown("#### Legend – symbols and where they are used in this website")
    R = c_solve(DATA, params)
    ex = {}
    try:
        I = R["I"]; t0 = I["T"][0]; s0 = I["S"][0]; n0 = I["N"][0]; k0 = I["K"][0]
        lab = LABELS[t0 - 1]
        ex = {
            "A": f"{s0} = {I['A'][(s0, t0)]:,.2f} ({lab})", "Q": f"{s0} = {I['C'][(s0, t0)]:,.2f} ({lab})",
            "D": f"{n0} = {I['D'][(n0, t0)]:,.2f} ({lab})", "c": f"C{k0} = ₹{[a[4] for a in I['arcs'] if a[1] == k0][0]:.2f}",
            "u": f"C{k0} = {I['U'][(k0, t0)]:,.2f} ({lab})",
            "f": f"C{k0} = {float(DATA['cap_factor'].set_index('Corridor').loc[k0, f'M{t0}']):.2f}",
            "alpha": ", ".join(f"{sec.split()[0]} {I['alpha'][n]:.0%}" for sec, n in
                               {I['sector'][n]: n for n in I['N']}.items()),
            "p": ", ".join(f"{sec.split()[0]} ₹{I['pen'][n]:.0f}" for sec, n in {I['sector'][n]: n for n in I['N']}.items()),
            "pi": f"{I['sector'][n0]} ₹{I['price'][(n0, t0)]:.2f}", "gamma": f"{s0} ₹{I['GC'][(s0, t0)]:.2f}",
            "o": f"₹{I['opex']:.2f}/SCM",
        }
        if R["status"] == "Optimal":
            fl = R["flows"]; ex["x"] = f"C{k0} total = {fl[(fl.Month == t0) & (fl.Corridor == k0)].Flow.sum():,.2f} ({lab})"
            ex["y"] = f"total = {R['summary']['Total_Shortage']:,.2f}"
            ex["g"] = f"{s0} used = {R['sources'][R['sources'].Source == s0].Used.sum():,.2f}"
            ex["v"] = f"total = {R['summary']['Floor_Violation']:,.2f}"
            tt = shadow_summary(R).iloc[0]
            ex["lam"] = f"{tt.Name}: ₹{tt['Avg shadow (₹/SCM)']:.2f}/SCM"
    except Exception:  # noqa: BLE001
        pass
    leg = pd.DataFrame([
        ("t", "Month index", "–", "All month axes; sidebar 'Months'", LABELS[0] + " … " + LABELS[-1]),
        ("s", "Gas source / contract (APM, NWG, HP-HT, RLNG)", "–", "Inputs → Sources; Diagnosis (supplier shortfall)", ""),
        ("n", "Demand node (A, B, P1–P4, I1, I2)", "–", "Inputs → Nodes; Network diagram boxes", ""),
        ("k", "Corridor (1–5)", "–", "Inputs → Corridors; Corridors tab; Network labels", ""),
        ("A₍s,t₎", "Gas available / delivered by supplier", UNIT, "Inputs → Supply; S2, S3 shocks; Diagnosis", ex.get("A", "")),
        ("Q₍s,t₎", "Contracted / allocated gas", UNIT, "Inputs → Contract; supplier vs MGL attribution", ex.get("Q", "")),
        ("D₍n,t₎", "Demand at node", UNIT, "Inputs → Demand; S5 surge; Results", ex.get("D", "")),
        ("c₍jn₎", "Transport cost on a pipe arc", "₹/SCM", "Inputs → Corridors; Network labels; Transport KPI", ex.get("c", "")),
        ("u_k", "Corridor capacity", UNIT, "Inputs → Corridors; Corridors tab; Shadow prices", ex.get("u", "")),
        ("f₍k,t₎", "Corridor availability factor (outage)", "0–1", "Inputs → Corridor availability; S4 outage", ex.get("f", "")),
        ("α_n", "Minimum service level (floor)", "%", "Tiers; 🎯 Required service level; Service-level tab", ex.get("alpha", "")),
        ("p_n", "Shortage penalty", "₹/SCM", "Tiers; Cost objective; Shortage penalty KPI", ex.get("p", "")),
        ("π₍n,t₎", "Net selling price", "₹/SCM", "Inputs → Prices; Profitability tab", ex.get("pi", "")),
        ("γ₍s,t₎", "Landed gas cost", "₹/SCM", "Inputs → Gas cost; S3 price spike; Profitability", ex.get("gamma", "")),
        ("o", "Operating cost per SCM delivered", "₹/SCM", "Profit objective; EBITDA/SCM", ex.get("o", "")),
        ("e₍s,n₎", "Eligibility of source for sector (APM only PNG(D)/CNG(T))", "0/1", "Inputs → Sources (Eligible); Priority page", ""),
        ("x₍jn,t₎", "Decision: gas flow on arc", UNIT, "Results; Network diagram (line width); Corridors", ex.get("x", "")),
        ("y₍n,t₎", "Decision: shortage (unmet demand)", UNIT, "Results (shortage charts); Diagnosis", ex.get("y", "")),
        ("g₍s,n,t₎", "Decision: gas of source s allotted to node n", UNIT, "Results → sourcing mix; Profitability", ex.get("g", "")),
        ("v₍n,t₎", "Decision: breach below service floor", UNIT, "Compliance tables; Service-level tab", ex.get("v", "")),
        ("λ (dual)", "Shadow price of a constraint", "₹/SCM", "Shadow-price tab; Home 3a; Diagnosis 'invest first'", ex.get("lam", "")),
    ], columns=["Symbol", "Meaning", "Unit", "Where it is used in this website", f"Example – {E.SCENARIOS[scen]['title'].split(' · ')[0]}"])
    show(leg)


# ======================================================================================
# Page: Simulator (all earlier tabs + profitability)
# ======================================================================================
ST_COL = {"Optimal": "#1E9E52", "Bottleneck": "#D62728", "Spare": "#B5BCC8"}
LANE = {"CNG Stations": ("#2F7BC4", "#DCEBFA", "#0D2E6E"), "PNG Households": ("#E06A33", "#FDE5D8", "#B23E0B"),
        "Industries": ("#56A030", "#E3F3D6", "#2B5E12"), "Commercial": ("#56A030", "#E3F3D6", "#2B5E12")}


def network_figure(R, month, scen_title=""):
    """Control-tower network in the layout of the project PPT (slide 5), driven by the LP result."""
    I = R["I"]
    rs = E.route_status(R, month)
    dv = R["deliveries"] if month == "avg" else R["deliveries"][R["deliveries"].Month == month]
    dn = dv.groupby("Node")[["Demand", "Delivered"]].mean() if month == "avg" else dv.set_index("Node")[["Demand", "Delivered"]]
    X1, X2, XD = 4.15, 6.85, 9.15
    pos = {"G": (0.9, 3.0), "A": (X1, 5.0), "B": (X2, 5.0), "P1": (X1, 3.5), "P2": (X1, 2.5),
           "P3": (X2, 3.5), "P4": (X2, 2.5), "I1": (X1, 1.3), "I2": (X1, 0.55)}
    W, H = 1.55, 0.72
    extra = [n for n in I["N"] if n not in pos]
    for i, n in enumerate(extra):
        pos[n] = (X2, 1.3 - 0.75 * i)
    fig = go.Figure()
    shapes, ann = [], []
    fmax = max(1e-9, rs.Flow.max())

    def box(x, y, w, h, line, fill, dash=None):
        shapes.append(dict(type="rect", x0=x - w / 2, x1=x + w / 2, y0=y - h / 2, y1=y + h / 2,
                           line=dict(color=line, width=2.5, dash=dash or "solid"), fillcolor=fill, layer="below"))

    def arrow(x0, y0, x1, y1, color, width, head=True):
        ann.append(dict(x=x1, y=y1, ax=x0, ay=y0, xref="x", yref="y", axref="x", ayref="y", text="",
                        showarrow=True, arrowhead=2 if head else 0, arrowsize=0.9, arrowwidth=width, arrowcolor=color))

    def label(x, y, text, size=12, color="#222", bg=None):
        ann.append(dict(x=x, y=y, text=text, showarrow=False, font=dict(size=size, color=color),
                        bgcolor=bg, xref="x", yref="y"))

    # trunk from city gate to the distribution bus
    gate_out = rs[rs.From == "G"].Flow.sum()
    used_y = [pos[r.To][1] for r in rs.itertuples() if r.From == "G" and r.To in pos]
    arrow(0.9 + 0.8, 3.0, 2.05, 3.0, "#333", 2 + 6 * gate_out / max(gate_out, 1e-9), head=False)
    if used_y:
        shapes.append(dict(type="line", x0=2.05, x1=2.05, y0=min(used_y), y1=max(used_y), line=dict(color="#333", width=4)))

    corr_label_done = set()
    for r in rs.itertuples():
        if r.From not in pos or r.To not in pos:
            continue
        col = ST_COL[r.Status]
        w = 1.2 + 9 * r.Flow / fmax if r.Flow > 1e-9 else 1.2
        x1, y1 = pos[r.To][0] - W / 2 - 0.02, pos[r.To][1]
        if r.From == "G":
            x0, y0 = 2.05, y1
        else:
            x0, y0 = pos[r.From][0] + W / 2 + 0.02, pos[r.From][1]
            if r.Corridor == 4 and pos[r.From][1] != pos[r.To][1]:
                y0 += 0.15 if pos[r.To][1] < pos[r.From][1] else -0.15
                y1 += 0.15 if pos[r.To][1] > pos[r.From][1] else -0.15
        arrow(x0, y0, x1, y1, col, w)
        if r.Corridor not in corr_label_done:
            corr_label_done.add(r.Corridor)
            sh_txt = f" · λ ₹{r.Shadow:.1f}" if (r.Shadow or 0) > 1e-6 else ""
            icon = {"Bottleneck": "⚠ ", "Optimal": "✔ ", "Spare": "○ "}[r.Status]
            ly = max(y0, y1) + 0.45 if r.Corridor != 4 else 4.2
            lx = (x0 + x1) / 2 if r.Corridor != 4 else (X1 + X2) / 2
            if r.Corridor in (3, 5):
                ly = (pos["P1"][1] if r.Corridor == 3 else pos["I1"][1]) + 0.42
                lx = (2.05 + X1 - W / 2) / 2
            label(lx, ly, f"<b>{icon}Corridor {r.Corridor}</b><br>{r.CFlow:,.1f} / {r.Capacity:,.1f} · "
                          f"{(r.Utilization or 0):.0%}<br>₹{r.Cost:.2f}/SCM{sh_txt}", 11, col, "rgba(255,255,255,0.85)")

    # virtual pipeline deliveries (tag under the node instead of long lines)
    vtag = {}
    if len(R["mitigation"]):
        m = R["mitigation"] if month == "avg" else R["mitigation"][R["mitigation"].Month == month]
        nmon = len(R["I"]["T"]) if month == "avg" else 1
        for where, vol in m[m.Where.str.startswith("Node")].groupby("Where").Volume.sum().items():
            vtag[where.split()[-1]] = vol / nmon

    # node boxes
    box(0.9, 3.0, 1.6, 1.25, "#4C9A2A", "#E3F3D6")
    label(0.9, 3.0, f"<b>City Gate<br>(Source) G</b><br>{gate_out:,.1f}", 14, "#2B5E12")
    for n in I["N"]:
        x, y = pos[n]
        line, fill, txt = LANE.get(I["sector"][n], ("#666", "#EEE", "#222"))
        h = H if not n.startswith("I") else 0.6
        de = float(dn.loc[n, "Demand"]) if n in dn.index else 0.0
        dl = float(dn.loc[n, "Delivered"]) if n in dn.index else 0.0
        fr = dl / de if de else 1.0
        badge = "#1E9E52" if fr >= 0.999 else ("#E0A800" if fr >= 0.9 else "#D62728")
        box(x, y, W, h, line, fill)
        nm = {"CNG Stations": "CNG Stations", "PNG Households": "PNG Node", "Industries": "Industrial",
              "Commercial": "Commercial"}.get(I["sector"][n], I["sector"][n])
        label(x, y + 0.1, f"<b>{nm} ({n})</b>", 12, txt)
        label(x, y - 0.17, f"<span style='color:{badge}'><b>{dl:,.1f}/{de:,.1f} · {fr:.0%}</b></span>", 11, txt)
        if n in vtag:
            label(x, y - h / 2 - 0.13, f"🚚 +{vtag[n]:,.2f} virtual pipeline", 10, "#B8860B")

    # demand boxes (right, dashed) and final arrows
    lanes = [("CNG Retail Demand", ["A", "B"], 5.0, "CNG Stations", ["B"]),
             ("PNG Demand", ["P1", "P2", "P3", "P4"], 3.0, "PNG Households", ["P3", "P4"]),
             ("Industry / Commercial Demand", ["I1", "I2"], 0.92, "Industries", ["I1", "I2"])]
    for title, members, y, sec, feeders in lanes:
        members = [m_ for m_ in members if m_ in dn.index]
        if not members:
            continue
        line, fill, txt = LANE[sec]
        de = float(dn.loc[members, "Demand"].sum()); dl = float(dn.loc[members, "Delivered"].sum())
        fr = dl / de if de else 1
        box(XD, y, 1.75, 0.95, line, "rgba(255,255,255,0.6)", dash="dash")
        label(XD, y + 0.15, f"<b>{title}</b>", 12, txt)
        label(XD, y - 0.2, f"{dl:,.1f} / {de:,.1f} ({fr:.1%})", 11, txt)
        for f_ in feeders:
            if f_ in pos:
                arrow(pos[f_][0] + W / 2 + 0.02, pos[f_][1], XD - 0.9, y, "#555", 2)

    # tier legend bar
    tiers = []
    for sec in ["PNG Households", "CNG Stations", "Commercial", "Industries"]:
        ns = [n for n in I["N"] if I["sector"][n] == sec]
        if ns:
            n = ns[0]
            tiers.append(f"Tier {I['tier'][n]} {sec}: {I['alpha'][n]:.0%}, ₹{I['pen'][n]:.0f}/SCM")
    shapes.append(dict(type="rect", x0=0.2, x1=10.0, y0=-0.55, y1=0.05, line=dict(color="#AAB", width=1.5),
                       fillcolor="#F5F7FB", layer="below"))
    label(5.1, -0.25, "<b>Priority tiers (min service / shortage penalty):</b>  " + "   ·   ".join(tiers), 11, "#333")

    mlabel = "Average of all months" if month == "avg" else LABELS[month - 1]
    fig.update_layout(shapes=shapes, annotations=ann, height=640, paper_bgcolor="white", plot_bgcolor="white",
                      margin=dict(l=10, r=10, t=70, b=10), font=dict(color="#222"),
                      title=dict(text=f"<b>GAS ALLOCATION NETWORK – CONTROL TOWER</b><br><span style='font-size:13px;color:#555'>"
                                      f"City Gate → Corridors → Demand nodes · {mlabel} · {scen_title} · "
                                      f"<span style='color:{ST_COL['Optimal']}'>■ optimal route</span> "
                                      f"<span style='color:{ST_COL['Bottleneck']}'>■ bottleneck</span> "
                                      f"<span style='color:#9AA3B0'>■ spare</span></span>",
                                 x=0.5, font=dict(size=20, color="#0D2E6E")),
                      showlegend=True, legend=dict(orientation="h", y=-0.02, font=dict(color="#222")))
    fig.update_xaxes(visible=False, range=[-0.1, 10.15])
    fig.update_yaxes(visible=False, range=[-0.7, 5.8])
    return fig, rs


def route_table(rs):
    nm = lambda n: "City Gate" if n == "G" else n  # noqa: E731
    t = pd.DataFrame({
        "Route": [f"{nm(r.From)} → {r.To}" for r in rs.itertuples()],
        "Corridor": rs.Corridor.values, "Flow": rs.Flow.values, "Corridor capacity": rs.Capacity.values,
        "Utilisation": rs.Utilization.values, "Shadow ₹/SCM": rs.Shadow.fillna(0).values, "Cost ₹/SCM": rs.Cost.values,
        "Status": [{"Optimal": "✅ Optimal route", "Bottleneck": "⚠️ Bottleneck", "Spare": "○ Spare"}[x] for x in rs.Status]})
    return t


def page_simulator():
    st.title("⛽ Gas Allocation over Months — LP Dashboard (PuLP)")
    sc = E.SCENARIOS[scen]
    st.caption(f"Scenario: **{sc['title']}** · Objective: **{'max regulated profit' if objective == 'profit' else 'min cost (problem statement)'}** · "
               f"Mitigation levers: **{'on' if params['mitigation'] else 'off'}** · 🎯 Service level: **{fsel}**")
    tabs = st.tabs(["📥 Inputs", "📊 Results", "💰 Profitability", "🌐 Network diagram", "🛣 Corridors",
                    "💲 Shadow prices", "🎚 Service level", "🎯 Sensitivity", "💾 Export"])

    # ---------------- Inputs
    with tabs[0]:
        st.caption("Edit any table directly; results update immediately. The scenario selected in the sidebar is applied "
                   "on top of these base inputs (see the **Scenarios** page).")
        if st.button("↺ Reset all edits for this dataset"):
            edits.pop(ds_name, None)
            for k in list(st.session_state.keys()):
                if str(k).startswith(f"ed|{ds_name}|"):
                    del st.session_state[k]
            st.rerun()
        store = edits.setdefault(ds_name, {})

        def ed(key, title, help_=None):
            st.markdown(f"**{title}**" + (f"  \n<span style='font-size:0.85em;opacity:0.7'>{help_}</span>" if help_ else ""),
                        unsafe_allow_html=True)
            cur = store.get(key, base_data[key])
            out = st.data_editor(cur, key=f"ed|{ds_name}|{key}", num_rows="fixed", width="stretch", hide_index=True)
            if not out.equals(base_data[key]):
                store[key] = out
            elif key in store:
                store.pop(key)

        c1, c2 = st.columns(2)
        with c1:
            ed("tiers", "Tiers (service floors & penalties)", "NonCurtailable = never cut (domestic PNG)")
            ed("nodes", "Nodes")
        with c2:
            ed("corridors", f"Corridors (cost ₹/SCM, capacity {UNIT})", "Rows with the same corridor number share its capacity")
            ed("sources", "Gas sources / suppliers", "Eligible = sectors allowed to use this gas; PriorityTo = served first")
        ed("demand", f"Demand ({UNIT})")
        c1, c2 = st.columns(2)
        with c1:
            ed("contract", f"Contracted / allocated gas ({UNIT})")
            ed("source_cost", "Landed gas cost (₹/SCM)")
        with c2:
            ed("supply", f"Source availability – actually delivered ({UNIT})")
            ed("prices", "Net selling price by sector (₹/SCM)")
        c1, c2 = st.columns(2)
        with c1:
            ed("cap_factor", "Corridor availability factor (1 = full)")
        with c2:
            ed("mitigation", "Mitigation levers (used when 'Allow mitigation levers' is ticked)")

    # recompute with any edits made above
    global DATA
    w2 = {k: (v.copy() if isinstance(v, pd.DataFrame) else dict(v)) for k, v in base_data.items()}
    for k, v in edits.get(ds_name, {}).items():
        w2[k] = v
    DATA = E.apply_scenario(D.normalize(w2), scen)
    R = solve_now()

    # ---------------- Results
    with tabs[1]:
        st.markdown(f"Solver status: **{R['status']}**")
        need_ok(R)
        kpi_row(R)
        dv = R["deliveries"]
        order = {"Label": [LABELS[t - 1] for t in R["I"]["T"]]}
        c1, c2 = st.columns(2)
        with c1:
            m = dv.groupby(["Month", "Label", "Sector"], as_index=False).Delivered.sum().sort_values("Month")
            fig = px.bar(m, x="Label", y="Delivered", color="Sector", color_discrete_map=SECTOR_COLORS,
                         title=f"Monthly delivery vs demand & supply ({UNIT})", category_orders=order)
            tot = dv.groupby(["Month", "Label"], as_index=False).Demand.sum().sort_values("Month")
            sup = R["sources"][~R["sources"].Source.str.startswith(("UNC", "MIT"))].groupby("Month").Available.sum()
            fig.add_trace(go.Scatter(x=tot.Label, y=tot.Demand, name="Demand", mode="lines+markers",
                                     line=dict(color="white", dash="dash")))
            fig.add_trace(go.Scatter(x=tot.Label, y=tot.Month.map(sup), name="Gas available", mode="lines",
                                     line=dict(color="#E15759")))
            chart(fig)
        with c2:
            sh = dv.groupby(["Month", "Label", "Sector"], as_index=False).Shortage.sum().sort_values("Month")
            fig = px.bar(sh, x="Label", y="Shortage", color="Sector", color_discrete_map=SECTOR_COLORS,
                         title=f"Shortage by customer type ({UNIT})", category_orders=order)
            chart(fig)
        c1, c2 = st.columns(2)
        with c1:
            hm = dv.pivot_table(index="Node", columns="Month", values="Fill_Rate").sort_index()
            fig = px.imshow(hm.values, x=[LABELS[t - 1] for t in hm.columns], y=hm.index, color_continuous_scale="RdYlGn",
                            zmin=0.7, zmax=1.0, text_auto=".0%", aspect="auto", title="Fill rate by node and month")
            chart(fig, 420)
        with c2:
            al = R["alloc"].groupby(["Month", "Label", "Source"], as_index=False).Volume.sum().sort_values("Month")
            fig = px.bar(al, x="Label", y="Volume", color="Source", title=f"Gas sourcing mix ({UNIT})",
                         category_orders=order)
            chart(fig, 420)
        st.markdown("**Regulatory compliance of this plan**")
        cp = E.compliance(R)
        show(paint(cp.style.format({"Floor": "{:.0%}", "Fill (period)": "{:.2%}", "Worst node-month": "{:.1%}"}),
                   good=cp.index[cp.Status.str.startswith("✅")], bad=cp.index[cp.Status.str.startswith("❌")]))
        s_ = R["summary"]
        worst = dv.groupby("Sector").apply(lambda d: d.Shortage.sum()).sort_values(ascending=False)
        if (cp.Status.str.startswith("✅")).all():
            rec(f"Plan is compliant at <b>{fsel}</b>: fill rate {s_['Fill_Rate']:.1%}, domestic PNG "
                f"{s_.get('Fill_PNG Households', 1):.1%}. Shortage ({s_['Total_Shortage']:,.2f} {UNIT_SHORT}) falls mainly on "
                f"<b>{worst.index[0]}</b>, as the priority rules intend.")
        else:
            br = ", ".join(cp[cp.Status.str.startswith("❌")].Sector)
            rec(f"Floor breached for <b>{br}</b> – tick <i>Allow mitigation levers</i> or see <i>Scarcity diagnosis & response</i> "
                "for the optimised plan that restores compliance.")
        st.markdown("**Delivery detail**")
        show(dv.drop(columns=["Month"]).style.format({"Demand": "{:,.3f}", "Delivered": "{:,.3f}", "Shortage": "{:,.3f}",
                                                      "Required": "{:,.3f}", "Floor_Violation": "{:,.3f}",
                                                      "Fill_Rate": "{:.1%}", "Price": "{:,.2f}", "Revenue": "{:,.1f}"}))

    # ---------------- Profitability
    with tabs[2]:
        need_ok(R)
        s = R["summary"]
        c = st.columns(5)
        c[0].metric("Revenue", money(s["Revenue"], SPU))
        c[1].metric("Gas cost", money(s["Gas_Cost"], SPU))
        c[2].metric("Network + mitigation + ToP", money(s["Transport_Cost"] + s["Mitigation_Cost"] + s["TakeOrPay_Cost"], SPU))
        c[3].metric("Profit (EBITDA)", money(s["Profit"], SPU))
        vol = s["Total_Demand"] - s["Total_Shortage"]
        c[4].metric("EBITDA / SCM", f"₹{s['Profit'] / max(vol, 1e-9):.2f}")
        sp = E.sector_pnl(R)
        loss = sp[sp.Margin < 0]
        if len(loss):
            st.error("⚠️ Loss-making segment(s): " + ", ".join(loss.Sector) +
                     ". Re-price (CNG/I&C are market-priced), shift cheaper eligible gas, or curtail above-floor volume.")
        else:
            st.success("✅ No segment is loss-making under this plan.")
        mlab, mdiv = money_unit(SPU)
        c1, c2 = st.columns(2)
        with c1:
            spp = sp.melt(id_vars="Sector", value_vars=["Avg_Price", "Avg_Gas_Cost", "Margin_per_SCM"], var_name="Metric", value_name="₹/SCM")
            fig = px.bar(spp, x="Sector", y="₹/SCM", color="Metric", barmode="group", title="Price, gas cost and margin per SCM by sector")
            chart(fig)
        with c2:
            mp = E.monthly_pnl(R)
            mp["Profit_disp"] = to_money(mp.Profit, SPU)
            fig = px.bar(mp, x="Label", y="Profit_disp", title=f"Monthly profit ({mlab})",
                         color=np.where(mp.Profit < 0, "Loss", "Profit"), color_discrete_map={"Loss": "#E15759", "Profit": "#59A14F"})
            chart(fig)
        sp_disp = sp.copy()
        for col_ in ["Revenue", "Gas_Cost", "Network_Cost", "Opex", "Margin"]:
            sp_disp[col_] = to_money(sp_disp[col_], SPU)
        st.markdown(f"**Segment P&L ({mlab})**")
        best_i = sp.Margin_per_SCM.idxmax() if len(sp) else None
        rec(f"Highest margin: <b>{sp.loc[best_i, 'Sector']}</b> (₹{sp.loc[best_i, 'Margin_per_SCM']:.2f}/SCM) – serve it fully "
            "above the regulatory floors. " + ("Loss segments must be re-priced or curtailed above their floor."
                                               if len(loss) else "All segments are profitable."))
        show(paint(sp_disp.style, good=[best_i], bad=list(loss.index)).format({"Volume": "{:,.2f}", "Revenue": "{:,.2f}", "Gas_Cost": "{:,.2f}", "Network_Cost": "{:,.2f}",
                                   "Opex": "{:,.2f}", "Margin": "{:,.2f}", "Margin_per_SCM": "{:,.2f}", "Avg_Price": "{:,.2f}",
                                   "Avg_Gas_Cost": "{:,.2f}"}))
        su = R["sources"][~R["sources"].Source.isin(["UNC"])].groupby("Source", as_index=False)[["Contract", "Available", "Used", "ToP_Unused", "Shortfall_vs_Contract"]].sum()
        st.markdown(f"**Source utilisation ({UNIT_SHORT}, horizon total)**")
        show(su.style.format({c_: "{:,.2f}" for c_ in su.columns if c_ != "Source"}))
        if len(R["mitigation"]):
            st.markdown("**Mitigation actions chosen by the optimiser**")
            show(R["mitigation"].drop(columns=["Month"]).style.format({"Volume": "{:,.3f}", "Cost": "{:,.2f}"}))

    # ---------------- Network
    with tabs[3]:
        need_ok(R)
        opts = ["avg"] + R["I"]["T"]
        mo = st.selectbox("Month", opts, format_func=lambda t: "Average of all months" if t == "avg" else LABELS[t - 1])
        fig, rs = network_figure(R, mo, E.SCENARIOS[scen]["title"].split(" (")[0])
        st.plotly_chart(fig, width="stretch")
        st.caption("Layout as in the project network diagram: City Gate → C1 → CNG A → C2 → CNG B; City Gate → C3 → PNG P1,P2 → "
                   "C4 → PNG P3,P4; City Gate → C5 → Industrial I1 / Commercial I2. Line width = flow; green = optimal route chosen "
                   "by the LP, red = bottleneck (full and shadow price > 0), grey = spare link; dotted yellow = virtual pipeline. "
                   "Changes with scenario, sidebar levers, inputs and month.")
        rt = route_table(rs)
        st.markdown("**Route summary**")
        show(paint(rt.style.format({"Flow": "{:,.2f}", "Corridor capacity": "{:,.2f}", "Utilisation": "{:.0%}",
                                    "Shadow ₹/SCM": "{:.2f}", "Cost ₹/SCM": "{:.2f}"}),
                   good=rt.index[rs.Status.values == "Optimal"], bad=rt.index[rs.Status.values == "Bottleneck"]))
        used = rt[rs.Status.values != "Spare"]
        bn = rs[rs.Status == "Bottleneck"].sort_values("Shadow", ascending=False)
        msg = "Optimal routing: " + "; ".join(used.Route.tolist()) + ". "
        if len(bn):
            b0 = bn.iloc[0]
            msg += (f"Corridor {b0.Corridor} is the bottleneck (shadow ₹{b0.Shadow:.2f}/SCM) – relieve it first "
                    "(line-pack now, augmentation next).")
        else:
            msg += "No corridor is a bottleneck in this view – the network can carry all gas the plan supplies."
        rec(msg)

    # ---------------- Corridors
    with tabs[4]:
        need_ok(R)
        ut = R["util"]
        hm = ut.pivot_table(index="Corridor", columns="Month", values="Utilization")
        fig = px.imshow(hm.values, x=[LABELS[t - 1] for t in hm.columns], y=[f"Corridor {k}" for k in hm.index],
                        color_continuous_scale="RdYlGn_r", zmin=0.5, zmax=1.0, text_auto=".0%", aspect="auto",
                        title="Corridor utilisation (flow / capacity)")
        chart(fig, 360)
        fig = px.line(ut.assign(Corr=lambda d: "Corridor " + d.Corridor.astype(str)), x="Label", y="Flow", color="Corr",
                      title=f"Corridor flow ({UNIT}) – dashed = capacity", markers=True)
        for k, g_ in ut.groupby("Corridor"):
            fig.add_trace(go.Scatter(x=g_.Label, y=g_.Capacity, mode="lines", line=dict(dash="dash", width=1),
                                     name=f"Cap C{k}", showlegend=False))
        chart(fig)
        shc = R["shadow"][R["shadow"].Type == "Corridor capacity"].assign(Corridor=lambda d: d.Item.str.split().str[-1].astype(int))
        cs = ut.groupby("Corridor").agg(**{"Avg utilisation": ("Utilization", "mean"), "Peak utilisation": ("Utilization", "max"),
                                           "Months ≥ 99 %": ("Utilization", lambda x: int((x >= 0.99).sum()))})
        cs["Avg shadow ₹/SCM"] = shc.groupby("Corridor").Shadow_Price.mean()
        cs["Months binding"] = shc.groupby("Corridor").Binding.sum().astype(int)
        cs = cs.reset_index()
        top = cs["Avg shadow ₹/SCM"].idxmax()
        st.markdown("**Corridor summary**")
        show(paint(cs.style.format({"Avg utilisation": "{:.1%}", "Peak utilisation": "{:.1%}", "Avg shadow ₹/SCM": "{:.2f}"}),
                   good=[top] if cs.loc[top, "Avg shadow ₹/SCM"] > 1e-6 else []))
        if cs.loc[top, "Avg shadow ₹/SCM"] > 1e-6:
            rec(f"Augment <b>Corridor {cs.loc[top, 'Corridor']}</b> first: binding in {cs.loc[top, 'Months binding']} months, "
                f"worth ₹{cs.loc[top, 'Avg shadow ₹/SCM']:.2f}/SCM on average. Corridors with low peak use have spare capacity.")
        else:
            rec("No corridor is binding – pipeline capacity is not the constraint in this scenario; focus on gas supply.")
        with st.expander("Monthly corridor detail"):
            show(ut.drop(columns=["Month"]).style.format({"Flow": "{:,.3f}", "Capacity": "{:,.3f}", "Uplift": "{:,.3f}",
                                                          "Design_Capacity": "{:,.3f}", "Utilization": "{:.1%}"}))

    # ---------------- Shadow prices
    with tabs[5]:
        need_ok(R)
        alt = st.select_slider("Alter capacity / supply / demand by", options=[-0.2, -0.1, -0.05, 0.05, 0.1, 0.2, 0.3],
                               value=0.1, format_func=lambda v: f"{v:+.0%}")
        with st.spinner("Re-solving for each constraint …"):
            si = c_shadow_impact(DATA, params, alt)
        sh = R["shadow"]
        top = si.sort_values("Actual objective gain (re-solve)", ascending=False).iloc[0]
        c = st.columns(3)
        c[0].metric("Highest-value constraint", top["Constraint"])
        c[1].metric("Avg shadow price (all supply & corridors)",
                    f"₹{sh[sh.Type.isin(['Source availability', 'Corridor capacity'])].Shadow_Price.mean():.2f}/SCM")
        c[2].metric(f"Objective gain from {alt:+.0%}", money(top["Actual objective gain (re-solve)"], SPU))
        st.caption("Estimated gain = Σ shadow price × extra units (linear). Actual = full re-solve. Linear estimates overstate the gain "
                   "once another constraint takes over. A corridor shows ₹0 while gas supply, not pipeline capacity, is the limit. "
                   "Corridors 3 & 4 serve non-curtailable households, so they are kept with spare capacity: try scenario S4 or "
                   "−10 % to see their value.")
        c1, c2 = st.columns(2)
        with c1:
            m = si.melt(id_vars="Constraint", value_vars=["Est. objective gain (linear)", "Actual objective gain (re-solve)"])
            m["value"] = to_money(m["value"], SPU)
            fig = px.bar(m, x="Constraint", y="value", color="variable", barmode="group",
                         title=f"Objective gain from {alt:+.0%} ({money_unit(SPU)[0]})")
            chart(fig)
        with c2:
            sp_ = sh[sh.Type.isin(["Source availability", "Corridor capacity"])]
            fig = px.line(sp_, x="Label", y="Shadow_Price", color="Item", title="Shadow price by month (₹/SCM)", markers=True)
            chart(fig)
        hm = sp_.pivot_table(index="Item", columns="Month", values="Shadow_Price")
        fig = px.imshow(hm.values, x=[LABELS[t - 1] for t in hm.columns], y=hm.index, text_auto=".1f", aspect="auto",
                        color_continuous_scale="Blues", title="Shadow-price heat-map (₹/SCM)")
        chart(fig, 380)
        st.markdown("**Impact of shadow prices on total cost / profit and on each corridor**")
        si_disp = si.copy()
        gi = si["Actual objective gain (re-solve)"].idxmax()
        good_si = [gi] if si.loc[gi, "Actual objective gain (re-solve)"] > 1e-6 else []
        for col_ in ["Est. objective gain (linear)", "Actual objective gain (re-solve)", "Change in profit", "Change in total cost"]:
            si_disp[col_] = to_money(si_disp[col_], SPU)
        show(paint(si_disp.style, good=good_si).format({c_: "{:,.2f}" for c_ in si_disp.columns if c_ not in ("Constraint", "Months binding")}
                                  | {"Avg util": "{:.1%}", "Peak util": "{:.1%}"}, na_rep="–"))
        if good_si:
            rec(f"Relax <b>{si.loc[gi, 'Constraint']}</b> first: {alt:+.0%} gives {money(si.loc[gi, 'Actual objective gain (re-solve)'], SPU)} "
                f"(avg shadow ₹{si.loc[gi, 'Avg shadow (₹/SCM)']:.2f}/SCM, binding {int(si.loc[gi, 'Months binding'])} months). "
                "Do it only if the cost per SCM is below the shadow price.")
        else:
            rec("No constraint gains from this change – supply and corridors are not limiting at this setting.")
        st.markdown(f"**Demand alteration – {alt:+.0%} demand at each node**")
        st.caption("Marginal profit = extra profit per extra SCM demanded. Nodes behind a bottleneck corridor, or served from expensive "
                   "spot gas, earn the least (or lose).")
        di = c_demand_impact(DATA, params, alt)
        di_disp = di.copy()
        for col_ in ["Change in objective", "Change in real cost (gas+network)", "Change in profit"]:
            di_disp[col_] = to_money(di_disp[col_], SPU)
        bi, wi = di["Marginal profit ₹/extra SCM"].idxmax(), di["Marginal profit ₹/extra SCM"].idxmin()
        show(paint(di_disp.style, good=[bi], bad=[wi] if di.loc[wi, "Marginal profit ₹/extra SCM"] < 0 else []).format(
            {c_: "{:,.2f}" for c_ in di_disp.columns if c_ not in ("Node", "Sector")} | {"Extra served (share)": "{:.0%}"}, na_rep="–"))
        rec(f"Grow sales first at <b>{di.loc[bi, 'Node']}</b> ({di.loc[bi, 'Sector']}): ₹{di.loc[bi, 'Marginal profit ₹/extra SCM']:.2f} "
            f"profit per extra SCM. Least attractive: {di.loc[wi, 'Node']} (₹{di.loc[wi, 'Marginal profit ₹/extra SCM']:.2f}).")
        with st.expander("All dual values (incl. node marginal cost and service-floor duals)"):
            show(sh.drop(columns=["Month"]))

    # ---------------- Service level
    with tabs[6]:
        need_ok(R)
        st.caption("Uniform minimum service floor for every curtailable node, 70% → 95% in 5% steps (domestic PNG stays at 100 %; "
                   "other levers as set in the sidebar). Select a floor in the sidebar to apply it everywhere.")
        with st.spinner("Solving 6 service levels …"):
            sv = c_service(DATA, params)
        ok = sv[sv["Feasible"] != "No"]
        c1, c2 = st.columns(2)
        with c1:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=[f"{a:.0%}" for a in ok["Service floor"]], y=to_money(ok[HEAD], SPU), name=HEAD))
            fig.add_trace(go.Scatter(x=[f"{a:.0%}" for a in ok["Service floor"]], y=ok["Shortage"], name=f"Shortage ({UNIT_SHORT})",
                                     yaxis="y2", mode="lines+markers"))
            fig.add_trace(go.Scatter(x=[f"{a:.0%}" for a in ok["Service floor"]], y=ok["Floor breach"], name="Floor breach",
                                     yaxis="y2", mode="lines+markers", line=dict(dash="dot")))
            fig.update_layout(title=f"{HEAD} & shortage vs service floor", yaxis=dict(title=money_unit(SPU)[0]),
                              yaxis2=dict(overlaying="y", side="right", title=UNIT_SHORT))
            chart(fig)
        with c2:
            fc = [c_ for c_ in ok.columns if c_.startswith("Fill ")]
            m = ok.melt(id_vars="Service floor", value_vars=fc + ["Fill rate"])
            m["Service floor"] = m["Service floor"].map(lambda a: f"{a:.0%}")
            fig = px.line(m, x="Service floor", y="value", color="variable", markers=True, title="Fill rate by sector vs floor")
            fig.update_yaxes(tickformat=".0%")
            chart(fig)
        feas = sv[sv["Feasible"] == "Yes"]
        rec_i = None
        if len(feas):
            if objective == "profit":
                cand = feas[feas["Profit"] >= feas["Profit"].max() - 0.01 * abs(feas["Profit"].max())]
            else:
                cand = feas[feas["Total cost"] <= feas["Total cost"].min() + 0.01 * abs(feas["Total cost"].min())]
            rec_i = cand["Service floor"].idxmax()
            r_ = sv.loc[rec_i]
            rec(f"Recommended uniform service level: <b>{r_['Service floor']:.0%}</b> – the highest floor met without breach while "
                f"{HEAD.lower()} stays within 1 % of the best ({money(r_[HEAD], SPU)}). Higher floors "
                + ("need mitigation or cost more." if rec_i != sv.index[-1] else "are all affordable here."))
        else:
            rec("No uniform floor can be met without breach – enable mitigation levers or lower the floor.")
        disp = sv.copy()
        for col_ in ["Objective", "Total cost", "Profit", "Transport", "Gas cost", "Shortage penalty", "Objective vs previous"]:
            if col_ in disp:
                disp[col_] = to_money(disp[col_], SPU)
        show(paint(disp.style, good=[rec_i] if rec_i is not None else [], bad=disp.index[disp["Feasible"] != "Yes"]).format({c_: "{:,.2f}" for c_ in disp.columns if c_ not in ("Feasible",)}
                               | {"Service floor": "{:.0%}", "Fill rate": "{:.2%}"} | {c_: "{:.2%}" for c_ in disp.columns if c_.startswith("Fill ")},
                               na_rep="–"))

    # ---------------- Sensitivity
    with tabs[7]:
        need_ok(R)
        st.caption("Each run re-solves the LP around your data and current scenario & levers.")
        res = st.session_state.setdefault("sens", {})
        st.markdown(f"**Tornado – impact of ±x% change on {HEAD.lower()}**")
        chg = st.number_input("Change (%)", 1, 50, 10)
        if st.button("Run tornado"):
            with st.spinner("Running tornado …"):
                res["tornado"] = c_tornado(DATA, params, chg / 100)
        if "tornado" in res:
            b, tor = res["tornado"]
            m = tor.melt(id_vars="Parameter", value_vars=["Low (−)", "High (+)"])
            m["value"] = to_money(m["value"], SPU)
            fig = px.bar(m, y="Parameter", x="value", color="variable", orientation="h", barmode="overlay",
                         title=f"Change in {HEAD.lower()} vs base {money(b, SPU)} ({money_unit(SPU)[0]})")
            chart(fig, 480)
            tp = tor.iloc[-1]
            rec(f"<b>{tp.Parameter}</b> moves {HEAD.lower()} the most (swing {money(tp.Swing, SPU)} for ±{chg}%) – "
                "monitor and hedge this input first; parameters at the bottom barely matter.")
        st.markdown("**One-way sweep**")
        c1, c2 = st.columns([2, 3])
        with c1:
            prm = st.selectbox("Parameter", list(E.TORNADO_PARAMS.keys()))
        with c2:
            lo, hi = st.slider("Range", 0.3, 2.0, (0.5, 1.5), 0.05)
        if st.button("Run sweep"):
            with st.spinner("Sweeping …"):
                res["sweep"] = (prm, c_sweep(DATA, params, prm, lo, hi))
        if "sweep" in res:
            prm_, sw = res["sweep"]
            c1, c2 = st.columns(2)
            with c1:
                fig = px.line(sw.assign(H=to_money(sw.Headline, SPU)), x="Multiplier", y="H", markers=True,
                              title=f"{HEAD} vs {prm_} ({money_unit(SPU)[0]})")
                chart(fig, 320)
            with c2:
                fig = px.line(sw, x="Multiplier", y="Fill rate", markers=True, title=f"Fill rate vs {prm_}")
                fig.update_yaxes(tickformat=".0%")
                chart(fig, 320)
            ok_ = sw[sw["Fill rate"] >= 0.95]
            rec(f"For <b>{prm_}</b>, fill rate stays ≥ 95 % for multipliers "
                + (f"{ok_.Multiplier.min():.2f}–{ok_.Multiplier.max():.2f}." if len(ok_) else "– none in this range; act on this input."))
        st.markdown(f"**Two-way: supply × demand → {HEAD.lower()}**")
        if st.button("Run heat-map (25 solves)"):
            with st.spinner("Running 25 solves …"):
                res["heat"] = c_heat(DATA, params)
        if "heat" in res:
            Z, F = res["heat"]
            grid = ["80%", "90%", "100%", "110%", "120%"]
            c1, c2 = st.columns(2)
            with c1:
                fig = px.imshow(to_money(pd.DataFrame(Z), SPU).values, x=[f"Supply {g_}" for g_ in grid], y=[f"Demand {g_}" for g_ in grid],
                                text_auto=".1f", aspect="auto", color_continuous_scale="RdYlGn" if objective == "profit" else "RdYlGn_r",
                                title=f"{HEAD} ({money_unit(SPU)[0]})")
                chart(fig, 400)
            with c2:
                fig = px.imshow(F, x=[f"Supply {g_}" for g_ in grid], y=[f"Demand {g_}" for g_ in grid], text_auto=".1%",
                                aspect="auto", color_continuous_scale="RdYlGn", zmin=0.7, zmax=1.0, title="Fill rate")
                chart(fig, 400)
            Fd = pd.DataFrame(F, index=grid, columns=grid)
            safe = [g_ for g_ in grid if Fd.loc["100%", g_] >= 0.95]
            rec("At today's demand, fill rate ≥ 95 % needs supply of at least "
                + (f"<b>{safe[0]}</b> of the base." if safe else "<b>more than 120 %</b> – supply is the binding issue."))

    # ---------------- Export
    with tabs[8]:
        need_ok(R)
        st.caption("Workbook contains: summary, scenario settings, deliveries, shortage matrix, flows, corridor utilisation, gas "
                   "allocation by source, source utilisation, mitigation, shadow prices, shadow & demand impact, service-level sweep, "
                   "segment P&L, compliance, any sensitivity runs you executed, and the input tables.")
        st.download_button("⬇ Download results (.xlsx)", build_export(R), file_name="cgd_gas_allocation_results.xlsx",
                           width="content")


def build_export(R):
    bio = io.BytesIO()
    s = R["summary"]
    with pd.ExcelWriter(bio, engine="openpyxl") as xw:
        summ = pd.DataFrame([(k, v) for k, v in s.items()], columns=["Metric", "Value"])
        summ.loc[len(summ)] = ("Money unit", f"Values × {SPU:g} = ₹ (₹/SCM × {UNIT})")
        summ.to_excel(xw, sheet_name="Summary", index=False)
        sett = {**{k: str(v) for k, v in params.items()}, "scenario": E.SCENARIOS[scen]["title"], "dataset": S_["name"]}
        pd.DataFrame(list(sett.items()), columns=["Setting", "Value"]).to_excel(xw, sheet_name="Scenario", index=False)
        R["deliveries"].to_excel(xw, sheet_name="Deliveries", index=False)
        R["deliveries"].pivot_table(index="Node", columns="Label", values="Shortage", sort=False).to_excel(xw, sheet_name="Shortage_Matrix")
        R["flows"].to_excel(xw, sheet_name="Flows", index=False)
        R["util"].to_excel(xw, sheet_name="Corridor_Utilization", index=False)
        R["alloc"].to_excel(xw, sheet_name="Gas_Allocation", index=False)
        R["sources"].to_excel(xw, sheet_name="Source_Utilization", index=False)
        R["mitigation"].to_excel(xw, sheet_name="Mitigation", index=False)
        R["shadow"].to_excel(xw, sheet_name="Shadow_Prices", index=False)
        E.sector_pnl(R).to_excel(xw, sheet_name="Segment_PnL", index=False)
        E.monthly_pnl(R).to_excel(xw, sheet_name="Monthly_PnL", index=False)
        E.compliance(R).to_excel(xw, sheet_name="Compliance", index=False)
        try:
            c_shadow_impact(DATA, params, 0.1).to_excel(xw, sheet_name="Shadow_Impact", index=False)
            c_demand_impact(DATA, params, 0.1).to_excel(xw, sheet_name="Demand_Impact", index=False)
            c_service(DATA, params).to_excel(xw, sheet_name="Service_Level", index=False)
        except Exception:  # noqa: BLE001
            pass
        res = st.session_state.get("sens", {})
        if "tornado" in res:
            res["tornado"][1].to_excel(xw, sheet_name="Tornado", index=False)
        if "sweep" in res:
            res["sweep"][1].to_excel(xw, sheet_name="Sweep_" + res["sweep"][0][:20].replace(" ", "_"), index=False)
        if "heat" in res:
            pd.DataFrame(res["heat"][0], index=[f"Demand {g}" for g in (0.8, 0.9, 1.0, 1.1, 1.2)],
                         columns=[f"Supply {g}" for g in (0.8, 0.9, 1.0, 1.1, 1.2)]).to_excel(xw, sheet_name="Heatmap")
        dg = st.session_state.get("last_diag")
        if dg is not None:
            dg.to_excel(xw, sheet_name="Diagnosis", index=False)
        for sheet, key in D.KEYMAP.items():
            DATA[key].to_excel(xw, sheet_name=f"Input_{sheet}"[:31], index=False)
    return bio.getvalue()


# ======================================================================================
# Page: Scenarios
# ======================================================================================
def page_scenarios():
    st.title("🧪 Five real-world CGD scarcity scenarios")
    st.caption("Each scenario is applied on top of the selected dataset and inputs. Select one in the sidebar to "
               "explore it in the Simulator and the Diagnosis page.")
    for key, sc in E.SCENARIOS.items():
        icon = {"Reference": "🟢", "Supplier": "🔴", "MGL": "🔵"}[sc["side"]]
        with st.expander(f"{icon} {sc['title']}", expanded=(key == scen)):
            st.markdown(f"**What happens:** {sc['problem']}")
            st.markdown(f"**Real-world basis:** {sc['real']}")
            if sc["ops"]:
                T = len(E.months_of(work))
                rows = []
                for op in sc["ops"]:
                    mths = E._window(T, op["window"])
                    rows.append({"Shock on": op["kind"], "Applies to": ", ".join(map(str, op["match"])),
                                 "Factor": f"×{op['factor']:.2f}",
                                 "Months": f"{LABELS[mths[0] - 1]} – {LABELS[mths[-1] - 1]}"})
                show(pd.DataFrame(rows))
    st.subheader("Side-by-side comparison")
    p0 = dict(params)
    with st.spinner("Solving all 5 scenarios …"):
        cs = c_compare(work, p0)
    mlab = money_unit(SPU)[0]
    disp = cs.copy()
    for col_ in ["Profit", "Total cost", "Revenue", "Gas cost"]:
        disp[col_] = to_money(disp[col_], SPU)
    bi = cs["Profit"].idxmax(); wi = cs["Profit"].idxmin()
    rec(f"Most resilient: <b>{cs.loc[bi, 'Scenario']}</b>; hardest hit: <b>{cs.loc[wi, 'Scenario']}</b> "
        f"(profit {money(cs.loc[wi, 'Profit'] - cs.loc[bi, 'Profit'], SPU)} vs best). Use <i>Compare scenarios</i> to see the optimised response for each.")
    show(paint(disp.drop(columns=["Key"]).style, good=[bi], bad=[wi]).format({"Profit": "{:,.1f}", "Total cost": "{:,.1f}", "Revenue": "{:,.1f}",
                                                  "Gas cost": "{:,.1f}", "Shortage": "{:,.2f}", "Fill rate": "{:.2%}"}
                                                 | {c_: "{:.2%}" for c_ in disp.columns if c_.startswith("Fill_")}))
    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(disp, x="Key", y=HEAD if HEAD in disp else "Profit", color="Expected side",
                     color_discrete_map={"Reference": "#59A14F", "Supplier": "#E15759", "MGL": "#4E79A7"},
                     title=f"{HEAD} by scenario ({mlab})", hover_name="Scenario")
        chart(fig)
    with c2:
        fc = [c_ for c_ in cs.columns if c_.startswith("Fill_") and c_ != "Fill_Rate"]
        m = cs.melt(id_vars="Key", value_vars=fc)
        m["variable"] = m["variable"].str.replace("Fill_", "")
        fig = px.bar(m, x="Key", y="value", color="variable", barmode="group", color_discrete_map=SECTOR_COLORS,
                     title="Fill rate by sector and scenario")
        fig.update_yaxes(tickformat=".0%", range=[0.6, 1.01])
        chart(fig)
    st.subheader("Who created the scarcity? (diagnosis of all 5)")
    with st.spinner("Diagnosing all 5 scenarios …"):
        cd = c_compare_diag(work, p0)
    cd["Diagnosed"] = cd["Diagnosed"].map({"supplier": "🔴 Supplier-side", "mgl": "🔵 MGL-side", "both": "🟠 Both",
                                           "none": "🟢 No physical scarcity"})
    show(cd.drop(columns=["Key"]).style.format({"Physical shortage": "{:,.2f}", "Supplier": "{:,.2f}", "MGL procurement": "{:,.2f}",
                                                "MGL network": "{:,.2f}", "Supplier share": "{:.0%}"}))
    m = cd.melt(id_vars="Key", value_vars=["Supplier", "MGL procurement", "MGL network"])
    fig = px.bar(m, x="Key", y="value", color="variable", color_discrete_map=SIDE_COLORS,
                 title=f"Shortage attributed to supplier vs MGL ({UNIT_SHORT})")
    chart(fig, 340)


# ======================================================================================
# Page: Compare scenarios
# ======================================================================================
def short_title(k):
    t = E.SCENARIOS[k]["title"]
    return t.split(" (")[0]


def page_compare():
    st.title("🆚 Compare scenarios")
    st.caption("Click two or more cases. Each is solved as-is and with the optimised response (regulated profit maximisation "
               "with mitigation levers), at the service level you choose. Best value in each row = green, worst = red.")
    keys = st.pills("Cases to compare (click to select 2 or more)", list(E.SCENARIOS), selection_mode="multi",
                    default=["S1", "S2"], format_func=short_title)
    keys = [k for k in E.SCENARIOS if k in (keys or [])]
    c1, c2 = st.columns(2)
    sl = c1.selectbox("🎯 Service level for this comparison", SL_OPTS, index=SL_OPTS.index(fsel))
    opt = c2.toggle("Show optimised response (with mitigation levers)", value=True)
    if len(keys) < 2:
        st.warning("Select at least two cases to compare.")
        return
    p2 = dict(params, svc_all=None if sl.startswith("Tier") else float(sl[:-1]) / 100)
    with st.spinner(f"Solving and diagnosing {len(keys)} cases …"):
        cases = {k: c_case(work, p2, k, opt) for k in keys}
    rows, num, better = {}, {}, {}

    def add(metric, vals, nums=None, hib=None):
        rows[metric] = vals
        if nums is not None:
            num[metric] = nums
            better[metric] = hib

    cols = []
    for k, c in cases.items():
        cols.append(short_title(k))
    final = {k: (c["opt"] if (opt and c["opt"] is not None) else c["base"]) for k, c in cases.items()}
    ok = {k: r["status"] == "Optimal" for k, r in final.items()}
    S = {k: final[k]["summary"] for k in keys if ok[k]}
    if not S:
        st.error("No case could be solved.")
        return
    g = lambda k, f: S[k].get(f, np.nan) if k in S else np.nan  # noqa: E731
    add("Profit (EBITDA)", [money(g(k, "Profit"), SPU) for k in keys], [g(k, "Profit") for k in keys], True)
    if opt:
        gain = [(g(k, "Profit") - cases[k]["base"]["summary"]["Profit"]) if cases[k]["base"]["status"] == "Optimal" else np.nan for k in keys]
        add("Profit gain from optimisation", [money(x, SPU) for x in gain], gain, True)
    add("Revenue", [money(g(k, "Revenue"), SPU) for k in keys], [g(k, "Revenue") for k in keys], True)
    add("Gas purchase cost", [money(g(k, "Gas_Cost"), SPU) for k in keys], [g(k, "Gas_Cost") for k in keys], False)
    add("Mitigation cost", [money(g(k, "Mitigation_Cost"), SPU) for k in keys], [g(k, "Mitigation_Cost") for k in keys], False)
    add(f"Total shortage ({UNIT_SHORT})", [f"{g(k, 'Total_Shortage'):,.2f}" for k in keys], [g(k, "Total_Shortage") for k in keys], False)
    add("Fill rate – overall", [pct(g(k, "Fill_Rate")) for k in keys], [g(k, "Fill_Rate") for k in keys], True)
    for sec in ["PNG Households", "CNG Stations", "Commercial", "Industries"]:
        f = f"Fill_{sec}"
        if any(f in S[k] for k in S):
            add(f"Fill rate – {sec}", [pct(g(k, f)) for k in keys], [g(k, f) for k in keys], True)
    comp = {k: (E.compliance(final[k])["Status"].str.startswith("✅").all() if ok[k] else False) for k in keys}
    add("All regulatory floors met", ["✅ Yes" if comp[k] else "❌ No" for k in keys], [1.0 if comp[k] else 0.0 for k in keys], True)
    loss = {k: (", ".join(E.sector_pnl(final[k]).query("Margin < 0").Sector) or "none") if ok[k] else "–" for k in keys}
    add("Loss-making segments", [loss[k] for k in keys], [0.0 if loss[k] == "none" else 1.0 for k in keys], False)
    tops = {k: (shadow_summary(final[k]).iloc[0] if ok[k] else None) for k in keys}
    add("Top limit (shadow price)", [f"{t.Name}: ₹{t['Avg shadow (₹/SCM)']:.2f}/SCM" if t is not None else "–" for t in tops.values()])
    add("Scarcity created by", [VERDICT_TXT.get(cases[k]["diag"]["verdict"], "–") if cases[k]["diag"] else "–" for k in keys])
    if opt:
        add("Recommended plan", [cases[k]["rec"] or "–" for k in keys])
        mit = {k: (final[k]["mitigation"].groupby("Option").Volume.sum().sort_values(ascending=False) if ok[k] else pd.Series(dtype=float)) for k in keys}
        add("Main optimised actions", [", ".join(f"{o.split('(')[0].strip()} {v:,.1f}" for o, v in mit[k].head(2).items()) or "re-allocation only"
                                       for k in keys])
    T = pd.DataFrame(rows, index=cols).T
    N = pd.DataFrame(num, index=cols).T

    def colour(df):
        css = pd.DataFrame("", index=df.index, columns=df.columns)
        for m in N.index:
            v = N.loc[m].astype(float)
            if v.nunique() <= 1 or v.isna().all():
                continue
            best = v.idxmax() if better[m] else v.idxmin()
            worst = v.idxmin() if better[m] else v.idxmax()
            css.loc[m, best] = GREEN; css.loc[m, worst] = RED
        return css
    st.markdown("**Side-by-side results" + (" – optimised response**" if opt else " – as-is**"))
    st.dataframe(T.style.apply(colour, axis=None), width="stretch")

    # best case & reasons
    cand = [k for k in keys if ok[k] and comp[k]] or [k for k in keys if ok[k]]
    best = max(cand, key=lambda k: S[k]["Profit"])
    reason = (f"highest profit ({money(S[best]['Profit'], SPU)}) with "
              + ("all regulatory floors met" if comp[best] else "the fewest floor breaches")
              + f", domestic PNG at {pct(S[best].get('Fill_PNG Households', np.nan))} and shortage {S[best]['Total_Shortage']:,.2f} {UNIT_SHORT}")
    st.success(f"🏆 **Best optimised outcome: {short_title(best)}** – {reason}.")
    for k in keys:
        if not ok[k]:
            continue
        dgv = cases[k]["diag"]["verdict"] if cases[k]["diag"] else "none"
        b0 = cases[k]["base"]["summary"]
        txt = (f"<b>{short_title(k)}</b>: {VERDICT_TXT[dgv]}. ")
        if opt and cases[k]["opt"] is not None:
            txt += (f"{cases[k]['rec']} plan changes profit by {money(S[k]['Profit'] - b0['Profit'], SPU)} and shortage by "
                    f"{S[k]['Total_Shortage'] - b0['Total_Shortage']:+,.2f} {UNIT_SHORT} versus doing nothing"
                    + (f", using {mit[k].index[0].split('(')[0].strip().lower()}" if len(mit[k]) else "") + ". ")
        txt += ("Floors met." if comp[k] else "Floors breached – needs supply or capacity beyond the available levers.")
        rec(txt)

    c1, c2 = st.columns(2)
    with c1:
        bars = []
        for k in keys:
            if cases[k]["base"]["status"] == "Optimal":
                bars.append({"Case": short_title(k).split(" · ")[0], "Plan": "As-is", "Profit": cases[k]["base"]["summary"]["Profit"]})
            if opt and ok[k]:
                bars.append({"Case": short_title(k).split(" · ")[0], "Plan": "Optimised", "Profit": S[k]["Profit"]})
        bd = pd.DataFrame(bars); bd["Profit"] = to_money(bd["Profit"], SPU)
        fig = px.bar(bd, x="Case", y="Profit", color="Plan", barmode="group", title=f"Profit: as-is vs optimised ({money_unit(SPU)[0]})",
                     color_discrete_map={"As-is": "#9AA3B0", "Optimised": "#2ECC71"})
        chart(fig)
    with c2:
        fr = []
        for k in keys:
            if ok[k]:
                for sec_, v in final[k]["deliveries"].groupby("Sector").apply(lambda d: d.Delivered.sum() / d.Demand.sum()).items():
                    fr.append({"Case": short_title(k).split(" · ")[0], "Sector": sec_, "Fill": v})
        fig = px.bar(pd.DataFrame(fr), x="Case", y="Fill", color="Sector", barmode="group", color_discrete_map=SECTOR_COLORS,
                     title="Fill rate by sector")
        fig.update_yaxes(tickformat=".0%", range=[0.6, 1.01])
        chart(fig)
    ms = []
    for k in keys:
        if ok[k]:
            m = final[k]["deliveries"].groupby(["Month", "Label"], as_index=False).Shortage.sum()
            m["Case"] = short_title(k).split(" · ")[0]
            ms.append(m)
    md = pd.concat(ms).sort_values("Month")
    fig = px.line(md, x="Label", y="Shortage", color="Case", markers=True, title=f"Monthly shortage ({UNIT_SHORT})")
    chart(fig, 340)


# ======================================================================================
# Page: Future expansion & outlook
# ======================================================================================
def page_future():
    st.title("🚀 Future expansion of the CGD network & outlook")
    st.subheader("1 · Scalability options")
    ex = pd.DataFrame(C.EXPANSION, columns=["Option", "What", "Why (reason)", "Scenario it solves", "Time-frame"])
    R = c_solve(DATA, params)
    top_corr = None
    if R["status"] == "Optimal":
        t = shadow_summary(R)
        tc = t[t.Type == "Corridor capacity"]
        if len(tc) and tc["Avg shadow (₹/SCM)"].iloc[0] > 1e-6:
            top_corr = tc.iloc[0]
    good = [0] if top_corr is not None else [7]
    show(paint(ex.style, good=good))
    if top_corr is not None:
        rec(f"First expansion step: debottleneck <b>{top_corr.Name}</b> (avg shadow ₹{top_corr['Avg shadow (₹/SCM)']:.2f}/SCM, "
            f"binding {int(top_corr['Months binding'])} months in the current scenario); in parallel, CBG and LNG buffer reduce "
            "dependence on imported spot gas.")
    else:
        rec("No corridor is binding in the current scenario – prioritise supply diversification (CBG, term LNG) and "
            "control-tower digitalisation before pipeline augmentation.")

    st.subheader("2 · Price escalation – trend and 3-year forecast")
    P = C.PRICE_TABLE
    pt = pd.DataFrame({k: v for k, v in P.items() if k != "years"}, index=P["years"]).T
    show(pt.reset_index().rename(columns={"index": "Item"}).style.format({y: "{:,.2f}" for y in P["years"]}))
    for n_ in C.PRICE_NOTES:
        st.caption(n_)
    fig = go.Figure()
    yrs = P["years"]
    pal = {"MGL CNG Mumbai (₹/kg) – base": "#4E79A7", "MGL CNG Mumbai (₹/kg) – high": "#E15759",
           "MGL domestic PNG (₹/SCM)": "#F28E2B"}
    for k, colr in pal.items():
        v = P[k]
        fig.add_trace(go.Scatter(x=yrs[:3], y=v[:3], name=k + " (actual)", mode="lines+markers", line=dict(color=colr, width=3)))
        fig.add_trace(go.Scatter(x=yrs[2:], y=v[2:], name=k + " (forecast)", mode="lines+markers",
                                 line=dict(color=colr, width=2, dash="dash")))
    fig.add_trace(go.Scatter(x=yrs, y=P["APM ceiling ($/MMBtu)"], name="APM ceiling $/MMBtu (right axis)", yaxis="y2",
                             mode="lines+markers", line=dict(color="#59A14F", dash="dot")))
    fig.update_layout(title="Price trend (solid) and forecast (dashed)", yaxis=dict(title="₹"),
                      yaxis2=dict(title="$/MMBtu", overlaying="y", side="right"))
    chart(fig, 420)
    cng = P["MGL CNG Mumbai (₹/kg) – base"]
    rec(f"CNG has risen ₹{cng[2] - cng[0]:.0f}/kg in two years (+{(cng[2] / cng[0]) ** 0.5 - 1:.1%}/yr). Budget for "
        f"₹{cng[3]:.0f}–{P['MGL CNG Mumbai (₹/kg) – high'][3]:.0f}/kg in FY28; lock term gas and CBG now to stay on the base path.")

    st.subheader("3 · ⚠️ Uncertain changes observed")
    cols = st.columns(2)
    for i, (t, d) in enumerate(C.UNCERTAINTIES):
        with cols[i % 2]:
            st.markdown(f"<div style='border-left:6px solid #F1A208;background:rgba(241,162,8,0.10);padding:8px 12px;"
                        f"border-radius:6px;margin-bottom:10px'><b>{t}</b><br><span style='font-size:0.92em'>{d}</span></div>",
                        unsafe_allow_html=True)
    rec("Run scenarios S2 (APM cut) and S3 (LNG shock) every quarter; these are the uncertainties already observed.")

    st.subheader("4 · Demand–supply outlook – next 2 years")
    c1, c2, c3 = st.columns(3)
    g1 = c1.slider("Demand growth – year 1", 0.0, 0.20, 0.08, 0.005, format="%.3f", help="PL Capital forecast for MGL FY27: +8.0 %")
    g2 = c2.slider("Demand growth – year 2", 0.0, 0.20, 0.112, 0.005, format="%.3f", help="PL Capital forecast for MGL FY28: +11.2 %")
    apm = c3.slider("APM/NWG allocation decline per year", 0.0, 0.30, 0.05, 0.01)
    o = c_outlook(work, g1, g2, apm)
    tot, sup = o["total"], o["supply"]
    fig = px.area(sup, x="Label", y="Supply", color="Source", title=f"Contracted supply by source vs projected demand ({UNIT})",
                  category_orders={"Label": tot.Label.tolist()})
    fig.add_trace(go.Scatter(x=tot.Label, y=tot.Demand, name="Projected demand", mode="lines+markers",
                             line=dict(color="white", width=3, dash="dash")))
    fig.add_trace(go.Bar(x=tot.Label, y=tot.Gap, name="Gap – spot / new contracts needed", marker_color="rgba(225,87,89,0.55)"))
    chart(fig, 460)
    dm = o["demand"].pivot_table(index="Label", columns="Sector", values="Demand", sort=False).reset_index()
    fig = px.line(dm.melt(id_vars="Label", var_name="Sector", value_name="Demand"), x="Label", y="Demand", color="Sector",
                  color_discrete_map=SECTOR_COLORS, title=f"Projected gas consumption by sector ({UNIT})")
    chart(fig, 340)
    y1, y2 = tot.iloc[:12], tot.iloc[12:]
    per_day = (lambda v: v / 30.4) if SPU >= 1e5 else (lambda v: v)
    unit_d = "MMSCMD" if SPU >= 1e5 else UNIT
    rec(f"Average gap: <b>{per_day(y1.Gap.mean()):,.2f} {unit_d}</b> in year 1 ({y1.Gap.sum() / y1.Demand.sum():.0%} of demand) and "
        f"<b>{per_day(y2.Gap.mean()):,.2f} {unit_d}</b> in year 2 ({y2.Gap.sum() / y2.Demand.sum():.0%}). Contract this volume "
        "(term LNG, HP-HT, CBG) ahead of time; relying on spot exposes margin to JKM spikes.")
    st.caption("Method: last 12 months of the selected dataset × growth rates; contracted supply = last 12 months of contracts "
               "(APM/NWG reduced by the decline rate; spot excluded). Assumptions are adjustable above.")


# ======================================================================================
# Page: Terminology
# ======================================================================================
def page_terms():
    st.title("📖 Terminology")
    st.caption("Brief, plain-language meaning of the terms used in this project.")
    q = st.text_input("Search a term", "")
    for head, items in C.TERMS:
        st.subheader(head)
        df = pd.DataFrame(items, columns=["Term", "Meaning"])
        if q:
            df = df[df.Term.str.contains(q, case=False) | df.Meaning.str.contains(q, case=False)]
        show(df)


# ======================================================================================
# Page: Diagnosis & response
# ======================================================================================
def page_diagnosis():
    st.title("🔎 Scarcity diagnosis & optimised response")
    sc = E.SCENARIOS[scen]
    st.caption(f"Scenario: **{sc['title']}** (change it in the sidebar)")
    with st.spinner("Diagnosing root cause (5 LP solves) …"):
        dg = c_diag(DATA, params)
    st.session_state["last_diag"] = dg["table"].reset_index().rename(columns={"index": "Month"})
    t = dg["totals"]
    if dg["verdict"] == "supplier":
        st.error(f"### 🔴 SUPPLIER-SIDE SCARCITY\n{dg['supplier_share']:.0%} of the shortage comes from gas that suppliers "
                 "contracted but did not deliver (GAIL / LNG seller). MGL's network and contracts are not the main cause.")
    elif dg["verdict"] == "mgl":
        st.warning(f"### 🔵 MGL-SIDE SCARCITY – this is OUR problem\n{dg['mgl_share']:.0%} of the shortage is created inside MGL: "
                   f"network bottlenecks ({t['MGL network']:,.2f} {UNIT_SHORT}) and/or under-contracted gas "
                   f"({t['MGL procurement']:,.2f} {UNIT_SHORT}). Suppliers delivered what was contracted.")
    elif dg["verdict"] == "both":
        st.warning(f"### 🟠 MIXED SCARCITY\nSupplier {dg['supplier_share']:.0%} · MGL {dg['mgl_share']:.0%}. Both playbooks apply.")
    else:
        st.success("### 🟢 No physical scarcity – every customer can be served. Use the response plan below to maximise profit.")

    c = st.columns(4)
    c[0].metric(f"Physical shortage ({UNIT_SHORT})", f"{dg['total']:,.2f}")
    c[1].metric("Supplier-caused", f"{t['Supplier']:,.2f}")
    c[2].metric("MGL procurement-caused", f"{t['MGL procurement']:,.2f}")
    c[3].metric("MGL network-caused", f"{t['MGL network']:,.2f}")
    tab = dg["table"]
    c1, c2 = st.columns([3, 2])
    with c1:
        m = tab.reset_index().melt(id_vars=["Month", "Label"], value_vars=["Supplier", "MGL procurement", "MGL network"])
        fig = px.bar(m.sort_values("Month"), x="Label", y="value", color="variable", color_discrete_map=SIDE_COLORS,
                     title=f"Root cause of shortage by month ({UNIT_SHORT})")
        chart(fig)
    with c2:
        if dg["total"] > 1e-9:
            fig = px.pie(values=t.values, names=t.index, color=t.index, color_discrete_map=SIDE_COLORS, hole=0.45,
                         title="Share of shortage")
            chart(fig)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Supplier delivery shortfall vs contract**")
        if len(dg["short_by_src"]):
            show(dg["short_by_src"].rename("Shortfall").reset_index().rename(columns={"index": "Source – supplier"}))
        else:
            st.write("Suppliers delivered 100 % of contracted quantities.")
    with c2:
        st.markdown("**Network bottlenecks (max-service run)**")
        show(dg["corridors"].reset_index().style.format({"Peak_util": "{:.0%}"}))

    st.divider()
    st.header("🛠 Optimised response (regulated profit maximisation)")
    st.caption("Domestic PNG is kept at 100 %, and CNG and other tiers at their floors (90–95 %). Above the floors, the optimiser "
               "chooses the gas sources, routes and mitigation levers that add the most profit.")
    with st.spinner("Optimising response options …"):
        rp = c_response(DATA, params)
    opts = {"Do nothing new": rp["before"], "Profit-first (recommended)": rp["profit_first"],
            "Service-first": rp["service_first"]}
    rows = []
    for name, r in opts.items():
        if r["status"] != "Optimal":
            continue
        s = r["summary"]; comp = E.compliance(r)
        rows.append({"Option": name, "Profit": s["Profit"], "Mitigation cost": s["Mitigation_Cost"],
                     "Shortage": s["Total_Shortage"], "Fill rate": s["Fill_Rate"],
                     "Domestic PNG": s.get("Fill_PNG Households", np.nan), "CNG": s.get("Fill_CNG Stations", np.nan),
                     "Compliant": "✅" if (comp["Status"] == "✅ Compliant").all() else "❌",
                     "Loss segments": ", ".join(E.sector_pnl(r).query("Margin < 0").Sector) or "none"})
    ct = pd.DataFrame(rows)
    rec_name = "Profit-first (recommended)"
    if len(ct) and ct.set_index("Option").loc[rec_name, "Compliant"] != "✅":
        rec_name = "Service-first"
    ctd = ct.copy()
    ctd["Profit"] = to_money(ctd["Profit"], SPU); ctd["Mitigation cost"] = to_money(ctd["Mitigation cost"], SPU)
    show(paint(ctd.style, good=ctd.index[ctd.Option == rec_name], bad=ctd.index[ctd.Compliant != "✅"]).format(
        {"Profit": "{:,.2f}", "Mitigation cost": "{:,.2f}", "Shortage": "{:,.2f}", "Fill rate": "{:.2%}",
         "Domestic PNG": "{:.2%}", "CNG": "{:.2%}"}))
    rec(f"Adopt the <b>{rec_name.replace(' (recommended)', '')}</b> plan: it keeps every regulatory floor and gives the highest "
        "profit among compliant options.")
    best_r = opts[rec_name]
    b0 = rp["before"]["summary"]; b1 = best_r["summary"]
    c = st.columns(4)
    c[0].metric("Recommended plan", rec_name.replace(" (recommended)", ""))
    c[1].metric("Profit", money(b1["Profit"], SPU), delta=money(b1["Profit"] - b0["Profit"], SPU))
    c[2].metric(f"Shortage ({UNIT_SHORT})", f"{b1['Total_Shortage']:,.2f}", delta=f"{b1['Total_Shortage'] - b0['Total_Shortage']:,.2f}",
                delta_color="inverse")
    sf = rp["supplier_full"]["summary"]
    c[3].metric("Profit lost to supplier shortfall", money(sf["Profit"] - b0["Profit"], SPU),
                help="Profit if suppliers had delivered the full contract, minus profit today. Basis for a shortfall claim.")

    c1, c2 = st.columns(2)
    with c1:
        mt = best_r["mitigation"]
        if len(mt):
            g_ = mt.groupby(["Option", "Side"], as_index=False)[["Volume", "Cost"]].sum()
            g_["Cost"] = to_money(g_["Cost"], SPU)
            st.markdown(f"**Actions chosen ({UNIT_SHORT}, cost {money_unit(SPU)[0]})**")
            show(g_.style.format({"Volume": "{:,.2f}", "Cost": "{:,.2f}"}))
        else:
            st.info("No extra mitigation is profitable or needed. Re-allocation of existing gas and routes is enough.")
    with c2:
        d0 = rp["before"]["deliveries"].groupby("Sector").agg(D=("Demand", "sum"), B=("Delivered", "sum"))
        d1 = best_r["deliveries"].groupby("Sector").agg(A=("Delivered", "sum"))
        cmp_ = d0.join(d1).reset_index()
        cmp_["Before"] = cmp_.B / cmp_.D; cmp_["After"] = cmp_.A / cmp_.D
        m = cmp_.melt(id_vars="Sector", value_vars=["Before", "After"])
        fig = px.bar(m, x="Sector", y="value", color="variable", barmode="group", title="Fill rate by sector: before vs after")
        fig.update_yaxes(tickformat=".0%", range=[0.6, 1.01])
        chart(fig, 330)
    st.markdown("**Which sector gets gas first in scarcity months (recommended plan)**")
    dv = best_r["deliveries"]
    scarce = dg["table"][dg["table"].Total_shortage > 1e-9].index.tolist() or best_r["I"]["T"]
    pr = dv[dv.Month.isin(scarce)].groupby(["Tier", "Sector"], as_index=False).agg(Demand=("Demand", "sum"), Delivered=("Delivered", "sum"))
    pr["Fill"] = pr.Delivered / pr.Demand
    pr["Curtailment"] = 1 - pr.Fill
    show(pr.sort_values("Tier").style.format({"Demand": "{:,.2f}", "Delivered": "{:,.2f}", "Fill": "{:.1%}", "Curtailment": "{:.1%}"}))

    st.divider()
    sides = ["supplier"] if dg["verdict"] == "supplier" else ["mgl"] if dg["verdict"] == "mgl" else ["supplier", "mgl"]
    for sd in sides:
        st.subheader("📋 Supplier-side action plan" if sd == "supplier" else "📋 MGL-side action plan (our problem)")
        for i, (step, txt, ref) in enumerate(E.PLAYBOOK[sd], 1):
            st.markdown(f"**{i}. {step}.** {txt}  \n<span style='opacity:0.65;font-size:0.85em'>Basis: {ref}</span>",
                        unsafe_allow_html=True)
    if dg["verdict"] in ("mgl", "both"):
        sh = rp["before"]["shadow"]
        cs_ = sh[sh.Type == "Corridor capacity"].groupby("Item").Shadow_Price.agg(["mean", "max"]).sort_values("mean", ascending=False)
        if cs_["mean"].max() > 0:
            st.info(f"**Invest first in {cs_.index[0]}**: average shadow price ₹{cs_['mean'].iloc[0]:.2f}/SCM "
                    f"(max ₹{cs_['max'].iloc[0]:.2f}/SCM). Each extra SCM of capacity there adds the most profit.")


# ======================================================================================
# Page: Priority & regulations
# ======================================================================================
def page_priority():
    st.title("🏛 Priority of supply in scarcity & regulatory compliance")
    st.markdown("When gas is short, the order of supply is set by **Government policy and PNGRB regulations first** and by "
                "**profitability second**. The simulator applies it as follows:")
    show(pd.DataFrame(C.PRIORITY_TABLE, columns=["Priority", "Customer segment", "Service level in model", "Why (policy basis)",
                                                 "Action in scarcity"]))
    st.subheader("Rules built into the optimiser")
    for r in C.RULES:
        st.markdown(f"- {r}")
    st.subheader("Compliance check of the current plan")
    R = solve_now()
    need_ok(R)
    cp = E.compliance(R)
    show(paint(cp.style.format({"Floor": "{:.0%}", "Fill (period)": "{:.2%}", "Worst node-month": "{:.1%}"}),
               good=cp.index[cp.Status.str.startswith("✅")], bad=cp.index[cp.Status.str.startswith("❌")]))
    rec("All sectors meet their floors – the curtailment order is respected." if cp.Status.str.startswith("✅").all()
        else "Some floors are breached – enable mitigation levers or use the Diagnosis page's optimised plan.")
    dv = R["deliveries"]
    cut = dv.groupby(["Tier", "Sector"], as_index=False).agg(Shortage=("Shortage", "sum"), Demand=("Demand", "sum"))
    cut["Share of total curtailment"] = cut.Shortage / max(cut.Shortage.sum(), 1e-9)
    fig = px.bar(cut.sort_values("Tier"), x="Sector", y="Shortage", color="Sector", color_discrete_map=SECTOR_COLORS,
                 title=f"Who was curtailed in the current scenario ({UNIT_SHORT})")
    chart(fig, 320)
    st.caption("Expected pattern: industrial absorbs most of the curtailment, then commercial, then CNG down to its floor; domestic PNG ≈ 0.")


# ======================================================================================
# Page: References
# ======================================================================================
def page_refs():
    st.title("📚 References")
    st.markdown("**Project credits**")
    st.markdown(credits_html(), unsafe_allow_html=True)
    for head, items in C.REFERENCES:
        st.subheader(head)
        for name, url in items:
            st.markdown(f"- [{name}]({url})")
    st.subheader("Standard books & codes")
    for b in C.BOOKS:
        st.markdown(f"- {b}")
    st.info(C.DATA_NOTE)


# ======================================================================================
PAGE_FN = {PAGES[0]: page_home, PAGES[1]: page_model, PAGES[2]: page_simulator, PAGES[3]: page_scenarios,
           PAGES[4]: page_compare, PAGES[5]: page_diagnosis, PAGES[6]: page_priority, PAGES[7]: page_future,
           PAGES[8]: page_terms, PAGES[9]: page_refs}
PAGE_FN[page]()
st.sidebar.markdown("---")
st.sidebar.markdown(credits_html(compact=True), unsafe_allow_html=True)
st.sidebar.caption("Built with Streamlit · PuLP (CBC) · Plotly")
