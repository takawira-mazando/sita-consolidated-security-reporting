"""Government multi-tenancy: Department -> Branch -> App.

SITA-style tenancy, modelled on SITA's own customer base (sita.co.za "SITA's
Customers", national list). The tenant is a government department (the
administrative organ of state, e.g. Department of Home Affairs, National
Treasury). National roles (exec, compliance, sre, admin) see the whole estate;
department roles (soc, appsec, dbsec) are scoped to the departments (and
optionally branches) they are assigned to. Every warehouse row that carries an
app (or database) is denormalised with `department_id`/`branch_id` at write
time so REST scoping needs no joins.

User management is delegated along the same tenancy tree, mirroring SITA's
Managed Services hierarchy. Each admin tier is a node in the Department ->
Branch tree and its authority is exactly its node's subtree:

  - tier 4, system `admin`        -> estate root (whole estate, grants anything);
                                      the overarching national superadmin
  - tier 3, `transversal-admin`   -> a transversal superadmin spanning all-department
                                      reports (empty scope) or multiple
                                      departments/branches (assigned scope)
  - tier 2, `dept-admin`          -> a department node (grants operational dept roles
                                     plus `branch-admin`, scoped to its departments)
  - tier 1, `branch-admin`        -> a branch node (grants operational dept roles,
                                     scoped to its branches)

A transversal superadmin grants the admin tiers beneath it (`dept-admin`,
`branch-admin`) plus the operational department roles, across its scope, but
never another `transversal-admin` or the system `admin`. Delegation is strictly
one-way down: a tier can never grant a role at or above its own node, and never
widen scope beyond its subtree. A department admin therefore can never reach
another department's admin functionality. See `ADMIN_TIERS`,
`OPERATIONAL_DEPARTMENT_ROLES` and `GRANTABLE_ROLES`.

Department ids are stable slugs so resolution requires no DB lookup. The five
legacy demo ids (treasury, home-affairs-digital, justice-document,
health-legacy, dpsa-hr) are retained for seed/demo/app-catalog compatibility;
their display names now match SITA's current naming. Branches mirror each
department's real Deputy Director-General-led organisational units, sourced
from the departments' Strategic Plans / Annual Reports / official structures.

The model also carries SITA's provincial mandate: `PROVINCES` (9) and
`PROVINCIAL_DEPARTMENTS` (113) model the three-tier tenancy hierarchy
Tenant (National | Provincial root) -> Sub-Tenant (Department) -> Asset (App),
with provincial personas (`province-soc-lead`, `province-dept-admin`,
`local-appsec`) scoped by province/department. See `PROVINCES`,
`PROVINCIAL_DEPARTMENTS`, `PROVINCE_DEPARTMENTS` and `DEPARTMENT_TO_PROVINCE`.
"""

NATIONWIDE_ROLES = {"exec", "compliance", "sre", "admin", "transversal-admin", "operator"}
PROVINCIAL_ROLES = {"province-soc-lead", "province-dept-admin", "local-appsec"}
DEPARTMENT_ROLES = {
    "soc",
    "appsec",
    "dbsec",
    "dept-admin",
    "branch-admin",
    # Provincial personas (SITA's 113 provincial departments across 9 provinces)
    "province-soc-lead",   # provincial Security Operations Centre lead
    "province-dept-admin", # provincial department administrator
    "local-appsec",        # local application security engineer
}

# Admin tiers for delegated user management, aligned to the tenancy tree:
#   tier 5 = managed-service creator (`operator`): the platform provider's own
#            credentials. Creates the SITA superuser (`admin`) — and peer
#            `operator` accounts for rotation — and nothing else.
#   tier 4 = estate root (`admin`, the SITA superuser): provisions department
#            superusers (`dept-admin`, `province-dept-admin`, `branch-admin`)
#            and national-level dashboard access (exec/compliance/sre) across
#            the whole estate; never a peer `admin`.
#   tier 3 = transversal superadmin (`transversal-admin`): spans all-department
#            reports when unscoped, or multiple departments/branches when assigned
#   tier 2 = department node (`dept-admin`, national or provincial)
#   tier 1 = branch node (`branch-admin`)
# A tier's scope is exactly its node's subtree: estate -> transversal scope ->
# departments -> branches. A tier can grant only roles at or beneath its node.
ADMIN_TIERS = {
    "operator": 5,
    "admin": 4,
    "transversal-admin": 3,
    "dept-admin": 2,
    "province-dept-admin": 2,
    "branch-admin": 1,
}

# Operational department roles beneath the admin tiers. A dept-admin can grant
# these across their departments; a branch-admin within their branches.
OPERATIONAL_DEPARTMENT_ROLES = DEPARTMENT_ROLES - set(ADMIN_TIERS)

# Roles each tier may grant, derived from the tenant role catalog. Delegation
# is a strict one-way cascade down the tenancy tree:
#   operator (creator)     -> creates the SITA superuser (`admin`) and peer
#                             `operator` accounts only (rotation)
#   admin (SITA superuser) -> creates department superusers (`dept-admin`,
#                             `province-dept-admin`, `branch-admin`) and
#                             provisions national-level dashboard access
#                             (`exec`, `compliance`, `sre`) estate-wide
#   transversal-admin      -> grants every operational department role plus the
#                             admin tiers beneath it and the specialist
#                             national roles across its scope
#   dept-admin             -> grants the operational department roles plus
#                             `branch-admin` within its department
#   branch-admin           -> grants the operational department roles within
#                             its branches
#   sre                    -> whole-estate user management for the operational
#                             department roles only; no admin-tier grants
GRANTABLE_ROLES = {
    "operator": {"admin", "operator"},
    "sre": OPERATIONAL_DEPARTMENT_ROLES,
    "admin": OPERATIONAL_DEPARTMENT_ROLES
        | {"transversal-admin", "dept-admin", "province-dept-admin", "branch-admin", "exec", "compliance", "sre"},
    "transversal-admin": OPERATIONAL_DEPARTMENT_ROLES
        | {"dept-admin", "branch-admin", "province-dept-admin", "transversal-admin", "sre", "exec", "compliance"},
    "dept-admin": OPERATIONAL_DEPARTMENT_ROLES | {"branch-admin"},
    "province-dept-admin": OPERATIONAL_DEPARTMENT_ROLES,
    "branch-admin": OPERATIONAL_DEPARTMENT_ROLES,
}


def tier_for_role(role: str) -> int:
    """Tenant-tree depth for a role (0 = not an admin tier)."""
    return ADMIN_TIERS.get(role, 0)

# id -> cluster name  (National Treasury Consolidated Financial Statements segments)
CLUSTERS = {
    "central-admin": "Central Government Administration",
    "finance-admin": "Financial and Administration Services",
    "economic": "Economic Services and Infrastructure Development",
    "justice": "Justice and Protection Services",
    "social": "Social Services",
}

# id -> ministry name  (current GNU Cabinet portfolios, post-June-2026 reshuffle)
MINISTRIES = {
    "presidency": "The Presidency",
    "finance": "Ministry of Finance",
    "home-affairs": "Ministry of Home Affairs",
    "justice": "Ministry of Justice and Constitutional Development",
    "police": "Ministry of Police",
    "defence": "Ministry of Defence and Military Veterans",
    "correctional": "Ministry of Correctional Services",
    "health": "Ministry of Health",
    "basic-education": "Ministry of Basic Education",
    "higher-education": "Ministry of Higher Education",
    "social-development": "Ministry of Social Development",
    "sport-arts-culture": "Ministry of Sport, Arts and Culture",
    "employment-labour": "Ministry of Employment and Labour",
    "science-innovation": "Ministry of Science, Technology and Innovation",
    "cogta": "Ministry of Cooperative Governance and Traditional Affairs",
    "dpsa": "Ministry of Public Service and Administration",
    "public-works": "Ministry of Public Works and Infrastructure",
    "communications": "Ministry of Communications and Digital Technologies",
    "agriculture": "Ministry of Agriculture",
    "land-reform": "Ministry of Land Reform and Rural Development",
    "forestry-fisheries": "Ministry of Forestry, Fisheries and the Environment",
    "electricity-energy": "Ministry of Electricity and Energy",
    "mineral-petroleum": "Ministry of Mineral and Petroleum Resources",
    "human-settlements": "Ministry of Human Settlements",
    "tourism": "Ministry of Tourism",
    "trade-industry": "Ministry of Trade, Industry and Competition",
    "transport": "Ministry of Transport",
    "water-sanitation": "Ministry of Water and Sanitation",
    "women-youth": "Ministry of Women, Youth and Persons with Disabilities",
    "dirco": "Ministry of International Relations and Cooperation",
    "public-enterprises": "Ministry of Public Enterprises",
    "state-security": "State Security",
}

# ministry id -> cluster id  (Treasury CFS segment each portfolio reports into)
MINISTRY_TO_CLUSTER = {
    "presidency": "central-admin",
    "finance": "finance-admin",
    "home-affairs": "justice",
    "justice": "justice",
    "police": "justice",
    "defence": "justice",
    "correctional": "justice",
    "health": "social",
    "basic-education": "social",
    "higher-education": "social",
    "social-development": "social",
    "sport-arts-culture": "social",
    "employment-labour": "social",
    "science-innovation": "social",
    "cogta": "central-admin",
    "dpsa": "finance-admin",
    "public-works": "central-admin",
    "communications": "economic",
    "agriculture": "economic",
    "land-reform": "economic",
    "forestry-fisheries": "economic",
    "electricity-energy": "economic",
    "mineral-petroleum": "economic",
    "human-settlements": "economic",
    "tourism": "economic",
    "trade-industry": "economic",
    "transport": "economic",
    "water-sanitation": "economic",
    "women-youth": "central-admin",
    "dirco": "central-admin",
    "public-enterprises": "finance-admin",
    "state-security": "justice",
}

# department id -> ministry id
DEPARTMENT_TO_MINISTRY = {
    "treasury": "finance",
    "home-affairs-digital": "home-affairs",
    "justice-document": "justice",
    "health-legacy": "health",
    "dpsa-hr": "dpsa",
    "presidency": "presidency",
    "centre-public-service-innovation": "dpsa",
    "cipc": "trade-industry",
    "dcmis": "defence",
    "daff": "agriculture",
    "arts-culture": "sport-arts-culture",
    "basic-education": "basic-education",
    "communications": "communications",
    "cogta": "cogta",
    "correctional-services": "correctional",
    "defence": "defence",
    "economic-development": "trade-industry",
    "energy": "electricity-energy",
    "environmental-affairs": "forestry-fisheries",
    "higher-education": "higher-education",
    "human-settlements": "human-settlements",
    "dirco": "dirco",
    "labour": "employment-labour",
    "military-veterans": "defence",
    "mineral-resources": "mineral-petroleum",
    "minerals-energy": "mineral-petroleum",
    "pme": "presidency",
    "public-enterprises": "public-enterprises",
    "public-works": "public-works",
    "rural-development": "land-reform",
    "science-technology": "science-innovation",
    "small-business": "trade-industry",
    "social-development": "social-development",
    "sport-recreation": "sport-arts-culture",
    "dtps": "communications",
    "tourism": "tourism",
    "trade-industry": "trade-industry",
    "traditional-affairs": "cogta",
    "transport": "transport",
    "water-sanitation": "water-sanitation",
    "women": "women-youth",
    "gcis": "presidency",
    "gpaa": "finance",
    "gpw": "communications",
    "icasa": "communications",
    "iec": "presidency",
    "ipid": "police",
    "npa": "justice",
    "nsg": "dpsa",
    "nyda": "women-youth",
    "psc": "dpsa",
    "ocj": "justice",
    "public-protector": "justice",
    "saps": "police",
    "sassa": "social-development",
    "siu": "justice",
    "ssa": "state-security",
    "stats-sa": "presidency",
    "csps": "police",
    "umalusi": "basic-education",
}

# id -> department name  (SITA's current customer list, national level)
DEPARTMENTS = {
    "treasury": "National Treasury",
    "home-affairs-digital": "Department of Home Affairs",
    "justice-document": "Department of Justice and Constitutional Development",
    "health-legacy": "Department of Health",
    "dpsa-hr": "Department of Public Service and Administration",
    "presidency": "The Presidency",
    "centre-public-service-innovation": "Centre for Public Service Innovation",
    "cipc": "Companies and Intellectual Property Commission",
    "dcmis": "Defence Command and Management Information Systems",
    "daff": "Department of Agriculture, Forestry and Fisheries",
    "arts-culture": "Department of Arts and Culture",
    "basic-education": "Department of Basic Education",
    "communications": "Department of Communications",
    "cogta": "Department of Cooperative Governance and Traditional Affairs",
    "correctional-services": "Department of Correctional Services",
    "defence": "Department of Defence",
    "economic-development": "Department of Economic Development",
    "energy": "Department of Energy",
    "environmental-affairs": "Department of Environmental Affairs",
    "higher-education": "Department of Higher Education and Training",
    "human-settlements": "Department of Human Settlements",
    "dirco": "Department of International Relations and Cooperation",
    "labour": "Department of Labour",
    "military-veterans": "Department of Military Veterans",
    "mineral-resources": "Department of Mineral Resources",
    "minerals-energy": "Department of Minerals and Energy",
    "pme": "Department of Planning, Monitoring and Evaluation",
    "public-enterprises": "Department of Public Enterprises",
    "public-works": "Department of Public Works",
    "rural-development": "Department of Rural Development and Land Reform",
    "science-technology": "Department of Science and Technology",
    "small-business": "Department of Small Business Development",
    "social-development": "Department of Social Development",
    "sport-recreation": "Department of Sport and Recreation",
    "dtps": "Department of Telecommunications and Postal Services",
    "tourism": "Department of Tourism",
    "trade-industry": "Department of Trade and Industry",
    "traditional-affairs": "Department of Traditional Affairs",
    "transport": "Department of Transport",
    "water-sanitation": "Department of Water and Sanitation",
    "women": "Department of Women",
    "gcis": "Government Communication and Information System",
    "gpaa": "Government Pensions Administration Agency",
    "gpw": "Government Printing Works",
    "icasa": "Independent Communications Authority of South Africa",
    "iec": "Independent Electoral Commission",
    "ipid": "Independent Police Investigation Directorate",
    "npa": "National Prosecuting Authority of South Africa",
    "nsg": "National School of Government",
    "nyda": "National Youth Development Agency",
    "psc": "Office of Public Service Commission",
    "ocj": "Office of the Chief Justice",
    "public-protector": "Public Protector",
    "saps": "South African Police Service",
    "sassa": "South African Social Security Agency",
    "siu": "Special Investigating Unit",
    "ssa": "State Security Agency Domestic Branch",
    "stats-sa": "Statistics South Africa",
    "csps": "The Civilian Secretariat for Police Service",
    "umalusi": "Umalusi",
}

# id -> (name, department_id)
# Branches are each department's real DDG-led organisational units.
BRANCHES = {
    # --- National Treasury ---
    "treasury-budget": ("Budget Office", "treasury"),
    "treasury-pfm": ("Public Finance", "treasury"),
    "treasury-tax-policy": ("Tax and Financial Sector Policy", "treasury"),
    "treasury-economic": ("Economic Policy and International Cooperation", "treasury"),
    "treasury-intergov": ("Intergovernmental Relations", "treasury"),
    "treasury-alms": ("Asset and Liability Management", "treasury"),
    "treasury-ag": ("Office of the Accountant-General", "treasury"),
    "treasury-cpo": ("Office of the Chief Procurement Officer", "treasury"),
    "treasury-counsel": ("Office of the General Counsel", "treasury"),
    "treasury-ict": ("Corporate Services & ICT", "treasury"),
    # --- Department of Home Affairs ---
    "dha-civic": ("Civic Services", "home-affairs-digital"),
    "dha-digital": ("Information Services (CIO)", "home-affairs-digital"),
    "dha-immigration": ("Immigration Services", "home-affairs-digital"),
    "dha-operations": ("Operations", "home-affairs-digital"),
    "dha-hrmd": ("Human Resource Management and Development", "home-affairs-digital"),
    "dha-ccss": ("Counter Corruption and Security Services", "home-affairs-digital"),
    "dha-finance": ("Finance and Supply Chain Management", "home-affairs-digital"),
    "dha-planning": ("Institutional Planning and Support", "home-affairs-digital"),
    # --- Department of Justice and Constitutional Development ---
    "doj-court-admin": ("Court Administration", "justice-document"),
    "doj-legal": ("Legislative Development and Legal Services", "justice-document"),
    "doj-master": ("Master of the High Court and Family Law Services", "justice-document"),
    "doj-ocla": ("Office of the Chief State Law Adviser", "justice-document"),
    "doj-constitutional": ("Constitutional Development", "justice-document"),
    "doj-institutional": ("Institutional Development and Support", "justice-document"),
    "doj-finance": ("Financial Management Services", "justice-document"),
    "doj-corporate": ("Corporate Services", "justice-document"),
    "doj-ict": ("Information and Communication Technology", "justice-document"),
    # --- Department of Health ---
    "doh-nhi": ("National Health Insurance", "health-legacy"),
    "doh-hiv": ("HIV/AIDS, TB, Maternal and Child Health", "health-legacy"),
    "doh-phc": ("Primary Health Care", "health-legacy"),
    "doh-hospitals": ("Hospitals, Tertiary Health Services and HR Development", "health-legacy"),
    "doh-regulations": ("Health Regulations and Compliance", "health-legacy"),
    "doh-cfo": ("Chief Financial Officer", "health-legacy"),
    # --- Department of Public Service and Administration ---
    "dpsa-admin": ("Administration", "dpsa-hr"),
    "dpsa-hr-ops": ("Human Resource Management and Development", "dpsa-hr"),
    "dpsa-nlrm": ("Negotiations, Labour Relations and Remuneration Management", "dpsa-hr"),
    "dpsa-ict": ("e-Government Services and Information Management", "dpsa-hr"),
    "dpsa-gsai": ("Government Services Access and Improvement", "dpsa-hr"),
    # --- The Presidency ---
    "presidency-private": ("Private Office of the President", "presidency"),
    "presidency-deputy": ("Office of the Deputy President", "presidency"),
    "presidency-cabinet": ("Cabinet Services", "presidency"),
    "presidency-policy": ("Policy and Research Services", "presidency"),
    "presidency-corporate": ("Corporate Management", "presidency"),
    # --- Centre for Public Service Innovation ---
    "cpsi-admin": ("Administration", "centre-public-service-innovation"),
    "cpsi-innovation": ("Public Sector Innovation", "centre-public-service-innovation"),
    # --- Companies and Intellectual Property Commission ---
    "cipc-regulation": ("Business Regulation and Reputation", "cipc"),
    "cipc-innovation": ("Innovation and Creativity", "cipc"),
    "cipc-intelligence": ("Business Intelligence and Systems", "cipc"),
    "cipc-governance": ("Compliance, Risk and Governance", "cipc"),
    "cipc-corporate": ("Corporate Services", "cipc"),
    # --- Defence Command and Management Information Systems ---
    "dcmis-cmis": ("Command and Management Information Systems", "dcmis"),
    "dcmis-enterprise": ("Enterprise Information Systems Management", "dcmis"),
    "dcmis-iw": ("Information Warfare", "dcmis"),
    # --- Department of Agriculture, Forestry and Fisheries ---
    "daff-corporate": ("Corporate Services", "daff"),
    "daff-policy": ("Policy, Planning, Monitoring and Evaluation", "daff"),
    "daff-trade": ("Economic Development, Trade and Marketing", "daff"),
    "daff-food": ("Food Security and Agrarian Reform", "daff"),
    "daff-forestry": ("Forestry and Natural Resources Management", "daff"),
    "daff-fisheries": ("Fisheries Management", "daff"),
    # --- Department of Arts and Culture ---
    "arts-culture-admin": ("Administration", "arts-culture"),
    "arts-institutional": ("Institutional Governance", "arts-culture"),
    "arts-promotion": ("Arts and Culture Promotion and Development", "arts-culture"),
    "arts-heritage": ("Heritage Promotion and Preservation", "arts-culture"),
    # --- Department of Basic Education ---
    "dbe-intelligence": ("Business Intelligence", "basic-education"),
    "dbe-curriculum": ("Curriculum Policy, Support and Monitoring", "basic-education"),
    "dbe-delivery": ("Delivery and Support", "basic-education"),
    "dbe-finance": ("Finance and Administration", "basic-education"),
    "dbe-infrastructure": ("Infrastructure", "basic-education"),
    "dbe-social": ("Social Mobilisation and Support Services", "basic-education"),
    "dbe-teachers": ("Teachers, Human Resource and Institutional Development", "basic-education"),
    # --- Department of Communications ---
    "comms-ict-intl": ("ICT International Relations and Affairs", "communications"),
    "comms-digital": ("Digital Society and Economy", "communications"),
    "comms-media": ("Media and Content", "communications"),
    "comms-access": ("Digital Communication, Access and Services", "communications"),
    "comms-resource": ("Resource and Stakeholder Management", "communications"),
    "comms-admin": ("Administration", "communications"),
    "comms-infrastructure": ("Digital Infrastructure and Technologies", "communications"),
    # --- Department of Cooperative Governance and Traditional Affairs ---
    "cogta-local": ("Local Government Operations and Support", "cogta"),
    "cogta-policy": ("Policy, Governance and Administration", "cogta"),
    "cogta-disaster": ("National Disaster Management Centre", "cogta"),
    "cogta-cwp": ("Community Work Programme", "cogta"),
    "cogta-traditional": ("Traditional Affairs: Research, Policy and Legislation", "cogta"),
    "cogta-corporate": ("Corporate Services", "cogta"),
    # --- Department of Correctional Services ---
    "dcs-remand": ("Remand Detention", "correctional-services"),
    "dcs-incarceration": ("Incarceration and Corrections", "correctional-services"),
    "dcs-community": ("Community Corrections", "correctional-services"),
    "dcs-rehab": ("Rehabilitation", "correctional-services"),
    "dcs-hr": ("Human Resources Management and Development", "correctional-services"),
    "dcs-institutional": ("Institutional Development Management and Support", "correctional-services"),
    "dcs-strategy": ("Strategic Management", "correctional-services"),
    "dcs-finance": ("Financial Management", "correctional-services"),
    "dcs-gito": ("Government Information Technology Officer", "correctional-services"),
    # --- Department of Defence ---
    "dod-army": ("SA Army", "defence"),
    "dod-airforce": ("SA Air Force", "defence"),
    "dod-navy": ("SA Navy", "defence"),
    "dod-mhs": ("SA Military Health Service", "defence"),
    "dod-jointops": ("Joint Operations", "defence"),
    "dod-intelligence": ("Defence Intelligence", "defence"),
    "dod-logistics": ("Logistics", "defence"),
    "dod-policy": ("Defence Policy, Strategy and Planning", "defence"),
    "dod-hr": ("Human Resources", "defence"),
    "dod-finance": ("Financial Management", "defence"),
    "dod-material": ("Defence Matériel", "defence"),
    "dod-legal": ("Defence Legal Services", "defence"),
    "dod-ems": ("Defence Enterprise Information System Management", "defence"),
    "dod-corporate": ("Corporate Staff", "defence"),
    # --- Department of Economic Development ---
    "ed-policy": ("Economic Policy and Investment", "economic-development"),
    "ed-industrial": ("Industrial Development Policy", "economic-development"),
    "ed-trade": ("Competition and Trade Policy", "economic-development"),
    "ed-corporate": ("Corporate Services", "economic-development"),
    # --- Department of Energy ---
    "energy-corporate": ("Corporate Services", "energy"),
    "energy-finance": ("Financial Management Services", "energy"),
    "energy-governance": ("Governance and Compliance", "energy"),
    "energy-policy": ("Policy and Planning", "energy"),
    "energy-petroleum": ("Petroleum and Petroleum Products Regulation", "energy"),
    "energy-nuclear": ("Nuclear Energy", "energy"),
    "energy-projects": ("Electrification and Energy Programme and Project Management", "energy"),
    "energy-clean": ("Clean Energy", "energy"),
    # --- Department of Environmental Affairs ---
    "ea-corporate": ("Corporate Management Services", "environmental-affairs"),
    "ea-regulatory": ("Regulatory Compliance and Sector Monitoring", "environmental-affairs"),
    "ea-ocean": ("Ocean and Coasts", "environmental-affairs"),
    "ea-climate": ("Climate Change and Air Quality, and Sustainable Development", "environmental-affairs"),
    "ea-fisheries": ("Fisheries Management", "environmental-affairs"),
    "ea-programmes": ("Environmental Programmes", "environmental-affairs"),
    "ea-biodiversity": ("Biodiversity and Conservation", "environmental-affairs"),
    "ea-chemistry": ("Chemicals and Waste Management", "environmental-affairs"),
    "ea-forestry": ("Forestry Management", "environmental-affairs"),
    # --- Department of Higher Education and Training ---
    "dhet-university": ("University Education", "higher-education"),
    "dhet-tvet": ("Technical and Vocational Education and Training", "higher-education"),
    "dhet-cet": ("Community Education and Training", "higher-education"),
    "dhet-skills": ("Skills Development", "higher-education"),
    "dhet-corporate": ("Corporate Services", "higher-education"),
    "dhet-planning": ("Planning, Policy and Strategy", "higher-education"),
    "dhet-finance": ("Office of the Chief Financial Officer", "higher-education"),
    # --- Department of Human Settlements ---
    "dhs-corporate": ("Corporate Services", "human-settlements"),
    "dhs-research": ("Research, Policy, Strategy and Planning", "human-settlements"),
    "dhs-housing": ("Affordable, Rental and Social Housing", "human-settlements"),
    "dhs-informal": ("Informal Settlements Upgrading and Emergency Housing", "human-settlements"),
    "dhs-entities": ("Entities Oversight, IGR, Monitoring and Evaluation", "human-settlements"),
    # --- Department of International Relations and Cooperation ---
    "dirco-africa": ("Africa", "dirco"),
    "dirco-americas": ("Americas and Europe", "dirco"),
    "dirco-asia": ("Asia and Middle East", "dirco"),
    "dirco-global": ("Global Governance and Continental Agenda", "dirco"),
    "dirco-diplomacy": ("Public Diplomacy", "dirco"),
    "dirco-consular": ("State Protocol and Consular Services", "dirco"),
    "dirco-training": ("Diplomatic Training, Research and Development", "dirco"),
    "dirco-corporate": ("Corporate Management", "dirco"),
    "dirco-finance": ("Financial and Asset Management", "dirco"),
    # --- Department of Labour ---
    "dol-inspection": ("Inspection and Enforcement Services", "labour"),
    "dol-employment": ("Public Employment Services", "labour"),
    "dol-policy": ("Labour Policy and Industrial Relations", "labour"),
    "dol-corporate": ("Corporate Services", "labour"),
    "dol-coo": ("Office of the Chief Operations Officer", "labour"),
    "dol-finance": ("Chief Financial Officer", "labour"),
    # --- Department of Military Veterans ---
    "dmv-corporate": ("Corporate Services", "military-veterans"),
    "dmv-socio": ("Socio-Economic Support Services", "military-veterans"),
    "dmv-empowerment": ("Empowerment and Stakeholder Management", "military-veterans"),
    # --- Department of Mineral Resources ---
    "dmr-corporate": ("Corporate Services", "mineral-resources"),
    "dmr-regulation": ("Mineral Regulation", "mineral-resources"),
    "dmr-policy": ("Mineral Policy and Promotions", "mineral-resources"),
    "dmr-mhs": ("Mine Health and Safety Inspectorate", "mineral-resources"),
    # --- Department of Minerals and Energy ---
    "dmre-corporate": ("Corporate Services", "minerals-energy"),
    "dmre-policy": ("Mining, Minerals and Energy Policy Development", "minerals-energy"),
    "dmre-regulation": ("Minerals and Petroleum Regulation", "minerals-energy"),
    "dmre-mhs": ("Mine Health and Safety Inspectorate", "minerals-energy"),
    "dmre-projects": ("Energy Programmes and Projects", "minerals-energy"),
    "dmre-nuclear": ("Nuclear Energy Regulation and Management", "minerals-energy"),
    "dmre-enforcement": ("Compliance and Enforcement", "minerals-energy"),
    # --- Department of Planning, Monitoring and Evaluation ---
    "pme-planning": ("National Planning Coordination", "pme"),
    "pme-sector": ("Sector Monitoring Services", "pme"),
    "pme-capacity": ("Public Sector Monitoring and Capacity Development", "pme"),
    "pme-evaluation": ("Evaluation, Evidence and Knowledge Systems", "pme"),
    "pme-corporate": ("Corporate Services", "pme"),
    # --- Department of Public Enterprises ---
    "dpe-corporate": ("Corporate Management", "public-enterprises"),
    "dpe-governance": ("SOC Governance, Assurance and Performance", "public-enterprises"),
    "dpe-enhancement": ("Business Enhancement, Transformation and Industrialisation", "public-enterprises"),
    # --- Department of Public Works ---
    "dpw-professional": ("Professional Services", "public-works"),
    "dpw-igr": ("Intergovernmental Relations Coordination", "public-works"),
    "dpw-epwp": ("Expanded Public Works Programme", "public-works"),
    "dpw-policy": ("Policy, Research and Regulation", "public-works"),
    "dpw-corporate": ("Corporate Services", "public-works"),
    "dpw-governance": ("Governance, Risk and Compliance", "public-works"),
    "dpw-finance": ("Finance", "public-works"),
    "dpw-pmo": ("Project Management Office", "public-works"),
    # --- Department of Rural Development and Land Reform ---
    "dlrrd-corporate": ("Corporate Services", "rural-development"),
    "dlrrd-splum": ("Spatial Planning and Land Use Management", "rural-development"),
    "dlrrd-redistribution": ("Land Redistribution and Development", "rural-development"),
    "dlrrd-tenure": ("Land Tenure and Administration", "rural-development"),
    "dlrrd-enterprise": ("Rural Enterprise and Industrial Development", "rural-development"),
    "dlrrd-infrastructure": ("Rural Infrastructure Development", "rural-development"),
    "dlrrd-geomatics": ("National Geomatics Management Services", "rural-development"),
    "dlrrd-deeds": ("Deeds Registration", "rural-development"),
    "dlrrd-restitution": ("Restitution (Land Claims)", "rural-development"),
    # --- Department of Science and Technology ---
    "dst-institutional": ("Institutional Planning and Support", "science-technology"),
    "dst-corporate": ("Corporate Services", "science-technology"),
    "dst-innovation": ("Technology Innovation", "science-technology"),
    "dst-international": ("International Cooperation and Resources", "science-technology"),
    "dst-research": ("Research Development and Support", "science-technology"),
    "dst-partnerships": ("Socio-Economic Innovation Partnerships", "science-technology"),
    # --- Department of Small Business Development ---
    "dsbd-policy": ("Sector Policy and Research", "small-business"),
    "dsbd-coops": ("Integrated Co-operatives and Micro Enterprise Development", "small-business"),
    "dsbd-enterprise": ("Enterprise Development, Innovation and Entrepreneurship", "small-business"),
    # --- Department of Social Development ---
    "dsd-welfare": ("Welfare Services", "social-development"),
    "dsd-security": ("Comprehensive Social Security", "social-development"),
    "dsd-community": ("Community Development", "social-development"),
    "dsd-corporate": ("Corporate Support Services", "social-development"),
    "dsd-strategy": ("Strategy and Organisational Transformation", "social-development"),
    "dsd-finance": ("Chief Financial Officer", "social-development"),
    # --- Department of Sport and Recreation ---
    "dsac-admin": ("Administration", "sport-recreation"),
    "dsac-sport": ("Recreation Development and Sport Promotion", "sport-recreation"),
    "dsac-arts": ("Arts and Culture Promotion and Development", "sport-recreation"),
    "dsac-heritage": ("Heritage Promotion and Preservation", "sport-recreation"),
    "dsac-finance": ("Chief Financial Officer", "sport-recreation"),
    # --- Department of Telecommunications and Postal Services ---
    "dtps-admin": ("Administration (Corporate Support Services)", "dtps"),
    "dtps-policy": ("ICT Policy and Strategy", "dtps"),
    "dtps-intl": ("ICT International Affairs and Trade", "dtps"),
    "dtps-soe": ("ICT Enterprise Development and SOE Oversight", "dtps"),
    "dtps-infrastructure": ("ICT Infrastructure Support and Development", "dtps"),
    # --- Department of Tourism ---
    "tourism-corporate": ("Corporate Management", "tourism"),
    "tourism-research": ("Tourism Research, Policy and International Relations", "tourism"),
    "tourism-destination": ("Destination Development", "tourism"),
    "tourism-sector": ("Tourism Sector Support Services", "tourism"),
    # --- Department of Trade and Industry ---
    "dtic-corporate": ("Corporate Management Services", "trade-industry"),
    "dtic-investment": ("Investment and Spatial Industrial Development", "trade-industry"),
    "dtic-research": ("Research (Chief Economist)", "trade-industry"),
    "dtic-sectors": ("Sectors", "trade-industry"),
    "dtic-transformation": ("Transformation and Competition", "trade-industry"),
    "dtic-regulation": ("Regulation", "trade-industry"),
    "dtic-trade": ("Trade", "trade-industry"),
    "dtic-incentives": ("Incentives", "trade-industry"),
    "dtic-exports": ("Exports", "trade-industry"),
    # --- Department of Traditional Affairs ---
    "dta-admin": ("Administration", "traditional-affairs"),
    "dta-policy": ("Research, Policy and Legislation", "traditional-affairs"),
    "dta-support": ("Institutional Support and Coordination", "traditional-affairs"),
    # --- Department of Transport ---
    "dot-aviation": ("Aviation", "transport"),
    "dot-planning": ("Integrated Transport Planning", "transport"),
    "dot-maritime": ("Maritime", "transport"),
    "dot-public": ("Public Transport", "transport"),
    "dot-rail": ("Rail", "transport"),
    "dot-roads": ("Roads", "transport"),
    "dot-corporate": ("Corporate Services", "transport"),
    # --- Department of Water and Sanitation ---
    "dws-corporate": ("Corporate Support Services", "water-sanitation"),
    "dws-governance": ("Governance and International Cooperation", "water-sanitation"),
    "dws-infrastructure": ("Water Resource Infrastructure Management", "water-sanitation"),
    "dws-services": ("Water Services Management", "water-sanitation"),
    "dws-resources": ("Water Resources Management", "water-sanitation"),
    "dws-regulation": ("Regulation, Compliance and Enforcement", "water-sanitation"),
    # --- Department of Women ---
    "dwypd-admin": ("Administration", "women"),
    "dwypd-women": ("Advocacy and Mainstreaming for the Rights of Women", "women"),
    "dwypd-mec": ("Monitoring, Evaluation, Research and Coordination", "women"),
    "dwypd-youth": ("Mainstreaming Youth and Persons with Disabilities Rights", "women"),
    # --- Government Communication and Information System ---
    "gcis-content": ("Content Processing and Dissemination", "gcis"),
    "gcis-intergov": ("Intergovernmental Coordination and Stakeholder Management", "gcis"),
    "gcis-corporate": ("Corporate Services", "gcis"),
    # --- Government Pensions Administration Agency ---
    "gpaa-corporate": ("Corporate Services", "gpaa"),
    "gpaa-finance": ("Financial Services", "gpaa"),
    "gpaa-enablement": ("Business Enablement", "gpaa"),
    "gpaa-strategy": ("Strategic Support", "gpaa"),
    "gpaa-governance": ("Governance", "gpaa"),
    # --- Government Printing Works ---
    "gpw-manufacturing": ("Manufacturing and Engineering", "gpw"),
    "gpw-operations": ("Operations Management", "gpw"),
    "gpw-finance": ("Financial Services", "gpw"),
    "gpw-corporate": ("Corporate Services", "gpw"),
    # --- Independent Communications Authority of South Africa ---
    "icasa-licensing": ("Licensing and Compliance", "icasa"),
    "icasa-policy": ("Policy, Research and Analysis", "icasa"),
    "icasa-engineering": ("Engineering and Technology", "icasa"),
    "icasa-regions": ("Regions and Consumer Affairs", "icasa"),
    "icasa-corporate": ("Corporate Services", "icasa"),
    # --- Independent Electoral Commission ---
    "iec-operations": ("Electoral Operations", "iec"),
    "iec-corporate": ("Corporate Services", "iec"),
    "iec-outreach": ("Outreach", "iec"),
    "iec-funding": ("Political Party Funding", "iec"),
    "iec-commission": ("Commission Services", "iec"),
    # --- Independent Police Investigation Directorate ---
    "ipid-investigations": ("Investigation and Information Management", "ipid"),
    "ipid-legal": ("Legal and Investigation Advisory Services", "ipid"),
    "ipid-compliance": ("Compliance Monitoring and Stakeholder Management", "ipid"),
    "ipid-corporate": ("Corporate Services", "ipid"),
    # --- National Prosecuting Authority of South Africa ---
    "npa-nps": ("National Prosecutions Service", "npa"),
    "npa-afu": ("Asset Forfeiture Unit", "npa"),
    "npa-soc": ("Strategy, Operations and Compliance", "npa"),
    "npa-legal": ("Legal Affairs Division", "npa"),
    "npa-sccu": ("Specialised Commercial Crime Unit", "npa"),
    "npa-pclu": ("Priority Crimes Litigation Unit", "npa"),
    "npa-soca": ("Sexual Offences and Community Affairs", "npa"),
    "npa-id": ("Investigating Directorate Against Corruption", "npa"),
    "npa-corporate": ("Corporate Services", "npa"),
    # --- National School of Government ---
    "nsg-admin": ("Administration", "nsg"),
    "nsg-learning": ("Learning and Professional Development", "nsg"),
    "nsg-support": ("Professional Support Services", "nsg"),
    "nsg-finance": ("Office of the Chief Financial Officer", "nsg"),
    # --- National Youth Development Agency ---
    "nyda-operations": ("Operations (Programme Design and Development)", "nyda"),
    "nyda-corporate": ("Corporate Services", "nyda"),
    "nyda-nys": ("National Youth Service", "nyda"),
    # --- Office of Public Service Commission ---
    "psc-admin": ("Administration", "psc"),
    "psc-integrity": ("Integrity and Anti-corruption", "psc"),
    "psc-monitoring": ("Monitoring and Evaluation", "psc"),
    "psc-leadership": ("Leadership and Management Practices", "psc"),
    "psc-provincial": ("Provincial Coordination", "psc"),
    # --- Office of the Chief Justice ---
    "ocj-court": ("Court Administration Services", "ocj"),
    "ocj-judicial": ("Judicial, Policy, Research, Education and Support Services", "ocj"),
    "ocj-corporate": ("Corporate Management Services", "ocj"),
    # --- Public Protector ---
    "pp-investigations": ("Investigations", "public-protector"),
    "pp-provincial": ("Provincial Investigations and Integration", "public-protector"),
    "pp-complaints": ("Complaints and Stakeholder Management", "public-protector"),
    "pp-legal": ("Legal Services", "public-protector"),
    "pp-corporate": ("Corporate Services", "public-protector"),
    # --- South African Police Service ---
    "saps-visible": ("Visible Policing", "saps"),
    "saps-operational": ("Operational Response Services", "saps"),
    "saps-detective": ("Detective Services", "saps"),
    "saps-forensic": ("Forensic Services", "saps"),
    "saps-intelligence": ("Crime Intelligence", "saps"),
    "saps-protection": ("Protection and Security Services", "saps"),
    "saps-criminal-record": ("Criminal Record and Crime Scene Management", "saps"),
    "saps-hr": ("Human Resource Development", "saps"),
    "saps-finance": ("Financial and Administrative Services", "saps"),
    "saps-technology": ("Technology Management Services", "saps"),
    "saps-dpci": ("Directorate for Priority Crime Investigation", "saps"),
    # --- South African Social Security Agency ---
    "sassa-grants": ("Grants Operations", "sassa"),
    "sassa-policy": ("Policy Implementation Support", "sassa"),
    "sassa-strategy": ("Strategy and Business Development", "sassa"),
    "sassa-corporate": ("Corporate Services", "sassa"),
    "sassa-finance": ("Finance", "sassa"),
    "sassa-ict": ("Information and Communication Technology", "sassa"),
    # --- Special Investigating Unit ---
    "siu-investigations": ("National Investigations", "siu"),
    "siu-operations": ("Operations", "siu"),
    "siu-legal": ("Legal Counsel", "siu"),
    "siu-finance": ("Finance", "siu"),
    "siu-human": ("Human Capital", "siu"),
    "siu-ict": ("ICT", "siu"),
    # --- State Security Agency Domestic Branch ---
    "ssa-domestic": ("Domestic Branch", "ssa"),
    "ssa-foreign": ("Foreign Branch", "ssa"),
    "ssa-ncc": ("National Communications Branch", "ssa"),
    "ssa-corporate": ("Corporate Services", "ssa"),
    "ssa-academy": ("South African National Academy of Intelligence", "ssa"),
    # --- Statistics South Africa ---
    "stats-economic": ("Economic Statistics", "stats-sa"),
    "stats-social": ("Population and Social Statistics", "stats-sa"),
    "stats-operations": ("Statistical Operations and Provincial Coordination", "stats-sa"),
    "stats-methodology": ("Methodology and Statistical Infrastructure", "stats-sa"),
    "stats-informatics": ("Statistical Support and Informatics", "stats-sa"),
    "stats-sanss": ("South African National Statistics System", "stats-sa"),
    "stats-corporate": ("Corporate Services", "stats-sa"),
    # --- The Civilian Secretariat for Police Service ---
    "csps-policy": ("Policy, Research and Legislation", "csps"),
    "csps-oversight": ("Civilian Oversight and Strategic Partnerships", "csps"),
    "csps-corporate": ("Corporate Services", "csps"),
    # --- Umalusi ---
    "umalusi-corporate": ("Corporate Services", "umalusi"),
    "umalusi-research": ("Qualifications and Research", "umalusi"),
    "umalusi-qa": ("Quality Assurance and Monitoring", "umalusi"),
}

# Hand-mapped demo applications/databases (kept for seed/demo/app-catalog compat).
# The five legacy demo apps get realistic branch ownership; everything else is
# derived from the national estate below so the whole 60-department estate is
# observable without maintaining per-app mappings.
_CURATED_APP_DEPARTMENTS = {
    "payment-gateway": "treasury",
    "customer-portal": "home-affairs-digital",
    "document-svc": "justice-document",
    "legacy-api": "health-legacy",
    "internal-hr": "dpsa-hr",
}

_CURATED_APP_BRANCHES = {
    "payment-gateway": "treasury-ict",
    "customer-portal": "dha-digital",
    "document-svc": "doj-ict",
    "legacy-api": "doh-hospitals",
    "internal-hr": "dpsa-hr-ops",
}

_CURATED_DB_TO_DEPARTMENT = {
    "DB-PAY-01": "treasury",
    "DB-CUST-01": "home-affairs-digital",
    "DB-CUST-02": "home-affairs-digital",
    "DB-DOC-01": "justice-document",
    "DB-HR-01": "dpsa-hr",
}

_CURATED_DB_TO_BRANCH = {
    "DB-PAY-01": "treasury-ict",
    "DB-CUST-01": "dha-digital",
    "DB-CUST-02": "dha-digital",
    "DB-DOC-01": "doj-ict",
    "DB-HR-01": "dpsa-hr-ops",
}


def _representative_branch(dept_id: str) -> str:
    """Pick the branch most likely to own the department's shared ICT estate.

    Prefers a technology-adjacent organisational unit (ICT / digital / systems);
    otherwise falls back to the first branch in config order (deterministic).
    """
    candidates = [b for b, (_, parent) in BRANCHES.items() if parent == dept_id]
    if not candidates:
        raise ValueError(f"department {dept_id!r} has no branches")
    for kw in ("ict", "digital", "technology", "info", "systems", "corporate"):
        for branch in candidates:
            if kw in branch:
                return branch
    return candidates[0]


def _national_estate() -> tuple[dict[str, str], dict[str, str], dict[str, str], dict[str, str]]:
    """Derive one default app + one database per department without a curated mapping."""
    app_dept: dict[str, str] = {}
    app_branch: dict[str, str] = {}
    db_dept: dict[str, str] = {}
    db_branch: dict[str, str] = {}
    for dept_id in DEPARTMENTS:
        if dept_id in _CURATED_APP_DEPARTMENTS.values():
            continue
        branch = _representative_branch(dept_id)
        app = f"{dept_id}-core"
        db = f"DB-{dept_id.upper()}-01"
        app_dept[app] = dept_id
        app_branch[app] = branch
        db_dept[db] = dept_id
        db_branch[db] = branch
    return app_dept, app_branch, db_dept, db_branch


_gen_app_dept, _gen_app_branch, _gen_db_dept, _gen_db_branch = _national_estate()


# --------------------------------------------------------------------------
# Provincial layer (real SITA mandate)
#
# SITA was established by an Act of Parliament to consolidate public sector
# ICT, which makes every national and provincial department a mandatory
# client: 43 national departments + 113 provincial departments across South
# Africa's 9 provinces (156 public clients in total, all connected to the
# National Next-Generation Broadband Network). Deeper transversal services are
# distributed: advanced SOC (cybersecurity) to 39 national departments and
# GPCE cloud (IaaS/hosting) to ~125 public clients.
#
# Tenancy is therefore a three-tier hierarchy:
#   System identity = Tenant (National Department | Provincial Administration)
#                   -> Sub-Tenant (Department) -> Asset (Application ID)
#
# Provincial departments are modelled here with real per-province lists that
# sum to 113. Their stable slugs are `<province>-<function>` (e.g. `gp-health`,
# `wc-economic-development`), namespaced so they can never collide with the
# national catalog. Provincial departments carry no branch subtree (branches
# are a national-department organisational concept); their assets sit directly
# under the department, and scoping to a province simply expands to that
# province's department set.
# --------------------------------------------------------------------------

PROVINCES = {
    "ec": "Eastern Cape",
    "fs": "Free State",
    "gp": "Gauteng",
    "kzn": "KwaZulu-Natal",
    "lp": "Limpopo",
    "mp": "Mpumalanga",
    "nw": "North West",
    "nc": "Northern Cape",
    "wc": "Western Cape",
}

PROVINCE_COUNT = len(PROVINCES)

# SITA's legislative mandate (national + provincial), as publicised by SITA.
SITA_MANDATE_NATIONAL_DEPARTMENTS = 43
SITA_MANDATE_PROVINCIAL_DEPARTMENTS = 113

# function key -> canonical display name (province prefix added at build time)
_PROVINCIAL_FUNCTIONS = {
    "premier": "Office of the Premier",
    "treasury": "Provincial Treasury",
    "education": "Department of Education",
    "health": "Department of Health",
    "social-development": "Department of Social Development",
    "public-works": "Department of Public Works and Infrastructure",
    "transport": "Department of Transport",
    "agriculture": "Department of Agriculture and Rural Development",
    "economic-development": "Department of Economic Development",
    "cogta": "Department of Cooperative Governance and Traditional Affairs",
    "safety-liaison": "Department of Community Safety",
    "sport-arts-culture": "Department of Sport, Arts and Culture",
    "human-settlements": "Department of Human Settlements",
    "environment": "Department of Environment and Tourism",
    "digital-transformation": "Department of Digital Transformation",
}

# provincial function -> national ministry it reports into (cluster rollups)
_PROVINCIAL_FUNCTION_TO_MINISTRY = {
    "premier": "presidency",
    "treasury": "finance",
    "education": "basic-education",
    "health": "health",
    "social-development": "social-development",
    "public-works": "public-works",
    "transport": "transport",
    "agriculture": "agriculture",
    "economic-development": "trade-industry",
    "cogta": "cogta",
    "safety-liaison": "police",
    "sport-arts-culture": "sport-arts-culture",
    "human-settlements": "human-settlements",
    "environment": "forestry-fisheries",
    "digital-transformation": "communications",
}

# per-province function lists — 12+12+15+13+12+13+12+11+13 = 113 departments.
_BASE13 = [
    "premier", "treasury", "education", "health", "social-development",
    "public-works", "transport", "agriculture", "economic-development",
    "cogta", "safety-liaison", "sport-arts-culture", "human-settlements",
]
_PROVINCE_FUNCTIONS = {
    "ec": [f for f in _BASE13 if f != "human-settlements"],                    # 12
    "fs": [f for f in _BASE13 if f != "sport-arts-culture"],                   # 12
    "gp": _BASE13 + ["environment", "digital-transformation"],                 # 15
    "kzn": _BASE13,                                                            # 13
    "lp": [f for f in _BASE13 if f != "human-settlements"],                    # 12
    "mp": _BASE13,                                                             # 13
    "nw": [f for f in _BASE13 if f != "sport-arts-culture"],                   # 12
    "nc": [f for f in _BASE13 if f not in ("human-settlements", "safety-liaison")],  # 11
    "wc": _BASE13,                                                             # 13
}

# slug -> (name, province_id)
PROVINCIAL_DEPARTMENTS: dict[str, tuple[str, str]] = {}
# province_id -> [department slugs]
PROVINCE_DEPARTMENTS: dict[str, list[str]] = {}
# department slug -> province_id (national departments are not provincial)
DEPARTMENT_TO_PROVINCE: dict[str, str] = {}

for _province, _province_name in PROVINCES.items():
    PROVINCE_DEPARTMENTS[_province] = []
    for _fn in _PROVINCE_FUNCTIONS[_province]:
        _slug = f"{_province}-{_fn}"
        PROVINCIAL_DEPARTMENTS[_slug] = (f"{_province_name} {_PROVINCIAL_FUNCTIONS[_fn]}", _province)
        PROVINCE_DEPARTMENTS[_province].append(_slug)
        DEPARTMENT_TO_PROVINCE[_slug] = _province

PROVINCIAL_DEPARTMENT_COUNT = len(PROVINCIAL_DEPARTMENTS)

# Fold the provincial departments into the unified catalogs so admin scope
# validation, tenancy scoping and ministry/cluster rollups all see them.
DEPARTMENTS.update({slug: name for slug, (name, _) in PROVINCIAL_DEPARTMENTS.items()})
DEPARTMENT_TO_MINISTRY.update({
    slug: _PROVINCIAL_FUNCTION_TO_MINISTRY[slug.split("-", 1)[1]]
    for slug in PROVINCIAL_DEPARTMENTS
})


def _provincial_estate() -> tuple[dict[str, str], dict[str, str], dict[str, str], dict[str, str]]:
    """Derive one default app + one database per provincial department.

    Provincial departments have no branch subtree, so branch mappings stay
    empty and the warehouse writer persists a NULL branch for these assets
    (columns are nullable; `branch_for_app` returns None).
    """
    app_dept: dict[str, str] = {}
    db_dept: dict[str, str] = {}
    for dept_id in PROVINCIAL_DEPARTMENTS:
        app = f"{dept_id}-core"
        db = f"DB-{dept_id.upper()}-01"
        app_dept[app] = dept_id
        db_dept[db] = dept_id
    return app_dept, {}, db_dept, {}


_pv_app_dept, _pv_app_branch, _pv_db_dept, _pv_db_branch = _provincial_estate()

# app_name -> department id  (curated + national estate + provincial estate)
APP_DEPARTMENTS = {**_CURATED_APP_DEPARTMENTS, **_gen_app_dept, **_pv_app_dept}
# app_name -> branch id
APP_BRANCHES = {**_CURATED_APP_BRANCHES, **_gen_app_branch, **_pv_app_branch}
# database inventory name -> department id
DB_TO_DEPARTMENT = {**_CURATED_DB_TO_DEPARTMENT, **_gen_db_dept, **_pv_db_dept}
# database inventory name -> branch id
DB_TO_BRANCH = {**_CURATED_DB_TO_BRANCH, **_gen_db_branch, **_pv_db_branch}


def province_for_department(department_id: str | None) -> str | None:
    """Province id for a department (None for national / unknown)."""
    if not department_id:
        return None
    return DEPARTMENT_TO_PROVINCE.get(department_id)


def provincial_departments_for_province(province_id: str | None) -> list[str]:
    """Department slugs belonging to a province (empty for unknown)."""
    if not province_id:
        return []
    return list(PROVINCE_DEPARTMENTS.get(province_id, []))


def is_provincial_department(department_id: str | None) -> bool:
    return department_id in DEPARTMENT_TO_PROVINCE



def department_for_app(app_name: str | None) -> str | None:
    if not app_name:
        return None
    app = str(app_name).lower()
    if app in APP_DEPARTMENTS:
        return APP_DEPARTMENTS[app]
    return None


def department_for_db(db_name: str | None) -> str | None:
    if not db_name:
        return None
    name = str(db_name).upper()
    if name in DB_TO_DEPARTMENT:
        return DB_TO_DEPARTMENT[name]
    return None


def branch_for_app(app_name: str | None) -> str | None:
    if not app_name:
        return None
    app = str(app_name).lower()
    if app in APP_BRANCHES:
        return APP_BRANCHES[app]
    return None


def branch_for_db(db_name: str | None) -> str | None:
    if not db_name:
        return None
    name = str(db_name).upper()
    if name in DB_TO_BRANCH:
        return DB_TO_BRANCH[name]
    return None


def ministry_for_department(department_id: str | None) -> str | None:
    if not department_id:
        return None
    return DEPARTMENT_TO_MINISTRY.get(department_id)


def cluster_for_department(department_id: str | None) -> str | None:
    ministry = ministry_for_department(department_id)
    if not ministry:
        return None
    return MINISTRY_TO_CLUSTER.get(ministry)


def cluster_for_ministry(ministry_id: str | None) -> str | None:
    if not ministry_id:
        return None
    return MINISTRY_TO_CLUSTER.get(ministry_id)


def _department_from_app_or_db(app_name: str | None, db_name: str | None = None) -> str | None:
    return department_for_app(app_name) or department_for_db(db_name)


def ministry_for_app(app_name: str | None, db_name: str | None = None) -> str | None:
    return ministry_for_department(_department_from_app_or_db(app_name, db_name))


def cluster_for_app(app_name: str | None, db_name: str | None = None) -> str | None:
    return cluster_for_department(_department_from_app_or_db(app_name, db_name))


def ministry_for_db(db_name: str | None) -> str | None:
    return ministry_for_department(department_for_db(db_name))


def cluster_for_db(db_name: str | None) -> str | None:
    return cluster_for_department(department_for_db(db_name))
