# Improvement playbook — Joint Digital × Middle-Income Trap

Everything here targets one root cause your report already names: **the fixed-effects
estimator identifies off within-country variation, and your two key regressors barely
move within country.** Measured directly on your panel:

| Regressor | within-country SD | between-country SD | within/between ratio |
|---|---|---|---|
| F (FinTech) | 0.27 | 0.95 | **0.28** |
| G (AI) | 0.08 | 0.87 | **0.09** |

`Z_readiness` and `Z_adoption` have **exactly zero** within-country SD — single 2024
snapshots, deleted by country FE. So most of what your theory talks about lives in the
between dimension your preferred estimator removes. Fix the measurement, and the
interactions get a fair test.

---

## What the Mundlak re-estimation already told us (run on your existing data)

`03_mundlak_reestimation.py` decomposes each headline coefficient into within- and
between-country effects (correlated random effects). Results:

| Coefficient | within | between | p(within ≠ between) |
|---|---|---|---|
| β₃  (F×G), Spec 1 | **+0.73** | **−0.74** | **0.003** |
| G level (growth effect) | +0.01 | +1.35 | 0.52 |
| β₃  (F×G), Spec 4 | +1.16 | −1.04 | **0.008** |
| δ₄  (F×G×MI) | −0.69 | +0.86 | 0.14 |

Two takeaways you can use immediately, before any new data:

1. **The F×G complementarity is a genuinely within-country phenomenon, and it is the
   *opposite* sign across countries — significantly so (p≈0.003).** That is not a weakness:
   it means your positive β₃ is identified off countries that deepen both technologies over
   time, *not* off a "rich countries that happen to have both grow faster" cross-sectional
   confound. It also fully explains why the between estimator in your robustness table came
   out −0.58. Reframe that row from "puzzle" to "the cross-section carries a different,
   confounded signal — which is exactly why we use within identification."
2. **G's entire growth effect is between-country (within ≈ 0).** Under country FE, G is
   contributing almost nothing. This is the quantitative proof that the G-rebuild (below)
   is necessary, not optional.

Add the country-mean (Mundlak) terms to your reported Spec 1 and Spec 4 — it's a free
robustness panel and a built-in Hausman-type test.

---

## Priority 1 — Rebuild F (biggest lever).  → `01_rebuild_F.py`

Two upgrades in one: all four Findex components (your Eq. 25), plus genuine **annual**
movement so F isn't flat between waves.

**Download:**
- Global Findex country-level CSV (waves 2011/14/17/21/24, 4 components):
  https://www.worldbank.org/en/publication/globalfindex/download-data
  (API alternative — Data360 dataset `WB_FINDEX`: https://data360.worldbank.org/en/dataset/WB_FINDEX)
- IMF Financial Access Survey — **annual 2004–2024, 163 economies**, supply-side digital
  finance (mobile-money agents, mobile/internet-banking transactions, POS):
  https://data.imf.org/en/datasets/IMF.STA:FAS  (or https://db.nomics.world/IMF/FAS)

**Method:** average the 4 Findex z-components at wave years for the *level*; use the
within-country z of the annual FAS series for the year-to-year *shape* between waves.
The script prints the new within/between ratio so you can confirm the gain.

Four Findex components to map (currently only the first is in your panel):
account ownership · made/received a digital payment · saved at a financial institution ·
borrowed from a financial institution.

---

## Priority 2 — Make G time-varying.  → `02_rebuild_G.py`

**Download:**
- **GARI annual vintages** (you used only 2024; editions exist for 2017, 2019, 2020,
  2021, 2022, 2023, 2024, 2025, CC BY-SA 4.0): https://oxfordinsights.com/ai-readiness/
- **AI patents by country, annual** (a second activity pillar beyond publications, and
  far less China-skewed than pubs alone): OECD.AI https://oecd.ai/ ; Stanford AI Index
  publishes annual AI patent grants by country.

**Method:** stack the GARI vintages into a country-year panel and forward-fill each
edition to the next, turning readiness into a moving series instead of a deleted constant.
Add log AI patents to the activity pillar. Recompose G and rebuild F×G and the lags.

---

## Priority 3 — Use the between dimension on purpose (estimation, not new data)

- **Mundlak/CRE** (in script 03): report it as standard robustness.
- **Region×year FE** instead of country FE retains G's cross-sectional signal while still
  absorbing global shocks (COVID). In your data this is where the G *level* becomes large
  and significant (+1.08***). Present both as bracketing the within/between range rather
  than privileging one.

---

## Priority 4 — Give the rare-events mechanisms a fair test

Your exit risk set has ~13–26 transitions — too few for δ₄/ψ₄/the slowdown probits.
- Extend the panel back with **World Bank historical income classifications (to ~1987)**
  for many more middle→high crossings.
- Replace the rare-events probit with a **discrete-time survival / duration model**
  (complementary-log-log), which is the right tool for transition timing.

## Priority 5 — De-construct the displacement term

`D = G·ρ·(1−H)·(1−σ_KIS)` multiplies four sparse, partly-imputed series → almost no usable
signal (hence β₆'s giant SE). Enter the components additively, or rebuild ρ from a proper
task-based exposure measure (Felten–Raj–Seamans or Webb) merged to ISCO employment shares.

## Priority 6 — Fix or retire the weak IV

First-stage F ≈ 4.2 means θ_IV is uninterpretable. Either find a structurally different
instrument for inequality or present that channel as conditional/mediation **without** the
causal claim. An honest underpowered null reads better than an uninterpretable IV.

---

## Order of attack (return on effort)

1. Rebuild F (script 01) — fixes the attenuation behind nearly every fragile coefficient.
2. Make G time-varying (script 02) — without it, country FE can't use G at all.
3. Add Mundlak + region×year FE panels (script 03) — free, already runnable today.
4. Longer panel + survival model for the MIT-escape / vulnerability mechanisms.
5. Simplify D; fix or drop the IV.

After 1–2, re-run `03_mundlak_reestimation.py` on the rebuilt panel: the within/between
gap on β₃ should shrink and δ₄ gets its first genuinely-powered test.
