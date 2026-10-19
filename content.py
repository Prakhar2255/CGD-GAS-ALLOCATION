"""Static text for the website pages: motivation, objectives, SDGs, regulations, references."""

MOTIVATION = """
India wants natural gas to grow from ~6 % to **15 % of its primary energy mix by 2030**, and City Gas
Distribution (CGD) is the fastest-growing consumer segment. For millions of households, auto-rickshaws, taxis
and buses, gas has become an essential service, not a luxury.

But **gas supply to CGD is not guaranteed**:

* **Domestic (APM) gas is declining.** In Oct–Nov 2024 the Government cut APM gas allocated to CGD for CNG by
  ~20 %. MGL's APM share fell from ~69 % of volumes to ~45 % (APM + NWG) and had to be replaced by costlier gas.
* **Imported LNG is volatile.** Geopolitical events (Europe 2022, West Asia 2026) delay cargoes and push
  spot prices up. MGL raised CNG prices citing spot RLNG costs.
* **Networks hit physical limits.** Demand in Mumbai, Thane and Raigad grows 7–10 % a year, and pipeline
  damage by third-party digging or CGS maintenance can cut throughput overnight.

When gas is scarce, a CGD company must decide in hours **who gets gas, from which source, through which route,
at what cost**. It must also stay within PNGRB / MoPNG priority rules and avoid running a segment at a loss.
Today this is mostly done with spreadsheets and experience. This project builds a **transparent, optimisation-based
decision-support simulator** for it.
"""

PROBLEM = """
Allocate the monthly gas available at the city gate(s) across CNG stations, domestic PNG nodes and
industrial/commercial customers over a 12- or 24-month horizon. The goal is to **minimise total delivered cost
plus shortage penalty** (problem-statement formulation), or to **maximise regulated profit** (extended
formulation). The allocation is subject to:

* source availability,
* node balance,
* corridor throughput capacity,
* regulatory priority-tier service floors, and
* eligibility of each gas source (e.g. APM gas only for CNG(T) and PNG(D)).

When scarcity occurs, the simulator also identifies **whether it was created by the supplier (e.g. GAIL) or
inside MGL** (procurement or network), and prescribes a regulation-compliant, profit-maximising response.
"""

OBJECTIVES = [
    ("Optimal monthly allocation",
     "Solve a 12/24-month linear programme (PuLP + CBC) that routes gas through the 5 corridors at least cost / "
     "highest margin."),
    ("Regulation-first priority",
     "Domestic PNG is non-curtailable (100 %), CNG(T) is held at a 90–95 % service floor, and only "
     "commercial and industrial loads are curtailed, in line with MoPNG/PNGRB."),
    ("Find the root cause of scarcity",
     "Separate supplier-side shortfall (GAIL / LNG seller) from MGL-side causes (under-contracting, network "
     "bottlenecks)."),
    ("Profit without loss",
     "Choose replacement gas, routes and mitigation levers that keep every segment's margin positive and "
     "maximise EBITDA."),
    ("Where to invest",
     "Use shadow prices to show the value of one more SCM of supply or corridor capacity, and so rank "
     "investments."),
    ("What-if analysis",
     "5 real-world scarcity scenarios, service-level sweep (70–95 %), tornado, one-way and two-way "
     "sensitivity, and an Excel export."),
]

SDGS = [
    (7, "Affordable and Clean Energy", "#FCC30B",
     "Reliable, affordable piped gas and CNG for households and transport (Target 7.1 universal access, 7.3 efficiency).",
     "https://sdgs.un.org/goals/goal7"),
    (11, "Sustainable Cities and Communities", "#FD9D24",
     "Clean public transport (CNG buses, taxis) and cleaner urban air in Mumbai MMR (Target 11.2, 11.6).",
     "https://sdgs.un.org/goals/goal11"),
    (13, "Climate Action", "#3F7E44",
     "Gas replaces diesel, petrol, LPG and coal and cuts CO₂ and particulates; optimal routing avoids flaring and waste (Target 13.2).",
     "https://sdgs.un.org/goals/goal13"),
    (9, "Industry, Innovation and Infrastructure", "#FD6925",
     "Resilient gas infrastructure; shadow prices guide where to augment the network (Target 9.1, 9.4).",
     "https://sdgs.un.org/goals/goal9"),
    (12, "Responsible Consumption and Production", "#BF8B2E",
     "Efficient use of scarce domestic gas: the right molecule to the right consumer (Target 12.2).",
     "https://sdgs.un.org/goals/goal12"),
    (3, "Good Health and Well-being", "#4C9F38",
     "Less indoor and urban air pollution from cleaner fuels (Target 3.9).",
     "https://sdgs.un.org/goals/goal3"),
]

PRIORITY_TABLE = [
    ("1", "Domestic PNG (households)", "Non-curtailable – 100 %",
     "Essential cooking fuel. MoPNG guidelines give PNG(D) first priority for domestic (APM) gas, meeting 100 % of "
     "requirement. MGL confirmed PNG kept 100 % APM allocation even after the Oct-2024 cuts.",
     "Never curtail. Serve from the cheapest eligible gas (APM) first."),
    ("2", "CNG – Transport (public & private vehicles)", "Floor 90–95 % (adjustable)",
     "Priority sector with domestic gas allocation. Public transport (buses, taxis, autos) depends on it. "
     "APM share was cut in 2024, so the balance is bought from costlier gas.",
     "Curtail only below the floor, after industry and commercial. Use virtual pipelines to protect stations."),
    ("3", "Commercial PNG (hospitals, hotels, eateries)", "Floor ~90 %",
     "Market-priced gas. Hospitals and crematoria are treated as essential within this group.",
     "Curtail after industry. Give notice under the customer contract."),
    ("4", "Industrial PNG", "Floor ~80 % (interruptible)",
     "Market-priced gas. Contracts usually allow interruption, and many plants have an alternate fuel.",
     "First to be curtailed in scarcity, with advance notice and pro-rata cuts across industrial customers."),
]

RULES = [
    "**Domestic PNG and CNG(T) first.** Domestic (APM/NWG) gas is allocated only to CNG(T) and PNG(D). The model "
    "enforces this through source **eligibility** and serves households from APM first (*PriorityTo*).",
    "**Market-priced gas for I&C.** Industrial and commercial customers are supplied from HP-HT, term RLNG or spot "
    "gas only, priced at market.",
    "**Curtailment order in scarcity:** Industrial → Commercial → CNG (down to its 90–95 % floor). Domestic PNG "
    "is never curtailed.",
    "**Safety first (T4S, IMS, ERDMP).** Line-pack / pressure uplift is limited to MAOP. Outages and "
    "emergencies follow the PNGRB ERDMP regulations.",
    "**Quality of Service.** PNGRB's Code of Practice for Quality of Service requires notice to customers and "
    "restoration within standard times. The service floors in the model represent these obligations.",
    "**Pricing.** CNG and I&C prices are market-determined, so higher gas cost can be passed through. Domestic "
    "PNG prices follow the APM price ceiling (Kirit Parikh formula, 2023). The model flags segments running at a loss.",
]

REFERENCES = [
    ("Regulator – PNGRB", [
        ("PNGRB – CGD regulations (index of all CGD regulations)", "https://pngrb.gov.in/eng-web/regulation-cgd.html"),
        ("PNGRB T4S – Technical Standards & Specifications incl. Safety Standards for CGD Networks (post-amendment, Dec-2025)",
         "https://pngrb.gov.in/OurRegulation/PNGRB%20Regulations/A.%20CGD%20Network/A.4.%20CGD%20T4S%20Regulations/20251217-CGD-T4S-Post-Amendment.pdf"),
        ("PNGRB CGD Authorisation Regulations, 2008 (as amended)",
         "https://pngrb.gov.in/OurRegulation/PNGRB%20Regulations/A.%20CGD%20Network/A.1.%20CGD%20Authorization%20Regulations/20250917-CGD-Auth-Post-Amendment.pdf"),
        ("PNGRB Code of Practice for Quality of Service for CGD Networks, 2010",
         "https://pngrb.gov.in/OurRegulation/PNGRB%20Regulations/A.%20CGD%20Network/A.5.%20CGD%20Service%20Regulations/CGD%20Service-Post%20Amendment-15.03.2018.pdf"),
        ("PNGRB Integrity Management System (IMS) for CGD Networks",
         "https://pngrb.gov.in/OurRegulation/PNGRB%20Regulations/A.%20CGD%20Network/A.7.%20CGD%20IMS%20Regulations/20250723-CGD-IMS-Post-Amendment.pdf"),
        ("PNGRB Determining Capacity of CGD Networks, 2015",
         "https://pngrb.gov.in/OurRegulation/PNGRB%20Regulations/A.%20CGD%20Network/A.8.%20CGD%20Capacity%20Determination%20Regulations/CGD%20Capacity-Post%20Amendment-30.09.2020.pdf"),
        ("PNGRB Access Code for CGD Networks, 2020",
         "https://pngrb.gov.in/OurRegulation/PNGRB%20Regulations/A.%20CGD%20Network/A.6.%20CGD%20Access%20Code%20Regulations/CGD%20Access%20Code-Original%20Reg-23.11.2020.pdf"),
        ("PNGRB Transportation Rate for CGD & CNG, 2020",
         "https://pngrb.gov.in/OurRegulation/PNGRB%20Regulations/A.%20CGD%20Network/A.2.%20CGD%20Tariff%20Regulations/CGD%20Tariff-Original%20Reg-23.11.2020.pdf"),
        ("PNGRB Emergency Response & Disaster Management Plan (ERDMP)", "https://pngrb.gov.in/eng-web/erdmp.html"),
    ]),
    ("Government policy – MoPNG / PPAC", [
        ("MoPNG – Natural gas policies & guidelines (CNG(T)/PNG(D) priority, allocation)",
         "https://mopng.gov.in/en/natural-gas/policies-guidelines"),
        ("PPAC – Petroleum Planning & Analysis Cell (gas data, allocation)", "https://ppac.gov.in/"),
        ("IEA – India Revised Domestic Gas Pricing (APM ceiling, 2023)", "https://www.iea.org/policies/17412-revised-domestic-gas-pricing"),
        ("CRISIL – Lower APM allocation to raise cost of city gas companies (Oct-2024)",
         "https://www.crisilratings.com/en/home/newsroom/press-releases/2024/10/lower-apm-allocation-to-raise-cost-of-city-gas-cos-by-rs-2-3-kg.html"),
    ]),
    ("Company data – Mahanagar Gas Ltd (input data)", [
        ("MGL Reg-30 disclosure – APM allocation cut (17-Oct-2024)",
         "https://nsearchives.nseindia.com/corporate/MGL_17102024180628_Reg30APMAllocationSigned17102024.pdf"),
        ("MGL Q2 FY25 earnings call (APM share, allocation)",
         "https://nsearchives.nseindia.com/corporate/MGL_30102024172114_EarningsConCall30102024Signed.pdf"),
        ("MGL Investor presentation Q2 FY26 (segment volumes, prices, network)",
         "https://nsearchives.nseindia.com/corporate/MGL25_30102025145644_InvestorPresentation30102025.pdf"),
        ("MGL Q3 FY26 earnings call transcript (sourcing mix, EBITDA/SCM)",
         "https://nsearchives.nseindia.com/corporate/MGL25_16022026122912_EarningCallTranscriptQ3FY26.pdf"),
        ("MGL Q1 FY27 volumes (Indian Chemical News)",
         "https://www.indianchemicalnews.com/gas/mahanagar-gas-posts-sharp-q1-recovery-as-cng-domestic-png-volumes-drive-growth-31336"),
        ("MGL CNG/PNG price revision Sep-2026 (Business Today)",
         "https://www.businesstoday.in/amp/latest/story/mgl-hikes-cng-png-prices-in-mumbai-from-september-1-check-revised-rates-552419-2026-08-31"),
        ("MGL CNG/PNG price revision May-2026 (Free Press Journal)",
         "https://www.freepressjournal.in/mumbai/mumbai-cng-price-hike-from-may-30-mgl-raises-rates-to-86-per-kg-png-at-52-per-scm"),
    ]),
    ("Sustainability & methods", [
        ("UN Sustainable Development Goals", "https://sdgs.un.org/goals"),
        ("PuLP – linear programming in Python (COIN-OR)", "https://coin-or.github.io/pulp/"),
        ("Streamlit Community Cloud – deploy guide", "https://docs.streamlit.io/deploy/streamlit-community-cloud"),
    ]),
]

BOOKS = [
    "Hillier, F. S. & Lieberman, G. J. – *Introduction to Operations Research* (LP, duality and shadow prices, sensitivity analysis).",
    "Winston, W. L. – *Operations Research: Applications and Algorithms* (network-flow and multi-period models).",
    "Mokhatab, S., Poe, W. A. & Mak, J. Y. – *Handbook of Natural Gas Transmission and Processing* (gas networks, line-pack).",
    "ASME B31.8 – *Gas Transmission and Distribution Piping Systems* (design basis referred to by PNGRB T4S).",
]

DATA_NOTE = """
**About the MGL input data.** Segment volumes (CNG, domestic PNG, industrial and commercial) are the
**quarterly average sales volumes reported by MGL** (incl. erstwhile UEPL), from Q2 FY25 (Jul-2024) to
Q1 FY27 (Jun-2026), converted to MMSCM per month. MGL does not publish zone-wise or monthly volumes,
contract quantities, landed gas costs or pipeline capacities. These are **modelled assumptions**, calibrated so
the base case reproduces MGL's reported ~₹9–10/SCM EBITDA and its sourcing mix (APM+NWG ≈ 45 %).
Replace them with internal data via *Upload Excel* for decision use.
"""
