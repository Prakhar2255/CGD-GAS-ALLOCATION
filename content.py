"""Static text for the website pages: motivation, objectives, SDGs, regulations, references."""

TITLE = "GAS-OPTIC"
SUBTITLE = ("A Demand- and Supply-Scarcity-Based Optimization Decision Support System Control Tower "
            "for Gas Allocation in City Gas Distribution")
ACRONYM_HTML = ("<b>G</b>as <b>A</b>llocation and <b>S</b>upply <b>O</b>ptimization <b>T</b>hrough "
                "<b>I</b>ntelligent <b>C</b>ontrol Tower")

CREDITS = {
    "FDP Course": "Decision Science for Enterprise Excellence (DSEE)",
    "Organiser": "Indian Foundation for Quality Management (IFQM), Bengaluru",
    "Authors": ["Dr Sandeep Sharda, Assistant Professor, Symbiosis Institute of Operations Management, Nashik",
                "Dr Pradeep Behera, Assistant Professor, Symbiosis Institute of Operations Management, Nashik"],
    "Supervisor cum Mentor": "Dr Nitin Sachdeva, IFQM",
}

# ---- 1 · Motivation (content from the project PPT: Background, Opportunity, Business case)
MOTIVATION_TILES = [
    ("16,420 km", "GAIL gas pipeline network, FY 2024-25"),
    ("127 MMSCMD", "Gas moved by GAIL in FY 2024-25, a record"),
    ("41.4 MMSCMD", "India city-gas use, 21 % of total gas"),
    ("~20 %", "APM gas cut for CNG, 16 Oct 2024"),
]
MOTIVATION_BACKGROUND = """
**Background of the situation**
* GAIL (India) Ltd runs a 16,420 km gas pipeline network and moved a record 127 MMSCMD in FY 2024-25.
* City gas firms such as IGL and MGL (GAIL holds about 23 % and 33 %) take gas at the city gate to CNG stations,
  PNG homes and industry.
* GAIL allocates the scarce APM gas: cut about 20 % on 16 Oct 2024, and again in Nov 2024 and Apr 2025.
* Priority tiers: domestic PNG and CNG first, industry and commercial last. City gas uses 41.4 MMSCMD, 21 % of India's gas.
* Balancing cost, capacity and priority by hand each month is hard, so a transparent optimisation model is needed.
"""
MOTIVATION_OPPORTUNITY = """
**Opportunity**

GAIL moved a record 127 MMSCMD over a 16,420 km network in FY 2024-25, and city gas is 21 % of India's gas use,
growing about 15 % a year to 2030. A 12-month optimisation model can lower delivered cost, protect the priority
tiers and show, through shadow prices, where extra gas or corridor capacity pays back most.
"""
BUSINESS_TILES = [
    ("~20 %", "Cut in cheap APM gas to IGL and MGL for CNG, year on year"),
    ("₹3.5–4.5/kg", "Rise in CNG input-gas cost after the cut (CRISIL, Oct 2024)"),
    ("15 %", "Share of projected CGD demand met by domestic gas, Q3 FY25 (MoPNG)"),
    ("~90 %", "Service-level allocation"),
]
BUSINESS_WHY = [
    ("Lower delivered cost", "The model minimises transport plus shortage penalty over all months."),
    ("Regulatory compliance", "Floors for domestic PNG, CNG and industry follow MoPNG's priority for domestic PNG and CNG."),
    ("Smarter investment", "Shadow prices show whether extra CGD supply or corridor capacity pays back."),
]
MOTIVATION_SRC = ("Sources (as in project PPT): GAIL Investor Presentation FY2024-25; Business Standard (APM cuts 16 Oct 2024, "
                  "16 Nov 2024, 16 Apr 2025); PNGRB study cited by GAIL; CRISIL (Oct 2024); MoPNG via PSU Watch.")

# ---- 2 · Problem statement (platform statement verbatim + our project statement)
PROBLEM_PLATFORM = (
    "GAIL is the nodal agency for domestic gas allocation to city gas distributors. IGL and MGL cut CNG gas supply by "
    "about 20% on 16 Oct 2024 and again in Nov 2024 and Apr 2025, so gas at the city gate no longer meets priority "
    "demand. Allocating the scarce gas to PNG households, CNG stations and industry within corridor limits is still "
    "done by hand each month.")

MOTIVATION = """
**Why this matters now**
* **Domestic (APM) gas is declining:** MGL's APM share fell from ~69 % to ~45 % (APM + NWG) and had to be replaced by costlier gas.
* **Imported LNG is volatile:** geopolitical events (Europe 2022, West Asia 2026) delay cargoes and push spot prices up.
* **Networks hit physical limits:** demand in Mumbai, Thane and Raigad grows 7–10 % a year; pipeline damage or CGS
  maintenance can cut throughput overnight.
"""

PROBLEM = """
Allocate the monthly gas available at the city gate(s) across CNG stations, domestic PNG nodes and
industrial/commercial customers over a 12- or 24-month horizon. The goal is to **minimise total delivered cost plus
shortage penalty** (problem-statement formulation), or to **maximise regulated profit** (extended formulation).
The allocation is subject to source availability, node balance, corridor throughput capacity, regulatory
priority-tier service floors, and eligibility of each gas source (e.g. APM gas only for CNG(T) and PNG(D)).

When scarcity occurs, the simulator also identifies **whether it was created by the supplier (e.g. GAIL) or inside
MGL** (procurement or network), and prescribes a regulation-compliant, profit-maximising response.
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
    ("Project PPT sources & market outlook", [
        ("GAIL Investor Presentation FY2024-25 (network 16,420 km, 127 MMSCMD, CGD 21 %)",
         "https://www.gailonline.com/pdf/InvestorsZone/GAIL_Investor_Presentation_FY2024_25.pdf"),
        ("Business Standard – MGL falls after APM gas allocation cut (16-Apr-2025)",
         "https://www.business-standard.com/amp/markets/news/mahanagar-gas-tumbles-over-6-after-apm-gas-allocation-cut-125041600209_1.html"),
        ("Govt raises APM gas price to $7/MMBtu (Apr-2026) – Angel One",
         "https://www.angelone.in/news/stocks/india-hikes-apm-gas-price-to-7-mmbtu-cng-png-and-fertiliser-sectors-to-be-impacted"),
        ("IEA: Middle-East crisis cuts ~20 % of LNG supply (2026) – GreentechLead",
         "https://greentechlead.com/renewable-energy/middle-east-crisis-cuts-20-of-lng-supply-triggers-price-surge-and-delays-lng-growth-iea-53218/amp"),
        ("JKM / TTF / Henry Hub weekly prices, Jul-2026 – Global LNG Hub",
         "https://globallnghub.com/natural-gas-prices-weekly-update-jkm-ttf-and-henry-hub-21-july-2026/"),
        ("MGL Q1 FY27 result update, capex & volume forecasts – PL Capital",
         "https://www.plindia.com/pl-research/mahanagar-gas-mahgl-in-q1fy27-result-update-volume-growth-remains-intact-accumulate/"),
        ("Scaling up CGD capacity (targets, CBG mandate, challenges), Aug-2026 – Indian Infrastructure",
         "https://indianinfrastructure.com/2026/08/11/scaling-up-efforts-to-enhance-cgd-capacity-and-uptake/"),
        ("PNGRB: India gas demand 297–365 MMSCMD by 2030 – Outlook Business",
         "https://www.outlookbusiness.com/news/indias-natural-gas-demand-can-grow-to-365-mmscmd-by-2030-if-situation-is-conducive-pngrb"),
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


# ---- 3a · Shadow prices (objective subsection)
SHADOW_EXPLAINER = [
    ("What it is", "The ₹ gain from **one extra SCM** of a limited resource: city-gate gas, corridor capacity or a service floor."),
    ("Buy or not buy", "If spot LNG costs **less** than the shadow price of gas, buying it pays back."),
    ("Invest where it pays", "The corridor with the highest shadow price × binding months is debottlenecked first."),
    ("Price of compliance", "The shadow price of a service floor shows what keeping households at 100 % (or CNG at 90–95 %) costs."),
]

# ---- Terminology (before References)
TERMS = [
    ("Gas & regulation", [
        ("CGD", "City Gas Distribution: the local pipeline network that supplies gas to homes, vehicles and industries in a city."),
        ("City Gate / CGS", "City Gate Station: where gas from the GAIL trunk pipeline enters the city network (source G in the model)."),
        ("GA", "Geographical Area authorised by PNGRB to one CGD company (e.g. Mumbai, Raigad)."),
        ("PNG (D)", "Piped Natural Gas to households (domestic) for cooking. Highest priority; never cut."),
        ("CNG (T)", "Compressed Natural Gas for transport (autos, taxis, buses, cars). Second priority."),
        ("I&C", "Industrial and Commercial PNG customers (factories, hotels, hospitals). Market-priced; curtailed first."),
        ("APM gas", "Administered Price Mechanism gas from old ONGC/OIL fields; cheapest; allotted by Government only to PNG(D) and CNG(T)."),
        ("NWG", "New Well Gas: gas from new wells of old fields, priced a little above APM."),
        ("HP-HT", "High-Pressure High-Temperature (deep-water) domestic gas; market-linked price with a ceiling."),
        ("RLNG (term / spot)", "Re-gasified imported LNG, bought on long-term contracts or on the spot market."),
        ("JKM / Henry Hub", "Benchmark prices for Asian spot LNG and US gas; drive LNG contract costs."),
        ("SCM, MMSCM, MMSCMD", "Standard Cubic Metre; million SCM; million SCM per day (volume of gas)."),
        ("MMBtu", "Million British thermal units: unit of gas energy used in prices ($/MMBtu). 1 MMBtu ≈ 25–27 SCM."),
        ("GAIL", "GAIL (India) Ltd: main pipeline operator and the nodal agency for domestic-gas allocation to CGD."),
        ("PNGRB", "Petroleum and Natural Gas Regulatory Board: authorises CGD areas, sets technical, safety and service rules."),
        ("MoPNG / PPAC", "Ministry of Petroleum & Natural Gas, and its Petroleum Planning & Analysis Cell: set allocation policy and publish data."),
        ("T4S", "PNGRB Technical Standards & Specifications including Safety Standards for CGD networks."),
        ("ERDMP / IMS", "Emergency Response & Disaster Management Plan; Integrity Management System (PNGRB regulations)."),
        ("MAOP", "Maximum Allowable Operating Pressure: safe upper limit for pipeline pressure."),
        ("Line-pack", "Extra gas stored in a pipeline by raising its pressure (within MAOP) to cover short peaks."),
        ("Virtual pipeline / LCNG", "Moving gas by road (CNG cascades or LNG→CNG skids) where the pipeline cannot reach."),
        ("Take-or-pay (ToP)", "Contract clause: the buyer pays for a minimum share of contracted gas even if not used."),
        ("CBG", "Compressed Biogas: renewable gas blended into CNG/PNG (mandate 1 % → 5 % by FY29)."),
    ]),
    ("Model & decision science", [
        ("Linear Programming (LP)", "Mathematical method that finds the best (optimal) plan when costs and limits are linear."),
        ("PuLP / CBC", "Python library to write the LP, and the open-source COIN-OR solver that solves it."),
        ("Objective function", "What the model optimises: minimum cost, or maximum regulated profit."),
        ("Decision variable", "What the model decides: flow on each corridor (x), shortage (y), gas from each source (g)."),
        ("Constraint", "A rule the plan must obey: supply limit, node balance, corridor capacity, service floor."),
        ("Corridor", "A group of pipeline links with a shared monthly capacity (5 corridors in this network)."),
        ("Service level / fill rate", "Delivered ÷ demand. Service floor = minimum fill rate a sector must get."),
        ("Shortage penalty", "₹ per SCM not supplied; higher for higher-priority customers, so they are served first."),
        ("Shadow price (dual value)", "₹ gain from one more unit of a limited resource; zero if the resource is not fully used."),
        ("Binding constraint", "A limit that is fully used in the optimal plan (it has a non-zero shadow price)."),
        ("Scenario", "A what-if situation (e.g. APM cut, pipeline outage) applied on top of the base data."),
        ("Sensitivity / tornado", "How much the result changes when one input moves ± x %; the biggest bar matters most."),
        ("Mitigation lever", "An emergency action the optimiser may choose: spot cargo, gas swap, line-pack, virtual pipeline."),
        ("Supplier-side vs MGL-side", "Whether the shortage comes from gas not delivered by suppliers, or from MGL's own contracts/network."),
        ("EBITDA / SCM", "Operating profit earned per SCM sold; MGL reports about ₹8–10 per SCM."),
        ("Control tower / DSS", "Decision Support System that monitors data and re-optimises the plan every month."),
    ]),
]

# ---- Future expansion & outlook
EXPANSION = [
    ("Corridor debottlenecking (looping / bigger feeders)", "Add capacity on the corridor with the highest shadow price",
     "Highest ₹ payback per SCM, measured live by the model", "S4, S5", "Short (6–18 months)"),
    ("Second city gate / CGS", "A second gas intake point (e.g. via the Mumbai–Nagpur trunk line)",
     "Removes the single point of failure at the city gate", "S4", "Medium (1–3 years)"),
    ("CNG station growth", "New online stations; convert mother-daughter stations to online",
     "National target 18,336 stations by 2034; CNG ≈ 70 % of MGL volume", "S5", "Continuous"),
    ("Domestic PNG expansion", "More household connections in existing areas",
     "MGL raised FY27 capex to ₹1,800 Cr, mainly for PNG-Dom", "Base growth", "Continuous"),
    ("New geographical areas", "Raigad; Ratnagiri, Latur and Dharashiv through subsidiary UEPL",
     "Growth outside saturated Mumbai; uses existing authorisations", "Growth", "Medium"),
    ("CBG blending & MGL CBG plant", "Compressed biogas into CNG/PNG",
     "Mandate 1 % (FY26) → 5 % (FY29); domestic, non-LNG supply", "S2, S3", "Medium"),
    ("LNG storage / peak-shaving; LNG for trucks", "Small-scale LNG buffer and LNG dispensing",
     "Cushion against cargo disruptions (e.g. Hormuz 2026); new heavy-vehicle demand", "S3", "Medium"),
    ("Control-tower digitalisation", "SCADA + GAS-OPTIC re-run every month (WD 3)",
     "Faster, priced and auditable allocation decisions", "All", "Immediate"),
]

PRICE_TABLE = {
    "years": ["FY25", "FY26", "FY27*", "FY28 F", "FY29 F", "FY30 F"],
    "APM ceiling ($/MMBtu)": [6.50, 6.75, 7.00, 7.25, 7.50, 7.75],
    "MGL CNG Mumbai (₹/kg) – base": [77.0, 81.0, 88.0, 91.5, 95.2, 99.0],
    "MGL CNG Mumbai (₹/kg) – high": [77.0, 81.0, 88.0, 95.0, 102.6, 110.9],
    "MGL domestic PNG (₹/SCM)": [48.0, 49.0, 53.0, 54.6, 56.2, 57.9],
}
PRICE_NOTES = [
    "FY27* = latest actual: APM $7.00 from Apr-2026; CNG ₹88/kg and PNG ₹53/SCM from 1-Sep-2026.",
    "FY28–FY30 are **forecasts**: APM assumes the official +$0.25/yr ceiling step continues; CNG base +4 %/yr, "
    "high +8 %/yr (if the LNG crisis persists); domestic PNG +3 %/yr.",
]
UNCERTAINTIES = [
    ("🌊 Strait of Hormuz disruption (Mar-2026)", "≈20 % of global LNG supply lost (IEA); Asian spot LNG (JKM) ~$21/MMBtu in March and high-$20s in July 2026."),
    ("✂️ Three APM cuts in 7 months", "16-Oct-2024 (~20 %), 16-Nov-2024 and 16-Apr-2025 (MGL ~18 %), partly replaced by costlier NWG."),
    ("📈 Price escalation", "APM price raised to $7/MMBtu (Apr-2026); MGL raised CNG to ₹86/kg (May) and ₹88/kg (Sep-2026)."),
    ("🛢 Pipeline tariff reset", "PNGRB unified-tariff zones revised from Jan-2026, raising transport cost for CGD."),
    ("🏭 Industrial demand switching", "MGL industrial/commercial PNG volume fell ~7 % YoY in Q1 FY27 as users switched fuel."),
    ("🔌 EVs and LPG competition", "Electric vehicles and LPG compete with CNG and PNG demand in newer areas."),
]
