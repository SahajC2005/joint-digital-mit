"""
Oxford Insights Government AI Readiness Index (GARI).

Source: https://oxfordinsights.com/ai-readiness/
Years: 2017-2025 (8 editions as of writing)
License: CC-BY-SA-4.0

Data is published annually as PDF reports plus an Excel data file
("Index_Data_<YEAR>.xlsx" or similar). Methodology changed between
editions; this loader handles version differences and harmonizes
to a consistent set of three subindex variables:

  - gari_government : Government pillar score
  - gari_tech_sector : Technology Sector pillar score
  - gari_data_infra : Data and Infrastructure pillar score

The composite overall_score is also retained for validation but
NOT used in our AI index (we use subindices for more variance).

Methodology change warning: the 2019 edition restructured pillars
significantly. 2017-2018 data may need rescaling; we document but
do not silently homogenize.
"""

from pathlib import Path
from typing import Optional

import pandas as pd

from config.settings import DATA_RAW, DATA_INTERIM, SOURCES
from src.utils.country_codes import to_iso3, validate_panel_coverage
from src.utils.logging_setup import get_logger

logger = get_logger(__name__)


GARI_COLS = ["gari_government", "gari_tech_sector", "gari_data_infra", "gari_overall"]


# Per-year column mapping (Oxford changes labels each edition; verify on download)
YEAR_COLUMN_MAP = {
    2017: {  # 2017 had only an overall score
        "country": "Country",
        "gari_overall": "Score",
    },
    2019: {
        "country": "Country",
        "gari_government": "Governance",
        "gari_tech_sector": "Technology",
        "gari_data_infra": "Data",
        "gari_overall": "Overall",
    },
    2020: {
        "country": "Country",
        "gari_government": "Government Score",
        "gari_tech_sector": "Technology Sector Score",
        "gari_data_infra": "Data and Infrastructure Score",
        "gari_overall": "Total Score",
    },
    # Mapping continues for each year - skeleton; verify on actual download
    2021: {"country": "Country", "gari_government": "Government",
           "gari_tech_sector": "Technology Sector", "gari_data_infra": "Data and Infrastructure",
           "gari_overall": "Overall"},
    2022: {"country": "Country", "gari_government": "Government",
           "gari_tech_sector": "Technology Sector", "gari_data_infra": "Data and Infrastructure",
           "gari_overall": "Total Score"},
    2023: {"country": "Country", "gari_government": "Government",
           "gari_tech_sector": "Technology Sector", "gari_data_infra": "Data and Infrastructure",
           "gari_overall": "Total Score"},
    2024: {"country": "Country", "gari_government": "Government",
           "gari_tech_sector": "Technology Sector", "gari_data_infra": "Data and Infrastructure",
           "gari_overall": "Total Score"},
    2025: {"country": "Country", "gari_government": "Government",
           "gari_tech_sector": "Technology Sector", "gari_data_infra": "Data and Infrastructure",
           "gari_overall": "Total Score"},
}


def _raw_gari_dir() -> Path:
    return DATA_RAW / "oxford_gari"


def load_year(year: int) -> pd.DataFrame:
    """
    Load and harmonize a single GARI edition.
    """
    raw_dir = _raw_gari_dir()
    candidates = list(raw_dir.glob(f"*{year}*.xlsx"))
    if not candidates:
        logger.warning(f"GARI {year}: no file matching *{year}*.xlsx in {raw_dir}")
        return pd.DataFrame(columns=["iso3", "year"] + GARI_COLS)

    fpath = candidates[0]
    logger.info(f"reading GARI {year} from {fpath.name}")

    df = pd.read_excel(fpath, sheet_name=0)
    mapping = YEAR_COLUMN_MAP.get(year)
    if mapping is None:
        logger.error(f"no column mapping for GARI year {year}; skipping")
        return pd.DataFrame(columns=["iso3", "year"] + GARI_COLS)

    rename = {v: k for k, v in mapping.items() if v in df.columns and k != "country"}
    if mapping["country"] not in df.columns:
        logger.error(f"GARI {year}: country column '{mapping['country']}' missing")
        return pd.DataFrame(columns=["iso3", "year"] + GARI_COLS)

    df = df.rename(columns={mapping["country"]: "_country_raw", **rename})
    df["year"] = year
    df["iso3"] = to_iso3(df["_country_raw"], source=f"gari_{year}")
    df = df.dropna(subset=["iso3"]).drop(columns="_country_raw")

    # Ensure all expected columns exist
    for col in GARI_COLS:
        if col not in df.columns:
            df[col] = pd.NA

    return df[["iso3", "year"] + GARI_COLS]


def clean_gari() -> pd.DataFrame:
    """
    Stack all available GARI editions into a long panel.
    """
    frames = [load_year(y) for y in SOURCES["oxford_gari"]["years"]]
    frames = [f for f in frames if len(f) > 0]
    if not frames:
        raise RuntimeError("no GARI editions loaded")

    panel = pd.concat(frames, ignore_index=True)

    # Sanity check: pre-2019 has only overall score; flag for users
    pre_2019 = panel["year"] < 2019
    if pre_2019.any():
        n_pre = pre_2019.sum()
        logger.info(
            f"GARI: {n_pre} pre-2019 rows have only overall score (subindex NA). "
            f"Used for sensitivity, not main index."
        )

    diagnostics = validate_panel_coverage(panel, expected_countries=150)
    logger.info(f"GARI clean panel: {diagnostics}")

    return panel.sort_values(["iso3", "year"]).reset_index(drop=True)


def main():
    DATA_INTERIM.mkdir(parents=True, exist_ok=True)
    out_path = DATA_INTERIM / "gari_clean.parquet"
    clean_gari().to_parquet(out_path, index=False)
    logger.info(f"wrote {out_path}")


if __name__ == "__main__":
    main()
