"""
REBUILD the AI index G so it has real WITHIN-country time variation.

In the current panel G's within/between SD ratio is 0.09, and the readiness/
adoption pillars (Z_readiness, Z_adoption) have EXACTLY ZERO within-country SD --
they are single 2024 snapshots that country fixed effects delete entirely.
The Mundlak decomposition confirms G's entire growth effect is between-country
(within = +0.01, between = +1.35). Until G moves over time, country-FE estimation
cannot use it.

TWO fixes, both add genuine annual variation:
  (A) Use the ANNUAL GARI vintages instead of only 2024.
      Editions: 2017, 2019, 2020, 2021, 2022, 2023, 2024, 2025
      https://oxfordinsights.com/ai-readiness/   (CC BY-SA 4.0, downloadable PDFs/data)
  (B) Add AI patent counts (annual, country-level) alongside AI publications.
      OECD.AI patent indicators: https://oecd.ai/   (OECD STI Micro-data Lab)
      Stanford AI Index also publishes annual AI patent grants by country.

DATA TO DOWNLOAD FIRST (run locally):
  - gari_panel.csv   : columns iso3, year, gari_total   (stack the vintages)
  - ai_patents.csv   : columns iso3, year, ai_patents
"""
import numpy as np, pandas as pd

GARI_CSV    = "gari_panel.csv"      # stacked vintages: iso3, year, gari_total
PATENTS_CSV = "ai_patents.csv"      # iso3, year, ai_patents
PANEL_CSV   = "final_panel_imputed.csv"
OUT_CSV     = "final_panel_G_rebuilt.csv"

def z(s):
    s = pd.to_numeric(s, errors="coerce"); return (s - s.mean()) / s.std()

def main():
    P = pd.read_csv(PANEL_CSV)

    # --- (A) time-varying readiness from GARI vintages ---
    gari = pd.read_csv(GARI_CSV)[["iso3","year","gari_total"]]
    P = P.merge(gari, on=["iso3","year"], how="left", suffixes=("","_new"))
    # carry each vintage forward to the next edition so every year has the latest reading
    P = P.sort_values(["iso3","year"])
    P["Z_readiness_tv"] = P.groupby("iso3")["gari_total"].transform(lambda s: s.ffill())
    P["Z_readiness_tv"] = z(P["Z_readiness_tv"])

    # --- (B) AI patents as a second annual activity pillar ---
    pat = pd.read_csv(PATENTS_CSV)[["iso3","year","ai_patents"]]
    P = P.merge(pat, on=["iso3","year"], how="left")
    P["Z_patents"] = z(np.log1p(P["ai_patents"]))

    # --- recompose G: activity = mean(publications, patents); add time-varying readiness ---
    # keep your existing Z_activity (publications) and Z_adoption; swap readiness for the TV one
    P["Z_activity_tv"] = P[["Z_activity","Z_patents"]].mean(axis=1)
    pillars = ["Z_readiness_tv","Z_activity_tv","Z_adoption"]
    P["G"] = P[pillars].mean(axis=1)

    # rebuild interactions and lags that depend on G
    P["FG"] = P["F"] * P["G"]
    for v in ["G","FG"]:
        P[v+"_l"] = P.groupby("iso3")[v].shift(1)

    w = P.groupby("iso3")["G"].std().mean(); b = P.groupby("iso3")["G"].mean().std()
    print(f"  NEW G within/between SD ratio = {w/b:.3f}  (was 0.092)")
    P.to_csv(OUT_CSV, index=False)
    print(f"  wrote {OUT_CSV}")

if __name__ == "__main__":
    main()
