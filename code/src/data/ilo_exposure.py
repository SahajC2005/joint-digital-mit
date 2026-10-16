"""
ILO Working Paper 140 - Generative AI Occupational Exposure (rho).

Source: Gmyrek et al., ILO WP 140, 2025.
Country coverage: ~84 countries with harmonized labor microdata.

Per the project spec, rho is treated as TIME-INVARIANT (country-level
constant). The variable captures the share of national employment in
occupations with high GenAI exposure.

Primary measure: rho_gradient4 = share of employment in Gradient 4
(highest exposure, ~3.3% of global employment).

Robustness measure: rho_any = share in any of Gradients 1-4
(~25% of global employment).
"""

from pathlib import Path

import pandas as pd

from config.settings import DATA_RAW, DATA_INTERIM
from src.utils.country_codes import to_iso3, validate_panel_coverage
from src.utils.logging_setup import get_logger

logger = get_logger(__name__)


RHO_COLS = ["rho_gradient4", "rho_any_exposure"]


def clean_ilo_exposure() -> pd.DataFrame:
    """
    Load the country-level exposure table from ILO WP 140 supplementary data.

    Expected file: data/raw/ilo_wp140/ILO_WP140_country_exposure.xlsx
    """
    raw_dir = DATA_RAW / "ilo_wp140"
    fpath = raw_dir / "ILO_WP140_country_exposure.xlsx"
    if not fpath.exists():
        raise FileNotFoundError(
            f"Missing ILO WP 140 country exposure file: {fpath}\n"
            "Download supplementary data from "
            "https://www.ilo.org/publications/generative-ai-and-jobs-refined-global-index-occupational-exposure"
        )

    df = pd.read_excel(fpath)

    rename = {
        "Country": "_country_raw",
        "Country name": "_country_raw",
        "Share in Gradient 4 (%)": "rho_gradient4",
        "Share in any gradient (%)": "rho_any_exposure",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    df["iso3"] = to_iso3(df["_country_raw"], source="ilo_wp140")
    df = df.dropna(subset=["iso3"]).drop(columns="_country_raw")

    # Convert from percentage (0-100) to share (0-1) for theoretical consistency
    for col in RHO_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce") / 100.0

    # No 'year' column - rho is time-invariant by design
    out = df[["iso3"] + [c for c in RHO_COLS if c in df.columns]]

    logger.info(f"ILO rho: {len(out)} countries with exposure data")
    return out


def main():
    DATA_INTERIM.mkdir(parents=True, exist_ok=True)
    out_path = DATA_INTERIM / "ilo_rho_clean.parquet"
    clean_ilo_exposure().to_parquet(out_path, index=False)
    logger.info(f"wrote {out_path}")


if __name__ == "__main__":
    main()
