# ⛽ GAS-OPTIC
**A Demand- and Supply-Scarcity-Based Optimization Decision Support System Control Tower for Gas Allocation in City Gas Distribution**  
*Gas Allocation and Supply Optimization through Intelligent Control Tower*

FDP Course: Decision Science for Enterprise Excellence (DSEE) · Organiser: Indian Foundation for Quality Management (IFQM), Bengaluru  
Authors: Dr Sandeep Sharda and Dr Pradeep Behera, Assistant Professors, Symbiosis Institute of Operations Management, Nashik · Supervisor cum Mentor: Dr Nitin Sachdeva, IFQM


A Streamlit website and simulator for allocating natural gas across a City Gas Distribution (CGD) network
(Mahanagar Gas Ltd, Mumbai MMR) when supply is scarce. The optimisation is a linear programme solved with **PuLP (CBC)**.

## What is inside

| Page | Contents |
|---|---|
| 🏠 Home | Title & credits; Motivation (background, opportunity, business case from the project PPT); problem statement (platform + ours); objectives incl. shadow prices and per-scenario output buttons; SDGs; how to use |
| 🧮 Model & formulation | Index sets, parameters, objective (problem-statement min-cost + extended regulated profit-max), constraints, diagnosis method, poster |
| ⚙️ Simulator | Same tabs as the earlier dashboard – **Inputs, Results, Network diagram, Corridors, Shadow prices, Service level (70–95 %), Sensitivity, Export** – plus a new **Profitability** tab |
| 🧪 Scenarios (5) | Five real CGD scarcity scenarios, compared side by side, with automatic root-cause diagnosis |
| 🆚 Compare scenarios | Pick 2+ cases, choose a service level; as-is vs optimised results, best/worst highlighted, reasons |
| 🔎 Scarcity diagnosis & response | Supplier-side vs MGL-side verdict, optimised profit-maximising and regulation-compliant response, action plan |
| 🏛 Priority & regulations | Curtailment order (domestic PNG never cut), rules built into the model, compliance check |
| 🚀 Future expansion & outlook | Scalability options, price escalation trend & 3-year forecast, uncertainties, 2-year demand–supply outlook |
| 📖 Terminology | Plain-language glossary of gas, regulatory and model terms |
| 📚 References | PNGRB (incl. T4S, QoS, IMS, ERDMP), MoPNG/PPAC, MGL disclosures, SDGs, standard books |

**Data sources (sidebar):**
- MGL 24-month data (Jul-2024 – Jun-2026)
- the original problem-statement data
- the earlier "corridors bind" demo data
- **Upload Excel**: use the template from the sidebar or `data/cgd_sample_data_template.xlsx`. Workbooks from the earlier dashboard are also accepted.

## Files

```
app.py                     Streamlit website (all pages)
engine.py                  PuLP model, scenarios, diagnosis, sensitivity
data.py                    built-in datasets, Excel template / upload
content.py                 text: motivation, SDGs, regulations, references
requirements.txt           Python packages
.streamlit/config.toml     dark theme (same look as before)
assets/problem_statement.jpg
data/*.xlsx                sample input workbooks
```

## Run on your computer

```bash
pip install -r requirements.txt
streamlit run app.py
```
It opens at http://localhost:8501.

## Deploy on Streamlit Community Cloud (free)

### Option A – keep your existing link (recommended)
Your current app (`cgd-gas-allocation-…streamlit.app`) is already linked to a GitHub repository.
1. Sign in at **https://share.streamlit.io** with the account that deployed the old app.
2. Find the app, click **⋮ → Settings**. It shows the GitHub repository, branch and main file (e.g. `app.py`).
3. Open that repository on GitHub. Click **Add file → Upload files** and drag in **all files and folders from this
   project** (`app.py`, `engine.py`, `data.py`, `content.py`, `requirements.txt`, `.streamlit/`, `assets/`, `data/`).
   Allow it to replace the old files. Then click **Commit changes**.
   - If the old main file had another name (e.g. `streamlit_app.py`), either rename this `app.py` to that name, or change
     *Main file path* in the app settings to `app.py`.
   - `.streamlit` is a hidden folder. If drag-and-drop skips it, create the file on GitHub via
     **Add file → Create new file**, name it `.streamlit/config.toml` and paste its contents.
4. Streamlit redeploys automatically within 1–3 minutes. The same URL now shows the new website.

### Option B – new app
1. Create a GitHub account and a new **public** repository (e.g. `cgd-gas-allocation-v2`).
2. Upload all project files as in A-3 and commit.
3. Go to **https://share.streamlit.io → Create app → Deploy a public app from GitHub**.
4. Select the repository and branch `main`, and set *Main file path* to `app.py`.
   Optionally, under *Advanced settings*, pick Python 3.12 and choose a custom sub-domain.
5. Click **Deploy**. The first build installs PuLP, Plotly and the other packages, which takes about 2–4 minutes.

### Troubleshooting
- **"ModuleNotFoundError"**: make sure `requirements.txt` is in the repository root.
- **Solver error**: `pulp==2.9.0` ships the CBC solver for Linux, so no extra installation is needed.
- **App sleeps after inactivity**: this is normal on the free tier. Click "Yes, get this app back up".
- The first page load runs about 25 LP solves for shadow prices, sensitivity and the service-level sweep, so it takes a few
  seconds. After that, results are cached.

## Data note
MGL segment volumes are the quarterly averages MGL reported (MMSCMD × days). Zone split, contracts, landed gas
costs, prices net of taxes, and corridor capacities are modelled assumptions, calibrated to MGL's reported EBITDA/SCM
(~₹9–10) and sourcing mix. Replace them with company data via *Upload Excel* before using the model for decisions.
