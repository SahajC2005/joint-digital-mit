# Re-run notes — what reproduces and what does not

Run locally on 2026-10-18. Before this, nothing in the repository had been executed: the
report, the memo and the playbook were written from runs whose outputs are not on disk.
This note records what happens when the committed code is pointed at the committed panel.

**Headline: the paper's conclusions survive. Both of the two coefficients the argument turns
on reproduce exactly — β₃ (F×G) = +1.096** and δ₄ (F×G×MI) = −0.609 n.s. — as does the whole
robustness row of §5 and the Mundlak within/between split. What does not reproduce is
confined to the inequality block of §4, where the published specifications are not recoverable
from the committed code and two of the signs flip.**

## How it was run

| | |
|---|---|
| panel | `data/processed/final_panel_imputed__5_.csv` — 3,255 rows × 139 cols, 217 countries, 2010–2024 |
| estimator | `PanelOLS` two-way FE, country-clustered SEs (as in `03_mundlak_reestimation.py`) |
| scripts added | `code/04_rerun_verify.py` (every published number), `code/05_spec_probes.py` (variants for the ones that miss) |
| outputs | `outputs/rerun/rerun_coefficients.csv`, `rerun_vs_published.csv`, `rerun_log.txt`, `spec_probes_log.txt` |
| environment | Python 3, `linearmodels` 7.1, pandas 2.2.3, numpy 2.2.3, `country_converter`. The versions pinned in `code/requirements.txt` were not used and nothing was installed into the project |

Two things had to be resolved before anything would run:

1. **The committed scripts point at the wrong panel.** `03_mundlak_reestimation.py` reads
   `final_panel_imputed.csv` and `reframed_analysis.py` reads `final_panel_imputed__5_.csv`.
   Only the second one carries `F`, `G`, `FG`, `MI`, the lagged regressors and the constructed
   interactions — the first has 50 columns and none of them. The mundlak script as committed
   cannot run. Everything here uses `final_panel_imputed__5_.csv`.
2. **The exit risk set is lagged.** `Exit` is coded on the row *after* the transition, so those
   rows have `MI == 0`. Conditioning on `MI == 1` gives a risk set with zero events. The
   correct condition is `MI_l == 1`.

Nothing was tuned to force a match. Where a published number is missed, `05_spec_probes.py`
reports the plausible alternative regressor sets and none of them was selected after the fact.

## Scorecard

41 published quantities, scored in `outputs/rerun/rerun_vs_published.csv`:

| verdict | n |
|---|---|
| reproduces (to 3 decimals, or within 0.005) | 20 |
| close (same sign, < 25% apart) | 10 |
| same sign, different magnitude | 7 |
| sign flip | 4 |

### Reproduces exactly

| quantity | published | re-run |
|---|---|---|
| β₃ F×G, baseline (Eq. 30) | 1.096** | **+1.0956\*\*** (N=1,380, 135 countries) |
| β₃, dynamic panel (Eq. 47) | 1.098** | +1.0980** |
| β₃, excluding China | 1.094** | +1.0943** |
| δ₄ F×G×MI (Eq. 33) | −0.609 n.s. | **−0.6092 n.s.** (p=0.517) |
| β₄ Gini level (Eq. 30′) | −0.236 | −0.2364 |
| β₃ / δ₄, drop COVID 2020–21 | 0.491 / +0.269 | +0.4915 / +0.2688 |
| β₃ / δ₄, wave-years-only F | −0.062 / −1.293 (N=412) | −0.0623 / −1.2926 (N=412) |
| β₃ / δ₄, 3-yr forward-average growth | 0.894** / +0.049 | +0.8943** / +0.0485 |
| β₃ / δ₄, complete case | ~1.21 / −1.17 | +1.2064 / −1.1738 |
| slope above the F·G threshold | +0.82* | +0.8243* |
| Mundlak β₃ within / between | +0.73 / −0.74, p≈0.003 | +0.729** / −0.744, p(diff)=0.003*** |
| Z_readiness, Z_adoption within-SD | exactly 0 | exactly 0 |
| AI source validation, log-log r | 0.964 | 0.9607 (1,589 country-years, 189 countries) |
| exit rate, non-vulnerable | 0.8% | 0.99% |

Every claim in §2, §3.1 and §5 of the report is therefore verified on the committed data.
The measurement diagnosis in `IMPROVEMENT_PLAYBOOK.md` also holds: F's within/between SD
ratio is 0.34 (playbook: 0.28), G's is 0.10 (playbook: 0.09), and `Z_readiness` and
`Z_adoption` have *exactly* zero within-country variation, so country FE absorb them whole.

### Close, but not the same number

| quantity | published | re-run | comment |
|---|---|---|---|
| ψ₄ vulnerability → exit | +1.223**, 13 events | **+1.4413\*\*\*, 16 events** | wrong-signed relative to theory, as reported, and more significant. The risk set here has 16 exits, not 13 |
| exit rate, vulnerable | 24% | 18.8% (vs 0.99% non-vulnerable) | the descriptive contrast holds — vulnerable country-years exit ~19× more often |
| φ₄ F×G×Gini×MI | +0.802 | +0.7400 n.s. | wrong-signed as reported |
| top Gini tercile, MI sample | 1.37 | +1.2561 | the backwards ordering holds: low −1.78, mid +0.90, high +1.26 |
| threshold on F·G | 0.351, below −1.55 | 0.369, below −1.5706 | grid-dependent; the regime flip is the same |
| β₃ in the memo | 1.014**, N=1403 | +1.0956**, N=1380 | see "memo vs report" below |
| income threshold | $6,216 PPP | $6,948 PPP | grid-dependent |

### Does not reproduce

These five sit in the inequality / displacement block of §4 and in the memo's threshold split.

| quantity | published | re-run | what the probes say |
|---|---|---|---|
| **β₆ displacement** | −24.85 n.s. | **+3.25 n.s.** | sign flip. No variant reproduces −24.85; adding the institutional interactions (`I_l`, `GI_l`, `GH_l`, `GS_l`) gets closest at −27.15. The published figure *is* on this panel's scale, though: the report's per-SD conversion of −1.09 equals −24.85 × (D_z/D_term scale factor) measured here to three decimals, so the regressor set differs, not the data |
| **β₁₁ F×G×Gini** | −0.118 n.s. | **+0.333 n.s.** | sign flip, and the sign is not stable: +0.33 in the Eq. 30′ set, +0.03 adding the displacement terms, −0.59 in the full primed set with the MI block. The "right sign, n.s." reading of this cell is specification-dependent |
| **γ₁ AI → inequality** | +0.005 n.s. | **−0.085 n.s.** | sign flip, but on the raw Gini scale the re-run gives −0.0063 against a published +0.005 — the same negligible magnitude with the opposite sign. Nothing turns on it |
| **ω F×Shock** | +0.614, *n.s.* | **+0.9764, p=0.001** | the report lists this as underpowered. On the committed panel it is significant in every variant tried (+0.77 to +0.98, p ≤ 0.044). This is the one case where the re-run is *stronger* than the published claim |
| **θ inequality → growth** | −153.9 | −1.88 (z units) / −33.8 (0–1 share units) | the published magnitude matches no Gini scale in the panel. Insignificant either way |
| **F×G above the income threshold** | −0.27 | +0.23 | sign flip on an insignificant coefficient at a grid point that itself differs ($6,948 vs $6,216) |
| β₁₀ G×Gini, β₇ D×Gini | −1.551, −9.473 | −0.986, −15.15 | same sign, both n.s. in both |
| β₃, between estimator | −0.581*** | −0.982*** | same sign and significance. Dropping the controls gives −0.619, the closest variant |

The pattern: **everything estimated off `F_l`, `G_l`, `FG_l` and the lagged control block
reproduces exactly; everything in the inequality extension does not.** The §4 coefficients
come from specifications whose exact regressor sets are not in `code/` — `inequality_analysis.py`
and `reframed_analysis.py` both estimate the Gini channel, but neither produces the published
numbers, and the primed equations (30′, 52–53) have no script. §4's estimates are not
reconstructible from this repository.

That matters more than the sign flips themselves. §4 exists to rescue the failed δ₄, the
report already concludes it fails, and the re-run agrees it fails — but it fails *differently*,
and two of the three "right sign, not significant" consolations in the table turn out to be
wrong-signed or significant here. **The §4 table should not be quoted until the specification
is recovered or re-specified.**

## Memo vs report — now settlable

The open issue in the README was that `results_memo.md` leads with an "escape dividend" where
`joint_digital_mit_report.md` concludes the escape mechanism is not identified. The re-run
does not make them agree, but it does say which one the data support.

- The memo's β₃ = **+1.014**, N=1,403. The report's β₃ = **1.096**, N=1,380. The committed
  panel gives **+1.0956, N=1,380** — the report's number, exactly. The memo was computed on
  a sample 23 observations larger that this repository does not contain.
- The memo's income threshold switches the dividend on below ≈$6,216 PPP (+2.78\*\*\* below,
  −0.27 above). The re-run finds a break at $6,948 with +1.98** below and **+0.23** above —
  the dividend is indeed concentrated in poorer countries, but it does not turn *negative*
  above the break, and the split is weaker.
- Meanwhile δ₄, the actual middle-income-band test, is −0.609 n.s. here exactly as published,
  and the Mundlak split confirms β₃ is a within-country effect (+0.73 within, −0.74 between,
  p=0.003).

So: **the report's framing is the one the committed data support.** A continuous income split
does put more of the complementarity in poorer countries, which is what the memo saw, but it
is a weaker result than the memo states and it is not the middle-income-escape claim —
the MI-band test fails here just as the report says. Calling β₃ an "escape dividend" is not
supported.

## Caveats on this re-run

1. **The panel is taken as given.** Nothing upstream was rebuilt — `src/run_pipeline.py`,
   `01_rebuild_F.py` and `02_rebuild_G.py` were not executed, and the raw-to-processed step
   is unverified. If `final_panel_imputed__5_.csv` is wrong, every number above is wrong in
   the same way, and the exact agreement with the report only shows the report was computed
   from this same file.
2. **Dependency versions differ** from `code/requirements.txt` (linearmodels 7.1 vs 6.0,
   numpy 2.2.3 vs 1.26.4). For OLS/FE point estimates this is not a plausible source of
   difference, and the exact matches on 20 quantities support that.
3. **The threshold searches are grid-dependent.** Both use a 40-point quantile grid over
   15–85%; a different grid moves the break and the two slopes.
4. **The exit probit is a rare-events model on 16 events.** The report's caveat applies with
   equal force to the re-run.
5. **`AI_scimago.csv` is not UTF-8.** It reads as latin-1 with a handful of mojibake country
   names (Côte d'Ivoire, Haiti, Curaçao) that fail to map to ISO3 and drop out of the
   correlation. 1,589 of 1,627 rows survive.
6. **Nothing in `outputs/rerun/` overwrites anything.** The published documents are unchanged;
   the re-run sits beside them.

## What to do next

1. **Recover or re-specify §4.** The inequality block is the only part that does not
   reproduce, and it is also the part with no script. Either find the notebook it came from
   (`notebooks/inequality_colab_full.ipynb` and its numbered copies are the obvious place) or
   re-specify the primed equations from scratch and re-estimate.
2. **Settle the memo's framing in the draft** along the lines above.
3. **Then measurement**, as the playbook already says: `01_rebuild_F.py` and `02_rebuild_G.py`
   are the highest-value change, and the re-run confirms why — the wave-years-only β₃ of
   −0.062 is what the interpolation is covering up.
