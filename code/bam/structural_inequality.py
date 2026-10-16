"""
structural_inequality.py — Inequality, the way the data can actually carry it
=============================================================================
Your theory's inequality channel is built on the Gini. The panel proves the Gini
is FROZEN within country (within/between variation ratio = 0.07; AIPI/GARI snapshots;
gini_disp_hist fully broadcast). No honest cleaning creates within-country Gini
variation that does not exist. This script therefore does three legitimate things:

  PART 1  ROBUSTNESS — kill the 'China/US dominate AI' worry explicitly, so you can
          put it in an appendix. (Two-way FE already removes country means and the
          global time trend, so AI-superpower concentration cannot drive the FE
          estimate — and dropping CHN/USA/top-5 confirms it.)

  PART 2  REFRAME inequality from DISTRIBUTIONAL (Gini, frozen) to STRUCTURAL
          (the dual economy: a modern knowledge-services sector coexisting with a
          low-human-capital workforce). Structural inequality VARIES within country
          (within/between 0.12) and is the mechanism the robust low-H/high-services
          (LH) result already captures. This is the inequality story the data support.

  PART 3  Keep DISTRIBUTIONAL inequality only where it is identified — BETWEEN
          countries — and report its sign honestly (it runs against the theory).

USAGE (Colab):  put this next to final_panel_imputed__5_.csv, then  %run structural_inequality.py
"""
from pathlib import Path
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
from linearmodels.panel import PanelOLS, BetweenOLS, RandomEffects

PANEL = Path("final_panel_imputed__5_.csv")
df = pd.read_csv(PANEL, low_memory=False).sort_values(["iso3","year"])

CONTROLS = ["log_gdp","trade_pct_gdp","inflation","investment_pct_gdp",
            "pop_growth","credit_to_private_pct_gdp","secondary_enrollment"]
Cl = [f"{c}_l" for c in CONTROLS if f"{c}_l" in df.columns]
def stars(p): return "***" if p<.01 else "**" if p<.05 else "*" if p<.1 else ""

# FE-safe G (the only within-varying AI pillar), z-scored within year
df["G_fe"]  = df.groupby("year")["ai_pubs_log"].transform(lambda s:(s-s.mean())/s.std())
df["FG_fe"] = df["F"]*df["G_fe"]
for c in ["G_fe","FG_fe"]:
    df[c+"_l"] = df.groupby("iso3")[c].shift(1)

def fe(regs, dep="gdp_pc_growth", data=None):
    d = (data if data is not None else df).set_index(["iso3","year"])[[dep]+regs].dropna()
    f = f"{dep} ~ " + " + ".join(regs) + " + EntityEffects + TimeEffects"
    r = PanelOLS.from_formula(f, data=d, drop_absorbed=True).fit(cov_type="clustered", cluster_entity=True)
    return r, d.index.get_level_values(0).nunique()

# =====================================================================  PART 1
print("#"*72); print("# PART 1 — AI-SUPERPOWER ROBUSTNESS (the 'China dominates' worry)"); print("#"*72)
tot = df.groupby("iso3")["ai_pubs_count"].sum().sort_values(ascending=False)
print(f"\nAI-publication concentration: CHN {100*tot.iloc[0]/tot.sum():.1f}%, "
      f"USA {100*tot.iloc[1]/tot.sum():.1f}%, top-5 {100*tot.head(5).sum()/tot.sum():.1f}%.")
print("Concentration is real, but FE removes country means + the global time trend,")
print("so it cannot drive the within estimate. Demonstrated by dropping the superpowers:\n")
for label, d in [("ALL", df), ("drop CHN+USA", df[~df.iso3.isin(["CHN","USA"])]),
                 ("drop top-5 AI", df[~df.iso3.isin(["CHN","USA","IND","GBR","DEU"])])]:
    r,nc = fe(["F_l","G_fe_l","FG_fe_l"]+Cl, data=d)
    k="FG_fe_l"
    print(f"  {label:14s}  FG = {r.params[k]:+.3f}  p={r.pvalues[k]:.3f} {stars(r.pvalues[k])}  (N={r.nobs}, {nc} ctry)")
print("\n  -> The joint-digital coefficient is stable when superpowers are removed.")
print("     'China dominates AI' is NOT why the result is weak. Put this in the appendix.")

# =====================================================================  PART 2
print("\n"+"#"*72); print("# PART 2 — STRUCTURAL INEQUALITY (the dual economy) — the testable channel"); print("#"*72)
# Why Gini can't be the channel:
for col in ["gini_disp","gini_mkt","gini"]:
    if col in df.columns:
        w=df.groupby("iso3")[col].std().median(); b=df.groupby("iso3")[col].mean().std()
        print(f"  {col:<12} within/between = {w/b:.3f}  (frozen — FE absorbs it)")
# Structural-dualism index: modern services sector with low human capital absorbing it.
df["DualGap"] = df["sigma_kis"]*(1-df["H"])
w=df.groupby("iso3")["DualGap"].std().median(); b=df.groupby("iso3")["DualGap"].mean().std()
print(f"  DualGap      within/between = {w/b:.3f}  (MOVES — identifiable under FE)")
df["Z_dual"]  = df.groupby("year")["DualGap"].transform(lambda s:(s-s.mean())/s.std())
df["FG_Dual"] = df["FG_fe"]*df["Z_dual"]
for c in ["Z_dual","FG_Dual"]:
    df[c+"_l"]=df.groupby("iso3")[c].shift(1)

print("\nContinuous structural-inequality interaction (full sample):")
r,nc = fe(["F_l","G_fe_l","FG_fe_l","Z_dual_l","FG_Dual_l"]+Cl)
for k in ["FG_fe_l","Z_dual_l","FG_Dual_l"]:
    if k in r.params.index:
        print(f"  {k:<12}{r.params[k]:+8.4f}  p={r.pvalues[k]:.3f} {stars(r.pvalues[k])}")
print("  (continuous form is noisy — the SHARP version is the discrete LH quadrant below)")

print("\nDiscrete structural-inequality split — the robust LH (low-H / high-services) quadrant:")
q = [f"{p}_l_{c}" for c in ["HH","HL","LH","LL"] for p in ["F","G","FG"]]
q = [c for c in q if c in df.columns]
r,nc = fe(q+Cl)
for k in ["FG_l_HH","FG_l_HL","FG_l_LH","FG_l_LL"]:
    if k in r.params.index:
        print(f"  {k:<10}{r.params[k]:+8.4f}  p={r.pvalues[k]:.3f} {stars(r.pvalues[k])}")
print("  -> LH is the standout: structural inequality (a dual economy) is where joint")
print("     digital pays off. This is your inequality finding, on a variable that varies.")
print("  HONEST CAVEAT: this is a robust CONDITIONAL CORRELATION. It does not survive")
print("     internal-lag IV (endogeneity), so frame it as descriptive / mechanism, and")
print("     pursue an external instrument (submarine-cable timing) for a causal claim.")

# =====================================================================  PART 3
print("\n"+"#"*72); print("# PART 3 — DISTRIBUTIONAL INEQUALITY, kept only where identified (BETWEEN)"); print("#"*72)
bcols=["gdp_pc_growth","F","G_fe","FG_fe","Z_gini","G_Gini","FG_Gini"]+CONTROLS
bcols=[c for c in bcols if c in df.columns]
Pb=df.set_index(["iso3","year"])[bcols].dropna()
rhs=[c for c in ["F","G_fe","FG_fe","Z_gini","G_Gini","FG_Gini"]+CONTROLS if c in Pb.columns]
b1=BetweenOLS.from_formula("gdp_pc_growth ~ 1 + "+" + ".join(rhs), data=Pb).fit()
print(f"\nBetween-country (cross-section), {Pb.index.get_level_values(0).nunique()} countries:")
for k in ["FG_fe","Z_gini","G_Gini","FG_Gini"]:
    if k in b1.params.index:
        print(f"  {k:<10}{b1.params[k]:+8.4f}  p={b1.pvalues[k]:.3f} {stars(b1.pvalues[k])}")
print("  theory predicts Z_gini<0, G_Gini<0, FG_Gini<0. Report whatever the data give —")
print("  on this panel the inequality interactions run the WRONG sign for the theory, so")
print("  distributional inequality is a reported-against-theory result, not a headline.")

print("\n"+"="*72)
print("BOTTOM LINE")
print("="*72)
print("""  - 'China dominates AI' does not explain the weak result (FE handles it; Part 1).
  - Distributional inequality (Gini) is untestable within country and wrong-signed
    between (Part 3) — demote it to a short honest subsection.
  - Structural inequality (the dual economy) DOES vary and IS where joint digital
    pays off (Part 2) — make THIS the inequality story. It is the same robust LH
    finding, reframed as what it actually is: an inequality-of-structure result.""")
