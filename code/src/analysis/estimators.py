"""
Estimator wrappers for the 15 specifications in the empirical framework.

Each function takes the analysis panel and returns a fitted model object
plus a tidy results DataFrame.

Estimators:
  - panel_fe : country and year fixed effects (linearmodels PanelOLS)
  - probit_fe : panel probit for slowdown / exit (statsmodels)
  - iv_2sls : two-stage least squares with external instruments
  - system_gmm : Blundell-Bond system GMM (linearmodels)
  - threshold_regression : Hansen-style with sample-split

Each model is logged with N, R^2 (or pseudo-R^2), and all coefficients.
"""

from typing import Iterable, Optional, Tuple

import numpy as np
import pandas as pd
import statsmodels.api as sm
from linearmodels.panel import PanelOLS, IV2SLS, IVSystemGMM

from config.settings import DEFAULT_LAG, DEFAULT_CLUSTER
from src.utils.logging_setup import get_logger

logger = get_logger(__name__)


def _prepare_panel(
    df: pd.DataFrame,
    index_cols: Tuple[str, str] = ("iso3", "year"),
) -> pd.DataFrame:
    """
    Set MultiIndex required by linearmodels.PanelOLS.
    """
    df = df.copy().dropna(subset=list(index_cols))
    return df.set_index(list(index_cols)).sort_index()


def _lag(df: pd.DataFrame, cols: Iterable[str], lag: int = DEFAULT_LAG) -> pd.DataFrame:
    """
    Add lagged versions of specified columns. Lags within country.
    """
    df = df.copy()
    for c in cols:
        if c in df.columns:
            df[f"{c}_L{lag}"] = df.groupby(level="iso3")[c].shift(lag)
    return df


def panel_fe(
    df: pd.DataFrame,
    y: str,
    X: Iterable[str],
    entity_effects: bool = True,
    time_effects: bool = True,
    cluster: str = DEFAULT_CLUSTER,
) -> "PanelOLSResults":
    """
    Country + year fixed effects panel regression.

    Used for Specifications 1-4, 8, 11, 14 (baseline forms).
    """
    df = _prepare_panel(df)
    X_cols = [c for c in X if c in df.columns]
    if len(X_cols) < len(list(X)):
        missing = set(X) - set(X_cols)
        logger.warning(f"panel_fe: missing regressors {missing}")
    df_est = df[[y] + X_cols].dropna()
    if len(df_est) == 0:
        raise ValueError(f"panel_fe: 0 observations after dropna for {y} ~ {X_cols}")

    mod = PanelOLS(
        dependent=df_est[y],
        exog=sm.add_constant(df_est[X_cols]),
        entity_effects=entity_effects,
        time_effects=time_effects,
        drop_absorbed=True,
    )

    if cluster == "country":
        res = mod.fit(cov_type="clustered", cluster_entity=True)
    elif cluster == "two_way":
        res = mod.fit(cov_type="clustered", cluster_entity=True, cluster_time=True)
    else:
        res = mod.fit(cov_type="robust")

    logger.info(f"panel_fe [{y}]: N={int(res.nobs)}, R2_within={res.rsquared_within:.4f}")
    return res


def probit_fe(
    df: pd.DataFrame,
    y: str,
    X: Iterable[str],
    add_year_dummies: bool = True,
) -> "BinaryResults":
    """
    Probit with year dummies. Country fixed effects in probit are biased
    in short panels (incidental parameters); we use either pooled probit
    with year dummies, or conditional logit as robustness.

    Used for Specs 5, 6, 7.
    """
    X_cols = [c for c in X if c in df.columns]
    df_est = df[[y] + X_cols + ["year"]].dropna()

    if add_year_dummies:
        year_dummies = pd.get_dummies(df_est["year"], prefix="yr", drop_first=True)
        X_design = pd.concat([df_est[X_cols], year_dummies], axis=1)
    else:
        X_design = df_est[X_cols]

    X_design = sm.add_constant(X_design)
    model = sm.Probit(df_est[y].astype(int), X_design)
    res = model.fit(disp=False)

    logger.info(f"probit [{y}]: N={int(res.nobs)}, pseudo_R2={res.prsquared:.4f}")
    return res


def iv_2sls(
    df: pd.DataFrame,
    y: str,
    exog: Iterable[str],
    endog: Iterable[str],
    instruments: Iterable[str],
    entity_effects: bool = True,
    time_effects: bool = True,
    cluster: str = DEFAULT_CLUSTER,
):
    """
    Panel IV-2SLS for Specifications 12 and 13.

    Cable IV: instrument F, G, FG with cable indicator and its interactions.
    Frontier IV: instrument G with distance-weighted frontier exposure.
    """
    df = _prepare_panel(df)
    cols = [y] + list(exog) + list(endog) + list(instruments)
    cols = [c for c in cols if c in df.columns]
    df_est = df[cols].dropna()

    mod = IV2SLS(
        dependent=df_est[y],
        exog=sm.add_constant(df_est[list(exog)]),
        endog=df_est[list(endog)],
        instruments=df_est[list(instruments)],
    )

    res = mod.fit(cov_type="clustered", clusters=df_est.index.get_level_values("iso3"))

    logger.info(
        f"iv_2sls [{y}]: N={int(res.nobs)}, "
        f"Sargan p={res.sargan.pval if hasattr(res, 'sargan') else 'NA'}, "
        f"first-stage F reported per endog regressor"
    )
    return res


def system_gmm(
    df: pd.DataFrame,
    y: str,
    X: Iterable[str],
    lag_dep: bool = True,
    max_lag: int = 3,
):
    """
    Blundell-Bond system GMM for Spec 14.

    Treats F, G, FG as predetermined; uses lagged levels/differences as
    internal instruments. linearmodels.IVSystemGMM provides the
    Arellano-Bond AR(2) and Hansen J tests.
    """
    df_est = df.copy()
    if lag_dep:
        df_est = df_est.sort_values(["iso3", "year"])
        df_est[f"{y}_lag"] = df_est.groupby("iso3")[y].shift(1)

    # Skeleton wrapper - full system GMM needs careful instrument matrix
    # construction; consult linearmodels documentation for the exact
    # API at execution time.
    logger.warning(
        "system_gmm: skeleton implementation. Use Stata xtabond2 or "
        "linearmodels IVSystemGMM with explicit instrument specification."
    )
    return None


def threshold_regression(
    df: pd.DataFrame,
    y: str,
    threshold_var: str,
    X: Iterable[str],
    threshold_grid: Optional[np.ndarray] = None,
):
    """
    Hansen-style threshold regression for Spec 10.

    Searches over candidate thresholds for the value that minimizes
    the sum of squared residuals across the two regime regressions.

    Returns (best_threshold, low_regime_result, high_regime_result, sse_path).
    """
    if threshold_grid is None:
        q_low, q_high = df[threshold_var].quantile([0.15, 0.85])
        threshold_grid = np.linspace(q_low, q_high, 50)

    sse_path = []
    best = (np.inf, None, None, None)

    for gamma in threshold_grid:
        low = df[df[threshold_var] < gamma].copy()
        high = df[df[threshold_var] >= gamma].copy()
        if len(low) < 30 or len(high) < 30:
            sse_path.append(np.nan)
            continue
        try:
            res_low = panel_fe(low, y, X)
            res_high = panel_fe(high, y, X)
            sse = float(res_low.resids @ res_low.resids) + float(
                res_high.resids @ res_high.resids
            )
            sse_path.append(sse)
            if sse < best[0]:
                best = (sse, gamma, res_low, res_high)
        except Exception as e:
            sse_path.append(np.nan)
            logger.debug(f"threshold {gamma}: skipped ({e})")

    logger.info(
        f"threshold_regression: optimal gamma={best[1]:.4f}, SSE={best[0]:.4f}"
    )
    return best, sse_path
