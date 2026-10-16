"""
Macro controls: growth, controls, human capital, institutions, income groups.

Sources:
  - WDI via wbdata API: growth, trade, inflation, investment, etc.
  - PWT 10.01: human capital index (hc), real GDP
  - Barro-Lee: tertiary education share (backup human capital)
  - WGI: government effectiveness and other governance indicators
  - WB income classification: MI dummy
"""

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from config.settings import DATA_RAW, DATA_INTERIM, SOURCES, YEAR_MIN, YEAR_MAX
from src.utils.country_codes import to_iso3, validate_panel_coverage
from src.utils.logging_setup import get_logger

logger = get_logger(__name__)


def load_wdi() -> pd.DataFrame:
    """
    Load WDI indicators specified in SOURCES['wdi']['indicators'].

    Real implementation uses wbdata. For now, expects pre-downloaded CSV.
    """
    fpath = DATA_RAW / "wdi" / "wdi_panel.csv"
    if not fpath.exists():
        logger.warning(f"WDI panel missing: {fpath}; download via wbdata")
        return pd.DataFrame()

    df = pd.read_csv(fpath)
    df["iso3"] = to_iso3(df["country"], source="wdi")
    df = df.dropna(subset=["iso3"])

    # Rename to short names per config
    rename = SOURCES["wdi"]["indicators"]
    df = df.rename(columns=rename)

    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df = df.query(f"{YEAR_MIN} <= year <= {YEAR_MAX}")

    cols = ["iso3", "year"] + list(rename.values())
    return df[[c for c in cols if c in df.columns]]


def load_pwt() -> pd.DataFrame:
    """
    Load Penn World Tables 10.01 — human capital and GDP.
    """
    fpath = DATA_RAW / "pwt" / "pwt1001.xlsx"
    if not fpath.exists():
        logger.warning(f"PWT file missing: {fpath}")
        return pd.DataFrame(columns=["iso3", "year", "hc", "rgdpna"])

    df = pd.read_excel(fpath, sheet_name="Data")
    df["iso3"] = df["countrycode"]
    df = df.rename(columns={"hc": "human_capital_pwt"})
    return df[["iso3", "year", "human_capital_pwt", "rgdpna", "pop"]]


def load_wgi() -> pd.DataFrame:
    """
    Load Worldwide Governance Indicators.

    WGI publishes one Excel file per dimension. For institutional quality I,
    primary measure is government_effectiveness; we also store others for
    sensitivity.
    """
    raw_dir = DATA_RAW / "wgi"
    frames = []
    for dim in SOURCES["wgi"]["dimensions"]:
        fpath = raw_dir / f"wgi_{dim}.xlsx"
        if not fpath.exists():
            logger.warning(f"WGI {dim} missing: {fpath}")
            continue
        # WGI files have countries as rows, years as columns (wide).
        wide = pd.read_excel(fpath, sheet_name=0)
        wide["iso3"] = to_iso3(wide.get("Country/Territory", wide.iloc[:, 0]), source=f"wgi_{dim}")
        wide = wide.dropna(subset=["iso3"])
        long = wide.melt(
            id_vars=["iso3"],
            value_vars=[c for c in wide.columns if str(c).isdigit()],
            var_name="year",
            value_name=f"wgi_{dim}",
        )
        long["year"] = long["year"].astype(int)
        frames.append(long)

    if not frames:
        return pd.DataFrame()

    panel = frames[0]
    for f in frames[1:]:
        panel = panel.merge(f, on=["iso3", "year"], how="outer")
    return panel


def load_income_groups() -> pd.DataFrame:
    """
    World Bank income group classification, country-year long format.

    File: data/raw/wb_income_groups/income_groups_long.csv
    Columns expected: iso3, year, income_group ('L'/'LM'/'UM'/'H')
    """
    fpath = DATA_RAW / "wb_income_groups" / "income_groups_long.csv"
    if not fpath.exists():
        logger.warning(f"Income groups file missing: {fpath}")
        return pd.DataFrame()

    df = pd.read_csv(fpath)
    df["mi_dummy"] = df["income_group"].isin(["LM", "UM"]).astype(int)
    df["um_dummy"] = (df["income_group"] == "UM").astype(int)
    return df


def build_macro_panel() -> pd.DataFrame:
    """
    Assemble all macro controls into a single country-year frame.
    """
    wdi = load_wdi()
    pwt = load_pwt()
    wgi = load_wgi()
    inc = load_income_groups()

    panel = wdi
    for other in [pwt, wgi, inc]:
        if len(other) > 0:
            panel = panel.merge(other, on=["iso3", "year"], how="outer")

    # Primary institutions variable: government effectiveness (matches
    # Chhetri-Koirala Table 1 specification).
    if "wgi_government_effectiveness" in panel.columns:
        panel["institutions"] = panel["wgi_government_effectiveness"]

    diagnostics = validate_panel_coverage(panel)
    logger.info(f"Macro controls panel: {diagnostics}")
    return panel


def main():
    DATA_INTERIM.mkdir(parents=True, exist_ok=True)
    out_path = DATA_INTERIM / "macro_controls.parquet"
    build_macro_panel().to_parquet(out_path, index=False)
    logger.info(f"wrote {out_path}")


if __name__ == "__main__":
    main()
