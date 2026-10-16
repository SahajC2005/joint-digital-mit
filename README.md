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
| `docs/joint_digital_mit_report.md` | the full empirical findings report — read this first |
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

## Two open issues

**1. `results_memo.md` and `joint_digital_mit_report.md` do not tell the same story.**
The report (18 Jun) concludes plainly that *"the middle-income-escape and displacement
mechanisms are not identified in these data."* The memo (1 Jul, newer) leads with
**"Escape dividend (FE): β₃(F×G) = +1.014\*\*"** and an income threshold switching on below
≈\$6,216 PPP (+2.78\*\*\* below, −0.27 above). These are not strictly contradictory — an
MI-dummy triple interaction and a continuous income-threshold split are different tests, and
the memo's Gini nulls agree with the report — but the memo relabels β₃ as the "escape
dividend" and leads on a threshold result, which reads as the MIT story working while the
report says it does not. **Unresolved. Settle which framing the evidence supports before any
of this goes into a draft.**

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

- **Nothing here has been re-run or verified in this repository.** All numbers quoted above
  are read from the project's own documents. The pipeline README notes the package was a
  *"draft pipeline, not yet executed end-to-end."*
- **Redistributed data.** `data/raw/` contains World Bank, IMF, ILO, PWT, WGI and Oxford GARI
  extracts under their respective terms. This is why the repository is private; check the
  licence of each source before any public release.
- Several notebooks (`NS_Constrained_AE_YieldCurve*`, `RRRReeeaaaalllll_B_spline`,
  `bspline3d.py`) are from adjacent work and may not belong to this paper.
