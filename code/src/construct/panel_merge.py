"""
Master panel construction.

Joins all interim datasets onto a balanced (country x year) skeleton
to produce the final analysis panel saved to data/processed/panel.parquet.

The skeleton uses the union of countries with any data and the year range
configured in config/settings.py.
"""

import pandas as pd

from config.settings import DATA_INTERIM, DATA_PROCESSED, YEAR_MIN, YEAR_MAX
from src.utils.country_codes import validate_panel_coverage
from src.utils.data_helpers import build_balanced_skeleton
from src.utils.logging_setup import get_logger

logger = get_logger(__name__)


# Interim files to merge in. Order matters only for join logging.
INTERIM_TABLES = [
    "macro_controls.parquet",      # growth, controls, institutions, income group
    "fintech_index.parquet",       # F and decomposition
    "ai_index.parquet",            # G and decomposition
    "kis_share.parquet",           # sigma_KIS
    "mi_status.parquet",           # MI dummy
    "slowdown_eps.parquet",        # EPS slowdown indicator
    "exit_indicator.parquet",      # exit hazard target
    "iv_cable.parquet",            # submarine cable IV
]

# Time-invariant tables (no year column)
TIME_INVARIANT = [
    "ilo_rho_clean.parquet",       # rho_i
]


def assemble_panel() -> pd.DataFrame:
    """
    Build the balanced country-year panel and merge all sources.
    """
    # Collect country universe from all sources
    all_countries = set()
    all_years = set(range(YEAR_MIN, YEAR_MAX + 1))
    for f in INTERIM_TABLES + TIME_INVARIANT:
        fpath = DATA_INTERIM / f
        if not fpath.exists():
            logger.warning(f"interim file missing: {fpath}")
            continue
        df = pd.read_parquet(fpath)
        if "iso3" in df.columns:
            all_countries.update(df["iso3"].dropna().unique())

    panel = build_balanced_skeleton(all_countries, all_years)
    logger.info(f"skeleton: {len(panel)} country-year cells")

    # Merge each time-varying interim
    for f in INTERIM_TABLES:
        fpath = DATA_INTERIM / f
        if not fpath.exists():
            continue
        df = pd.read_parquet(fpath)
        if {"iso3", "year"}.issubset(df.columns):
            n_before = panel.shape[1]
            panel = panel.merge(df, on=["iso3", "year"], how="left", suffixes=("", f"_{f}"))
            logger.info(f"merged {f}: {panel.shape[1] - n_before} new columns")

    # Merge time-invariant
    for f in TIME_INVARIANT:
        fpath = DATA_INTERIM / f
        if not fpath.exists():
            continue
        df = pd.read_parquet(fpath)
        if "iso3" in df.columns and "year" not in df.columns:
            n_before = panel.shape[1]
            panel = panel.merge(df, on="iso3", how="left", suffixes=("", f"_{f}"))
            logger.info(f"merged time-invariant {f}: {panel.shape[1] - n_before} new columns")

    diagnostics = validate_panel_coverage(panel)
    logger.info(f"final panel: {diagnostics}")

    return panel


def main():
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    panel = assemble_panel()

    # Useful precomputed interactions to save in the panel
    if {"F", "G"}.issubset(panel.columns):
        panel["F_x_G"] = panel["F"] * panel["G"]
    if {"F", "institutions"}.issubset(panel.columns):
        panel["F_x_I"] = panel["F"] * panel["institutions"]
    if {"G", "institutions"}.issubset(panel.columns):
        panel["G_x_I"] = panel["G"] * panel["institutions"]
    if {"G", "human_capital_pwt"}.issubset(panel.columns):
        panel["G_x_H"] = panel["G"] * panel["human_capital_pwt"]
    if {"G", "sigma_kis"}.issubset(panel.columns):
        panel["G_x_KIS"] = panel["G"] * panel["sigma_kis"]
    if {"F", "G", "institutions"}.issubset(panel.columns):
        panel["F_x_G_x_I"] = panel["F"] * panel["G"] * panel["institutions"]

    # Displacement interaction: G * rho * (1-H) * (1-sigma_KIS)
    needed = {"G", "rho_gradient4", "human_capital_pwt", "sigma_kis"}
    if needed.issubset(panel.columns):
        # H needs to be normalized to [0,1] scale; PWT hc is roughly 1-4. Rescale.
        h_norm = (panel["human_capital_pwt"] - panel["human_capital_pwt"].min()) / (
            panel["human_capital_pwt"].max() - panel["human_capital_pwt"].min()
        )
        panel["displacement_term"] = (
            panel["G"] * panel["rho_gradient4"] * (1 - h_norm) * (1 - panel["sigma_kis"])
        )

    panel.to_parquet(DATA_PROCESSED / "panel.parquet", index=False)
    logger.info(f"wrote final panel: {DATA_PROCESSED / 'panel.parquet'}")


if __name__ == "__main__":
    main()
