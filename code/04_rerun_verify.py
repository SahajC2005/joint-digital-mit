"""
04_rerun_verify.py
==================
Re-estimates every headline coefficient quoted in `docs/joint_digital_mit_report.md`
and `docs/results_memo.md` on the committed panel, and scores each one against the
published value.

Nothing in this repository had been executed before this script: the documents were
written from runs whose outputs are not on disk. This script exists so that every
number in them can be checked against the committed data and code.

Panel:  data/processed/panel_estimation.csv  (the estimation-ready panel:
        it already carries F, G, FG, MI, the lagged regressors and the constructed
        interaction terms; the other processed panels do not).

Writes:
  outputs/rerun/rerun_coefficients.csv   every coefficient from every spec
  outputs/rerun/rerun_vs_published.csv   the published value, the re-run value, the gap
  outputs/rerun/rerun_log.txt            full console output

Usage:  python code/04_rerun_verify.py
"""
from pathlib import Path
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from linearmodels.panel import PanelOLS, BetweenOLS, RandomEffects
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parent.parent
PANEL = ROOT / "data" / "processed" / "panel_estimation.csv"
OUT = ROOT / "outputs" / "rerun"
OUT.mkdir(parents=True, exist_ok=True)

CONTROLS = ["log_gdp", "trade_pct_gdp", "inflation", "investment_pct_gdp",
            "pop_growth", "credit_to_private_pct_gdp", "secondary_enrollment"]
Cl = [f"{c}_l" for c in CONTROLS]

DEP = "gdp_pc_growth"

rows = []          # one record per (spec, parameter)


def stars(p):
    return "***" if p < .01 else "**" if p < .05 else "*" if p < .1 else ""


def record(spec, param, est, se, p, n, k, note=""):
    rows.append(dict(spec=spec, param=param, estimate=est, std_error=se,
                     p_value=p, stars=stars(p), n_obs=int(n), n_countries=int(k),
                     note=note))


def fe(spec, data, regs, dep=DEP, keep=None, entity=True, time=True, note=""):
    """Two-way FE with country-clustered SEs. Returns the fitted result."""
    d = data[[dep] + regs].dropna()
    if d.empty:
        print(f"-- {spec}: no observations, skipped")
        return None
    eff = (" + EntityEffects" if entity else "") + (" + TimeEffects" if time else "")
    f = f"{dep} ~ " + " + ".join(regs) + eff
    r = PanelOLS.from_formula(f, data=d, drop_absorbed=True).fit(
        cov_type="clustered", cluster_entity=True)
    k = d.index.get_level_values(0).nunique()
    for key in (keep or regs):
        if key in r.params.index:
            record(spec, key, r.params[key], r.std_errors[key], r.pvalues[key],
                   r.nobs, k, note)
    print(f"\n== {spec} ==  N={int(r.nobs):,}  countries={k}")
    for key in (keep or regs):
        if key in r.params.index:
            print(f"   {key:<14}{r.params[key]:+9.4f}  se={r.std_errors[key]:7.4f}"
                  f"  p={r.pvalues[key]:.3f} {stars(r.pvalues[key])}")
    return r


# ---------------------------------------------------------------- load
df = pd.read_csv(PANEL, low_memory=False).sort_values(["iso3", "year"])
P = df.set_index(["iso3", "year"])
print(f"panel: {df.shape[0]:,} rows x {df.shape[1]} cols, "
      f"{df.iso3.nunique()} countries, {df.year.min()}-{df.year.max()}")

SPEC1 = ["F_l", "G_l", "FG_l"] + Cl                       # Eq. 30 baseline
SPEC4 = ["F_l", "G_l", "FG_l", "MI_l", "F_MI_l", "G_MI_l", "FG_MI_l"] + Cl   # Eq. 33

# ---------------------------------------------------------------- §2 core result
print("\n" + "#" * 72)
print("# SECTION 2 - the core result (beta3) and SECTION 3.1 (delta4)")
print("#" * 72)

fe("baseline_spec1", P, SPEC1, keep=["F_l", "G_l", "FG_l"])
fe("mit_spec4", P, SPEC4, keep=["FG_l", "MI_l", "FG_MI_l"])
fe("dynamic_lagged_dep", P, ["g_l"] + SPEC1, keep=["g_l", "FG_l"])
fe("exclude_china", P.drop(index="CHN", level=0, errors="ignore"), SPEC1, keep=["FG_l"])
fe("exclude_china_spec4", P.drop(index="CHN", level=0, errors="ignore"), SPEC4,
   keep=["FG_MI_l"])

# ---------------------------------------------------------------- §3.2 displacement
print("\n" + "#" * 72)
print("# SECTION 3.2 - displacement drag (beta6)")
print("#" * 72)
fe("displacement", P, ["F_l", "G_l", "FG_l", "D_term_l"] + Cl, keep=["FG_l", "D_term_l"])

# ---------------------------------------------------------------- §3.3 vulnerability -> exit
print("\n" + "#" * 72)
print("# SECTION 3.3 - vulnerability -> exit probit (psi4)")
print("#" * 72)
# The exit is recorded on the row AFTER the transition (those rows have MI == 0),
# so the risk set is countries that were middle-income in the PREVIOUS year.
risk = df[(df["MI_l"] == 1) & df["Vuln"].notna() & df["Exit"].notna()].copy()
if len(risk):
    X = sm.add_constant(risk[["Vuln"]].astype(float))
    pr = sm.Probit(risk["Exit"].astype(float), X).fit(disp=0)
    record("exit_probit", "Vuln", pr.params["Vuln"], pr.bse["Vuln"],
           pr.pvalues["Vuln"], pr.nobs, risk.iso3.nunique(),
           note=f"{int(risk['Exit'].sum())} exit events in risk set")
    print(f"   Vuln {pr.params['Vuln']:+.4f}  se={pr.bse['Vuln']:.4f} "
          f"p={pr.pvalues['Vuln']:.3f} {stars(pr.pvalues['Vuln'])}  "
          f"N={int(pr.nobs)}  exits={int(risk['Exit'].sum())}")
    rate_v = risk.loc[risk.Vuln == 1, "Exit"].mean()
    rate_n = risk.loc[risk.Vuln == 0, "Exit"].mean()
    record("exit_rates", "exit_rate_vulnerable", rate_v, np.nan, np.nan,
           int((risk.Vuln == 1).sum()), risk.iso3.nunique(), "descriptive")
    record("exit_rates", "exit_rate_not_vulnerable", rate_n, np.nan, np.nan,
           int((risk.Vuln == 0).sum()), risk.iso3.nunique(), "descriptive")
    print(f"   exit rate: vulnerable {rate_v:.3%}  non-vulnerable {rate_n:.3%}")

# ---------------------------------------------------------------- §4 inequality block
print("\n" + "#" * 72)
print("# SECTION 4 - the inequality extension")
print("#" * 72)
fe("ineq_gini_level", P, ["F_l", "G_l", "FG_l", "Z_gini_l"] + Cl,
   keep=["FG_l", "Z_gini_l"])
fe("ineq_erosion", P, ["F_l", "G_l", "FG_l", "Z_gini_l", "G_Gini_l", "FG_Gini_l"] + Cl,
   keep=["G_Gini_l", "FG_Gini_l"])
fe("ineq_displacement_amp", P,
   ["F_l", "G_l", "FG_l", "Z_gini_l", "D_term_l", "D_Gini_l"] + Cl,
   keep=["D_term_l", "D_Gini_l"])
fe("ineq_mit_escape_phi4", P,
   ["F_l", "G_l", "FG_l", "MI_l", "F_MI_l", "G_MI_l", "FG_MI_l",
    "Z_gini_l", "G_Gini_l", "FG_Gini_l", "Gini_MI_l", "G_Gini_MI_l", "FG_Gini_MI_l"] + Cl,
   keep=["FG_MI_l", "FG_Gini_l", "FG_Gini_MI_l"])
fe("fintech_shock_resilience", P, ["F_l", "G_l", "FG_l", "F_Shock"] + Cl,
   keep=["F_Shock"])

# AI -> inequality first stage (gamma1) and inequality -> growth (theta)
fe("gamma1_ai_to_gini", P, ["F_l", "G_l", "FG_l"] + Cl, dep="Z_gini_l",
   keep=["G_l"], note="gamma1: AI -> inequality")
fe("theta_gini_to_growth", P, ["Z_gini_l"] + Cl, keep=["Z_gini_l"],
   note="theta: inequality -> growth")

# Gini terciles inside the middle-income sample
print("\n-- Gini terciles within the middle-income sample --")
mi = df[df["MI"] == 1].copy()
mi["gini_tercile"] = pd.qcut(mi["Z_gini_l"], 3, labels=["low", "mid", "high"])
for t in ["low", "mid", "high"]:
    sub = mi[mi.gini_tercile == t].set_index(["iso3", "year"])
    fe(f"mi_gini_tercile_{t}", sub, SPEC1, keep=["FG_l"],
       note="middle-income sample split by lagged Gini tercile")

# ---------------------------------------------------------------- §5 robustness
print("\n" + "#" * 72)
print("# SECTION 5 - robustness on beta3 and delta4")
print("#" * 72)

no_covid = P[~P.index.get_level_values(1).isin([2020, 2021])]
fe("drop_covid", no_covid, SPEC1, keep=["FG_l"])
fe("drop_covid_spec4", no_covid, SPEC4, keep=["FG_MI_l"])

# wave-years-only F: F observed, not interpolated
wave = df.copy()
wave["F"] = wave["F_wave"]
wave["F_l"] = wave.groupby("iso3")["F"].shift(1)
wave["FG_l"] = wave["F_l"] * wave.groupby("iso3")["G"].shift(1)
wave["F_MI_l"] = wave["F_l"] * wave["MI_l"]
wave["FG_MI_l"] = wave["FG_l"] * wave["MI_l"]
wave = wave[wave["F_l"].notna()].set_index(["iso3", "year"])
fe("wave_years_only", wave, SPEC1, keep=["FG_l"],
   note="F from Findex wave years only, no interpolation")
fe("wave_years_only_spec4", wave, SPEC4, keep=["FG_MI_l"],
   note="F from Findex wave years only, no interpolation")

fe("forward_avg_growth", P, SPEC1, dep="g3f", keep=["FG_l"],
   note="3-year forward-average growth")
fe("forward_avg_growth_spec4", P, SPEC4, dep="g3f", keep=["FG_MI_l"],
   note="3-year forward-average growth")

# between estimator
bcols = [DEP, "F_l", "G_l", "FG_l"] + Cl
Pb = P[bcols].dropna()
b = BetweenOLS.from_formula(f"{DEP} ~ 1 + " + " + ".join(["F_l", "G_l", "FG_l"] + Cl),
                            data=Pb).fit()
record("between_estimator", "FG_l", b.params["FG_l"], b.std_errors["FG_l"],
       b.pvalues["FG_l"], b.nobs, Pb.index.get_level_values(0).nunique())
print(f"\n== between_estimator ==  countries={Pb.index.get_level_values(0).nunique()}")
print(f"   FG_l          {b.params['FG_l']:+9.4f}  p={b.pvalues['FG_l']:.3f} "
      f"{stars(b.pvalues['FG_l'])}")
Pb4 = P[[DEP] + SPEC4].dropna()
b4 = BetweenOLS.from_formula(f"{DEP} ~ 1 + " + " + ".join(SPEC4), data=Pb4).fit()
record("between_estimator_spec4", "FG_MI_l", b4.params["FG_MI_l"],
       b4.std_errors["FG_MI_l"], b4.pvalues["FG_MI_l"], b4.nobs,
       Pb4.index.get_level_values(0).nunique())
print(f"   FG_MI_l       {b4.params['FG_MI_l']:+9.4f}  p={b4.pvalues['FG_MI_l']:.3f}")

# complete case: no imputed lagged regressor
cc = P[P["imp_any_l"] == 0]
fe("complete_case", cc, SPEC1, keep=["FG_l"], note="imp_any_l == 0")
fe("complete_case_spec4", cc, SPEC4, keep=["FG_MI_l"], note="imp_any_l == 0")

# ---------------------------------------------------------------- threshold searches
print("\n" + "#" * 72)
print("# threshold regressions")
print("#" * 72)


def threshold_on(data, var, q_lo=.15, q_hi=.85, n=40, label=""):
    d = data[[DEP, var] + Cl].dropna().copy()
    best = (None, np.inf, None, None, None, None)
    for g in np.quantile(d[var], np.linspace(q_lo, q_hi, n)):
        d["below"] = (d[var] < g).astype(int) * d[var]
        d["above"] = (d[var] >= g).astype(int) * d[var]
        f = f"{DEP} ~ below + above + " + " + ".join(Cl) + " + EntityEffects + TimeEffects"
        r = PanelOLS.from_formula(f, data=d, drop_absorbed=True).fit(
            cov_type="clustered", cluster_entity=True)
        sse = float((r.resids ** 2).sum())
        if sse < best[1]:
            best = (g, sse, r.params["below"], r.params["above"],
                    r.pvalues["below"], r.pvalues["above"])
    g, _, bl, ba, pl, pa = best
    k = d.index.get_level_values(0).nunique()
    record(f"threshold_{label}", "threshold", g, np.nan, np.nan, len(d), k)
    record(f"threshold_{label}", "slope_below", bl, np.nan, pl, len(d), k)
    record(f"threshold_{label}", "slope_above", ba, np.nan, pa, len(d), k)
    print(f"\n== threshold on {var} ==  N={len(d):,}  countries={k}")
    print(f"   break={g:+.4f}  below={bl:+.4f} (p={pl:.3f})  above={ba:+.4f} (p={pa:.3f})")
    return best


threshold_on(P, "FG_l", label="FG_l")

# income threshold from the memo: dividend below ~ $6,216 PPP
print("\n-- income threshold on the F x G dividend --")
di = df.dropna(subset=[DEP, "F_l", "G_l", "FG_l", "gdp_pc_ppp"] + Cl).copy()
grid = np.quantile(di["gdp_pc_ppp"], np.linspace(.15, .85, 40))
best = (None, np.inf, None, None, None, None)
for y in grid:
    d = di.copy()
    lo = (d["gdp_pc_ppp"] < y).astype(float)
    d["FG_lo"] = d["FG_l"] * lo
    d["FG_hi"] = d["FG_l"] * (1 - lo)
    d = d.set_index(["iso3", "year"])
    f = (f"{DEP} ~ F_l + G_l + FG_lo + FG_hi + " + " + ".join(Cl)
         + " + EntityEffects + TimeEffects")
    r = PanelOLS.from_formula(f, data=d, drop_absorbed=True).fit(
        cov_type="clustered", cluster_entity=True)
    sse = float((r.resids ** 2).sum())
    if sse < best[1]:
        best = (y, sse, r.params["FG_lo"], r.params["FG_hi"],
                r.pvalues["FG_lo"], r.pvalues["FG_hi"])
y, _, blo, bhi, plo, phi = best
record("income_threshold", "threshold_gdp_pc_ppp", y, np.nan, np.nan, len(di),
       di.iso3.nunique())
record("income_threshold", "FG_below", blo, np.nan, plo, len(di), di.iso3.nunique())
record("income_threshold", "FG_above", bhi, np.nan, phi, len(di), di.iso3.nunique())
print(f"   break=${y:,.0f} PPP  below={blo:+.4f} (p={plo:.3f})  "
      f"above={bhi:+.4f} (p={phi:.3f})")

# ---------------------------------------------------------------- Mundlak / CRE
print("\n" + "#" * 72)
print("# Mundlak / correlated random effects - within vs between beta3")
print("#" * 72)
KEY = ["F_l", "G_l", "FG_l", "MI_l", "F_MI_l", "G_MI_l", "FG_MI_l"]
dm = df.copy()
for v in KEY:
    dm[v + "_bar"] = dm.groupby("iso3")[v].transform("mean")


def cre(spec, regs, keys):
    bars = [v + "_bar" for v in regs]
    d = dm.dropna(subset=[DEP] + regs + bars + Cl).set_index(["iso3", "year"])
    f = f"{DEP} ~ 1 + " + " + ".join(regs + bars + Cl)
    r = RandomEffects.from_formula(f, data=d).fit(cov_type="clustered",
                                                  cluster_entity=True)
    k = d.index.get_level_values(0).nunique()
    print(f"\n== {spec} ==  N={int(r.nobs):,}  countries={k}")
    for v in keys:
        wi, lam, pl = r.params[v], r.params[v + "_bar"], r.pvalues[v + "_bar"]
        record(spec, v + "_within", wi, r.std_errors[v], r.pvalues[v], r.nobs, k)
        record(spec, v + "_between", wi + lam, np.nan, pl, r.nobs, k,
               note="p is on the within-between difference (the _bar term)")
        print(f"   {v:<9} within={wi:+.3f}  between={wi + lam:+.3f}  "
              f"p(diff)={pl:.3f} {stars(pl)}")


cre("mundlak_spec1", ["F_l", "G_l", "FG_l"], ["FG_l"])
cre("mundlak_spec4", KEY, ["FG_l", "FG_MI_l"])

# ---------------------------------------------------------------- measurement diagnostics
print("\n" + "#" * 72)
print("# measurement: within vs between standard deviation")
print("#" * 72)
for v in ["F", "G", "Z_readiness", "Z_activity", "Z_adoption", "Z_gini"]:
    if v not in df.columns:
        continue
    s = df[["iso3", v]].dropna()
    within = s.groupby("iso3")[v].transform(lambda x: x - x.mean()).std()
    between = s.groupby("iso3")[v].mean().std()
    ratio = within / between if between else np.nan
    record("measurement_sd", v, ratio, within, np.nan, len(s), s.iso3.nunique(),
           note=f"within_sd={within:.4f} between_sd={between:.4f}")
    print(f"   {v:<14} within={within:.4f}  between={between:.4f}  ratio={ratio:.3f}")

# AI source validation: OpenAlex vs Scimago (memo quotes log-log r = 0.964)
print("\n-- AI source validation (OpenAlex vs Scimago) --")
try:
    import country_converter as coco
    # scimago_ai_publications.csv is not UTF-8; a handful of country names are mojibake and
    # simply fail to map, which is why N is 1,589 and not the full file.
    sc = pd.read_csv(ROOT / "data" / "raw" / "scimago_ai_publications.csv",
                     encoding="latin-1", low_memory=False)
    sc["iso3"] = coco.CountryConverter().convert(sc["country"].tolist(),
                                                 to="ISO3", not_found=None)
    oa = pd.read_csv(ROOT / "data" / "raw" / "openalex_ai_pubs.csv", low_memory=False)
    m = sc.merge(oa, on=["iso3", "year"], how="inner")
    m = m[(m["documents"] > 0) & (m["ai_pubs_count"] > 0)]
    rr = float(np.corrcoef(np.log(m["documents"]), np.log(m["ai_pubs_count"]))[0, 1])
    record("ai_source_validation", "loglog_corr_openalex_scimago", rr, np.nan,
           np.nan, len(m), m.iso3.nunique(), "Scimago documents vs OpenAlex ai_pubs_count")
    print(f"   log-log r = {rr:.4f}   N={len(m):,} country-years, "
          f"{m.iso3.nunique()} countries")
except Exception as e:
    print(f"   could not compute: {e}")

# ---------------------------------------------------------------- scorecard
# Every number quoted in the two documents, with where it is quoted, matched to
# the spec/param above. published_n is given only where the document states it.
PUBLISHED = [
    # label, source, spec, param, published value, published stars
    ("beta3 F x G (baseline, Eq. 30)",        "report §2",   "baseline_spec1",        "F_l",            None,     ""),
    ("beta3 F x G (baseline, Eq. 30)",        "report §2",   "baseline_spec1",        "FG_l",           1.096,    "**"),
    ("beta3, dynamic panel (Eq. 47)",         "report §2",   "dynamic_lagged_dep",    "FG_l",           1.098,    "**"),
    ("beta3, excluding China",                "report §2/5", "exclude_china",         "FG_l",           1.094,    "**"),
    ("delta4 F x G x MI (Eq. 33)",            "report §3.1", "mit_spec4",             "FG_MI_l",       -0.609,    ""),
    ("beta6 displacement (Eqs. 13, 32)",      "report §3.2", "displacement",          "D_term_l",     -24.85,     ""),
    ("psi4 vulnerability -> exit",            "report §3.3", "exit_probit",           "Vuln",           1.223,    "**"),
    ("exit rate, vulnerable",                 "report §3.3", "exit_rates",            "exit_rate_vulnerable",      0.24,  ""),
    ("exit rate, non-vulnerable",             "report §3.3", "exit_rates",            "exit_rate_not_vulnerable",  0.008, ""),
    ("beta4 Gini level (Eq. 30')",            "report §4",   "ineq_gini_level",       "Z_gini_l",      -0.236,    ""),
    ("beta10 G x Gini",                       "report §4",   "ineq_erosion",          "G_Gini_l",      -1.551,    ""),
    ("beta11 F x G x Gini (key)",             "report §4",   "ineq_erosion",          "FG_Gini_l",     -0.118,    ""),
    ("beta7 D x Gini",                        "report §4",   "ineq_displacement_amp", "D_Gini_l",      -9.473,    ""),
    ("phi4 F x G x Gini x MI (key)",          "report §4",   "ineq_mit_escape_phi4",  "FG_Gini_MI_l",   0.802,    ""),
    ("gamma1 AI -> inequality",               "report §4",   "gamma1_ai_to_gini",     "G_l",            0.005,    ""),
    ("theta inequality -> growth",            "report §4",   "theta_gini_to_growth",  "Z_gini_l",    -153.9,      ""),
    ("omega F x Shock",                       "report §4",   "fintech_shock_resilience", "F_Shock",     0.614,    ""),
    ("top Gini tercile, MI sample",           "report §4",   "mi_gini_tercile_high",  "FG_l",           1.37,     ""),
    ("beta3, drop COVID 2020-21",             "report §5",   "drop_covid",            "FG_l",           0.491,    ""),
    ("delta4, drop COVID 2020-21",            "report §5",   "drop_covid_spec4",      "FG_MI_l",        0.269,    ""),
    ("beta3, wave-years-only F",              "report §5",   "wave_years_only",       "FG_l",          -0.062,    ""),
    ("delta4, wave-years-only F",             "report §5",   "wave_years_only_spec4", "FG_MI_l",       -1.293,    ""),
    ("beta3, 3-yr forward-average growth",    "report §5",   "forward_avg_growth",    "FG_l",           0.894,    "**"),
    ("delta4, 3-yr forward-average growth",   "report §5",   "forward_avg_growth_spec4","FG_MI_l",       0.049,    ""),
    ("beta3, between estimator",              "report §5",   "between_estimator",     "FG_l",          -0.581,    "***"),
    ("delta4, between estimator",             "report §5",   "between_estimator_spec4","FG_MI_l",        0.158,    ""),
    ("beta3, complete case",                  "report §5",   "complete_case",         "FG_l",           1.21,     ""),
    ("delta4, complete case",                 "report §5",   "complete_case_spec4",   "FG_MI_l",       -1.17,     ""),
    ("threshold on F x G",                    "report §2",   "threshold_FG_l",        "threshold",      0.351,    ""),
    ("slope below threshold",                 "report §2",   "threshold_FG_l",        "slope_below",   -1.55,     ""),
    ("slope above threshold",                 "report §2",   "threshold_FG_l",        "slope_above",    0.82,     "*"),
    ("Mundlak beta3 within",                  "README",      "mundlak_spec1",         "FG_l_within",    0.73,     ""),
    ("Mundlak beta3 between",                 "README",      "mundlak_spec1",         "FG_l_between",  -0.74,     ""),
    ("F within/between SD ratio",             "playbook",    "measurement_sd",        "F",              0.28,     ""),
    ("G within/between SD ratio",             "playbook",    "measurement_sd",        "G",              0.09,     ""),
    ("Z_readiness within/between ratio",      "playbook",    "measurement_sd",        "Z_readiness",    0.0,      ""),
    ("Z_adoption within/between ratio",       "playbook",    "measurement_sd",        "Z_adoption",     0.0,      ""),
    ("AI source validation log-log r",        "memo",        "ai_source_validation",  "loglog_corr_openalex_scimago", 0.964, ""),
    ("beta3 (memo figure)",                   "memo",        "baseline_spec1",        "FG_l",           1.014,    "**"),
    ("income threshold (PPP)",                "memo",        "income_threshold",      "threshold_gdp_pc_ppp", 6216.0, ""),
    ("F x G below income threshold",          "memo",        "income_threshold",      "FG_below",       2.78,     "***"),
    ("F x G above income threshold",          "memo",        "income_threshold",      "FG_above",      -0.27,     ""),
]

res_idx = pd.DataFrame(rows).set_index(["spec", "param"])
comp = []
for label, src, spec, param, pub, pub_stars in PUBLISHED:
    if pub is None:
        continue
    try:
        r = res_idx.loc[(spec, param)]
    except KeyError:
        comp.append(dict(quantity=label, source=src, spec=spec, param=param,
                         published=pub, published_stars=pub_stars, rerun=np.nan,
                         rerun_stars="", abs_diff=np.nan, rel_diff=np.nan,
                         n_obs=np.nan, verdict="not estimated"))
        continue
    if isinstance(r, pd.DataFrame):
        r = r.iloc[0]
    est = float(r["estimate"])
    diff = est - pub
    rel = abs(diff) / abs(pub) if pub else np.nan
    same_sign = (np.sign(est) == np.sign(pub)) or pub == 0
    if abs(diff) < 0.005 or (pub and rel < 0.01):
        verdict = "reproduces"
    elif same_sign and (rel < 0.25 if pub else True):
        verdict = "close"
    elif same_sign:
        verdict = "same sign, different magnitude"
    else:
        verdict = "SIGN FLIP"
    comp.append(dict(quantity=label, source=src, spec=spec, param=param,
                     published=pub, published_stars=pub_stars, rerun=round(est, 4),
                     rerun_stars=r["stars"], abs_diff=round(diff, 4),
                     rel_diff=round(rel, 4) if rel == rel else np.nan,
                     n_obs=r["n_obs"], verdict=verdict))

cdf = pd.DataFrame(comp)
cdf.to_csv(OUT / "rerun_vs_published.csv", index=False)
print("\n" + "#" * 72)
print("# SCORECARD: re-run vs published")
print("#" * 72)
for v, g in cdf.groupby("verdict"):
    print(f"\n--- {v} ({len(g)}) ---")
    for _, r in g.iterrows():
        print(f"   {r['quantity']:<40} pub={r['published']:>9.3f}{r['published_stars']:<3} "
              f"rerun={r['rerun']:>9.3f}{r['rerun_stars']:<3}")
print(f"\nwrote {OUT / 'rerun_vs_published.csv'}  ({len(cdf)} rows)")

# ---------------------------------------------------------------- write
res = pd.DataFrame(rows)
res.to_csv(OUT / "rerun_coefficients.csv", index=False)
print(f"\nwrote {OUT / 'rerun_coefficients.csv'}  ({len(res)} rows)")
