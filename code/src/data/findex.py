"""
Global Findex acquisition and cleaning.

Source: World Bank Global Findex Database.
Waves: 2011, 2014, 2017, 2021, 2024.

Following Chhetri-Koirala (2026), constructs four components:
  - DP: digital payment usage (made/received digital payment)
  - MA: mobile money account ownership
  - MP: digital merchant payments
  - DA: digital account engagement

These are then z-scored and averaged in src/construct/fintech_index.py.

NOTE: This module currently provides the data contract. The actual
download requires either:
  (a) Manual download from the Findex portal into data/raw/findex/
  (b) Programmatic access via World Bank API (some indicators only)
The data contract below documents what the cleaned output must look like.
"""

from pathlib import Path
from typing import Optional

import pandas as pd

from config.settings import DATA_RAW, DATA_INTERIM, SOURCES
from src.utils.country_codes import to_iso3, validate_panel_coverage
from src.utils.data_helpers import interpolate_within_country
from src.utils.logging_setup import get_logger

logger = get_logger(__name__)


# ---- Output contract ----
# Cleaned Findex output (data/interim/findex_clean.parquet) has columns:
#   iso3 : str          ISO3 country code
#   year : int          year (annual, interpolated between waves)
#   wave : int          original wave year (NaN for interpolated rows)
#   findex_dp : float   digital payment usage, 0-100
#   findex_ma : float   mobile money account, 0-100
#   findex_mp : float   digital merchant payments, 0-100
#   findex_da : float   digital account engagement, 0-100

FINDEX_COLS = ["findex_dp", "findex_ma", "findex_mp", "findex_da"]


def _raw_findex_dir() -> Path:
    return DATA_RAW / "findex"


def load_raw_findex() -> pd.DataFrame:
    """
    Load all available Findex wave files from data/raw/findex/.

    Expected files: GlobalFindex_<year>.xlsx for year in {2011, 2014, 2017, 2021, 2024}.

    Each wave's microaggregate sheet has a 'Country' column and per-indicator columns.
    Indicator codes vary slightly across waves; mapping is centralized below.
    """
    raw_dir = _raw_findex_dir()
    if not raw_dir.exists():
        raise FileNotFoundError(
            f"Findex raw directory missing: {raw_dir}\n"
            f"Download wave files from {SOURCES['findex']['url']} "
            f"and place in {raw_dir}/."
        )

    # Wave-specific indicator code mapping (varies across waves)
    # Codes verified against Findex documentation; check before each wave update.
    wave_code_map = {
        2011: {
            "findex_dp": "made_or_received_digital_payment",
            "findex_ma": "mobile_money_account",
            "findex_mp": "merchant_digital_payment",
            "findex_da": "account_used_digital_channel",
        },
        2014: {
            "findex_dp": "made_or_received_digital_payment",
            "findex_ma": "mobile_account",
            "findex_mp": "used_a_mobile_phone_or_internet_to_pay_bills",
            "findex_da": "made_or_received_digital_payment",
        },
        2017: {
            "findex_dp": "fin45",
            "findex_ma": "fin11",
            "findex_mp": "fin22",
            "findex_da": "fin10",
        },
        2021: {
            "findex_dp": "fin45_t_d",
            "findex_ma": "fin11_t_d",
            "findex_mp": "fin22_t_d",
            "findex_da": "fin10_t_d",
        },
        2024: {
            "findex_dp": "fin45_t_d",
            "findex_ma": "fin11_t_d",
            "findex_mp": "fin22_t_d",
            "findex_da": "fin10_t_d",
        },
    }

    frames = []
    for wave in SOURCES["findex"]["waves"]:
        wave_file = raw_dir / f"GlobalFindex_{wave}.xlsx"
        if not wave_file.exists():
            logger.warning(f"Findex wave {wave} file missing: {wave_file}")
            continue

        logger.info(f"reading Findex wave {wave}")
        raw = pd.read_excel(wave_file, sheet_name="Country level")

        # Standardize country column name
        country_col = next(
            (c for c in raw.columns if c.lower() in ("country", "economy", "country name")),
            None,
        )
        if country_col is None:
            raise ValueError(f"no country column in {wave_file}")

        wave_df = pd.DataFrame({"_country_raw": raw[country_col]})
        wave_df["year"] = wave
        wave_df["wave"] = wave

        # Pull the four indicators
        for out_col, src_code in wave_code_map[wave].items():
            # Fuzzy match column name (Findex columns sometimes have unit suffixes)
            cols = [c for c in raw.columns if src_code in str(c).lower()]
            if not cols:
                logger.warning(
                    f"wave {wave}: indicator {src_code} -> {out_col} not found"
                )
                wave_df[out_col] = pd.NA
            else:
                wave_df[out_col] = pd.to_numeric(raw[cols[0]], errors="coerce")

        frames.append(wave_df)

    if not frames:
        raise RuntimeError("no Findex wave files loaded")

    return pd.concat(frames, ignore_index=True)


def clean_findex(raw: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """
    Harmonize country codes, drop aggregates, interpolate between waves.
    """
    if raw is None:
        raw = load_raw_findex()

    raw["iso3"] = to_iso3(raw["_country_raw"], source="findex")
    raw = raw.dropna(subset=["iso3"]).drop(columns="_country_raw")

    # Aggregate over duplicate country-year (rare but possible across sheets)
    raw = (
        raw.groupby(["iso3", "year"], as_index=False)
        .agg({**{c: "mean" for c in FINDEX_COLS}, "wave": "first"})
    )

    # Expand to annual frequency and interpolate within country
    countries = raw["iso3"].unique()
    years = range(raw["year"].min(), raw["year"].max() + 1)
    skeleton = pd.DataFrame(
        [(c, y) for c in countries for y in years],
        columns=["iso3", "year"],
    )
    panel = skeleton.merge(raw, on=["iso3", "year"], how="left")

    for col in FINDEX_COLS:
        panel = interpolate_within_country(panel, col)

    diagnostics = validate_panel_coverage(panel)
    logger.info(f"findex clean panel: {diagnostics}")

    return panel.sort_values(["iso3", "year"]).reset_index(drop=True)


def main():
    DATA_INTERIM.mkdir(parents=True, exist_ok=True)
    out_path = DATA_INTERIM / "findex_clean.parquet"
    clean_findex().to_parquet(out_path, index=False)
    logger.info(f"wrote {out_path}")


if __name__ == "__main__":
    main()
