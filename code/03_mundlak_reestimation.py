"""
Mundlak / Correlated-Random-Effects re-estimation of the F x G complementarity.
Runs on the EXISTING panel (final_panel_imputed.csv) -- no new data needed.

Decomposes beta3 (F x G) and delta4 (F x G x MI) into WITHIN-country and
BETWEEN-country effects, and tests whether they differ. This is the cheapest
power/interpretation upgrade available and explains the between-estimator sign flip.

Requires: pip install linearmodels pycountry_convert
"""
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
from linearmodels.panel import PanelOLS, RandomEffects
import pycountry_convert as pc

CSV = "final_panel_imputed.csv"          # <-- point at your panel
df = pd.read_csv(CSV)

CONTROLS = ["log_gdp","trade_pct_gdp","inflation","investment_pct_gdp",
            "pop_growth","credit_to_private_pct_gdp","secondary_enrollment"]
Cl = [f"{c}_l" for c in CONTROLS]
star = lambda p: "***" if p<.01 else "**" if p<.05 else "*" if p<.1 else ""

def region(i):
    try: return pc.country_alpha2_to_continent_code(pc.country_alpha3_to_country_alpha2(i))
    except: return None
df["region"] = df["iso3"].map(region)

# ---- A. baseline two-way FE (reproduce headline) ----
def fe(dep, regs):
    d = df.dropna(subset=[dep]+regs).copy().set_index(["iso3","year"])
    f = f"{dep} ~ 1 + " + " + ".join(regs) + " + EntityEffects + TimeEffects"
    return PanelOLS.from_formula(f, data=d, drop_absorbed=True).fit(cov_type="clustered", cluster_entity=True)

# ---- B. Mundlak / CRE: add country means, estimate by RE ----
KEY = ["F_l","G_l","FG_l","MI_l","F_MI_l","G_MI_l","FG_MI_l"]
for v in KEY:
    df[v+"_bar"] = df.groupby("iso3")[v].transform("mean")

def cre(dep, regs):
    bars = [v+"_bar" for v in regs]
    d = df.dropna(subset=[dep]+regs+bars+Cl).copy().set_index(["iso3","year"])
    f = f"{dep} ~ 1 + " + " + ".join(regs+bars+Cl)
    return RandomEffects.from_formula(f, data=d).fit(cov_type="clustered", cluster_entity=True)

# ---- C. region+year FE (retain G cross-section) ----
def regfe(dep, regs):
    d = df.dropna(subset=[dep]+regs+Cl+["region"]).copy().set_index(["iso3","year"])
    dums = pd.get_dummies(d["region"], prefix="rg", drop_first=True).astype(float)
    X = pd.concat([d[regs+Cl], dums], axis=1)
    dd = pd.concat([d[[dep]], X], axis=1)
    f = f"{dep} ~ 1 + " + " + ".join(X.columns) + " + TimeEffects"
    return PanelOLS.from_formula(f, data=dd, drop_absorbed=True).fit(cov_type="clustered", cluster_entity=True)

if __name__ == "__main__":
    s1, s4 = fe("gdp_pc_growth", ["F_l","G_l","FG_l"]+Cl), fe("gdp_pc_growth", ["F_l","G_l","FG_l","MI_l","F_MI_l","G_MI_l","FG_MI_l"]+Cl)
    print("A. BASELINE FE            beta3=%+.3f%s  delta4=%+.3f%s" %
          (s1.params["FG_l"], star(s1.pvalues["FG_l"]), s4.params["FG_MI_l"], star(s4.pvalues["FG_MI_l"])))
    for lbl, regs, keys in [("Spec1", ["F_l","G_l","FG_l"], ["F_l","G_l","FG_l"]),
                            ("Spec4", ["F_l","G_l","FG_l","MI_l","F_MI_l","G_MI_l","FG_MI_l"], ["FG_l","FG_MI_l"])]:
        r = cre("gdp_pc_growth", regs)
        print(f"\nB. MUNDLAK/CRE [{lbl}]")
        for v in keys:
            wi, lam, pl = r.params[v], r.params[v+"_bar"], r.pvalues[v+"_bar"]
            print(f"   {v:9s} within={wi:+.3f}  between={wi+lam:+.3f}  p(diff)={pl:.3f}{star(pl)}")
    r1, r4 = regfe("gdp_pc_growth", ["F_l","G_l","FG_l"]), regfe("gdp_pc_growth", ["F_l","G_l","FG_l","MI_l","F_MI_l","G_MI_l","FG_MI_l"])
    print("\nC. REGION+YEAR FE         beta3=%+.3f%s  delta4=%+.3f%s  (G_l=%+.3f%s retained)" %
          (r1.params["FG_l"], star(r1.pvalues["FG_l"]), r4.params["FG_MI_l"], star(r4.pvalues["FG_MI_l"]),
           r1.params["G_l"], star(r1.pvalues["G_l"])))
