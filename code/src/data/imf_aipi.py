"""
IMF AI Preparedness Index (AIPI).

Source: IMF Staff Discussion Note 24/01 (Cazzaniga et al., 2024).
URL: https://www.imf.org/external/datamapper/datasets/AIPI

Provides country-level scores on:
  - aipi_digital_infra
  - aipi_human_capital
  - aipi_innovation
  - aipi_regulation

Limited time variation (2023, 2024 vintages); use latest available as
country-level cross-sectional anchor for the Adoption pillar.
"""

from pathlib import Path

import pandas as pd

from config.settings import DATA_RAW, DATA_INTERIM, SOURCES
from src.utils.country_codes import to_iso3, validate_panel_coverage
from src.utils.logging_setup import get_logger

logger = get_logger(__name__)


AIPI_COLS = [
    "aipi_overall",
    "aipi_digital_infra",
    "aipi_human_capital",
    "aipi_innovation",
    "aipi_regulation",
]


def clean_imf_aipi() -> pd.DataFrame:
    """
    Load and harmonize IMF AIPI from data/raw/imf_aipi/.

    Expected file: AIPI_<vintage>.csv with country and four sub-index columns.
    """
    raw_dir = DATA_RAW / "imf_aipi"
    candidates = list(raw_dir.glob("AIPI*.csv")) + list(raw_dir.glob("AIPI*.xlsx"))
    if not candidates:
        raise FileNotFoundError(f"No IMF AIPI file in {raw_dir}")

    fpath = sorted(candidates)[-1]
    logger.info(f"reading IMF AIPI from {fpath.name}")

    if fpath.suffix == ".xlsx":
        df = pd.read_excel(fpath)
    else:
        df = pd.read_csv(fpath)

    rename = {
        "Country": "_country_raw",
        "country": "_country_raw",
        "Overall": "aipi_overall",
        "Digital Infrastructure": "aipi_digital_infra",
        "Human Capital and Labor Market Policies": "aipi_human_capital",
        "Innovation and Economic Integration": "aipi_innovation",
        "Regulation and Ethics": "aipi_regulation",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    df["iso3"] = to_iso3(df["_country_raw"], source="imf_aipi")
    df = df.dropna(subset=["iso3"]).drop(columns="_country_raw")

    # AIPI is essentially cross-sectional; assign to latest year for merge
    df["year"] = SOURCES["imf_aipi"]["years"][-1]

    diagnostics = validate_panel_coverage(df)
    logger.info(f"IMF AIPI clean: {diagnostics}")
    return df[["iso3", "year"] + [c for c in AIPI_COLS if c in df.columns]]


def main():
    DATA_INTERIM.mkdir(parents=True, exist_ok=True)
    out_path = DATA_INTERIM / "imf_aipi_clean.parquet"
    clean_imf_aipi().to_parquet(out_path, index=False)
    logger.info(f"wrote {out_path}")


if __name__ == "__main__":
    main()
