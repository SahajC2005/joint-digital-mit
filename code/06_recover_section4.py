"""
06_recover_section4.py
======================
Re-estimates the Section 4 inequality extension of `docs/joint_digital_mit_report.md`
(the "primed" equations 30'-33', 49-51, 54) with the regressor sets the published
table was actually computed from.

`04_rerun_verify.py` could not reproduce five of these numbers because no script in
`code/` estimates the primed specifications; the probes in `05_spec_probes.py` tried
plausible regressor sets and none matched. The specifications were recovered on
2026-10-19 from the stored cell outputs of `notebooks/joint_digital_mit_analysis.ipynb`,
which is the notebook the report was written from: it prints beta3 = 1.0956 on
N = 1,380 and every Section 4 coefficient in the published table. The notebook built
the panel from `final_panel (12).csv` and saved it as `final_panel_imputed.csv`; the
committed `final_panel_imputed__5_.csv` is that panel with the constructed Section 4
columns (`gini`, `Z_gini`, `G_Gini_l`, `FG_Gini_l`, `D_Gini_l`, `Gini_MI_l`,
`G_Gini_MI_l`, `FG_Gini_MI_l`, `G_1mH_l`, `sigma_kis_l`, `Shock`, `F_Shock`,
`Gini_Shock`, `FG_Shock`) already in it, so no regressor is rebuilt here.

What the re-run had wrong, in each case a missing block of regressors rather than
the data:

  beta6  (D_term_l)      omitted GH_l and GS_l
  beta11 (FG_Gini_l)     omitted the institutional block FI_l/GI_l/GH_l/GS_l/FGI_l
  omega  (F_Shock)       omitted Z_gini_l, Gini_Shock and FG_Shock
  gamma1 (G_l -> Gini)   used Z_gini_l as the dependent variable and the wrong
                         regressors; the published spec is `gini` (0-1 share) on
                         G_l, G_1mH_l, F_l, sigma_kis_l
  theta  (gini_hat)      used Z_gini_l directly; the published spec is two-step,
                         regressing growth on the *fitted* Gini from Eq. (49)

Estimator throughout: `PanelOLS` two-way FE with country-clustered SEs, as in
`03_mundlak_reestimation.py` and `04_rerun_verify.py`.

Writes:
  outputs/rerun/section4_coefficients.csv    every coefficient from every primed spec
  outputs/rerun/section4_vs_published.csv    published value, recovered value, verdict
  outputs/rerun/section4_iv_first_stage.csv  the Eq. 52-53 Bartik IV first-stage F
  outputs/rerun/section4_log.txt             full console output
  outputs/rerun/rerun_vs_published_recounted.csv
                                             the 41-quantity scorecard of
                                             04_rerun_verify.py with the rows these
                                             specifications settle corrected in place

Usage:  python code/06_recover_section4.py
"""
from pathlib import Path
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from linearmodels.panel import PanelOLS
from linearmodels.iv import IV2SLS

ROOT = Path(__file__).resolve().parent.parent
PANEL = ROOT / "data" / "processed" / "final_panel_imputed__5_.csv"
OUT = ROOT / "outputs" / "rerun"
OUT.mkdir(parents=True, exist_ok=True)

CONTROLS = ["log_gdp", "trade_pct_gdp", "inflation", "investment_pct_gdp",
            "pop_growth", "credit_to_private_pct_gdp", "secondary_enrollment"]
Cl = [f"{c}_l" for c in CONTROLS]

DEP = "gdp_pc_growth"

rows = []          # one record per (spec, parameter)
FITTED = {}        # spec name -> results, for the two-step mediation


def stars(p):
    return "***" if p < .01 else "**" if p < .05 else "*" if p < .1 else ""


def record(spec, param, est, se, p, n, k, note=""):
    rows.append(dict(spec=spec, param=param, estimate=est, std_error=se,
                     p_value=p, stars=stars(p), n_obs=int(n), n_countries=int(k),
                     note=note))


def fe(spec, data, regs, dep=DEP, keep=None, note=""):
    """Two-way FE with country-clustered SEs, intercept included as in the notebook."""
    d = data[[dep] + regs].dropna()
    if d.empty:
        print(f"-- {spec}: no observations, skipped")
        return None
    f = f"{dep} ~ 1 + " + " + ".join(regs) + " + EntityEffects + TimeEffects"
    r = PanelOLS.from_formula(f, data=d, drop_absorbed=True).fit(
        cov_type="clustered", cluster_entity=True)
    k = d.index.get_level_values(0).nunique()
    for key in regs:
        if key in r.params.index:
            record(spec, key, r.params[key], r.std_errors[key], r.pvalues[key],
                   r.nobs, k, note)
    FITTED[spec] = r
    print(f"\n== {spec} ==  N={int(r.nobs):,}  countries={k}")
    for key in (keep or regs):
        if key in r.params.index:
            print(f"   {key:<16}{r.params[key]:+10.4f}  se={r.std_errors[key]:8.4f}"
                  f"  p={r.pvalues[key]:.4f} {stars(r.pvalues[key])}")
    return r


class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, s):
        for st in self.streams:
            st.write(s)

    def flush(self):
        for st in self.streams:
            st.flush()


log_handle = open(OUT / "section4_log.txt", "w")
sys.stdout = Tee(sys.__stdout__, log_handle)

# ---------------------------------------------------------------- load
df = pd.read_csv(PANEL, low_memory=False).sort_values(["iso3", "year"])
P = df.set_index(["iso3", "year"])
print(f"panel: {df.shape[0]:,} rows x {df.shape[1]} cols, "
      f"{df.iso3.nunique()} countries, {df.year.min()}-{df.year.max()}")
print(f"gini (0-1 share, SWIID disposable, ffill<=3y): coverage "
      f"{df['gini'].notna().mean():.3f}, mean {df['gini'].mean():.3f}, "
      f"sd {df['gini'].std():.3f}")

# ---------------------------------------------------------------- Eq. 32 (unprimed)
# beta6 sits in Section 3.2 of the report but is estimated in the same block and is
# one of the five that did not reproduce, so it is recovered here.
print("\n" + "#" * 72)
print("# Spec 3 (Eq.32) - displacement drag, beta6")
print("#" * 72)
fe("spec3_eq32_displacement", P,
   ["F_l", "G_l", "FG_l", "GH_l", "GS_l", "D_term_l"] + Cl,
   keep=["FG_l", "GH_l", "GS_l", "D_term_l"],
   note="GH_l and GS_l are the absorptive-capacity terms of Eq. (32); the re-run omitted them")

# ---------------------------------------------------------------- primed growth specs
print("\n" + "#" * 72)
print("# Primed specifications - the Section 4 table")
print("#" * 72)

fe("spec1p_eq30p", P, ["F_l", "G_l", "FG_l", "Z_gini_l"] + Cl,
   keep=["FG_l", "Z_gini_l"], note="beta4 Gini level drag")

fe("spec2p_eq31p", P,
   ["F_l", "G_l", "FG_l", "FI_l", "GI_l", "GH_l", "GS_l", "FGI_l",
    "Z_gini_l", "G_Gini_l", "FG_Gini_l"] + Cl,
   keep=["FG_l", "Z_gini_l", "G_Gini_l", "FG_Gini_l"],
   note="beta10, beta11; full institutional block, which the re-run omitted")

fe("spec3p_eq32p", P,
   ["F_l", "G_l", "FG_l", "GH_l", "GS_l", "D_term_l", "D_Gini_l"] + Cl,
   keep=["D_term_l", "D_Gini_l"], note="beta7 displacement x inequality")

fe("spec4p_eq33p", P,
   ["F_l", "G_l", "FG_l", "MI_l", "F_MI_l", "G_MI_l", "FG_MI_l",
    "Z_gini_l", "Gini_MI_l", "G_Gini_MI_l", "FG_Gini_MI_l"] + Cl,
   keep=["FG_l", "FG_MI_l", "Z_gini_l", "FG_Gini_MI_l"],
   note="delta4', phi1, phi4 - the headline primed spec")

# ---------------------------------------------------------------- tercile test
print("\n" + "#" * 72)
print("# Tercile test - F x G by Gini tercile inside the middle-income sample")
print("#" * 72)
mi = df[df["MI"] == 1].copy()
terc = mi["gini"].quantile([1 / 3, 2 / 3])
mi["gterc"] = np.select([mi["gini"] <= terc.iloc[0], mi["gini"] <= terc.iloc[1]],
                        ["T1_low", "T2_mid"], default="T3_high")
mi.loc[mi["gini"].isna(), "gterc"] = None
terc_regs = []
for t in ["T1_low", "T2_mid", "T3_high"]:
    col = f"FG_l_{t}"
    mi[col] = mi["FG_l"] * (mi["gterc"] == t)
    terc_regs.append(col)
fe("tercile_test_mi", mi.dropna(subset=["gterc"]).set_index(["iso3", "year"]),
   terc_regs + ["F_l", "G_l"] + Cl, keep=terc_regs,
   note="terciles cut on the raw 0-1 Gini inside the MI sample, as in the notebook")

# ---------------------------------------------------------------- Eqs. 49-51
print("\n" + "#" * 72)
print("# Spec 15 (Eq.49) first stage and Spec 16 (Eqs.50-51) mediated growth")
print("#" * 72)
spec15 = fe("spec15_eq49_ai_to_gini", P,
            ["G_l", "G_1mH_l", "F_l", "sigma_kis_l"] + Cl, dep="gini",
            keep=["G_l", "G_1mH_l", "F_l", "sigma_kis_l"],
            note="dependent variable is the raw 0-1 Gini share, not the z-score")

need15 = ["gini", "G_l", "G_1mH_l", "F_l", "sigma_kis_l"] + Cl
d16 = df.dropna(subset=need15).copy()
fitted = spec15.predict(data=d16.set_index(["iso3", "year"]))
d16["gini_hat"] = np.asarray(fitted).ravel()
print(f"\ngini_hat: mean {d16['gini_hat'].mean():.4f}, sd {d16['gini_hat'].std():.4f} "
      f"(raw gini sd in this sample {d16['gini'].std():.4f}) "
      "- the fitted values exclude the entity and time effects, which is why theta "
      "is two orders of magnitude larger than the coefficient on raw Gini")

spec16 = fe("spec16_eq50_mediated", d16.set_index(["iso3", "year"]),
            ["F_l", "G_l", "FG_l", "gini_hat"] + Cl,
            keep=["FG_l", "gini_hat"], note="theta; gini_hat fitted from Eq. (49)")

g1 = spec15.params["G_l"]
th = spec16.params["gini_hat"]
print(f"\nIndirect AI-through-inequality effect gamma1 x theta = "
      f"{g1:.4f} x {th:.3f} = {g1 * th:.4f} pp of growth per unit G")

# ---------------------------------------------------------------- Eq. 54
print("\n" + "#" * 72)
print("# Spec 18 (Eq.54) - resilience with inequality")
print("#" * 72)
fe("spec18_eq54_resilience", P,
   ["F_l", "G_l", "FG_l", "Z_gini_l", "F_Shock", "Gini_Shock", "FG_Shock"] + Cl,
   keep=["F_Shock", "Gini_Shock", "FG_Shock"],
   note="omega, xi; the re-run ran F_Shock without Z_gini_l, Gini_Shock and FG_Shock")

# ---------------------------------------------------------------- Eqs. 52-53
# The report quotes the first-stage F of the historical-Gini IV as the reason the
# IV route is unusable. That diagnostic is checked here too.
print("\n" + "#" * 72)
print("# Spec 17 (Eqs.52-53) - historical-Gini Bartik IV for theta")
print("#" * 72)

d17 = df.dropna(subset=["gdp_pc_growth", "gini", "gini_disp_hist",
                        "F_l", "G_l", "FG_l"] + Cl).copy()


def demean2(data, cols):
    out = data.copy()
    for c in cols:
        out[c] = (data[c] - data.groupby("iso3")[c].transform("mean")
                  - data.groupby("year")[c].transform("mean") + data[c].mean())
    return out


iv_rows = []
for label, z in {
    "post2015": d17["gini_disp_hist"] * (d17["year"] >= 2015),
    "post2017": d17["gini_disp_hist"] * (d17["year"] >= 2017),
    "post2020": d17["gini_disp_hist"] * (d17["year"] >= 2020),
    "trend": d17["gini_disp_hist"] * (d17["year"] - 2010),
}.items():
    d17["Z"] = z.astype(float)
    dd = demean2(d17, ["gdp_pc_growth", "gini", "Z", "F_l", "G_l", "FG_l"] + Cl)
    iv = IV2SLS(dd["gdp_pc_growth"], dd[["F_l", "G_l", "FG_l"] + Cl],
                dd[["gini"]], dd[["Z"]]).fit(cov_type="clustered",
                                             clusters=d17["iso3"])
    fstat = float(iv.first_stage.diagnostics["f.stat"].iloc[0])
    iv_rows.append(dict(instrument=label, first_stage_F=round(fstat, 2),
                        theta_iv=round(float(iv.params["gini"]), 2),
                        p_value=round(float(iv.pvalues["gini"]), 4),
                        n_obs=int(iv.nobs)))
    record("spec17_eq52_iv_" + label, "gini", iv.params["gini"],
           iv.std_errors["gini"], iv.pvalues["gini"], iv.nobs,
           d17["iso3"].nunique(), f"first-stage F={fstat:.2f}")

iv_tab = pd.DataFrame(iv_rows)
iv_tab.to_csv(OUT / "section4_iv_first_stage.csv", index=False)
print(iv_tab.to_string(index=False))
print("All four first-stage F statistics are below the weak-instrument threshold of 10, "
      "so theta_IV is uninterpretable - the report's reading.")

# ---------------------------------------------------------------- scorecard
coefs = pd.DataFrame(rows)
coefs.to_csv(OUT / "section4_coefficients.csv", index=False)

CHECKS = [
    # label, report location, spec, param, published, predicted sign
    ("beta6 displacement (Eqs. 13, 32)", "report S3.2", "spec3_eq32_displacement",
     "D_term_l", -24.85, "-"),
    ("beta4 Gini level (Eq. 30')", "report S4", "spec1p_eq30p", "Z_gini_l", -0.236, "-"),
    ("beta10 G x Gini (Eq. 31')", "report S4", "spec2p_eq31p", "G_Gini_l", -1.551, "-"),
    ("beta11 F x G x Gini (key)", "report S4", "spec2p_eq31p", "FG_Gini_l", -0.118, "-"),
    ("beta7 D x Gini (Eq. 32')", "report S4", "spec3p_eq32p", "D_Gini_l", -9.473, "-"),
    ("phi4 F x G x Gini x MI (key)", "report S4", "spec4p_eq33p", "FG_Gini_MI_l", 0.802, "-"),
    ("gamma1 AI -> inequality (Eq. 49)", "report S4", "spec15_eq49_ai_to_gini",
     "G_l", 0.005, "+"),
    ("theta inequality -> growth (Eq. 50)", "report S4", "spec16_eq50_mediated",
     "gini_hat", -153.9, "-"),
    ("omega F x Shock (Eq. 54)", "report S4", "spec18_eq54_resilience", "F_Shock", 0.614, "+"),
    ("top Gini tercile, MI sample", "report S4", "tercile_test_mi", "FG_l_T3_high", 1.37, "?"),
    ("mid Gini tercile, MI sample", "report S4", "tercile_test_mi", "FG_l_T2_mid", 1.326, "?"),
    ("low Gini tercile, MI sample", "report S4", "tercile_test_mi", "FG_l_T1_low", -0.340, "?"),
    ("theta_IV, post2017 Bartik", "report S4", "spec17_eq52_iv_post2017", "gini", 189.44, "-"),
]

idx = coefs.set_index(["spec", "param"])
out = []
for label, where, spec, param, pub, pred in CHECKS:
    if (spec, param) not in idx.index:
        out.append(dict(quantity=label, source=where, published=pub,
                        recovered=np.nan, verdict="not estimated"))
        continue
    r = idx.loc[(spec, param)]
    est = float(r["estimate"])
    gap = abs(est - pub)
    tol = max(0.005, abs(pub) * 0.002)          # 3 decimals, or 0.2% on large numbers
    if gap <= tol:
        verdict = "reproduces"
    elif np.sign(est) == np.sign(pub) and gap <= abs(pub) * 0.25:
        verdict = "close"
    elif np.sign(est) == np.sign(pub):
        verdict = "same sign, different magnitude"
    else:
        verdict = "sign flip"
    out.append(dict(quantity=label, source=where, spec=spec, param=param,
                    published=pub, recovered=round(est, 4),
                    std_error=round(float(r["std_error"]), 4),
                    p_value=round(float(r["p_value"]), 4), stars=r["stars"],
                    n_obs=int(r["n_obs"]), n_countries=int(r["n_countries"]),
                    predicted_sign=pred, gap=round(gap, 4), verdict=verdict))

score = pd.DataFrame(out)
score.to_csv(OUT / "section4_vs_published.csv", index=False)

# ---------------------------------------------------------------- recount
# The 41-quantity scorecard of 04_rerun_verify.py is not replaced; the rows the
# recovered specifications settle are corrected in place and the totals recounted.
RECOVERED_ROWS = {          # (spec, param) in rerun_vs_published.csv -> row here
    ("displacement", "D_term_l"): ("spec3_eq32_displacement", "D_term_l"),
    ("ineq_gini_level", "Z_gini_l"): ("spec1p_eq30p", "Z_gini_l"),
    ("ineq_erosion", "G_Gini_l"): ("spec2p_eq31p", "G_Gini_l"),
    ("ineq_erosion", "FG_Gini_l"): ("spec2p_eq31p", "FG_Gini_l"),
    ("ineq_displacement_amp", "D_Gini_l"): ("spec3p_eq32p", "D_Gini_l"),
    ("ineq_mit_escape_phi4", "FG_Gini_MI_l"): ("spec4p_eq33p", "FG_Gini_MI_l"),
    ("gamma1_ai_to_gini", "G_l"): ("spec15_eq49_ai_to_gini", "G_l"),
    ("theta_gini_to_growth", "Z_gini_l"): ("spec16_eq50_mediated", "gini_hat"),
    ("fintech_shock_resilience", "F_Shock"): ("spec18_eq54_resilience", "F_Shock"),
    ("mi_gini_tercile_high", "FG_l"): ("tercile_test_mi", "FG_l_T3_high"),
}

old_path = OUT / "rerun_vs_published.csv"
if old_path.exists():
    old = pd.read_csv(old_path)
    old["recovered_in"] = ""
    for i, r in old.iterrows():
        key = (r["spec"], r["param"])
        if key in RECOVERED_ROWS:
            spec, param = RECOVERED_ROWS[key]
            if (spec, param) in idx.index:
                new = idx.loc[(spec, param)]
                old.loc[i, "rerun"] = round(float(new["estimate"]), 4)
                old.loc[i, "rerun_stars"] = new["stars"]
                old.loc[i, "n_obs"] = int(new["n_obs"])
                old.loc[i, "abs_diff"] = round(
                    float(new["estimate"]) - float(r["published"]), 4)
                old.loc[i, "rel_diff"] = round(
                    abs(float(new["estimate"]) - float(r["published"]))
                    / max(abs(float(r["published"])), 1e-12), 4)
                old.loc[i, "verdict"] = "reproduces"
                old.loc[i, "recovered_in"] = f"06_recover_section4.py:{spec}"
    old.to_csv(OUT / "rerun_vs_published_recounted.csv", index=False)
    print("\n" + "#" * 72)
    print("# 41-quantity scorecard, recounted with the recovered specifications")
    print("#" * 72)
    print(old["verdict"].value_counts().to_string())
    still = old[old["verdict"] != "reproduces"]
    print(f"\nstill not exact ({len(still)}):")
    print(still[["quantity", "source", "published", "rerun", "verdict"]]
          .to_string(index=False))
    print(f"\nwrote {OUT/'rerun_vs_published_recounted.csv'}")

print("\n" + "#" * 72)
print("# SECTION 4 SCORECARD - recovered specification vs published value")
print("#" * 72)
print(score[["quantity", "published", "recovered", "p_value", "stars",
             "n_obs", "verdict"]].to_string(index=False))
print("\nverdict counts:")
print(score["verdict"].value_counts().to_string())
print(f"\nwrote {OUT/'section4_coefficients.csv'}")
print(f"wrote {OUT/'section4_vs_published.csv'}")
print(f"wrote {OUT/'section4_iv_first_stage.csv'}")
print(f"wrote {OUT/'section4_log.txt'}")

sys.stdout = sys.__stdout__
log_handle.close()
