"""
Country-code harmonization.

All datasets are converted to ISO 3166-1 alpha-3 codes. This module
documents every non-trivial mapping so merge failures are traceable.

Common pitfalls handled:
  - Kosovo (no official ISO3; use 'XKX' per IMF/WB convention)
  - Channel Islands, West Bank/Gaza, Taiwan: aggregate or country-specific
  - Historical entities (USSR, Yugoslavia, Czechoslovakia) excluded
  - Multiple names for same country (Cote d'Ivoire / Ivory Coast)
"""

from typing import Iterable, Optional

import pandas as pd
import country_converter as coco

from src.utils.logging_setup import get_logger

logger = get_logger(__name__)

# Single converter instance; coco loads ~20MB of mapping data
_CC = coco.CountryConverter()


# ---- Manual overrides for known edge cases ----
# Format: {raw_name_lowercased: ISO3}
MANUAL_OVERRIDES = {
    "kosovo": "XKX",
    "kosovo, republic of": "XKX",
    "west bank and gaza": "PSE",
    "palestine, state of": "PSE",
    "taiwan, china": "TWN",
    "taiwan, province of china": "TWN",
    "taiwan province of china": "TWN",
    "chinese taipei": "TWN",
    "korea, dem. people's rep.": "PRK",
    "korea, rep.": "KOR",
    "korea, republic of": "KOR",
    "south korea": "KOR",
    "lao pdr": "LAO",
    "macao sar, china": "MAC",
    "hong kong sar, china": "HKG",
    "egypt, arab rep.": "EGY",
    "iran, islamic rep.": "IRN",
    "syrian arab republic": "SYR",
    "venezuela, rb": "VEN",
    "yemen, rep.": "YEM",
    "turkiye": "TUR",
    "turkey": "TUR",
    "cote d'ivoire": "CIV",
    "ivory coast": "CIV",
    "eswatini": "SWZ",
    "swaziland": "SWZ",  # pre-2018 name
    "czechia": "CZE",
    "czech republic": "CZE",
    "north macedonia": "MKD",
    "macedonia, fyr": "MKD",
    "cabo verde": "CPV",
    "cape verde": "CPV",
    "myanmar": "MMR",
    "burma": "MMR",
    "congo, dem. rep.": "COD",
    "congo, rep.": "COG",
}


# ---- Entities to drop (regional aggregates, historical states) ----
DROP_ENTITIES = {
    "world", "high income", "low income", "middle income",
    "upper middle income", "lower middle income",
    "east asia & pacific", "europe & central asia", "latin america & caribbean",
    "middle east & north africa", "north america", "south asia", "sub-saharan africa",
    "oecd members", "european union", "euro area", "arab world",
    "ussr", "yugoslavia", "czechoslovakia", "yugoslav sfr",
    "netherlands antilles",
}


def to_iso3(
    names: Iterable[str],
    source: str = "unknown",
    strict: bool = False,
) -> pd.Series:
    """
    Convert a series of country names/codes to ISO3.

    Parameters
    ----------
    names : iterable of str
        Raw country identifiers (names, ISO2, ISO3, numeric).
    source : str
        Dataset name for logging unmapped values.
    strict : bool
        If True, raise on any unmapped value. If False, return NaN.

    Returns
    -------
    pd.Series of ISO3 codes, NaN where unmapped or dropped.
    """
    s = pd.Series(names).astype(str).str.strip()
    s_lower = s.str.lower()

    # Drop regional/historical aggregates
    is_aggregate = s_lower.isin(DROP_ENTITIES)
    if is_aggregate.any():
        n_dropped = int(is_aggregate.sum())
        logger.info(f"[{source}] dropping {n_dropped} aggregate/historical entries")

    # Manual overrides
    mapped = s_lower.map(MANUAL_OVERRIDES)

    # For the rest, use coco
    needs_coco = mapped.isna() & ~is_aggregate
    if needs_coco.any():
        coco_result = _CC.convert(
            names=s.loc[needs_coco].tolist(),
            to="ISO3",
            not_found=None,
        )
        if isinstance(coco_result, str):
            coco_result = [coco_result]
        mapped.loc[needs_coco] = coco_result

    # Final NaN out
    mapped.loc[is_aggregate] = None
    unmapped = mapped.isna() & ~is_aggregate
    if unmapped.any():
        unique_unmapped = s.loc[unmapped].unique()
        logger.warning(
            f"[{source}] could not map {len(unique_unmapped)} unique countries: "
            f"{sorted(unique_unmapped)[:10]}{'...' if len(unique_unmapped) > 10 else ''}"
        )
        if strict:
            raise ValueError(f"[{source}] unmapped countries with strict=True")

    return mapped


def validate_panel_coverage(
    df: pd.DataFrame,
    expected_countries: Optional[int] = None,
    expected_years: Optional[tuple] = None,
) -> dict:
    """
    Sanity-check a country-year panel.

    Reports duplicate (country, year) pairs, country count, year range,
    and missingness rates. Returns diagnostics dict for logging.
    """
    assert {"iso3", "year"}.issubset(df.columns), "panel must have iso3 and year"

    dupes = df.duplicated(subset=["iso3", "year"]).sum()
    n_countries = df["iso3"].nunique()
    year_min, year_max = df["year"].min(), df["year"].max()

    diagnostics = {
        "rows": len(df),
        "n_countries": n_countries,
        "year_range": (int(year_min), int(year_max)),
        "duplicates": int(dupes),
        "missing_pct": df.isna().mean().to_dict(),
    }

    if dupes > 0:
        logger.error(f"panel has {dupes} duplicate (iso3, year) rows")
    if expected_countries and n_countries < expected_countries:
        logger.warning(
            f"only {n_countries} countries; expected at least {expected_countries}"
        )
    if expected_years:
        if year_min > expected_years[0] or year_max < expected_years[1]:
            logger.warning(
                f"year range {year_min}-{year_max} narrower than expected "
                f"{expected_years[0]}-{expected_years[1]}"
            )

    return diagnostics
