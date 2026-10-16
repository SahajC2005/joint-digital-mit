"""
General-purpose data utilities used across the construction pipeline.
"""

from typing import Iterable, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

from config.settings import WINSORIZE_PERCENTILES
from src.utils.logging_setup import get_logger

logger = get_logger(__name__)


def zscore(s: pd.Series, ddof: int = 1) -> pd.Series:
    """
    Standardize to mean zero, unit variance using global sample.

    Implements Chhetri-Koirala eq. (10): Z = (X - mean) / sd.
    """
    mu = s.mean()
    sd = s.std(ddof=ddof)
    if sd == 0 or pd.isna(sd):
        logger.warning(f"zscore: zero variance in {s.name}, returning zeros")
        return pd.Series(0.0, index=s.index, name=s.name)
    return (s - mu) / sd


def winsorize(
    s: pd.Series,
    percentiles: Tuple[float, float] = WINSORIZE_PERCENTILES,
) -> pd.Series:
    """
    Cap values at given percentiles. Default 1%/99% from config.
    """
    low, high = s.quantile(percentiles[0]), s.quantile(percentiles[1])
    return s.clip(lower=low, upper=high)


def equal_weighted_index(
    df: pd.DataFrame,
    components: Iterable[str],
    standardize: bool = True,
) -> pd.Series:
    """
    Construct an equal-weighted composite index.

    Implements Chhetri-Koirala eq. (11):
        Index_it = (1/K) * sum_k Z_{k,it}

    Components are z-scored across the full panel before averaging.
    """
    components = list(components)
    missing = [c for c in components if c not in df.columns]
    if missing:
        raise KeyError(f"missing index components: {missing}")

    if standardize:
        zs = df[components].apply(zscore)
    else:
        zs = df[components]

    return zs.mean(axis=1)


def pca_index(
    df: pd.DataFrame,
    components: Iterable[str],
    standardize: bool = True,
) -> Tuple[pd.Series, dict]:
    """
    Construct the first principal component as an alternative composite.

    Used for robustness per Chhetri-Koirala (their PCA check).
    Returns the index and a diagnostics dict with variance explained
    and component loadings.

    Rows with any missing components are excluded from PCA fitting but
    the index value is NaN for them in the output.
    """
    components = list(components)
    X = df[components].copy()
    if standardize:
        X = X.apply(zscore)

    complete = X.dropna()
    if len(complete) < len(components):
        logger.error(
            f"pca_index: only {len(complete)} complete rows for "
            f"{len(components)} components"
        )

    pca = PCA(n_components=1)
    scores_complete = pca.fit_transform(complete.values).flatten()

    # Sign convention: positive loadings on average
    if pca.components_[0].mean() < 0:
        scores_complete = -scores_complete
        loadings = -pca.components_[0]
    else:
        loadings = pca.components_[0]

    index = pd.Series(np.nan, index=df.index, name="pca_index")
    index.loc[complete.index] = scores_complete

    diagnostics = {
        "variance_explained": float(pca.explained_variance_ratio_[0]),
        "loadings": dict(zip(components, loadings.tolist())),
        "n_obs_fitted": len(complete),
    }
    logger.info(
        f"pca_index: 1st component explains "
        f"{diagnostics['variance_explained']:.1%} of variance"
    )

    return index, diagnostics


def interpolate_within_country(
    df: pd.DataFrame,
    value_col: str,
    method: str = "linear",
    limit: Optional[int] = None,
) -> pd.DataFrame:
    """
    Linearly interpolate missing values within each country's time series.

    Used for Findex (triennial waves) and other irregular sources.
    Does NOT extrapolate beyond observed range by default.
    """
    df = df.sort_values(["iso3", "year"]).copy()
    df[value_col] = (
        df.groupby("iso3", group_keys=False)[value_col]
        .apply(lambda x: x.interpolate(method=method, limit=limit, limit_area="inside"))
    )
    return df


def build_balanced_skeleton(
    countries: Iterable[str],
    years: Iterable[int],
) -> pd.DataFrame:
    """
    Create a balanced (country x year) skeleton for merging.

    Every dataset gets left-joined onto this to make missingness explicit.
    """
    countries = sorted(set(countries))
    years = sorted(set(years))
    idx = pd.MultiIndex.from_product([countries, years], names=["iso3", "year"])
    return pd.DataFrame(index=idx).reset_index()
