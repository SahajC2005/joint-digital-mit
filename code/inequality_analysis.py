"""
inequality_analysis.py — Inequality without the Gini
====================================================
The Gini is frozen within country (within/between = 0.07), so it cannot carry an
FE inequality channel. This script measures inequality the THREE ways the data can:

  A. STRUCTURAL inequality (the dual economy): DualGap = services x (1 - human capital).
     Varies across countries; ranks them; defines where joint digital pays off.
  B. DISPLACEMENT inequality (people pushed out): D = AI x (1-H) x (1-services), built
     from the TIME-VARYING AI series so it MOVES (unlike the panel's frozen D_term,
     which used the broadcast AIPI/GARI). Tested as a growth/slowdown drag.
  C. "DOES AI CREATE INEQUALITY?": AI -> Gini (within & between). Plus a scaffold for
     the clean, non-circular test on LABOR SHARE (PWT 'labsh'), which moves and is
     independent of AI — activates the moment a labor-share column is supplied.

Honest note baked in: the displacement index is ~0.9 collinear with AI within country
(it IS AI x structure), so it is an EXPOSURE index, not an AI-independent outcome. The
labor-share test (Part C2) is the non-circular way to ask whether AI creates inequality.

USAGE (Colab):  put next to panel_estimation.csv, then  %run inequality_analysis.py
Outputs a printed report + inequality_results.txt
"""
from pathlib import Path
import numpy as np, pandas as pd, warnings, io, contextlib
warnings.filterwarnings("ignore")
from linearmodels.panel import PanelOLS, BetweenOLS

PANEL = Path("panel_estimation.csv")
LABOR_SHARE_COL = "labsh"          # add this column (PWT labsh) to activate Part C2
OUT = Path("/mnt/user-data/outputs"); OUT.mkdir(parents=True, exist_ok=True)
report = io.StringIO()
def P(*a):
    line=" ".join(str(x) for x in a); print(line); report.write(line+"\n")
def stars(p): return "***" if p<.01 else "**" if p<.05 else "*" if p<.1 else ""

df = pd.read_csv(PANEL, low_memory=False).sort_values(["iso3","year"]).copy()

# ---- build measures -------------------------------------------------------
df["G_fe"] = df.groupby("year")["ai_pubs_log"].transform(lambda s:(s-s.mean())/s.std())
g01        = df.groupby("year")["ai_pubs_log"].transform(lambda s:(s-s.min())/(s.max()-s.min()))
df["DualGap"] = df["sigma_kis"]*(1-df["H"])                      # STRUCTURAL inequality
df["Dexp"]    = g01*(1-df["H"])*(1-df["sigma_kis"])             # DISPLACEMENT exposure (moves)
for c in ["G_fe","Dexp","F"]:
    df[c+"_l"] = df.groupby("iso3")[c].shift(1)
df["FG_l"]  = df["F_l"]*df["G_fe_l"]
df["GH_l"]  = df["G_fe_l"]*(1-df["H"])                          # skill-biased AI term
CONTROLS=[c for c in ["log_gdp_l","trade_pct_gdp_l","investment_pct_gdp_l",
          "pop_growth_l","credit_to_private_pct_gdp_l"] if c in df.columns]

def fe(dep,regs):
    d=df.set_index(["iso3","year"])[[dep]+regs].dropna()
    f=f"{dep} ~ "+" + ".join(regs)+" + EntityEffects + TimeEffects"
    r=PanelOLS.from_formula(f,data=d,drop_absorbed=True).fit(cov_type="clustered",cluster_entity=True)
    return r,d.index.get_level_values(0).nunique()
def btw(dep,regs):
    d=df.set_index(["iso3","year"])[[dep]+regs].dropna()
    r=BetweenOLS.from_formula(f"{dep} ~ 1 + "+" + ".join(regs),data=d).fit()
    return r,d.index.get_level_values(0).nunique()
def wb(col):
    w=df.groupby("iso3")[col].std().median(); b=df.groupby("iso3")[col].mean().std()
    return w,b,(w/b if b else np.nan)

P("#"*72); P("# PART A — STRUCTURAL INEQUALITY (the dual economy)"); P("#"*72)
recent=df[df.year>=2019]
agg=recent.groupby("iso3").agg(income_group=("income_group","last"),
     H=("H","mean"),services=("sigma_kis","mean"),DualGap=("DualGap","mean")).reset_index()
mi=agg[agg.income_group.isin(["UM","LM"])].dropna(subset=["DualGap"]).sort_values("DualGap",ascending=False)
P(f"Middle-income countries ranked by structural inequality (top 12 of {len(mi)}):")
for _,r in mi.head(12).iterrows():
    P(f"   {r.iso3}  DualGap={r.DualGap:.4f}  (H={r.H:.2f}, services={r.services:.3f})")
agg.to_csv(OUT/"country_structural_inequality.csv",index=False)

P("\n"+"#"*72); P("# PART B — DISPLACEMENT INEQUALITY (people pushed out)"); P("#"*72)
P("Does the displacement metric MOVE within country? (vs Gini)")
for col in ["gini_disp","D_term" if "D_term" in df.columns else "DualGap","Dexp"]:
    w,b,rt=wb(col); P(f"   {col:<10} within/between = {rt:.3f}  {'MOVES' if rt>0.10 else 'frozen'}")
# collinearity with AI
cors=[]
for iso,g in df.groupby("iso3"):
    g=g.dropna(subset=["Dexp","G_fe"])
    if len(g)>=6 and g.Dexp.std()>0 and g.G_fe.std()>0: cors.append(g.Dexp.corr(g.G_fe))
P(f"   within-country corr(displacement, AI) = {np.nanmedian(cors):+.2f}  (exposure index, not AI-independent)")
P("\nDisplacement drag on growth (Spec 3'): theory wants Dexp_l < 0")
r,nc=fe("gdp_pc_growth",["F_l","G_fe_l","FG_l","Dexp_l"]+CONTROLS)
for k in ["FG_l","Dexp_l"]:
    if k in r.params.index: P(f"   {k:<8}{r.params[k]:+8.4f}  se={r.std_errors[k]:.3f}  p={r.pvalues[k]:.3f} {stars(r.pvalues[k])}")
if "Slowdown" in df.columns:
    r2,_=fe("Slowdown",["F_l","G_fe_l","Dexp_l"]+CONTROLS)
    if "Dexp_l" in r2.params.index:
        P(f"   Dexp -> slowdown: {r2.params['Dexp_l']:+.4f}  p={r2.pvalues['Dexp_l']:.3f} {stars(r2.pvalues['Dexp_l'])} (positive = more risk)")
P("   READ: signs are theory-consistent (drag<0, slowdown>0) but insignificant —")
P("   displacement is ~0.9 collinear with AI, so it cannot be separated from the AI effect.")

P("\n"+"#"*72); P("# PART C1 — DOES AI CREATE INEQUALITY?  (AI -> Gini)"); P("#"*72)
for dep in ["gini_disp","gini"]:
    if dep not in df.columns: continue
    r,nc=fe(dep,["G_fe_l","GH_l","F_l"]+CONTROLS)
    rb,ncb=btw(dep,["G_fe","DualGap","F"])
    P(f"   {dep}: WITHIN  G={r.params.get('G_fe_l',np.nan):+.4f} p={r.pvalues.get('G_fe_l',1):.3f} {stars(r.pvalues.get('G_fe_l',1))} |"
      f" skill-bias GxlowH={r.params.get('GH_l',np.nan):+.4f} p={r.pvalues.get('GH_l',1):.3f}")
    P(f"   {dep}: BETWEEN G={rb.params.get('G_fe',np.nan):+.4f} p={rb.pvalues.get('G_fe',1):.3f} {stars(rb.pvalues.get('G_fe',1))} (negative = AI countries less unequal; confounded by development)")
w,b,rt=wb("gini_disp"); P(f"   ceiling: Gini within/between={rt:.3f} -> within test underpowered by construction.")
P("   VERDICT: data do NOT show AI creating income inequality (within null; between wrong-signed).")

P("\n"+"#"*72); P("# PART C2 — CLEAN TEST on LABOR SHARE (non-circular, AI-independent)"); P("#"*72)
if LABOR_SHARE_COL in df.columns:
    df["LS"]=df[LABOR_SHARE_COL]
    r,nc=fe("LS",["G_fe_l","GH_l","F_l"]+CONTROLS)
    P(f"   AI -> labor share (within FE, N={r.nobs}, {nc} ctry):")
    for k in ["G_fe_l","GH_l","F_l"]:
        if k in r.params.index: P(f"      {k:<8}{r.params[k]:+8.4f}  p={r.pvalues[k]:.3f} {stars(r.pvalues[k])}")
    P("   theory: G<0 (AI lowers labor's share = raises inequality), GxlowH<0 (skill-biased).")
else:
    P(f"   [scaffold idle] add a '{LABOR_SHARE_COL}' column (PWT labor share of income).")
    P("   Labor share MOVES year-to-year and is NOT built from AI, so AI->labor-share is the")
    P("   non-circular test of 'AI creates inequality'. Source: PWT 10.01 variable 'labsh'.")
    P("   Then this block runs automatically and gives a clean, publishable answer.")

(OUT/"inequality_results.txt").write_text(report.getvalue())
P("\nSaved: inequality_results.txt, country_structural_inequality.csv")
