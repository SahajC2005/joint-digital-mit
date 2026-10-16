"""
Knowledge-Intensive Services (KIS) employment share.

Two-source strategy:
  1. GGDC 10-Sector Database (long history, ~40 countries, to 2018)
  2. ILOSTAT employment by ISIC sector (broader coverage, 2000+)

GGDC is preferred for the McMillan-Rodrik structural transformation
decomposition (it has matching productivity data). ILOSTAT fills gaps
and extends to recent years.

KIS definition (Eurostat convention):
  ISIC Rev.4 sections J (ICT), K (Finance & Insurance),
  M (Professional, Scientific, Technical), P (Education).

GGDC mapping to these (10-sector classification):
  "Finance, insurance, real estate, business services" -> KIS
  "Community, social, personal services" -> partial KIS (includes education)
"""

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from config.settings import DATA_RAW, DATA_INTERIM
from src.utils.country_codes import to_iso3, validate_panel_coverage
from src.utils.logging_setup import get_logger

logger = get_logger(__name__)


def load_ggdc() -> pd.DataFrame:
    """
    Load GGDC 10-Sector employment shares and compute KIS share.
    """
    fpath = DATA_RAW / "ggdc_10sector" / "10SD_Database.xlsx"
    if not fpath.exists():
        logger.warning(f"GGDC file missing: {fpath}")
        return pd.DataFrame(columns=["iso3", "year", "kis_share_ggdc"])

    # Load employment ('EMP') sheet
    emp = pd.read_excel(fpath, sheet_name="EMP")

    # GGDC long format expected after some reshape; this is a skeleton.
    # Real implementation: pivot wide-format country-year-sector
    # into long, sum KIS sectors, divide by total non-agriculture.
    logger.info("GGDC loader skeleton - implement reshape on actual file")
    return pd.DataFrame(columns=["iso3", "year", "kis_share_ggdc"])


def load_ilostat() -> pd.DataFrame:
    """
    Load ILOSTAT employment-by-sector and compute KIS share.

    ILOSTAT API access via pandasdmx. Indicator: EMP_TEMP_SEX_ECO_NB_A.
    """
    raw_path = DATA_RAW / "ilostat" / "employment_by_sector.csv"
    if not raw_path.exists():
        logger.warning(f"ILOSTAT employment file missing: {raw_path}")
        return pd.DataFrame(columns=["iso3", "year", "kis_share_ilostat"])

    df = pd.read_csv(raw_path)
    # Long format: country, year, sex, classification, sector, value
    # KIS sectors at ISIC Rev.4 1-digit:
    kis_codes = ["J", "K", "M", "P"]

    # Total non-agriculture: all sections except A
    df["is_kis"] = df["sector"].isin(kis_codes)
    df["is_nonag"] = df["sector"] != "A"

    grouped = (
        df[df["sex"] == "SEX_T"]  # total, not sex-disaggregated
        .groupby(["iso3", "year"])
        .apply(lambda g: pd.Series({
            "kis_emp": g.loc[g["is_kis"], "value"].sum(),
            "nonag_emp": g.loc[g["is_nonag"], "value"].sum(),
        }))
        .reset_index()
    )
    grouped["kis_share_ilostat"] = np.where(
        grouped["nonag_emp"] > 0, grouped["kis_emp"] / grouped["nonag_emp"], np.nan
    )

    return grouped[["iso3", "year", "kis_share_ilostat"]]


def construct_kis_share() -> pd.DataFrame:
    """
    Combine GGDC and ILOSTAT into a single sigma_KIS series.

    Priority: GGDC when available (matched to productivity data for
    McMillan-Rodrik decomposition); ILOSTAT to fill and extend.
    """
    ggdc = load_ggdc()
    ilostat = load_ilostat()

    merged = ilostat.merge(ggdc, on=["iso3", "year"], how="outer")
    merged["sigma_kis"] = merged["kis_share_ggdc"].where(
        merged["kis_share_ggdc"].notna(), merged["kis_share_ilostat"]
    )

    diagnostics = validate_panel_coverage(merged)
    logger.info(f"KIS share panel: {diagnostics}")
    return merged.sort_values(["iso3", "year"]).reset_index(drop=True)


def main():
    DATA_INTERIM.mkdir(parents=True, exist_ok=True)
    out_path = DATA_INTERIM / "kis_share.parquet"
    construct_kis_share().to_parquet(out_path, index=False)
    logger.info(f"wrote {out_path}")


if __name__ == "__main__":
    main()
