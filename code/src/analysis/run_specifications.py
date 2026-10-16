"""
Run the empirical specifications and produce output tables.

Mapping of specifications to functions:
  Spec 1  - run_baseline_joint_digital
  Spec 2  - run_full_interaction
  Spec 3  - run_displacement
  Spec 4  - run_mit_interaction       (headline result)
  Spec 5  - run_slowdown_probit
  Spec 6  - run_exit_hazard
  Spec 7  - run_vulnerability_threshold
  Spec 8  - run_quadrant_heterogeneity
  Spec 9  - estimate_escape_frontier  (calibration; not regression)
  Spec 10 - run_threshold_regression
  Spec 11 - run_mediator_mcm_rodrik
  Spec 12 - run_iv_frontier
  Spec 13 - run_iv_cable
  Spec 14 - run_system_gmm
  Spec 15 - run_robustness_index_alternatives

Tables organized per the reporting structure in the empirical framework
section of the paper.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from stargazer.stargazer import Stargazer

from config.settings import (
    DATA_PROCESSED,
    OUTPUT_TABLES,
    DEFAULT_LAG,
    CONVERGENCE_THRESHOLD_G,
)
from src.analysis.estimators import (
    panel_fe,
    probit_fe,
    iv_2sls,
    system_gmm,
    threshold_regression,
    _lag,
)
from src.utils.logging_setup import get_logger

logger = get_logger(__name__)


# ----- Common variable lists -----

CONTROLS = [
    "gdp_pc_ppp_log",     # log GDP per capita
    "trade_pct_gdp",
    "inflation",
    "investment_pct_gdp",
    "pop_growth",
    "credit_to_private_pct_gdp",
    "secondary_enrollment",
]


def _add_log_gdp(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "gdp_pc_ppp" in df.columns:
        df["gdp_pc_ppp_log"] = np.log(df["gdp_pc_ppp"])
    return df


# ============================================================
# CORE SPECIFICATIONS
# ============================================================

def run_baseline_joint_digital(panel: pd.DataFrame):
    """
    Spec 1: g_it = a + b1 F + b2 G + b3 F*G + Gamma X + mu_i + lam_t + eps
    """
    df = _add_log_gdp(panel)
    df = _lag(df.set_index(["iso3", "year"]).sort_index(),
              ["F", "G", "F_x_G"] + CONTROLS).reset_index()

    X = [f"F_L{DEFAULT_LAG}", f"G_L{DEFAULT_LAG}", f"F_x_G_L{DEFAULT_LAG}"] + [
        f"{c}_L{DEFAULT_LAG}" for c in CONTROLS
    ]
    return panel_fe(df, y="gdp_pc_growth", X=X)


def run_full_interaction(panel: pd.DataFrame):
    """
    Spec 2: all interactions per theoretical eq. 23.
    """
    df = _add_log_gdp(panel)
    interaction_terms = ["F", "G", "F_x_G", "F_x_I", "G_x_I", "G_x_H", "G_x_KIS", "F_x_G_x_I"]
    df = _lag(df.set_index(["iso3", "year"]).sort_index(),
              interaction_terms + CONTROLS).reset_index()
    X = [f"{t}_L{DEFAULT_LAG}" for t in interaction_terms] + [
        f"{c}_L{DEFAULT_LAG}" for c in CONTROLS
    ]
    return panel_fe(df, y="gdp_pc_growth", X=X)


def run_displacement(panel: pd.DataFrame):
    """
    Spec 3: includes the labor displacement interaction term.
    """
    df = _add_log_gdp(panel)
    terms = ["F", "G", "F_x_G", "G_x_H", "G_x_KIS", "displacement_term"]
    df = _lag(df.set_index(["iso3", "year"]).sort_index(),
              terms + CONTROLS).reset_index()
    X = [f"{t}_L{DEFAULT_LAG}" for t in terms] + [
        f"{c}_L{DEFAULT_LAG}" for c in CONTROLS
    ]
    return panel_fe(df, y="gdp_pc_growth", X=X)


def run_mit_interaction(panel: pd.DataFrame):
    """
    Spec 4: F*G interacted with middle-income dummy.
    Headline test of joint digital MIT escape.
    """
    df = _add_log_gdp(panel)
    df = df.copy()
    df["F_x_MI"] = df["F"] * df["mi_status"]
    df["G_x_MI"] = df["G"] * df["mi_status"]
    df["F_x_G_x_MI"] = df["F"] * df["G"] * df["mi_status"]

    terms = ["F", "G", "F_x_G", "mi_status", "F_x_MI", "G_x_MI", "F_x_G_x_MI"]
    df = _lag(df.set_index(["iso3", "year"]).sort_index(),
              terms + CONTROLS).reset_index()
    X = [f"{t}_L{DEFAULT_LAG}" for t in terms] + [
        f"{c}_L{DEFAULT_LAG}" for c in CONTROLS
    ]
    return panel_fe(df, y="gdp_pc_growth", X=X)


def run_slowdown_probit(panel: pd.DataFrame):
    """
    Spec 5: probit on slowdown_eps.
    """
    df = _add_log_gdp(panel)
    df = _lag(df.set_index(["iso3", "year"]).sort_index(),
              ["F", "G", "F_x_G"] + CONTROLS).reset_index()
    X = [f"F_L{DEFAULT_LAG}", f"G_L{DEFAULT_LAG}", f"F_x_G_L{DEFAULT_LAG}"] + [
        f"{c}_L{DEFAULT_LAG}" for c in CONTROLS
    ]
    return probit_fe(df.dropna(subset=["slowdown_eps"]), y="slowdown_eps", X=X)


def run_exit_hazard(panel: pd.DataFrame):
    """
    Spec 6: discrete-time hazard for MI -> HI transition.
    """
    df = _add_log_gdp(panel)
    df = df[df["at_risk"] == 1].copy()
    df = _lag(df.set_index(["iso3", "year"]).sort_index(),
              ["F", "G", "F_x_G"] + CONTROLS).reset_index()
    X = [f"F_L{DEFAULT_LAG}", f"G_L{DEFAULT_LAG}", f"F_x_G_L{DEFAULT_LAG}"] + [
        f"{c}_L{DEFAULT_LAG}" for c in CONTROLS
    ]
    return probit_fe(df.dropna(subset=["exit"]), y="exit", X=X)


def run_vulnerability_threshold(panel: pd.DataFrame, spec3_results):
    """
    Spec 7: test if countries above the vulnerability threshold (eq. 30)
    have lower exit hazard.
    """
    # Recover coefficients from Spec 3 to build the threshold
    coefs = spec3_results.params
    eta_9_delta0 = coefs.get(f"displacement_term_L{DEFAULT_LAG}", 0)
    eta_2 = coefs.get(f"G_L{DEFAULT_LAG}", 0)
    eta_6 = coefs.get(f"G_x_KIS_L{DEFAULT_LAG}", 0)
    # eta_5 (G_x_I) absent in Spec 3; default to Spec 2 estimate if rerun together

    df = panel.copy()
    h_norm = (df["human_capital_pwt"] - df["human_capital_pwt"].min()) / (
        df["human_capital_pwt"].max() - df["human_capital_pwt"].min()
    )
    df["disp_potential"] = (
        eta_9_delta0
        * df["rho_gradient4"]
        * (1 - h_norm)
        * (1 - df["sigma_kis"])
    )
    df["productivity_potential"] = (
        eta_2
        + eta_6 * h_norm * df["sigma_kis"]
    )
    df["vulnerable"] = (df["disp_potential"] > df["productivity_potential"]).astype(int)

    df = df[df["at_risk"] == 1].copy()
    df = _add_log_gdp(df)
    df = _lag(df.set_index(["iso3", "year"]).sort_index(),
              ["F", "G", "F_x_G", "vulnerable"] + CONTROLS).reset_index()
    X = [f"F_L{DEFAULT_LAG}", f"G_L{DEFAULT_LAG}", f"F_x_G_L{DEFAULT_LAG}",
         f"vulnerable_L{DEFAULT_LAG}"] + [f"{c}_L{DEFAULT_LAG}" for c in CONTROLS]
    return probit_fe(df.dropna(subset=["exit"]), y="exit", X=X)


# ============================================================
# NEW SPECIFICATIONS
# ============================================================

def run_quadrant_heterogeneity(panel: pd.DataFrame):
    """
    Spec 8: split by median H and median sigma_KIS, fully interacted.
    """
    df = _add_log_gdp(panel)
    h_med = df["human_capital_pwt"].median()
    kis_med = df["sigma_kis"].median()
    df["q_HH"] = ((df["human_capital_pwt"] >= h_med) & (df["sigma_kis"] >= kis_med)).astype(int)
    df["q_HL"] = ((df["human_capital_pwt"] >= h_med) & (df["sigma_kis"] < kis_med)).astype(int)
    df["q_LH"] = ((df["human_capital_pwt"] < h_med) & (df["sigma_kis"] >= kis_med)).astype(int)
    df["q_LL"] = ((df["human_capital_pwt"] < h_med) & (df["sigma_kis"] < kis_med)).astype(int)

    for q in ["HH", "HL", "LH", "LL"]:
        df[f"F_x_G_x_{q}"] = df["F_x_G"] * df[f"q_{q}"]

    terms = [f"F_x_G_x_{q}" for q in ["HH", "HL", "LH", "LL"]]
    df = _lag(df.set_index(["iso3", "year"]).sort_index(),
              terms + ["F", "G"] + CONTROLS).reset_index()
    X = [f"F_L{DEFAULT_LAG}", f"G_L{DEFAULT_LAG}"] + [
        f"{t}_L{DEFAULT_LAG}" for t in terms
    ] + [f"{c}_L{DEFAULT_LAG}" for c in CONTROLS]
    return panel_fe(df, y="gdp_pc_growth", X=X)


def estimate_escape_frontier(panel: pd.DataFrame, spec1_results) -> pd.DataFrame:
    """
    Spec 9: compute the (F, G) frontier where growth equals threshold.

    From eq. 26: F*(G) = (g_bar - a_G * G) / (a_F + a_FG * G)
    """
    a_F = spec1_results.params.get(f"F_L{DEFAULT_LAG}", 0)
    a_G = spec1_results.params.get(f"G_L{DEFAULT_LAG}", 0)
    a_FG = spec1_results.params.get(f"F_x_G_L{DEFAULT_LAG}", 0)
    g_bar = CONVERGENCE_THRESHOLD_G * 100  # back to percentage points

    G_grid = np.linspace(panel["G"].quantile(0.1), panel["G"].quantile(0.9), 100)
    F_frontier = (g_bar - a_G * G_grid) / (a_F + a_FG * G_grid)

    frontier_df = pd.DataFrame({
        "G": G_grid,
        "F_threshold": F_frontier,
    })
    return frontier_df


def run_threshold_regression(panel: pd.DataFrame):
    """
    Spec 10: Hansen threshold regression on F*G.
    """
    df = _add_log_gdp(panel)
    df = df.dropna(subset=["F_x_G", "gdp_pc_growth"])
    return threshold_regression(
        df,
        y="gdp_pc_growth",
        threshold_var="F_x_G",
        X=["F", "G", "F_x_G"] + CONTROLS,
    )


def run_mediator_mcm_rodrik(panel: pd.DataFrame):
    """
    Spec 11: McMillan-Rodrik between-sector reallocation as mediator.

    Requires precomputed delta_P_between. See src/construct/structural_transformation.py
    (not yet implemented; mediator analysis pending GGDC sector decomposition).
    """
    logger.warning("Spec 11: requires McMillan-Rodrik decomposition (not yet built)")
    return None


# ============================================================
# IDENTIFICATION
# ============================================================

def run_iv_cable(panel: pd.DataFrame):
    """
    Spec 13: instrument F, G, FG with submarine cable timing.
    """
    df = _add_log_gdp(panel)
    df = df.copy()
    df["z_cable_x_year"] = df["z_cable"] * (df["year"] - df["year"].min())
    return iv_2sls(
        df,
        y="gdp_pc_growth",
        exog=CONTROLS,
        endog=["F", "G", "F_x_G"],
        instruments=["z_cable", "z_cable_x_year"],
    )


def run_iv_frontier(panel: pd.DataFrame):
    """
    Spec 12: instrument G with distance-to-frontier exposure.
    """
    df = _add_log_gdp(panel)
    if "z_frontier" not in df.columns:
        logger.warning("z_frontier not in panel; build via instruments.py")
        return None
    return iv_2sls(
        df,
        y="gdp_pc_growth",
        exog=["F"] + CONTROLS,
        endog=["G", "F_x_G"],
        instruments=["z_frontier"],
    )


def run_system_gmm(panel: pd.DataFrame):
    """
    Spec 14: system GMM dynamic panel.
    """
    return system_gmm(
        panel,
        y="gdp_pc_growth",
        X=["F", "G", "F_x_G"] + CONTROLS,
    )


# ============================================================
# ROBUSTNESS
# ============================================================

def run_robustness_index_alternatives(panel: pd.DataFrame):
    """
    Spec 15: re-run Spec 1 with PCA index, Access/Usage decomposition,
    individual pillars.
    """
    results = {}
    df = _add_log_gdp(panel)

    # PCA versions
    if "F_pca" in df.columns and "G_pca" in df.columns:
        df_pca = df.copy()
        df_pca["F_pca_x_G_pca"] = df_pca["F_pca"] * df_pca["G_pca"]
        df_pca = _lag(df_pca.set_index(["iso3", "year"]).sort_index(),
                      ["F_pca", "G_pca", "F_pca_x_G_pca"] + CONTROLS).reset_index()
        X = [f"F_pca_L{DEFAULT_LAG}", f"G_pca_L{DEFAULT_LAG}",
             f"F_pca_x_G_pca_L{DEFAULT_LAG}"] + [
            f"{c}_L{DEFAULT_LAG}" for c in CONTROLS
        ]
        results["pca"] = panel_fe(df_pca, y="gdp_pc_growth", X=X)

    # Access vs Usage
    if {"F_access", "G_access", "F_usage", "G_usage"}.issubset(df.columns):
        for variant in ["access", "usage"]:
            df_v = df.copy()
            df_v[f"FG_{variant}"] = df_v[f"F_{variant}"] * df_v[f"G_{variant}"]
            df_v = _lag(df_v.set_index(["iso3", "year"]).sort_index(),
                        [f"F_{variant}", f"G_{variant}", f"FG_{variant}"] + CONTROLS).reset_index()
            X = [f"F_{variant}_L{DEFAULT_LAG}", f"G_{variant}_L{DEFAULT_LAG}",
                 f"FG_{variant}_L{DEFAULT_LAG}"] + [
                f"{c}_L{DEFAULT_LAG}" for c in CONTROLS
            ]
            results[variant] = panel_fe(df_v, y="gdp_pc_growth", X=X)

    return results


# ============================================================
# DRIVER
# ============================================================

def main():
    panel = pd.read_parquet(DATA_PROCESSED / "panel.parquet")
    logger.info(f"loaded panel: {panel.shape}")
    OUTPUT_TABLES.mkdir(parents=True, exist_ok=True)

    results = {}

    # Core
    results["spec1_baseline"] = run_baseline_joint_digital(panel)
    results["spec2_full"] = run_full_interaction(panel)
    results["spec3_displacement"] = run_displacement(panel)
    results["spec4_mit"] = run_mit_interaction(panel)
    results["spec5_slowdown"] = run_slowdown_probit(panel)
    results["spec6_exit"] = run_exit_hazard(panel)
    results["spec7_vulnerability"] = run_vulnerability_threshold(panel, results["spec3_displacement"])

    # New
    results["spec8_quadrants"] = run_quadrant_heterogeneity(panel)
    frontier = estimate_escape_frontier(panel, results["spec1_baseline"])
    frontier.to_csv(OUTPUT_TABLES / "spec9_escape_frontier.csv", index=False)
    results["spec10_threshold"] = run_threshold_regression(panel)
    results["spec11_mediator"] = run_mediator_mcm_rodrik(panel)

    # Identification
    results["spec12_frontier_iv"] = run_iv_frontier(panel)
    results["spec13_cable_iv"] = run_iv_cable(panel)
    results["spec14_sysgmm"] = run_system_gmm(panel)

    # Robustness
    results["spec15_robustness"] = run_robustness_index_alternatives(panel)

    # Write tables. Stargazer accepts statsmodels results; linearmodels
    # results require small adapter; placeholder here.
    logger.info("Results dictionary ready; table formatting via stargazer in notebook.")
    return results


if __name__ == "__main__":
    main()
