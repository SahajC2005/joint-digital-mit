"""
IV instruments for F, G, and FG.

Two external instruments, each motivated by a published identification strategy:

1. Submarine cable arrival (Hjort-Poulsen 2019, AER)
   Indicator: 1 if country i was connected to a backbone submarine cable
   in or before year t. Plausibly exogenous because cable routing is driven
   by engineering and geographic considerations.

2. Distance-to-frontier exposure
   Z^frontier_it = (1 / (d_{i,USA} + d_{i,CHN})) * G^frontier_t
   where d is CEPII gravity distance and G^frontier is the AI capability
   index at the global frontier. Captures spillover exposure independent
   of own-country development.

System GMM uses lagged levels/differences from these and other variables
as internal instruments; handled in src/analysis/estimators.py.
"""

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from config.settings import DATA_RAW, DATA_INTERIM
from src.utils.country_codes import to_iso3
from src.utils.logging_setup import get_logger

logger = get_logger(__name__)


# ---- Submarine cable instrument ----

def load_cable_arrivals() -> pd.DataFrame:
    """
    Country-level submarine cable backbone connection year.

    Expected file: data/raw/cables/cable_arrivals.csv with columns:
      iso3, first_backbone_year

    Compiled manually from TeleGeography submarine cable map. Document
    sources in data/raw/cables/SOURCES.md.
    """
    fpath = DATA_RAW / "cables" / "cable_arrivals.csv"
    if not fpath.exists():
        logger.warning(f"Cable arrivals file missing: {fpath}")
        return pd.DataFrame(columns=["iso3", "first_backbone_year"])

    return pd.read_csv(fpath)


def build_cable_iv(years: range) -> pd.DataFrame:
    """
    Construct the panel-format cable instrument:
      Z_cable_it = 1 if year >= first_backbone_year for country i
    """
    cables = load_cable_arrivals()
    if len(cables) == 0:
        return pd.DataFrame(columns=["iso3", "year", "z_cable"])

    out = []
    for _, row in cables.iterrows():
        for y in years:
            out.append({
                "iso3": row["iso3"],
                "year": y,
                "z_cable": int(y >= row["first_backbone_year"]),
            })
    df = pd.DataFrame(out)
    logger.info(f"cable IV: {df['iso3'].nunique()} countries, {df['z_cable'].sum()} 1s")
    return df


# ---- Distance-to-frontier instrument ----

FRONTIER_COUNTRIES = ["USA", "CHN"]  # primary AI frontier; sensitivity to USA-only


def load_cepii_gravity() -> pd.DataFrame:
    """
    Load CEPII gravity distance for distance-to-frontier IV.

    Expected file: data/raw/cepii/dist_cepii.dta or .csv
    Columns: iso3_o, iso3_d, distw_harmonic
    """
    fpath = DATA_RAW / "cepii" / "dist_cepii.csv"
    if not fpath.exists():
        logger.warning(f"CEPII gravity file missing: {fpath}")
        return pd.DataFrame()
    return pd.read_csv(fpath)


def build_frontier_iv(
    g_panel: pd.DataFrame,
    cepii: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Construct distance-weighted frontier exposure instrument.

    Z^frontier_it = sum_{f in frontier} (G_ft / d_if)
    Inverse-distance weighting; standardized across the panel.

    Parameters
    ----------
    g_panel : DataFrame
        Country-year G index values; used to extract frontier G_ft.
    cepii : DataFrame, optional
        Gravity distances. Loaded from disk if None.
    """
    if cepii is None:
        cepii = load_cepii_gravity()
    if len(cepii) == 0:
        return pd.DataFrame(columns=["iso3", "year", "z_frontier"])

    # Frontier G_ft series
    frontier_g = (
        g_panel[g_panel["iso3"].isin(FRONTIER_COUNTRIES)]
        .pivot(index="year", columns="iso3", values="G")
    )

    # Build country->frontier distance map
    dist_to_frontier = (
        cepii[cepii["iso3_d"].isin(FRONTIER_COUNTRIES)]
        .pivot(index="iso3_o", columns="iso3_d", values="distw_harmonic")
    )

    # Z_it = sum_f (G_ft / d_if), normalized
    out_rows = []
    for iso, dist_row in dist_to_frontier.iterrows():
        for year in frontier_g.index:
            z = 0.0
            for f in FRONTIER_COUNTRIES:
                if f in dist_row.index and f in frontier_g.columns:
                    d = dist_row[f]
                    g = frontier_g.loc[year, f]
                    if pd.notna(d) and pd.notna(g) and d > 0:
                        z += g / d
            out_rows.append({"iso3": iso, "year": year, "z_frontier": z})

    df = pd.DataFrame(out_rows)
    # Standardize
    df["z_frontier"] = (df["z_frontier"] - df["z_frontier"].mean()) / df["z_frontier"].std()
    return df


def main():
    DATA_INTERIM.mkdir(parents=True, exist_ok=True)
    years = range(2010, 2025)

    cable_iv = build_cable_iv(years)
    cable_iv.to_parquet(DATA_INTERIM / "iv_cable.parquet", index=False)

    # Frontier IV requires G panel; built later in 03_construct_indices.py
    logger.info("cable IV written; frontier IV built downstream")


if __name__ == "__main__":
    main()
