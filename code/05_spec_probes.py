"""
05_spec_probes.py
=================
For the coefficients where `04_rerun_verify.py` does not reproduce the published
value, this script asks the obvious follow-up question: is some *other* plausible
regressor set the one the document was written from?

It prints a small menu of variants per coefficient so the gap can be attributed to
a specification difference rather than to the data. Nothing here is tuned to force
a match; the variants are the ones the framework and the other scripts suggest.

Usage:  python code/05_spec_probes.py
"""
from pathlib import Path
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
from linearmodels.panel import PanelOLS, BetweenOLS

ROOT = Path(__file__).resolve().parent.parent
d = pd.read_csv(ROOT / "data" / "processed" / "final_panel_imputed__5_.csv",
                low_memory=False).sort_values(["iso3", "year"])
P = d.set_index(["iso3", "year"])

C = ["log_gdp", "trade_pct_gdp", "inflation", "investment_pct_gdp",
     "pop_growth", "credit_to_private_pct_gdp", "secondary_enrollment"]
Cl = [c + "_l" for c in C]


def fe(regs, dep="gdp_pc_growth", data=P):
    x = data[[dep] + regs].dropna()
    f = f"{dep} ~ " + " + ".join(regs) + " + EntityEffects + TimeEffects"
    return PanelOLS.from_formula(f, data=x, drop_absorbed=True).fit(
        cov_type="clustered", cluster_entity=True)


def show(tag, r, keys):
    s = " ".join(f"{k}={r.params[k]:+.4f}(p={r.pvalues[k]:.3f})"
                 for k in keys if k in r.params.index)
    print(f"{tag:46s} N={int(r.nobs):5d}  {s}")


print("=== beta6 displacement variants (published -24.85; per-SD -1.09) ===")
for tag, regs, keys in [
    ("D_term_l only + F,G,FG", ["F_l", "G_l", "FG_l", "D_term_l"] + Cl, ["D_term_l"]),
    ("D_z_l (standardised)", ["F_l", "G_l", "FG_l", "D_z_l"] + Cl, ["D_z_l"]),
    ("D_term_l + MI block",
     ["F_l", "G_l", "FG_l", "MI_l", "F_MI_l", "G_MI_l", "FG_MI_l", "D_term_l"] + Cl,
     ["D_term_l"]),
    ("D_term_l + G_1mH_l + sigma_kis_l",
     ["F_l", "G_l", "FG_l", "D_term_l", "G_1mH_l", "sigma_kis_l"] + Cl, ["D_term_l"]),
    ("D_term_l, no controls", ["F_l", "G_l", "FG_l", "D_term_l"], ["D_term_l"]),
    ("D_term_l + I_l/GI_l/GH_l/GS_l",
     ["F_l", "G_l", "FG_l", "I_l", "GI_l", "GH_l", "GS_l", "D_term_l"] + Cl,
     ["D_term_l"]),
]:
    show(tag, fe(regs), keys)

print("\n=== beta11 F x G x Gini variants (published -0.118) ===")
for tag, regs, keys in [
    ("Eq30' G_Gini + FG_Gini",
     ["F_l", "G_l", "FG_l", "Z_gini_l", "G_Gini_l", "FG_Gini_l"] + Cl,
     ["G_Gini_l", "FG_Gini_l"]),
    ("+ D_term, D_Gini",
     ["F_l", "G_l", "FG_l", "Z_gini_l", "G_Gini_l", "FG_Gini_l", "D_term_l",
      "D_Gini_l"] + Cl, ["G_Gini_l", "FG_Gini_l", "D_Gini_l"]),
    ("full primed with MI block",
     ["F_l", "G_l", "FG_l", "MI_l", "F_MI_l", "G_MI_l", "FG_MI_l", "Z_gini_l",
      "G_Gini_l", "FG_Gini_l", "Gini_MI_l", "G_Gini_MI_l", "FG_Gini_MI_l",
      "D_term_l", "D_Gini_l"] + Cl,
     ["FG_Gini_l", "FG_Gini_MI_l", "D_Gini_l"]),
    ("contemporaneous Gini terms",
     ["F_l", "G_l", "FG_l", "Z_gini", "G_Gini", "FG_Gini"] + Cl,
     ["G_Gini", "FG_Gini"]),
]:
    show(tag, fe(regs), keys)

print("\n=== theta inequality -> growth (published -153.9) ===")
for tag, regs, keys in [
    ("Z_gini_l (z units)", ["Z_gini_l"] + Cl, ["Z_gini_l"]),
    ("gini (0-1 share units)", ["gini"] + Cl, ["gini"]),
    ("gini_disp", ["gini_disp"] + Cl, ["gini_disp"]),
    ("gini + F,G,FG", ["F_l", "G_l", "FG_l", "gini"] + Cl, ["gini"]),
]:
    show(tag, fe(regs), keys)
print("   gini units:", d["gini"].describe()[["mean", "std", "min", "max"]]
      .round(4).to_dict())

print("\n=== omega F x Shock (published +0.614, reported n.s.) ===")
for tag, regs, keys in [
    ("F_Shock + baseline", ["F_l", "G_l", "FG_l", "F_Shock"] + Cl, ["F_Shock"]),
    ("+ Gini_Shock, Z_gini_l",
     ["F_l", "G_l", "FG_l", "F_Shock", "Gini_Shock", "Z_gini_l"] + Cl, ["F_Shock"]),
    ("+ FG_Shock", ["F_l", "G_l", "FG_l", "F_Shock", "FG_Shock"] + Cl, ["F_Shock"]),
]:
    show(tag, fe(regs), keys)

print("\n=== between estimator (published -0.581***) ===")
for tag, regs in [("lagged F_l,G_l,FG_l + controls", ["F_l", "G_l", "FG_l"] + Cl),
                  ("contemporaneous F,G,FG + controls", ["F", "G", "FG"] + C),
                  ("lagged, no controls", ["F_l", "G_l", "FG_l"])]:
    x = P[["gdp_pc_growth"] + regs].dropna()
    b = BetweenOLS.from_formula("gdp_pc_growth ~ 1 + " + " + ".join(regs), data=x).fit()
    k = "FG_l" if "FG_l" in b.params.index else "FG"
    print(f"{tag:46s} k={x.index.get_level_values(0).nunique():4d}  "
          f"{k}={b.params[k]:+.4f}(p={b.pvalues[k]:.3f})")

print("\n=== gamma1 AI -> inequality (published +0.005) ===")
for tag, dep, regs, keys in [
    ("Z_gini_l on G_l, FE", "Z_gini_l", ["F_l", "G_l", "FG_l"] + Cl, ["G_l"]),
    ("gini on G, FE", "gini", ["F", "G", "FG"] + C, ["G"]),
    ("Z_gini on G, no controls", "Z_gini", ["G"], ["G"]),
]:
    show(tag, fe(regs, dep=dep), keys)
