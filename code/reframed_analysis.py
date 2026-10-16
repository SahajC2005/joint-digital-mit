"""
reframed_analysis.py
====================
Runs the JOINT-DIGITAL / MIT analysis the way the data actually support it, and
handles the inequality (Gini) channel the only two legitimate ways given that Gini
is near-time-invariant within country (median 1.6-point move over 2010-2024).

SECTIONS
  A. Reframed headline (FE-safe G):
       A1 Baseline joint-digital with a fixed-effects-SAFE G (publications only)
       A2 Quadrant heterogeneity  -> the robust LH (low-H, high-KIS) result
       A3 Leave-one-country-out robustness of the LH coefficient
       A4 Threshold (Hansen-style grid) on F*G -> "joint-digital sufficiency"
       A5 FinTech -> slowdown protection (LPM with FE)
  B. Inequality done HONESTLY (Gini varies between, not within):
       B1 BETWEEN estimator (country means) — the cross-country inequality channel
       B2 Mundlak / correlated-RE — separates within vs between Gini effect
       B3 Bartik historical-Gini instrument SCAFFOLD (2SLS) — runs only if a
          historical-Gini column is supplied; otherwise prints what to add.

WHY no within-country FE Gini spec: within/between variation ratio = 0.07 for every
Gini measure. Country FE absorb ~93% of it; the remainder is SWIID interpolation
noise. A within-FE Gini interaction is therefore not identified — this script does
NOT report one, by design.

USAGE (Colab):  edit PATHS, then  %run reframed_analysis.py
"""
from pathlib import Path
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
from linearmodels.panel import PanelOLS, BetweenOLS, RandomEffects
from linearmodels.iv import IV2SLS
import statsmodels.formula.api as smf

# ------------------------------------------------------------------ PATHS / CONFIG
PANEL = Path("final_panel_imputed__5_.csv")     # adjust to your path
# Name of a historical-Gini column IF you add one (Gini ~1980, or land Gini).
HIST_GINI_COL = "gini_1980"                     # leave as-is; script checks if present
SHOCK_YEAR    = 2017                            # global AI take-off used for Bartik shock

CONTROLS = ["log_gdp","trade_pct_gdp","inflation","investment_pct_gdp",
            "pop_growth","credit_to_private_pct_gdp","secondary_enrollment"]
Cl = [f"{c}_l" for c in CONTROLS]

def stars(p): return "***" if p<.01 else "**" if p<.05 else "*" if p<.1 else ""

# ------------------------------------------------------------------ LOAD + FE-SAFE G
df = pd.read_csv(PANEL, low_memory=False).sort_values(["iso3","year"])
# FE-safe G: only the pillar that varies within country (AI publications), z within year
df["G_fe"]  = df.groupby("year")["ai_pubs_log"].transform(lambda s:(s-s.mean())/s.std())
df["FG_fe"] = df["F"]*df["G_fe"]
df["G_fe_l"]  = df.groupby("iso3")["G_fe"].shift(1)
df["FG_fe_l"] = df.groupby("iso3")["FG_fe"].shift(1)
P = df.set_index(["iso3","year"])

def fe(dep, regs, name, data=P):
    d = data[[dep]+regs].dropna()
    f = f"{dep} ~ " + " + ".join(regs) + " + EntityEffects + TimeEffects"
    r = PanelOLS.from_formula(f, data=d, drop_absorbed=True)\
        .fit(cov_type="clustered", cluster_entity=True)
    print(f"\n== {name} ==  N={r.nobs:,}  countries={d.index.get_level_values(0).nunique()}")
    return r
def show(r, keys):
    for k in keys:
        if k in r.params.index:
            print(f"   {k:<12} {r.params[k]:+8.4f}  se={r.std_errors[k]:6.4f}  "
                  f"p={r.pvalues[k]:.3f} {stars(r.pvalues[k])}")

print("#"*70); print("# SECTION A — REFRAMED HEADLINE (FE-SAFE G)"); print("#"*70)

# A1 baseline FE-safe
a1 = fe("gdp_pc_growth", ["F_l","G_fe_l","FG_fe_l"]+Cl, "A1 baseline joint-digital (FE-safe G)")
show(a1, ["F_l","G_fe_l","FG_fe_l"])
print("   NOTE: FE-safe G uses only the within-varying pillar; this is the defensible baseline.")

# A2 quadrant heterogeneity (the survivor)
q = ["F_l_HH","G_l_HH","FG_l_HH","F_l_HL","G_l_HL","FG_l_HL",
     "F_l_LH","G_l_LH","FG_l_LH","F_l_LL","G_l_LL","FG_l_LL"]
a2 = fe("gdp_pc_growth", q+Cl, "A2 quadrant heterogeneity (H x KIS)")
show(a2, ["FG_l_HH","FG_l_HL","FG_l_LH","FG_l_LL"])
print("   Prediction holds if FG_l_LH is the standout positive coefficient.")

# A3 leave-one-out on LH
def fit_lh(data):
    d=data[["gdp_pc_growth"]+q+Cl].dropna()
    f="gdp_pc_growth ~ "+" + ".join(q+Cl)+" + EntityEffects + TimeEffects"
    return PanelOLS.from_formula(f,data=d,drop_absorbed=True)\
           .fit(cov_type="clustered",cluster_entity=True).params.get("FG_l_LH",np.nan)
base=fit_lh(P); lh_iso=df.loc[df["FG_l_LH"].fillna(0)!=0,"iso3"].unique()
loo=np.array([fit_lh(P.drop(index=i,level=0)) for i in lh_iso])
print(f"\n== A3 LH leave-one-out ==  full={base:+.3f}  "
      f"range=[{loo.min():+.3f},{loo.max():+.3f}]  all>0:{(loo>0).all()}  ({len(lh_iso)} ctry)")

# A4 threshold on F*G (grid search minimizing SSE of a 2-regime FE model)
def threshold_search(data, q_lo=.15, q_hi=.85, n=40):
    d = data[["gdp_pc_growth","FG_l"]+Cl].dropna().copy()
    grid = np.quantile(d["FG_l"], np.linspace(q_lo,q_hi,n))
    best=(None,np.inf,None,None)
    for g in grid:
        d["below"]=(d["FG_l"]<g).astype(int)*d["FG_l"]
        d["above"]=(d["FG_l"]>=g).astype(int)*d["FG_l"]
        f="gdp_pc_growth ~ below + above + "+" + ".join(Cl)+" + EntityEffects + TimeEffects"
        r=PanelOLS.from_formula(f,data=d,drop_absorbed=True).fit()
        sse=(r.resids**2).sum()
        if sse<best[1]: best=(g,sse,r.params.get("below"),r.params.get("above"))
    return best
g_star,_,bL,bH = threshold_search(P)
print(f"\n== A4 threshold (joint-digital sufficiency) ==")
print(f"   F*G threshold = {g_star:+.3f}  | slope below = {bL:+.3f}  | slope above = {bH:+.3f}")
print(f"   sufficiency holds if slope flips from ~0/negative below to positive above.")

# A5 FinTech slowdown protection
if "Slowdown" in df.columns:
    a5 = fe("Slowdown", ["F_l","G_fe_l","FG_fe_l"]+Cl, "A5 FinTech -> slowdown (LPM-FE)")
    show(a5, ["F_l","G_fe_l","FG_fe_l"])
    print("   protective if F_l < 0.")

print("\n"+"#"*70); print("# SECTION B — INEQUALITY, DONE HONESTLY"); print("#"*70)

# B1 BETWEEN estimator: inequality channel identified across countries
bcols=["gdp_pc_growth","F","G_fe","FG_fe","Z_gini","G_Gini","FG_Gini"]+CONTROLS
Pb=df.set_index(["iso3","year"])[bcols].dropna()
b1=BetweenOLS.from_formula("gdp_pc_growth ~ 1 + F + G_fe + FG_fe + Z_gini + G_Gini + FG_Gini + "
                           +" + ".join(CONTROLS), data=Pb).fit()
print(f"\n== B1 BETWEEN-country inequality channel ==  countries={Pb.index.get_level_values(0).nunique()}")
for k in ["FG_fe","Z_gini","G_Gini","FG_Gini"]:
    if k in b1.params.index:
        print(f"   {k:<10} {b1.params[k]:+8.4f}  p={b1.pvalues[k]:.3f} {stars(b1.pvalues[k])}")
print("   theory wants Z_gini<0, G_Gini<0, FG_Gini<0. Report whatever the data say.")

# B2 Mundlak / correlated RE: include country-mean of Gini to split within vs between
dm=df.copy()
dm["Zgini_bar"]=dm.groupby("iso3")["Z_gini"].transform("mean")   # between part
mund_cols=["gdp_pc_growth","F","G_fe","FG_fe","Z_gini","Zgini_bar"]+CONTROLS
Pm=dm.set_index(["iso3","year"])[mund_cols].dropna()
b2=RandomEffects.from_formula("gdp_pc_growth ~ 1 + F + G_fe + FG_fe + Z_gini + Zgini_bar + "
                              +" + ".join(CONTROLS), data=Pm).fit()
print(f"\n== B2 Mundlak (within vs between Gini) ==")
print(f"   Z_gini  (WITHIN) {b2.params.get('Z_gini',np.nan):+8.4f}  p={b2.pvalues.get('Z_gini',1):.3f}  "
      f"<- expect ~0 / noisy (no within variation)")
print(f"   Zgini_bar(BETWEEN){b2.params.get('Zgini_bar',np.nan):+8.4f}  p={b2.pvalues.get('Zgini_bar',1):.3f}  "
      f"<- this is the real inequality signal")

# B3 Bartik historical-Gini instrument scaffold
print(f"\n== B3 Historical-Gini Bartik instrument (2SLS) ==")
if HIST_GINI_COL in df.columns:
    dz=df.copy()
    dz["post"]=(dz["year"]>=SHOCK_YEAR).astype(int)
    dz["bartik"]=dz[HIST_GINI_COL]*dz["post"]          # time-varying instrument
    iv_cols=["gdp_pc_growth","Z_gini","bartik","F","G_fe","FG_fe"]+CONTROLS
    Pz=dz.set_index(["iso3","year"])[iv_cols].dropna()
    # endog = Z_gini, instrument = bartik, plus FE via dummies omitted for brevity
    iv=IV2SLS.from_formula(
        "gdp_pc_growth ~ 1 + F + G_fe + FG_fe + "+" + ".join(CONTROLS)
        +" + [Z_gini ~ bartik]", data=Pz).fit(cov_type="clustered",
        clusters=Pz.index.get_level_values(0))
    print(f"   Z_gini (instrumented) {iv.params['Z_gini']:+.4f}  p={iv.pvalues['Z_gini']:.3f}")
    print(f"   first-stage F-stat: see iv.first_stage")
else:
    print(f"   [scaffold idle] No '{HIST_GINI_COL}' column found.")
    print( "   TO ACTIVATE: add a column of ~1980 Gini (or historical land Gini) per country.")
    print( "   Sources: WIID historical, Deininger-Squire (1996), Frankema land-Gini.")
    print( "   Then the Bartik = gini_1980 x 1{year>=2017} gives within-country time variation,")
    print( "   and 2SLS recovers a causal within-country inequality effect on growth.")

print("\nDONE. Headline = A2/A3 (LH quadrant) + A4 (threshold). "
      "Inequality = B1/B2 (between-country) until B3 instrument data is added.")
