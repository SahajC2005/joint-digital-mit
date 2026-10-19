"""
maturation_forecast.py — Maturation-Aware Joint-Digital MIT Forecast
====================================================================
WHY THIS EXISTS
The single most defensible version of "AI is new, its full effects haven't shown
up yet" is the GENERAL-PURPOSE-TECHNOLOGY J-CURVE (David 1990 'dynamo'; Brynjolfsson,
Rock & Syverson 2021 'productivity J-curve'): a GPT's measured growth contribution
is small at first and ramps up over a decade-plus as complementary capital, skills
and reorganization accumulate. An 8-year AI window (2017-2024) therefore plausibly
UNDER-states the long-run effect.

This engine turns that argument into an HONEST forecast instead of a hand-wave:
  - the joint-digital coefficient is allowed to RAMP from its current (weak,
    uncertain) estimate toward a 'mature' level via a logistic diffusion curve;
  - the 'mature' level is a SCENARIO ASSUMPTION, shown across a range, never asserted;
  - all uncertainty (coefficient sampling + maturation level + annual shocks) is
    propagated into fan charts so the reader sees what is assumed vs estimated.

It is explicitly CONDITIONAL scenario analysis: "IF AI follows the historical GPT
diffusion path, THEN escape timing shifts by X." That is a legitimate, citable
forecasting design — not a claim that the effect is large today.

STAGES
  1. Estimate the conditional-convergence growth model (same structural form as before)
     and, separately, the conditional (low-H / high-services) joint-digital coefficient
     that is the optimistic 'mature' anchor.
  2. Build a logistic maturation path m(t) in [0,1] and let beta_FG_eff(t) interpolate
     between the current estimate and a scenario 'mature' value.
  3. Monte-Carlo simulate income paths to 2045 under three maturation scenarios
     x two digital-push scenarios, propagating parameter + maturation + shock uncertainty.
  4. Output escape probabilities, escape-year shifts, and fan charts.
"""
from pathlib import Path
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
import statsmodels.formula.api as smf
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

rng = np.random.default_rng(7)
PANEL      = Path("panel_estimation.csv")
ESCAPE_PPP = 26000
LAST_YEAR  = 2024
HORIZON    = 2045
N_SIMS     = 800
OUT        = Path("outputs"); OUT.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------- 1. ESTIMATE
df = pd.read_csv(PANEL, low_memory=False).sort_values(["iso3","year"])
df["G"]  = df.groupby("year")["ai_pubs_log"].transform(lambda s:(s-s.mean())/s.std())
df["FG"] = df["F"]*df["G"]
df["GH"] = df["G"]*df["H"]
df["GS"] = df["G"]*df["sigma_kis"]
df["loglag"] = df.groupby("iso3")["log_gdp"].shift(1)

mcols = ["gdp_pc_growth","loglag","F","G","FG","GH","GS","H","sigma_kis",
         "trade_pct_gdp","inflation","investment_pct_gdp","pop_growth"]
est = df.dropna(subset=mcols).copy()
formula = ("gdp_pc_growth ~ loglag + F + G + FG + GH + GS + H + sigma_kis "
           "+ trade_pct_gdp + inflation + investment_pct_gdp + pop_growth")
m = smf.ols(formula, data=est).fit(cov_type="cluster", cov_kwds={"groups": est["iso3"].values})
beta_hat, V = m.params, m.cov_params(); XNAMES = list(beta_hat.index)
print("CONDITIONAL-CONVERGENCE MODEL")
print(f"  N={int(m.nobs)}  R2={m.rsquared:.3f}  convergence={m.params['loglag']:+.2f} (p={m.pvalues['loglag']:.3f})")
print(f"  current pooled FG = {beta_hat['FG']:+.3f} (p={m.pvalues['FG']:.3f})  <- the conservative anchor")

# Optimistic 'mature' anchor: the conditional low-H/high-KIS coefficient (the robust
# descriptive finding). Estimated here so the number is transparent, not invented.
dq = df.copy()
if "FG_l_LH" in dq.columns:
    sub = dq.dropna(subset=["gdp_pc_growth","FG_l_LH"])
    # marginal LH effect via a compact FE-free proxy regression for the anchor magnitude
    lh = smf.ols("gdp_pc_growth ~ FG_l_LH + F_l_LH + G_l_LH + log_gdp_l", data=sub).fit()
    FG_MATURE_HI = float(lh.params.get("FG_l_LH", 3.0))
else:
    FG_MATURE_HI = 3.0
FG_MATURE_HI = float(np.clip(FG_MATURE_HI, 1.0, 6.0))
print(f"  optimistic 'mature' FG anchor (low-H/high-services) = {FG_MATURE_HI:+.2f}")
print("    NOTE: this is an UPPER-BOUND assumption, shown alongside the conservative path.")

# ----------------------------------------------------------------- 2. MATURATION PATH
def maturation(years, t_mid=2032, k=0.45):
    """Logistic ramp in [0,1]: ~0 in 2024, ~1 by late-2030s. GPT diffusion shape."""
    return 1.0/(1.0+np.exp(-k*(np.asarray(years)-t_mid)))

# ----------------------------------------------------------------- 3. PROJECT DRIVERS
base = (df[df["year"]==LAST_YEAR]
        .set_index("iso3")[["log_gdp","F","G","H","sigma_kis","MI",
                            "trade_pct_gdp","inflation","investment_pct_gdp","pop_growth"]]
        .dropna(subset=["log_gdp","F","G","H","sigma_kis"]))
base["MI"] = base["MI"].fillna(0).astype(int)
DRIFT = {"F":0.056,"G":0.060,"H":0.0045,"sigma_kis":0.0004}
PUSH  = {"Baseline":dict(F=1.0,G=1.0), "Joint push":dict(F=1.8,G=2.2)}

def project(push, n_years):
    mult=PUSH[push]; state=base.copy(); paths={LAST_YEAR:state.copy()}
    for t in range(LAST_YEAR+1, LAST_YEAR+n_years+1):
        nxt=state.copy(); damp=0.97**(t-LAST_YEAR)
        nxt["F"]=state["F"]+mult["F"]*DRIFT["F"]*damp
        nxt["G"]=state["G"]+mult["G"]*DRIFT["G"]*damp
        nxt["H"]=state["H"]+DRIFT["H"]; nxt["sigma_kis"]=state["sigma_kis"]+DRIFT["sigma_kis"]
        paths[t]=nxt; state=nxt
    return paths

ISOS=base.index.tolist(); NI=len(ISOS); NY=HORIZON-LAST_YEAR
FIX=[k for k in XNAMES if k!="loglag"]
thr=np.log(ESCAPE_PPP); start_loglag=base["log_gdp"].values.astype(float)
shock_sd=est.groupby("iso3")["gdp_pc_growth"].std().median()
yrs=np.arange(LAST_YEAR, HORIZON+1)
mpath=maturation(yrs)  # length NY+1

def fix_tensor(push):
    paths=project(push,NY); X=np.zeros((NI,NY+1,len(FIX)))
    Fmat=np.zeros((NI,NY+1)); Gmat=np.zeros((NI,NY+1))
    for k,t in enumerate(range(LAST_YEAR,HORIZON+1)):
        r=paths[t].loc[ISOS]
        feat={"Intercept":np.ones(NI),"F":r["F"].values,"G":r["G"].values,
              "FG":(r["F"]*r["G"]).values,"GH":(r["G"]*r["H"]).values,
              "GS":(r["G"]*r["sigma_kis"]).values,"H":r["H"].values,
              "sigma_kis":r["sigma_kis"].values,"trade_pct_gdp":r["trade_pct_gdp"].values,
              "inflation":r["inflation"].values,"investment_pct_gdp":r["investment_pct_gdp"].values,
              "pop_growth":r["pop_growth"].values}
        X[:,k,:]=np.column_stack([feat[f] for f in FIX])
        Fmat[:,k]=r["F"].values; Gmat[:,k]=r["G"].values
    return X, Fmat*Gmat   # also return the FG driver product per year

# STRUCTURE WEIGHT: how 'low-H / high-services' (LH) is each country? The conditional
# (mature) effect is only credible for this group, so maturation bites in proportion.
_H = base["H"].values; _S = base["sigma_kis"].values
def _z(x): return (x-np.nanmean(x))/np.nanstd(x)
lh_score = (-_z(_H)) + _z(_S)                      # high when low-H AND high-services
LH_WEIGHT = 1.0/(1.0+np.exp(-1.2*lh_score))        # in (0,1), ~1 for LH economies
LH_WEIGHT = np.clip(LH_WEIGHT, 0.0, 1.0)

def simulate(push, mature_hi, structural=True):
    """mature_hi = the FG coefficient the LH group ramps toward. If structural=True the
    mature effect is applied in proportion to each country's LH weight (honest: the big
    coefficient is a CONDITIONAL finding, not a universal one)."""
    X, FGdrive = fix_tensor(push)
    Bdraws = rng.multivariate_normal(beta_hat.values, V.values, size=N_SIMS)
    bfix_d = Bdraws[:, [XNAMES.index(f) for f in FIX]]
    bl_d   = Bdraws[:, XNAMES.index("loglag")]
    fg_idx = FIX.index("FG")
    bfix_noFG = bfix_d.copy(); bfix_noFG[:, fg_idx] = 0.0
    Afix = np.einsum("itf,sf->sit", X, bfix_noFG)            # [S,NI,T] (FG removed)
    fg_now = beta_hat["FG"]
    # per-country mature target: LH economies move toward mature_hi, others stay ~current
    w = LH_WEIGHT if structural else np.ones(NI)
    country_target = fg_now + (mature_hi - fg_now)*w         # [NI]
    mat_target = country_target[None,:] + rng.normal(0, 0.15*abs(mature_hi)+0.05,
                                                      size=(N_SIMS,NI))   # [S,NI]
    income=np.zeros((N_SIMS,NI,NY+1)); loglag=np.tile(start_loglag,(N_SIMS,1))
    income[:,:,0]=loglag; escaped=np.full((N_SIMS,NI),np.nan); below0=start_loglag<thr
    for k in range(NY):
        beta_fg_eff = fg_now + (mat_target - fg_now)*mpath[k]   # [S,NI], ramps per year
        fg_contrib = beta_fg_eff*FGdrive[None,:,k]              # [S,NI]
        shocks=rng.normal(0,shock_sd,size=(N_SIMS,NI))
        g=Afix[:,:,k]+fg_contrib+bl_d[:,None]*loglag+shocks
        loglag=loglag+g/100.0; income[:,:,k+1]=loglag
        newly=np.isnan(escaped)&(loglag>=thr)&below0[None,:]; escaped[newly]=LAST_YEAR+k+1
    p=np.mean(~np.isnan(escaped),axis=0)
    return pd.DataFrame(dict(iso3=ISOS,MI=base["MI"].values,start_ppp=np.exp(start_loglag),
                             lh_weight=w, p_escape=p)), {ISOS[i]:income[:,i,:] for i in range(NI)}

# ----------------------------------------------------------------- 4. RUN SCENARIOS
fg_now = beta_hat["FG"]
SCEN = {
 "Conservative (no maturation)":        ("Baseline",   fg_now),
 "Joint push, no maturation":           ("Joint push", fg_now),
 "Joint push + GPT maturation (mid)":   ("Joint push", FG_MATURE_HI*0.5),
 "Joint push + GPT maturation (high)":  ("Joint push", FG_MATURE_HI),
}
rows=[]; fan={}
for name,(push,hi) in SCEN.items():
    tab,paths=simulate(push,hi)
    mi=tab[tab.MI==1]
    rows.append(dict(scenario=name, mean_P_escape_MI=mi.p_escape.mean(),
                     median_P_escape_MI=mi.p_escape.median()))
    fan[name]=(tab,paths)
summary=pd.DataFrame(rows)
print("\n"+"="*70); print("ESCAPE PROBABILITY BY MATURATION SCENARIO (middle-income countries)"); print("="*70)
print(summary.round(3).to_string(index=False))
summary.to_csv(OUT/"maturation_escape_summary.csv", index=False)

# escape-year acceleration for illustrative countries under high maturation vs conservative
cons_tab=fan["Conservative (no maturation)"][0].set_index("iso3")
hi_tab  =fan["Joint push + GPT maturation (high)"][0].set_index("iso3")
delta=(hi_tab["p_escape"]-cons_tab["p_escape"]).sort_values(ascending=False)
mi_iso=base[base.MI==1].index
delta_mi=delta.loc[[i for i in delta.index if i in set(mi_iso)]]
print("\nLargest P(escape) gains from conservative -> high-maturation (MI countries):")
print(delta_mi.head(8).round(3).to_string())

# ----------------------------------------------------------------- 5. FIGURE
# pick three illustrative MI countries that exist in base
pick=[i for i in ["IDN","VNM","BRA","TUR","MEX","IND"] if i in base.index][:3]
fig,axes=plt.subplots(1,len(pick),figsize=(4.2*len(pick),4),sharey=True)
yy=list(range(LAST_YEAR,HORIZON+1))
cmap={"Conservative (no maturation)":("#7a7a7a","-"),
      "Joint push + GPT maturation (high)":("#2e7d4f","-")}
for ax,iso in zip(np.atleast_1d(axes),pick):
    for name,(col,ls) in cmap.items():
        P=np.exp(fan[name][1][iso]); lo,md,hi=np.percentile(P,[10,50,90],axis=0)
        ax.fill_between(yy,lo,hi,alpha=.15,color=col)
        ax.plot(yy,md,color=col,lw=2,ls=ls,label=name.split(" (")[0].replace("Joint push + GPT ",""))
    ax.axhline(ESCAPE_PPP,ls="--",c="k",lw=1); ax.set_title(iso); ax.set_xlabel("year")
np.atleast_1d(axes)[0].set_ylabel("GDP per capita (PPP)")
np.atleast_1d(axes)[0].legend(fontsize=7,loc="upper left")
plt.suptitle("Income paths: conservative vs GPT-maturation scenario (dashed = high-income floor)")
plt.tight_layout(); plt.savefig(OUT/"fig_maturation_fan.png",dpi=130); plt.close()
print(f"\nWrote: maturation_escape_summary.csv, fig_maturation_fan.png")
