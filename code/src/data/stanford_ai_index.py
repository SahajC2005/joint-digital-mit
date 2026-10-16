"""
Stanford AI Index — AI Activity components.

Source: Stanford HAI AI Index, annual since 2017 (2017 was first edition).
Country-level data per the project plan is requested directly from Stanford HAI.

If the data request is delayed or refused, this module supports a fallback
constructed from:
  - OpenAlex API: AI publications per capita (concept IDs for AI/ML)
  - WIPO patent data: patents in IPC G06N (machine learning / neural networks)
  - Crunchbase / PitchBook (optional, paid): AI private investment

Variables produced:
  - ai_pubs_pc       : AI publications per million population (log)
  - ai_patents_pc    : AI patents per million population (log)
  - ai_investment    : AI private investment, USD (log)
  - ai_workforce     : AI workforce share of LinkedIn employed users
"""

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from config.settings import DATA_RAW, DATA_INTERIM, SOURCES
from src.utils.country_codes import to_iso3, validate_panel_coverage
from src.utils.logging_setup import get_logger

logger = get_logger(__name__)


AI_INDEX_COLS = ["ai_pubs_pc", "ai_patents_pc", "ai_investment", "ai_workforce"]


def _raw_dir() -> Path:
    return DATA_RAW / "stanford_ai_index"


def load_stanford_data() -> pd.DataFrame:
    """
    Load Stanford-provided country-year file if available.

    Expected: data/raw/stanford_ai_index/stanford_country_panel_<vintage>.csv
    """
    raw_dir = _raw_dir()
    candidates = list(raw_dir.glob("stanford_country_panel_*.csv"))
    if not candidates:
        logger.warning(
            "No Stanford AI Index country panel file found. "
            "Falling back to OpenAlex+WIPO. Request data via Stanford HAI."
        )
        return pd.DataFrame(columns=["iso3", "year"] + AI_INDEX_COLS)

    fpath = sorted(candidates)[-1]
    logger.info(f"reading Stanford AI Index from {fpath.name}")
    df = pd.read_csv(fpath)

    # Adjust to known column layout once data received (placeholder names)
    rename = {
        "country": "_country_raw",
        "publications_ai": "ai_pubs_pc",
        "patents_ai": "ai_patents_pc",
        "investment_ai_usd": "ai_investment",
        "linkedin_ai_share": "ai_workforce",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    df["iso3"] = to_iso3(df["_country_raw"], source="stanford")
    df = df.dropna(subset=["iso3"]).drop(columns=[c for c in ["_country_raw"] if c in df.columns])

    # Log-transform skewed measures (publications, patents, investment)
    for col in ["ai_pubs_pc", "ai_patents_pc", "ai_investment"]:
        if col in df.columns:
            df[col] = np.log1p(pd.to_numeric(df[col], errors="coerce"))

    return df[["iso3", "year"] + [c for c in AI_INDEX_COLS if c in df.columns]]


def load_openalex_fallback() -> pd.DataFrame:
    """
    Fallback: query OpenAlex for AI publications by country-year.

    Skeleton only - implement when needed. OpenAlex has free API access.
    Concept IDs for AI: C154945302 (artificial intelligence),
    C119857082 (machine learning).

    See https://docs.openalex.org/ for API details.
    """
    logger.info("OpenAlex fallback not yet implemented; returning empty frame")
    return pd.DataFrame(columns=["iso3", "year", "ai_pubs_pc"])


def clean_stanford_ai_index() -> pd.DataFrame:
    """
    Primary entry: try Stanford direct, fall back to constructed.
    """
    df = load_stanford_data()
    if len(df) == 0:
        df = load_openalex_fallback()

    if len(df) == 0:
        logger.error("No Stanford AI Index data loaded; downstream G index will use GARI+AIPI only")

    diagnostics = validate_panel_coverage(df) if len(df) > 0 else {}
    logger.info(f"Stanford AI Index clean panel: {diagnostics}")
    return df


def main():
    DATA_INTERIM.mkdir(parents=True, exist_ok=True)
    out_path = DATA_INTERIM / "stanford_ai_index_clean.parquet"
    clean_stanford_ai_index().to_parquet(out_path, index=False)
    logger.info(f"wrote {out_path}")


if __name__ == "__main__":
    main()
