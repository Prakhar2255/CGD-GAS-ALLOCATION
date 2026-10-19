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

st.set_page_config(page_title="CGD Gas Allocation – LP Simulator", page_icon="⛽", layout="wide")

SECTOR_COLORS = {"PNG Households": "#F28E2B", "CNG Stations": "#4E79A7", "Commercial": "#B07AA1",
                 "Industries": "#59A14F"}
SIDE_COLORS = {"Supplier": "#E15759", "MGL procurement": "#F1CE63", "MGL network": "#4E79A7"}
PAGES = ["🏠 Home", "🧮 Model & formulation", "⚙️ Simulator", "🧪 Scenarios (5)",
         "🔎 Scarcity diagnosis & response", "🏛 Priority & regulations", "📚 References"]
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


# ======================================================================================
# Sidebar – navigation, data, scenario and levers (same structure as the earlier dashboard)
# ======================================================================================
st.sidebar.markdown("## ⛽ CGD Gas Allocation")
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
floor_opts = ["Off - use tier floors", "70%", "75%", "80%", "85%", "90%", "95%"]
fsel = st.sidebar.selectbox("Uniform service floor (all curtailable nodes)", floor_opts, index=0)
lv["svc_all"] = None if fsel.startswith("Off") else float(fsel[:-1]) / 100
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
def page_home():
    st.title("⛽ Gas Allocation in City Gas Distribution under Scarcity")
    st.markdown("##### An LP-based website & simulator (PuLP) — Mahanagar Gas Ltd (MGL), Mumbai MMR · 5-corridor network · 24-month data")
    a, b = st.columns([3, 2])
    with a:
        st.subheader("1 · Motivation")
        st.markdown(C.MOTIVATION)
    with b:
        st.subheader("At a glance (base case)")
        R = c_solve(E.apply_scenario(work, "S1"), E.default_params(S_.get("default_objective", "profit")))
        if R["status"] == "Optimal":
            s = R["summary"]
            x1, x2 = st.columns(2)
            x1.metric("Demand over horizon", f"{s['Total_Demand']:,.0f} {UNIT_SHORT}")
            x2.metric("Fill rate", pct(s["Fill_Rate"]))
            x1.metric("Profit (EBITDA)", money(s["Profit"], SPU))
            x2.metric("EBITDA / SCM", f"₹{s['Profit'] / max(1e-9, s['Total_Demand'] - s['Total_Shortage']):.2f}")
            dd = R["deliveries"].groupby(["Label", "Month", "Sector"], as_index=False).Demand.sum().sort_values("Month")
            fig = px.area(dd, x="Label", y="Demand", color="Sector", color_discrete_map=SECTOR_COLORS,
                          title=f"Demand by sector ({UNIT})")
            chart(fig, 300)
    st.subheader("2 · Problem statement")
    st.markdown(C.PROBLEM)
    st.subheader("3 · Objectives of the project")
    cols = st.columns(3)
    for i, (t, d) in enumerate(C.OBJECTIVES):
        with cols[i % 3]:
            st.markdown(f"**{i + 1}. {t}**  \n{d}")
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
1. **Simulator** – edit the inputs, move the sidebar levers, and see allocation, network flows, corridors, shadow prices, service levels and sensitivity. Export everything to Excel.
2. **Scenarios (5)** – compare five real CGD scarcity situations side by side.
3. **Scarcity diagnosis & response** – find out whether a shortage comes from the **supplier (GAIL / LNG seller)** or from **MGL itself**, and get the optimised, regulation-compliant, profit-maximising response.
4. **Priority & regulations** – the curtailment order (domestic PNG is never cut) and a compliance check of the current plan.
5. **References** – PNGRB (incl. T4S), MoPNG, MGL disclosures, SDGs and standard books.
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


# ======================================================================================
# Page: Simulator (all earlier tabs + profitability)
# ======================================================================================
def network_figure(R, month, mitig=True):
    I = R["I"]
    pos = {"G": (0.0, 0.45), "A": (1.3, 1.0), "B": (2.6, 1.0), "P1": (1.3, 0.62), "P2": (1.3, 0.38),
           "P3": (2.6, 0.62), "P4": (2.6, 0.38), "I1": (1.3, 0.02), "I2": (2.6, 0.02)}
    nodes = ["G"] + I["N"]
    extra = [n for n in nodes if n not in pos]
    for i, n in enumerate(extra):
        pos[n] = (3.6, 1.0 - 0.2 * i)
    fl = R["flows"]; ut = R["util"]; dv = R["deliveries"]
    if month == "avg":
        f = fl.groupby(["Arc", "Corridor", "From", "To"], as_index=False).Flow.mean()
        u = ut.groupby("Corridor").Utilization.mean().to_dict()
        d = dv.groupby("Node", as_index=False)[["Demand", "Delivered"]].mean()
    else:
        f = fl[fl.Month == month]; u = ut[ut.Month == month].set_index("Corridor").Utilization.to_dict()
        d = dv[dv.Month == month]
    fig = go.Figure()
    fmax = max(1e-9, f.Flow.max())
    for r in f.itertuples():
        if r.From not in pos or r.To not in pos:
            continue
        x0, y0 = pos[r.From]; x1, y1 = pos[r.To]
        ui = float(u.get(r.Corridor, 0))
        col = f"rgb({int(60 + 195 * min(1, ui))},{int(190 - 150 * min(1, ui))},70)"
        w = 1 + 9 * r.Flow / fmax
        fig.add_annotation(x=x1 - 0.13, y=y1, ax=x0 + 0.13, ay=y0, xref="x", yref="y", axref="x", ayref="y",
                           showarrow=True, arrowhead=3, arrowsize=0.6, arrowwidth=w, arrowcolor=col, opacity=0.9)
        fig.add_annotation(x=(x0 + x1) / 2, y=(y0 + y1) / 2 + 0.035, showarrow=False,
                           text=f"C{r.Corridor} · {r.Flow:,.1f} · {ui:.0%}", font=dict(size=11, color=col),
                           bgcolor="rgba(20,20,20,0.75)")
    if mitig and len(R["mitigation"]):
        m = R["mitigation"] if month == "avg" else R["mitigation"][R["mitigation"].Month == month]
        mv = m[m.Where.str.startswith("Node")].groupby("Where").Volume.sum()
        for where, vol in mv.items():
            n = where.split()[-1]
            if n in pos:
                x1, y1 = pos[n]
                fig.add_trace(go.Scatter(x=[0.0, x1], y=[0.45 - 0.08, y1 - 0.06], mode="lines",
                                         line=dict(dash="dot", width=2, color="#EDC948"),
                                         name=f"Virtual pipeline → {n}: {vol:,.2f}", hoverinfo="name"))
    dmap = d.set_index("Node")
    for n in nodes:
        x, y = pos[n]
        if n == "G":
            txt = "<b>City Gate</b><br>(CGS – GAIL)"
            colr = "#2E7D32"
        else:
            de, dl = float(dmap.loc[n, "Demand"]), float(dmap.loc[n, "Delivered"])
            fr = dl / de if de else 1
            colr = "#2E7D32" if fr >= 0.999 else ("#F9A825" if fr >= 0.9 else "#C62828")
            txt = f"<b>{n}</b> · {I['sector'][n]}<br>{dl:,.1f}/{de:,.1f} ({fr:.0%})"
        fig.add_annotation(x=x, y=y, text=txt, showarrow=False, font=dict(size=11, color="white"),
                           bgcolor=colr, bordercolor="white", borderwidth=1, borderpad=6)
    fig.update_xaxes(visible=False, range=[-0.35, 3.0 if not extra else 4.0])
    fig.update_yaxes(visible=False, range=[-0.15, 1.15])
    fig.update_layout(height=560, title="Line width = flow · colour = corridor utilisation (green→red) · "
                                        "box = delivered/demand (green ≥100 %, amber ≥90 %, red <90 %)",
                      showlegend=True, legend=dict(orientation="h", y=-0.05))
    return fig


def page_simulator():
    st.title("⛽ Gas Allocation over Months — LP Dashboard (PuLP)")
    sc = E.SCENARIOS[scen]
    st.caption(f"Scenario: **{sc['title']}** · Objective: **{'max regulated profit' if objective == 'profit' else 'min cost (problem statement)'}** · "
               f"Mitigation levers: **{'on' if params['mitigation'] else 'off'}**")
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
        show(E.compliance(R).style.format({"Floor": "{:.0%}", "Fill (period)": "{:.2%}", "Worst node-month": "{:.1%}"}))
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
        show(sp_disp.style.format({"Volume": "{:,.2f}", "Revenue": "{:,.2f}", "Gas_Cost": "{:,.2f}", "Network_Cost": "{:,.2f}",
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
        st.plotly_chart(network_figure(R, mo), width="stretch")
        st.caption("Network as in the problem statement: City Gate → C1 → CNG A → C2 → CNG B; City Gate → C3 → PNG P1,P2 → C4 → "
                   "PNG P3,P4; City Gate → C5 → Industrial I1 / Commercial I2. Dotted yellow lines = virtual-pipeline deliveries.")

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
        for col_ in ["Est. objective gain (linear)", "Actual objective gain (re-solve)", "Change in profit", "Change in total cost"]:
            si_disp[col_] = to_money(si_disp[col_], SPU)
        show(si_disp.style.format({c_: "{:,.2f}" for c_ in si_disp.columns if c_ not in ("Constraint", "Months binding")}
                                  | {"Avg util": "{:.1%}", "Peak util": "{:.1%}"}, na_rep="–"))
        st.markdown(f"**Demand alteration – {alt:+.0%} demand at each node**")
        st.caption("Marginal profit = extra profit per extra SCM demanded. Nodes behind a bottleneck corridor, or served from expensive "
                   "spot gas, earn the least (or lose).")
        di = c_demand_impact(DATA, params, alt)
        di_disp = di.copy()
        for col_ in ["Change in objective", "Change in real cost (gas+network)", "Change in profit"]:
            di_disp[col_] = to_money(di_disp[col_], SPU)
        show(di_disp.style.format({c_: "{:,.2f}" for c_ in di_disp.columns if c_ not in ("Node", "Sector")}
                                  | {"Extra served (share)": "{:.0%}"}, na_rep="–"))
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
        disp = sv.copy()
        for col_ in ["Objective", "Total cost", "Profit", "Transport", "Gas cost", "Shortage penalty", "Objective vs previous"]:
            if col_ in disp:
                disp[col_] = to_money(disp[col_], SPU)
        show(disp.style.format({c_: "{:,.2f}" for c_ in disp.columns if c_ not in ("Feasible",)}
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
    show(disp.drop(columns=["Key"]).style.format({"Profit": "{:,.1f}", "Total cost": "{:,.1f}", "Revenue": "{:,.1f}",
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
    show(ctd.style.format({"Profit": "{:,.2f}", "Mitigation cost": "{:,.2f}", "Shortage": "{:,.2f}", "Fill rate": "{:.2%}",
                           "Domestic PNG": "{:.2%}", "CNG": "{:.2%}"}))
    rec = opts[rec_name]
    b0 = rp["before"]["summary"]; b1 = rec["summary"]
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
        mt = rec["mitigation"]
        if len(mt):
            g_ = mt.groupby(["Option", "Side"], as_index=False)[["Volume", "Cost"]].sum()
            g_["Cost"] = to_money(g_["Cost"], SPU)
            st.markdown(f"**Actions chosen ({UNIT_SHORT}, cost {money_unit(SPU)[0]})**")
            show(g_.style.format({"Volume": "{:,.2f}", "Cost": "{:,.2f}"}))
        else:
            st.info("No extra mitigation is profitable or needed. Re-allocation of existing gas and routes is enough.")
    with c2:
        d0 = rp["before"]["deliveries"].groupby("Sector").agg(D=("Demand", "sum"), B=("Delivered", "sum"))
        d1 = rec["deliveries"].groupby("Sector").agg(A=("Delivered", "sum"))
        cmp_ = d0.join(d1).reset_index()
        cmp_["Before"] = cmp_.B / cmp_.D; cmp_["After"] = cmp_.A / cmp_.D
        m = cmp_.melt(id_vars="Sector", value_vars=["Before", "After"])
        fig = px.bar(m, x="Sector", y="value", color="variable", barmode="group", title="Fill rate by sector: before vs after")
        fig.update_yaxes(tickformat=".0%", range=[0.6, 1.01])
        chart(fig, 330)
    st.markdown("**Which sector gets gas first in scarcity months (recommended plan)**")
    dv = rec["deliveries"]
    scarce = dg["table"][dg["table"].Total_shortage > 1e-9].index.tolist() or rec["I"]["T"]
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
    show(E.compliance(R).style.format({"Floor": "{:.0%}", "Fill (period)": "{:.2%}", "Worst node-month": "{:.1%}"}))
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
           PAGES[4]: page_diagnosis, PAGES[5]: page_priority, PAGES[6]: page_refs}
PAGE_FN[page]()
st.sidebar.caption("Built with Streamlit · PuLP (CBC) · Plotly")
