"""
Project-wide configuration.

Centralizes paths, parameter values, data source URLs, and analysis settings.
Edit this file rather than hardcoding values in scripts.
"""

from pathlib import Path

# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_INTERIM = PROJECT_ROOT / "data" / "interim"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"

OUTPUT_TABLES = PROJECT_ROOT / "output" / "tables"
OUTPUT_FIGURES = PROJECT_ROOT / "output" / "figures"
OUTPUT_LOGS = PROJECT_ROOT / "output" / "logs"

# Final panel file
PANEL_PATH = DATA_PROCESSED / "panel.parquet"


# ============================================================
# PANEL DEFINITION
# ============================================================

# Time window - tentative. Final decision deferred per spec.
# Lower bound driven by Oxford GARI (starts 2017); upper bound by data
# availability lag. Sensitivity tested across these windows.
YEAR_MIN = 2011  # Earliest, for FinTech-only specifications
YEAR_MAX = 2024
AI_YEAR_MIN = 2017  # AI variables not reliable before this

# Country universe: all sovereign states with at least one observation in
# any variable. Exclusions documented in src/utils/country_codes.py.
COUNTRY_CODE = "iso3"  # standardize on ISO 3166-1 alpha-3


# ============================================================
# DATA SOURCES
# ============================================================
# Each entry: {name, url, file_format, citation, license, last_checked}
# Download dates and checksums logged in data/raw/MANIFEST.json

SOURCES = {
    # ---- FinTech (F) ----
    "findex": {
        "name": "Global Findex Database",
        "url": "https://www.worldbank.org/en/publication/globalfindex/Data",
        "format": "xlsx",
        "waves": [2011, 2014, 2017, 2021, 2024],
        "citation": "Demirguc-Kunt et al., World Bank",
        "license": "CC-BY-4.0",
        "indicators": [
            "fin45_t_d",   # made/received digital payment, % age 15+
            "fin11_t_d",   # mobile money account, % age 15+
            "fin22_t_d",   # made digital merchant payment, % age 15+
            "fin10_t_d",   # accessed account through digital channel, % age 15+
        ],
    },

    # ---- AI penetration (G) ----
    "oxford_gari": {
        "name": "Oxford Insights Government AI Readiness Index",
        "url": "https://oxfordinsights.com/ai-readiness/",
        "format": "xlsx",
        "years": list(range(2017, 2026)),
        "citation": "Oxford Insights, annual",
        "license": "CC-BY-SA-4.0",
        "subindices": [
            "government",
            "technology_sector",
            "data_infrastructure",
        ],
    },

    "stanford_ai_index": {
        "name": "Stanford AI Index - Global Vibrancy",
        "url": "https://hai.stanford.edu/ai-index",
        "format": "csv",  # via data request
        "years": list(range(2018, 2026)),
        "citation": "Stanford HAI, annual",
        "license": "CC-BY-ND-4.0 (verify with request)",
        "components_used": [
            "ai_publications_per_capita",
            "ai_patents_per_capita",
            "ai_private_investment_log",
            "ai_workforce_share",  # from LinkedIn data
        ],
        "notes": "Request data via Stanford HAI contact form; some components"
                 " derivable from OpenAlex + WIPO if request blocked.",
    },

    "imf_aipi": {
        "name": "IMF AI Preparedness Index",
        "url": "https://www.imf.org/external/datamapper/datasets/AIPI",
        "format": "csv",
        "years": [2023, 2024],  # snapshot, limited time variation
        "citation": "Cazzaniga et al., IMF Staff Discussion Note 24/01",
        "license": "Public",
        "subindices": [
            "digital_infrastructure",
            "human_capital_labor",
            "innovation_integration",
            "regulation_ethics",
        ],
    },

    # ---- AI task exposure (rho) - time-invariant per spec ----
    "ilo_wp140": {
        "name": "ILO Working Paper 140 - GenAI Occupational Exposure",
        "url": "https://www.ilo.org/publications/generative-ai-and-jobs",
        "format": "xlsx",
        "years": [2025],  # snapshot, used as time-invariant per design
        "citation": "Gmyrek et al., ILO WP 140, 2025",
        "license": "CC-BY-4.0",
        "country_coverage": 84,
        "measures": [
            "gradient_4_share",  # highest exposure share of employment
            "any_exposure_share",  # robustness
        ],
    },

    # ---- Knowledge-intensive services share (sigma_KIS) ----
    "ggdc_10sector": {
        "name": "GGDC 10-Sector Database",
        "url": "https://www.rug.nl/ggdc/productivity/10-sector/",
        "format": "xlsx",
        "years_range": [1950, 2018],
        "citation": "Timmer, de Vries, de Vries (2015) update",
        "license": "Public",
        "kis_sectors": [
            "Finance, insurance, real estate, business services",
            "Government services",
            "Community, social, personal services",
        ],
    },

    "ilostat_employment": {
        "name": "ILOSTAT Employment by Sector",
        "url": "https://ilostat.ilo.org/data/",
        "format": "csv",
        "years_range": [2000, 2024],
        "citation": "ILO Department of Statistics",
        "license": "CC-BY-4.0",
        "indicator_code": "EMP_TEMP_SEX_ECO_NB_A",
        "isic_rev4_kis": ["J", "K", "M", "P"],  # ICT, Finance, Professional, Education
    },

    # ---- Human capital (H) ----
    "pwt": {
        "name": "Penn World Tables",
        "url": "https://www.rug.nl/ggdc/productivity/pwt/",
        "format": "xlsx",
        "version": "10.01",
        "years_range": [1950, 2019],
        "citation": "Feenstra, Inklaar, Timmer (2015)",
        "license": "CC-BY-4.0",
        "variables": ["hc", "rgdpna", "pop", "emp", "ck"],
    },

    "barro_lee": {
        "name": "Barro-Lee Educational Attainment",
        "url": "http://www.barrolee.com/",
        "format": "xlsx",
        "years_range": [1950, 2015],  # quinquennial, project forward
        "citation": "Barro and Lee (2013)",
        "license": "Public",
        "variables": ["lyr_total", "yr_sch_tert", "pct_sch_tert"],
    },

    # ---- Institutions (I) ----
    "wgi": {
        "name": "Worldwide Governance Indicators",
        "url": "https://www.worldbank.org/en/publication/worldwide-governance-indicators",
        "format": "xlsx",
        "years_range": [1996, 2023],
        "citation": "Kaufmann, Kraay, Mastruzzi",
        "license": "Public",
        "dimensions": [
            "voice_accountability",
            "political_stability",
            "government_effectiveness",
            "regulatory_quality",
            "rule_of_law",
            "control_of_corruption",
        ],
    },

    # ---- Growth and controls ----
    "wdi": {
        "name": "World Development Indicators",
        "url": "https://databank.worldbank.org/source/world-development-indicators",
        "format": "csv",
        "citation": "World Bank",
        "license": "CC-BY-4.0",
        "indicators": {
            "NY.GDP.PCAP.KD.ZG": "gdp_pc_growth",
            "NY.GDP.PCAP.PP.KD": "gdp_pc_ppp",
            "NE.TRD.GNFS.ZS": "trade_pct_gdp",
            "FP.CPI.TOTL.ZG": "inflation",
            "NE.GDI.TOTL.ZS": "investment_pct_gdp",
            "SP.POP.GROW": "pop_growth",
            "FS.AST.DOMS.GD.ZS": "credit_to_private_pct_gdp",
            "SE.SEC.ENRR": "secondary_enrollment",
        },
    },

    "wb_income_groups": {
        "name": "World Bank Country Income Classifications",
        "url": "https://datahelpdesk.worldbank.org/knowledgebase/articles/906519",
        "format": "xlsx",
        "citation": "World Bank Atlas method, annual reclassification",
        "license": "Public",
        "groups": ["L", "LM", "UM", "H"],
        "mit_definition": "LM or UM",  # primary definition; sensitivity to UM-only
    },

    # ---- IV instruments ----
    "telegeography_cables": {
        "name": "TeleGeography Submarine Cable Map",
        "url": "https://www.submarinecablemap.com/",
        "format": "manual_compilation",
        "citation": "TeleGeography; Hjort and Poulsen (2019) AER for methodology",
        "license": "Restricted - construct landing-year panel manually",
        "notes": "Hjort-Poulsen instrument: indicator for backbone connection year.",
    },

    "cepii_gravity": {
        "name": "CEPII Gravity Database",
        "url": "http://www.cepii.fr/CEPII/en/bdd_modele/bdd_modele_item.asp?id=8",
        "format": "csv",
        "citation": "CEPII, multiple years",
        "license": "Public",
        "variables": ["distw_harmonic", "comlang_off", "contig"],
        "notes": "Used for distance-to-frontier IV. Frontier = USA, CHN.",
    },
}


# ============================================================
# INDEX CONSTRUCTION PARAMETERS
# ============================================================

# Following Chhetri-Koirala eq. (10)-(13) for FinTech, extended for AI.
INDEX_PARAMS = {
    "fintech": {
        "method": "equal_weighted_zscore",
        "components": [
            "digital_payment_usage",
            "mobile_money_account",
            "digital_merchant_payments",
            "digital_account_engagement",
        ],
        "robustness": ["pca_first_component"],
        "decomposition": {
            "access": ["mobile_money_account", "digital_account_engagement"],
            "usage": ["digital_payment_usage", "digital_merchant_payments"],
        },
    },
    "ai": {
        "method": "equal_weighted_zscore",
        "pillars": {
            "readiness": ["gari_government", "gari_tech_sector", "gari_data_infra"],
            "activity": ["ai_pubs_pc", "ai_patents_pc", "ai_investment_log", "ai_workforce"],
            "adoption": ["aipi_digital_infra", "aipi_human_capital", "aipi_innovation", "aipi_regulation"],
        },
        "robustness": ["pca_first_component", "individual_pillar_regressions"],
        "decomposition": {
            "access": ["gari_data_infra", "aipi_digital_infra"],
            "usage": ["ai_pubs_pc", "ai_patents_pc", "ai_workforce", "aipi_innovation"],
        },
    },
}


# ============================================================
# ANALYSIS PARAMETERS
# ============================================================

# Lag for endogeneity mitigation (Chhetri-Koirala convention)
DEFAULT_LAG = 1

# Convergence growth threshold for escape-frontier calibration (eq. 26)
# Set to historical median high-income GDP per capita growth
CONVERGENCE_THRESHOLD_G = 0.02

# Standard errors
CLUSTER_LEVELS = ["country", "region", "income_group"]
DEFAULT_CLUSTER = "country"

# Random seed for any sampling, bootstrap, etc.
SEED = 42

# Winsorization for robustness
WINSORIZE_PERCENTILES = (0.01, 0.99)


# ============================================================
# LOGGING
# ============================================================

LOG_FORMAT = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
LOG_LEVEL = "INFO"
