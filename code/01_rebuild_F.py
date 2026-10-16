"""
REBUILD the FinTech index F so it (a) uses all 4 Findex components your Eq.25
specifies, and (b) has genuine ANNUAL within-country variation via IMF FAS.

This is the single highest-leverage fix: in the current panel F's within/between
SD ratio is only 0.28, and beta3 collapses (wave-years-only) / flips (between).

DATA TO DOWNLOAD FIRST (sandbox can't reach these hosts; run locally):
  1. Global Findex country-level .csv  (waves 2011/14/17/21/24)
     https://www.worldbank.org/en/publication/globalfindex/download-data
     or Data360 API dataset WB_FINDEX: https://data360.worldbank.org/en/dataset/WB_FINDEX
  2. IMF Financial Access Survey (ANNUAL 2004-2024), country panel
     https://data.imf.org/en/datasets/IMF.STA:FAS   (or db.nomics.world/IMF/FAS)

Edit the CONFIG block to match the exact column names in the files you download.
"""
import numpy as np, pandas as pd

# ---------------- CONFIG: set these to your downloaded column names ----------------
FINDEX_CSV = "findex_country.csv"
FAS_CSV    = "imf_fas.csv"
PANEL_CSV  = "final_panel_imputed.csv"
OUT_CSV    = "final_panel_F_rebuilt.csv"

# The 4 Findex components to average (Eq.25). Map to the series in YOUR download.
FINDEX_COMPONENTS = {
    "account":   "account.t.d",            # account ownership (you already have this)
    "digpay":    "fin14a.d",               # made OR received a digital payment
    "saved":     "fin16.d",                # saved at a financial institution
    "borrowed":  "fin22a.d",               # borrowed from a financial institution
}
FINDEX_ISO, FINDEX_YEAR = "countrynewwb", "year"   # rename to your file's keys

# Annual FAS series that proxy the SAME construct (used for within-country interpolation)
FAS_SERIES = ["FCMOAA_NUM",   # mobile-money agent outlets / 100k adults
              "FCMIBT_NUM",   # mobile & internet banking transactions
              "FCDOTP_NUM"]   # (example) digital payment volume -- adjust to availability
FAS_ISO, FAS_YEAR = "iso3", "year"
# -----------------------------------------------------------------------------------

def z(s):
    s = pd.to_numeric(s, errors="coerce")
    return (s - s.mean()) / s.std()

def build_findex_F():
    fx = pd.read_csv(FINDEX_CSV).rename(columns={FINDEX_ISO:"iso3", FINDEX_YEAR:"year"})
    comp_z = []
    for name, col in FINDEX_COMPONENTS.items():
        if col in fx.columns:
            fx[f"z_{name}"] = z(fx[col]); comp_z.append(f"z_{name}")
        else:
            print(f"  [warn] Findex column '{col}' not found -- skipping {name}")
    fx["F_findex"] = fx[comp_z].mean(axis=1)        # average of available z-components
    return fx[["iso3","year","F_findex"]]

def build_fas_trend():
    fa = pd.read_csv(FAS_CSV).rename(columns={FAS_ISO:"iso3", FAS_YEAR:"year"})
    have = [c for c in FAS_SERIES if c in fa.columns]
    if not have:
        print("  [warn] no FAS series matched; F will be wave-only interpolated")
        return None
    fa["F_fas"] = fa[[*have]].apply(z).mean(axis=1)  # annual digital-finance intensity
    return fa[["iso3","year","F_fas"]]

def main():
    panel = pd.read_csv(PANEL_CSV)
    findex = build_findex_F()
    fas    = build_fas_trend()

    # start from full 4-component Findex on wave years
    P = panel.merge(findex, on=["iso3","year"], how="left")

    if fas is not None:
        P = P.merge(fas, on=["iso3","year"], how="left")
        # within-country z of the annual FAS proxy = the year-to-year SHAPE
        P["F_fas_w"] = P.groupby("iso3")["F_fas"].transform(z)
        # anchor: Findex wave levels; shape: FAS annual movement between waves
        P = P.sort_values(["iso3","year"])
        P["F_anchor"] = P.groupby("iso3")["F_findex"].transform(lambda s: s.interpolate().ffill().bfill())
        P["F_new"] = P["F_anchor"] + P["F_fas_w"].fillna(0) * P.groupby("iso3")["F_anchor"].transform("std")
    else:
        P["F_new"] = P.groupby("iso3")["F_findex"].transform(lambda s: s.interpolate())

    # standardise and overwrite F, then rebuild interactions
    P["F"]  = z(P["F_new"])
    P["FG"] = P["F"] * P["G"]
    for v in ["F","FG"]:
        P[v+"_l"] = P.groupby("iso3")[v].shift(1)
    # diagnostic: did we buy within-country variation?
    w = P.groupby("iso3")["F"].std().mean(); b = P.groupby("iso3")["F"].mean().std()
    print(f"  NEW F within/between SD ratio = {w/b:.3f}  (was 0.281)")
    P.to_csv(OUT_CSV, index=False)
    print(f"  wrote {OUT_CSV}")

if __name__ == "__main__":
    main()
