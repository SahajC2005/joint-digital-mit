"""
FinTech index construction.

Implements Chhetri-Koirala (2026) eqs. (10) through (13):

  Z_k,it = (X_k,it - mean) / sd               eq. (10)
  F_it = (1/4) * (Z_DP + Z_MA + Z_MP + Z_DA)  eq. (11)
  Access_it = (1/2) * (Z_MA + Z_DA)           eq. (12)
  Usage_it  = (1/2) * (Z_DP + Z_MP)           eq. (13)

Plus PCA robustness check per the original paper.
"""

import pandas as pd

from config.settings import DATA_INTERIM, INDEX_PARAMS
from src.utils.data_helpers import equal_weighted_index, pca_index, zscore
from src.utils.logging_setup import get_logger

logger = get_logger(__name__)


# Component name -> Findex column name mapping
COMPONENT_MAP = {
    "digital_payment_usage": "findex_dp",
    "mobile_money_account": "findex_ma",
    "digital_merchant_payments": "findex_mp",
    "digital_account_engagement": "findex_da",
}


def construct_fintech_index(findex_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build the FinTech index F and its Access/Usage decompositions.

    Parameters
    ----------
    findex_df : DataFrame
        Output of src.data.findex.clean_findex (cleaned, annualized panel).

    Returns
    -------
    DataFrame with columns:
      iso3, year, F, F_pca, F_access, F_usage,
      Z_findex_dp, Z_findex_ma, Z_findex_mp, Z_findex_da
    """
    df = findex_df.copy()

    # Z-score each component across the full panel (Chhetri-Koirala eq. 10)
    for label, raw_col in COMPONENT_MAP.items():
        if raw_col not in df.columns:
            logger.error(f"FinTech component missing: {raw_col}")
            df[raw_col] = pd.NA
        df[f"Z_{raw_col}"] = zscore(df[raw_col])

    # Equal-weighted composite (eq. 11)
    df["F"] = equal_weighted_index(
        df,
        components=[COMPONENT_MAP[c] for c in INDEX_PARAMS["fintech"]["components"]],
        standardize=True,
    )

    # PCA robustness
    df["F_pca"], pca_diag = pca_index(
        df,
        components=[COMPONENT_MAP[c] for c in INDEX_PARAMS["fintech"]["components"]],
    )
    logger.info(f"FinTech PCA diagnostics: {pca_diag}")

    # Access/Usage decompositions (eqs. 12 and 13)
    df["F_access"] = equal_weighted_index(
        df,
        components=[
            COMPONENT_MAP[c]
            for c in INDEX_PARAMS["fintech"]["decomposition"]["access"]
        ],
        standardize=True,
    )
    df["F_usage"] = equal_weighted_index(
        df,
        components=[
            COMPONENT_MAP[c]
            for c in INDEX_PARAMS["fintech"]["decomposition"]["usage"]
        ],
        standardize=True,
    )

    keep_cols = ["iso3", "year", "F", "F_pca", "F_access", "F_usage"] + [
        f"Z_{c}" for c in COMPONENT_MAP.values()
    ]
    return df[keep_cols].copy()


def main():
    findex_clean = pd.read_parquet(DATA_INTERIM / "findex_clean.parquet")
    F = construct_fintech_index(findex_clean)
    F.to_parquet(DATA_INTERIM / "fintech_index.parquet", index=False)
    logger.info(f"FinTech index: {F['F'].notna().sum()} country-year obs with F")


if __name__ == "__main__":
    main()
