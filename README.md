# Joint Digital Transformation and the Middle-Income Trap

Working repository for **"FinTech, AI, and the Middle-Income Trap: Joint Digital
Transformation as an Escape Mechanism."**

Does the *interaction* of FinTech penetration (**F**) and AI capability (**G**) raise growth,
and does it act as an escape lever from the middle-income trap? Country-year panel,
217 World Bank–classified economies, ≈2010–2024, two-way fixed effects with
country-clustered standard errors.

## Layout

```
code/        pipeline (src/), rebuild + re-estimation scripts, Bam/ forecasting
notebooks/   Colab/analysis notebooks (one copy each, newest kept)
data/raw/    source data: Findex, PWT, WGI, WDI, ILO, OpenAlex, IMF AIPI, Oxford GARI
data/processed/  constructed panels (final_panel, panel.parquet, unified_panel, ...)
docs/        report, results memo, improvement playbook, derivations/ (PDF)
figures/     paper figures
outputs/     estimation logs, inequality results, Bam forecast outputs
MANIFEST.txt every file's original path, and every excluded file with the reason
```

## Start here

| file | what it is |
|---|---|
| `docs/RERUN_NOTES.md` | **the re-run: which published numbers reproduce on this data and which do not — read this first** |
| `docs/joint_digital_mit_report.md` | the full empirical findings report |
| `docs/results_memo.md` | later one-page summary of headline numbers |
| `docs/IMPROVEMENT_PLAYBOOK.md` | diagnosis of the identification problem + the fixes, with data links |
| `docs/README.md` | the original replication-package README (pipeline stages) |
| `outputs/inequality_results.txt` | raw output of the inequality/dual-economy battery |

## Findings in one paragraph

**What holds:** F and G are growth complements. β₃(F×G) ≈ **+1.01 to +1.10**, significant at
5%, stable across dynamic specification, threshold regression (break at F·G ≈ 0.351),
dropping China, and complete-case re-estimation. A Mundlak decomposition shows this is a
genuinely *within-country* phenomenon (+0.73 within vs −0.74 between, p≈0.003) — it is
identified off countries that deepen both technologies over time, not off a cross-sectional
rich-country confound.

**What does not hold:** the parts that make this a middle-income-trap paper.
δ₄(F×G×MI) = −0.609, n.s. — the complementarity is *smaller* inside the middle-income band
(0.85) than outside it (1.46). The displacement drag has the right sign but no power
(≈0.9 collinear with AI). The vulnerability→exit link comes out wrong-signed and significant
(ψ₄ = +1.223, on only 13 exit events). The inequality extension written to rescue δ₄ fails
too: φ₄ = +0.802 (wrong sign), and the top-inequality tercile shows the *largest* joint-digital
effect, the reverse of the hypothesis. The IV is weak throughout (first-stage F ≈ 2.8–6.6).

*Re-run status (2026-10-18, §4 settled 2026-10-19): everything in "what holds" reproduces on
the committed panel to three decimals. Of "what does not hold", δ₄ and the tercile ordering
reproduce, ψ₄ reproduces in sign and significance on 16 rather than 13 events, and the §4
inequality figures — β₆, β₁₁, φ₄, γ₁, θ and ω — now reproduce to four decimals once the
primed specifications are estimated as written. See `docs/RERUN_NOTES.md`.*

## Open issues (the first is now settled)

**1. `results_memo.md` and `joint_digital_mit_report.md` do not tell the same story —
settled by the re-run, in the report's favour.** The report (18 Jun) concludes plainly that
*"the middle-income-escape and displacement mechanisms are not identified in these data."*
The memo (1 Jul, newer) leads with **"Escape dividend (FE): β₃(F×G) = +1.014\*\*"** and an
income threshold switching on below ≈\$6,216 PPP.

Re-estimated here, the committed panel gives β₃ = **+1.0956\*\*, N=1,380** — the report's
1.096 to three decimals, not the memo's 1.014 on N=1,403, a sample this repository does not
contain. The income split is real but weaker than the memo states (break at \$6,948, +1.98\*\*
below, **+0.23** above rather than −0.27), and δ₄, the actual middle-income-band test, is
−0.609 n.s. exactly as published. **Use the report's framing. β₃ is a within-country
complementarity (+0.73 within vs −0.74 between, p=0.003), not an "escape dividend".**

**2. Measurement is the binding constraint, and it is fixable.** Per
`IMPROVEMENT_PLAYBOOK.md`, measured on the panel itself:

| regressor | within-country SD | between-country SD | within/between |
|---|---|---|---|
| F (FinTech) | 0.27 | 0.95 | 0.28 |
| G (AI) | 0.08 | 0.87 | 0.09 |

`Z_readiness` and `Z_adoption` have **exactly zero** within-country SD (single 2024
snapshots, absorbed by country FE). F is one Findex component of four, interpolated between
waves — β₃ collapses to −0.06 on wave-years-only data. `code/01_rebuild_F.py` and
`code/02_rebuild_G.py` exist to address this and are the highest-value next step.

## Provenance

Consolidated on 2026-10-16 from `~/Downloads/joint_digital_mit 2` (copied, originals
untouched). That folder held 623 MB / 298 files with heavy duplication. This repository is a
**curated replication set**: 146 files, ~102 MB.

Kept: all code, all unique data (raw and processed), all project documents and derivations,
figures, and run outputs. Where a file existed in several versions, the newest was kept and
renamed to a clean name; where copies were byte-identical, one was kept.

Excluded: a bundled 352 MB `.venv`; `.zip`/`.tar.gz` archives whose contents are present
unpacked; 17 downloaded third-party papers (arXiv/journal PDFs — literature, not project
output); `.numbers` files duplicating an `.xlsx`; and a nested copy of `src/`/`config/`/`tests/`.

`MANIFEST.txt` lists every kept file with its original path and every excluded file with the
reason, so nothing is silently lost — the source folder is still intact if anything needs
recovering.

## Caveats

- **The estimation has now been re-run; the upstream pipeline has not.** Every published
  coefficient was re-estimated on the committed panel on 2026-10-18 — see the section below
  and `docs/RERUN_NOTES.md`. What remains unverified is the raw-to-processed step:
  `src/run_pipeline.py`, `01_rebuild_F.py` and `02_rebuild_G.py` were not executed, and the
  pipeline README still describes a *"draft pipeline, not yet executed end-to-end."*
- **Redistributed data.** `data/raw/` contains World Bank, IMF, ILO, PWT, WGI and Oxford GARI
  extracts under their respective terms. This is why the repository is private; check the
  licence of each source before any public release.
- Several notebooks (`NS_Constrained_AE_YieldCurve*`, `RRRReeeaaaalllll_B_spline`,
  `bspline3d.py`) are from adjacent work and may not belong to this paper.

---

## Measured vs. documented (added 2026-10-18)

The estimation was re-run locally against the committed panel. Full detail, including every
specification probe, is in **`docs/RERUN_NOTES.md`**.

| | |
|---|---|
| `code/04_rerun_verify.py` | re-estimates all 41 published quantities and scores each one |
| `code/05_spec_probes.py` | alternative regressor sets for the ones that miss |
| `code/06_recover_section4.py` | the §4 primed specifications, recovered and re-estimated |
| `outputs/rerun/rerun_coefficients.csv` | every coefficient from every spec (59 rows) |
| `outputs/rerun/rerun_vs_published.csv` | published value, re-run value, gap, verdict (41 rows) |
| `outputs/rerun/rerun_vs_published_recounted.csv` | the same 41 rows after the §4 recovery |
| `outputs/rerun/section4_vs_published.csv` | the §4 table, published vs recovered (13 rows) |
| `outputs/rerun/section4_coefficients.csv`, `section4_iv_first_stage.csv` | every §4 coefficient; the Bartik first-stage F |
| `outputs/rerun/rerun_log.txt`, `spec_probes_log.txt`, `section4_log.txt` | full console output |

**29 of 41 reproduce to three decimals, 8 are close, 3 differ in magnitude, 1 flips sign**
(20/10/7/4 before the §4 specifications were recovered on 2026-10-19).

**What reproduces.** The whole spine of the paper. β₃ (F×G) = **+1.0956\*\*** against a
published 1.096\*\*; δ₄ (F×G×MI) = **−0.6092 n.s.** against −0.609; the dynamic panel, the
exclude-China variant, every cell of the §5 robustness table (drop-COVID 0.491, wave-years-only
−0.062 on N=412, forward-average 0.894\*\*, complete-case 1.21/−1.17), the threshold's upper
slope, the Mundlak within/between split (+0.729 / −0.744, p=0.003) and the AI source validation
(log-log r = 0.961 vs 0.964). The playbook's measurement diagnosis holds too: `Z_readiness` and
`Z_adoption` have *exactly* zero within-country variation.

**§4, and how it was settled.** The first re-run missed five §4 figures (β₆ came out +3.25
against a published −24.85, β₁₁ +0.33 against −0.118, ω significant where the report calls it
underpowered, θ on no recognisable Gini scale, γ₁ wrong-signed) and concluded the primed
specifications were not reconstructible. **That conclusion was wrong.** They are in
`notebooks/joint_digital_mit_analysis.ipynb`, a tracked notebook whose stored outputs print
every §4 coefficient to four decimals; `04_rerun_verify.py` and `05_spec_probes.py` had
guessed the regressor sets instead of reading them, and in each case the guess dropped a
block of terms the primed equation carries (the absorptive-capacity pair `GH`/`GS` for β₆,
the institutional block for β₁₁, `FG_Shock` for ω, the skill-bias term for γ₁; θ is a
two-step coefficient on a *fitted* Gini, not on Gini).

`code/06_recover_section4.py` estimates the specifications as written and **all 13 of them
reproduce to four decimals**, including the Bartik first-stage F of 4.20. Substantively
nothing moves: β₁₁ is correctly signed and p = 0.87, **φ₄ = +0.802 is wrong-signed**, the
tercile ordering is backwards, the IV is weak, and ω = +0.614 is insignificant — so the one
place the first re-run looked *stronger* than the paper was its own artifact. **The §4 table
can be quoted as written**; the earlier instruction not to is withdrawn. §4 fails, exactly as
the report says it does.

Two defects in the committed code were found on the way and are documented in the notes:
`03_mundlak_reestimation.py` points at `final_panel_imputed.csv`, which lacks every regressor
it uses, and the exit risk set must condition on `MI_l == 1` (conditioning on `MI == 1` yields
zero events, because `Exit` is coded on the post-transition row).
