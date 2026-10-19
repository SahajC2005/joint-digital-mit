"""
forecast_engine.py — Joint-Digital MIT Forecasting & Scenario Engine
====================================================================
Turns the estimated structural growth relationship into forward projections of
middle-income ESCAPE probability under policy scenarios, with full uncertainty.

PIPELINE
  1. Estimate a Barro-style CONDITIONAL-CONVERGENCE growth model with the digital
     terms that survived the analysis (F, G, F*G, and the G*H / G*sigma_KIS
     complementarities that drive the LH-quadrant result).
  2. Project each country's drivers (F, G, H, sigma_KIS) forward 2025-2040 under
     four scenarios.
  3. MONTE-CARLO simulate income paths: draw coefficients from their sampling
     distribution (param uncertainty) + annual shocks (process uncertainty),
     roll log GDP per-capita forward, and record the year each country crosses the
     high-income threshold.
  4. Output: P(escape by horizon) per country/scenario, escape-year shift, fan charts.

HONESTY: this is SCENARIO SIMULATION, not point prediction. 10-year country growth
is intrinsically high-variance; the fan charts show that. The digital coefficients
are uncertain (the FE-safe joint effect was insignificant), so that uncertainty is
PROPAGATED through the coefficient draws rather than hidden.
"""
from pathlib import Path
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
import statsmodels.formula.api as smf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

rng = np.random.default_rng(42)
PANEL          = Path("panel_estimation.csv")
ESCAPE_PPP     = 26000          # high-income floor (HI 10th pct of gdp_pc_ppp)
LAST_YEAR      = 2024
HORIZON        = 2040
N_SIMS         = 600
OUT            = Path("/mnt/user-data/outputs")

# --------------------------------------------------------------- 1. ESTIMATE MODEL
df = pd.read_csv(PANEL, low_memory=False).sort_values(["iso3","year"])
# FE-safe G (within-varying pillar) z-scored within year
df["G"] = df.groupby("year")["ai_pubs_log"].transform(lambda s:(s-s.mean())/s.std())
df["FG"]  = df["F"]*df["G"]
df["GH"]  = df["G"]*df["H"]
df["GS"]  = df["G"]*df["sigma_kis"]
df["loglag"] = df.groupby("iso3")["log_gdp"].shift(1)

mcols = ["gdp_pc_growth","loglag","F","G","FG","GH","GS","H","sigma_kis",
         "trade_pct_gdp","inflation","investment_pct_gdp","pop_growth"]
est = df.dropna(subset=mcols).copy()
formula = ("gdp_pc_growth ~ loglag + F + G + FG + GH + GS + H + sigma_kis "
           "+ trade_pct_gdp + inflation + investment_pct_gdp + pop_growth")
m = smf.ols(formula, data=est).fit(cov_type="cluster",
                                    cov_kwds={"groups": est["iso3"].values})
print("CONDITIONAL-CONVERGENCE GROWTH MODEL")
print(f"  N={int(m.nobs)}  R2={m.rsquared:.3f}  convergence(loglag)={m.params['loglag']:+.2f} "
      f"(p={m.pvalues['loglag']:.3f})")
for k in ["F","G","FG","GH","GS"]:
    s="***" if m.pvalues[k]<.01 else "**" if m.pvalues[k]<.05 else "*" if m.pvalues[k]<.1 else ""
    print(f"  {k:<4} {m.params[k]:+7.3f} (p={m.pvalues[k]:.3f}) {s}")
beta_hat, V = m.params, m.cov_params()
XNAMES = list(beta_hat.index)

# --------------------------------------------------------------- 2. DRIVER PROJECTION
# Starting state: each country's last observed values
base = (df[df["year"]==LAST_YEAR]
        .set_index("iso3")[["log_gdp","F","G","H","sigma_kis","MI",
                            "trade_pct_gdp","inflation","investment_pct_gdp","pop_growth"]]
        .dropna(subset=["log_gdp","F","G","H","sigma_kis"]))
base["MI"] = base["MI"].fillna(0).astype(int)
# historical within-country annual drift (damped, capped) for baseline
DRIFT = {"F":0.056, "G":0.060, "H":0.0045, "sigma_kis":0.0004}
SCEN = {
    "Stall":        dict(F=0.0,   G=0.0),                 # drivers freeze
    "Baseline":     dict(F=1.0,   G=1.0),                 # historical trend continues
    "AI push":      dict(F=1.0,   G=2.2),                 # AI accelerates, FinTech normal
    "Joint push":   dict(F=1.8,   G=2.2),                 # both pushed together
}
def project(scenario, n_years):
    """Return dict year->DataFrame of drivers for all countries under a scenario."""
    mult = SCEN[scenario]
    state = base.copy()
    paths = {LAST_YEAR: state.copy()}
    for t in range(LAST_YEAR+1, LAST_YEAR+n_years+1):
        nxt = state.copy()
        damp = 0.97**(t-LAST_YEAR)          # trends fade toward a ceiling
        nxt["F"]         = state["F"]        + mult.get("F",1)*DRIFT["F"]*damp
        nxt["G"]         = state["G"]        + mult.get("G",1)*DRIFT["G"]*damp
        nxt["H"]         = state["H"]        + DRIFT["H"]
        nxt["sigma_kis"] = state["sigma_kis"]+ DRIFT["sigma_kis"]
        paths[t] = nxt; state = nxt
    return paths

# --------------------------------------------------------------- 3. MONTE-CARLO SIM (vectorized)
shock_sd = est.groupby("iso3")["gdp_pc_growth"].std().median()
ISOS = base.index.tolist()
NI   = len(ISOS)
NY   = HORIZON - LAST_YEAR                      # number of forward steps
FIX  = [k for k in XNAMES if k != "loglag"]     # features that don't depend on sim path
bfix = beta_hat[FIX].values
bl   = beta_hat["loglag"]
thr  = np.log(ESCAPE_PPP)
start_loglag = base["log_gdp"].values.astype(float)

def fix_tensor(scenario):
    """Return Xfix[i, t, feat] for t=0..NY using projected drivers (no loglag)."""
    paths = project(scenario, NY)
    T = NY + 1
    X = np.zeros((NI, T, len(FIX)))
    for k,t in enumerate(range(LAST_YEAR, HORIZON+1)):
        r = paths[t].loc[ISOS]
        feat = {"Intercept":np.ones(NI),"F":r["F"].values,"G":r["G"].values,
                "FG":(r["F"]*r["G"]).values,"GH":(r["G"]*r["H"]).values,
                "GS":(r["G"]*r["sigma_kis"]).values,"H":r["H"].values,
                "sigma_kis":r["sigma_kis"].values,"trade_pct_gdp":r["trade_pct_gdp"].values,
                "inflation":r["inflation"].values,"investment_pct_gdp":r["investment_pct_gdp"].values,
                "pop_growth":r["pop_growth"].values}
        X[:,k,:] = np.column_stack([feat[f] for f in FIX])
    return X

def simulate(scenario):
    X = fix_tensor(scenario)                                  # [NI, T, F]
    Bdraws = rng.multivariate_normal(beta_hat.values, V.values, size=N_SIMS)
    bfix_d = Bdraws[:, [XNAMES.index(f) for f in FIX]]        # [S, F]
    bl_d   = Bdraws[:, XNAMES.index("loglag")]                # [S]
    # Afix[s,i,t] = X[i,t,:] dot bfix_d[s,:]
    Afix = np.einsum("itf,sf->sit", X, bfix_d)                # [S, NI, T]
    income = np.zeros((N_SIMS, NI, NY+1))
    loglag = np.tile(start_loglag, (N_SIMS,1))                # [S, NI]
    income[:,:,0] = loglag
    escaped_year = np.full((N_SIMS, NI), np.nan)
    below0 = start_loglag < thr
    for k in range(NY):
        shocks = rng.normal(0, shock_sd, size=(N_SIMS, NI))
        g = Afix[:,:,k] + bl_d[:,None]*loglag + shocks        # % growth
        loglag = loglag + g/100.0
        income[:,:,k+1] = loglag
        newly = np.isnan(escaped_year) & (loglag >= thr) & below0[None,:]
        escaped_year[newly] = LAST_YEAR + k + 1
    p_escape = np.mean(~np.isnan(escaped_year), axis=0)       # [NI]
    med_year = np.array([np.nanmedian(escaped_year[:,i]) if np.any(~np.isnan(escaped_year[:,i]))
                         else np.nan for i in range(NI)])
    tab = pd.DataFrame(dict(iso3=ISOS, MI=base["MI"].values,
                            start_ppp=np.exp(start_loglag), p_escape=p_escape,
                            med_escape_year=med_year))
    return tab, {ISOS[i]: income[:,i,:] for i in range(NI)}

print(f"\nSimulating {N_SIMS} draws x {len(base)} countries x {HORIZON-LAST_YEAR} yrs per scenario...")
res = {sc: simulate(sc)[0] for sc in SCEN}
_, base_paths = simulate("Baseline")
_, push_paths = simulate("Joint push")

# --------------------------------------------------------------- 4. OUTPUT + FIGURES
# (a) scenario comparison table for MI countries
mi_tab = res["Baseline"][res["Baseline"]["MI"]==1][["iso3","start_ppp","p_escape"]]\
         .rename(columns={"p_escape":"p_baseline"})
mi_tab = mi_tab.merge(res["Joint push"][["iso3","p_escape"]]
                      .rename(columns={"p_escape":"p_jointpush"}), on="iso3")
mi_tab["flip"] = mi_tab["p_jointpush"] - mi_tab["p_baseline"]
mi_tab = mi_tab.sort_values("flip", ascending=False)
mi_tab.to_csv(OUT/"forecast_escape_by_scenario.csv", index=False)
print(f"\nTop 'flippers' — MI countries where Joint push most raises P(escape by {HORIZON}):")
print(mi_tab.head(10).round(3).to_string(index=False))

# (b) figure 1: scenario escape probabilities (MI aggregate)
fig, ax = plt.subplots(figsize=(7,4))
agg = {sc: res[sc][res[sc]["MI"]==1]["p_escape"].mean() for sc in SCEN}
ax.bar(list(agg.keys()), list(agg.values()),
       color=["#b0b0b0","#4878a8","#d68b3f","#3a8a5a"])
ax.set_ylabel(f"Mean P(escape by {HORIZON})")
ax.set_title("Middle-income escape probability by digital scenario")
for i,(k,v) in enumerate(agg.items()): ax.text(i,v+.005,f"{v:.2f}",ha="center")
plt.tight_layout(); plt.savefig(OUT/"fig_scenario_escape.png", dpi=130); plt.close()

# (c) figure 2: income fan chart for a few illustrative MI countries
pick = mi_tab.head(3)["iso3"].tolist()
yrs = list(range(LAST_YEAR, HORIZON+1))
fig, axes = plt.subplots(1, len(pick), figsize=(4*len(pick),4), sharey=True)
for ax,i in zip(np.atleast_1d(axes), pick):
    for paths,lab,col in [(base_paths,"Baseline","#4878a8"),(push_paths,"Joint push","#3a8a5a")]:
        P = np.exp(paths[i])  # ppp levels
        lo,md,hi = np.percentile(P,[10,50,90],axis=0)
        ax.fill_between(yrs, lo, hi, alpha=.18, color=col)
        ax.plot(yrs, md, color=col, lw=2, label=lab)
    ax.axhline(ESCAPE_PPP, ls="--", c="k", lw=1)
    ax.set_title(i); ax.set_xlabel("year")
np.atleast_1d(axes)[0].set_ylabel("GDP per capita (PPP)")
np.atleast_1d(axes)[0].legend(fontsize=8)
plt.suptitle("Projected income with 10-90% uncertainty band (dashed = high-income floor)")
plt.tight_layout(); plt.savefig(OUT/"fig_income_fan.png", dpi=130); plt.close()

print(f"\nWrote: forecast_escape_by_scenario.csv, fig_scenario_escape.png, fig_income_fan.png")
print("Scenario mean P(escape) for MI countries:", {k:round(v,3) for k,v in agg.items()})
