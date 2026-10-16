"""
Middle-Income Trap variables.

Three dependent constructs:

  1. mi_status: middle-income indicator at time t
     Primary: World Bank LM or UM classification
     Sensitivity: GDP-PC relative to USA (Eichengreen-Park-Shin convention,
       middle income = $10k-$20k 2005 PPP)

  2. slowdown_eps: Eichengreen-Park-Shin (2013) slowdown episode
     A country-year is in a slowdown if:
       (a) country was middle-income at t
       (b) 7-year average growth at t falls by >=2 pp from 7-year average
           ending at t-7
       (c) 7-year average growth at t < some threshold (typically 3.5%)
     We follow EPS exactly and document deviations.

  3. exit: discrete-time hazard target for MI->HI transition
     exit_it = 1 if country was middle income at t-1 and high income at t,
              0 if middle income at both t-1 and t,
              NaN otherwise (already high or low-income drop)
"""

from typing import Optional

import numpy as np
import pandas as pd

from config.settings import DATA_INTERIM, YEAR_MIN, YEAR_MAX
from src.utils.logging_setup import get_logger

logger = get_logger(__name__)


# Eichengreen-Park-Shin parameters
EPS_WINDOW = 7
EPS_GROWTH_DROP = 0.02  # 2 percentage point drop
EPS_GROWTH_THRESHOLD = 0.035  # 3.5% absolute growth threshold


def construct_mi_status(income_groups: pd.DataFrame) -> pd.DataFrame:
    """
    Construct middle-income dummy from World Bank classifications.
    """
    out = income_groups.copy()
    out["mi_status"] = out["income_group"].isin(["LM", "UM"]).astype(int)
    out["um_status"] = (out["income_group"] == "UM").astype(int)
    out["hi_status"] = (out["income_group"] == "H").astype(int)
    return out[["iso3", "year", "mi_status", "um_status", "hi_status", "income_group"]]


def construct_exit_indicator(mi_panel: pd.DataFrame) -> pd.DataFrame:
    """
    Exit_it = 1 if country transitioned MI -> H between t-1 and t.
    """
    df = mi_panel.sort_values(["iso3", "year"]).copy()
    df["mi_lag"] = df.groupby("iso3")["mi_status"].shift(1)
    df["hi_lag"] = df.groupby("iso3")["hi_status"].shift(1)

    # In risk set: was middle income last period
    df["at_risk"] = (df["mi_lag"] == 1).astype(int)

    # Exit: was MI last period, is HI this period
    df["exit"] = np.where(
        (df["mi_lag"] == 1) & (df["hi_status"] == 1),
        1,
        np.where(df["mi_lag"] == 1, 0, np.nan),
    )

    return df[["iso3", "year", "at_risk", "exit"]]


def _eps_slowdown_for_country(g: pd.DataFrame) -> pd.DataFrame:
    """
    Apply EPS criteria to a single country's growth series.

    Input must be sorted by year. Uses 'gdp_pc_growth' (annual, %).
    """
    g = g.sort_values("year").copy()
    g["growth_dec"] = g["gdp_pc_growth"] / 100.0  # convert pp to decimal

    # 7-year rolling mean ending at year t (inclusive)
    g["g7_t"] = g["growth_dec"].rolling(window=EPS_WINDOW, min_periods=EPS_WINDOW).mean()
    # 7-year mean ending at t-7
    g["g7_lag7"] = g["g7_t"].shift(EPS_WINDOW)

    g["drop_in_growth"] = g["g7_lag7"] - g["g7_t"]
    g["below_threshold"] = g["g7_t"] < EPS_GROWTH_THRESHOLD

    g["slowdown_eps"] = (
        (g["drop_in_growth"] >= EPS_GROWTH_DROP)
        & g["below_threshold"]
        & (g["mi_status"] == 1)
    ).astype(int)
    # Only valid where window is complete
    g.loc[g["g7_lag7"].isna(), "slowdown_eps"] = np.nan

    return g


def construct_slowdown_indicator(mi_growth_panel: pd.DataFrame) -> pd.DataFrame:
    """
    Compute EPS slowdown indicator country-by-country.

    Required columns: iso3, year, gdp_pc_growth, mi_status
    """
    required = {"iso3", "year", "gdp_pc_growth", "mi_status"}
    missing = required - set(mi_growth_panel.columns)
    if missing:
        raise KeyError(f"slowdown construction missing: {missing}")

    result = (
        mi_growth_panel.groupby("iso3", group_keys=False)
        .apply(_eps_slowdown_for_country)
    )
    n_slow = int(result["slowdown_eps"].sum())
    logger.info(f"EPS slowdown episodes identified: {n_slow}")
    return result[["iso3", "year", "slowdown_eps", "g7_t", "drop_in_growth"]]


def main():
    # Requires macro_controls and income_groups already in interim
    macro = pd.read_parquet(DATA_INTERIM / "macro_controls.parquet")

    mi_status = construct_mi_status(macro[["iso3", "year", "income_group"]])
    mi_status.to_parquet(DATA_INTERIM / "mi_status.parquet", index=False)

    exit_df = construct_exit_indicator(mi_status)
    exit_df.to_parquet(DATA_INTERIM / "exit_indicator.parquet", index=False)

    growth_panel = macro.merge(mi_status, on=["iso3", "year"])
    slowdown = construct_slowdown_indicator(growth_panel)
    slowdown.to_parquet(DATA_INTERIM / "slowdown_eps.parquet", index=False)


if __name__ == "__main__":
    main()
