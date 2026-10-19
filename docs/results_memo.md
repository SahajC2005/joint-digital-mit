# Results memo — Joint Digital Transformation & the Middle-Income Trap

*Rewritten 2026-10-19 against the re-run (`docs/RERUN_NOTES.md`). The earlier version of this
memo led with an "escape dividend" of β₃ = +1.014\*\* on N=1,403. That sample is not in this
repository and that framing is not what the data support; both are corrected below. The
figures the re-run did not touch are marked **unverified** rather than deleted.*

## Verified on the committed panel

- **F and G are growth complements.** β₃(F×G) = **+1.0956\*\***, N=1,380, 135 countries
  (two-way FE, country-clustered SEs). Stable across dynamic specification (+1.0980\*\*),
  dropping China (+1.0943\*\*), and 3-year forward-average growth (+0.8943\*\*).
- **It is a within-country effect.** Mundlak decomposition: **+0.729 within** vs
  **−0.744 between**, p(diff) = 0.003. The complementarity is identified off countries that
  deepen both technologies over time, not off a rich-country cross-section.
- **It switches on above a joint-penetration threshold.** Break at F·G ≈ 0.369; slope −1.571
  below, **+0.824\*** above.
- **AI-source validation.** OpenAlex vs Scimago, log-log r = **0.961** (1,589 country-years,
  189 countries).

## Revised

- **Not an escape dividend.** δ₄(F×G×MI) = **−0.609, n.s.** (p = 0.517) — the middle-income-band
  test fails, exactly as published. The complementarity is *smaller* inside the band than
  outside it. β₃ should be described as a digital complementarity, not as an escape lever.
- **Income threshold: weaker, and it does not reverse.** A grid search puts the break at
  **≈\$6,948 PPP**, with **+1.98\*\*** below and **+0.23 (n.s.)** above — previously stated as
  \$6,216 with +2.78\*\*\* below and −0.27 above. The dividend is concentrated in poorer
  countries; it does not turn negative in richer ones. The break is grid-dependent.
- **β₃ = 1.014 on N=1,403** was the figure this memo used to lead with. The committed panel
  gives 1.0956 on N=1,380 — the report's number. Use the report's.

## Unverified — not re-estimated

These were not re-run and should not be quoted without re-estimating them first.

- **Instrumented β₃ = +1.337\*\*\* (over-identified).** No IV specification was re-run. The
  report's own IV battery has a first-stage F of 2.8–6.6, below the weak-instrument
  threshold, so the attenuation story this number carries is not currently supported.
- **Concentration loop (U32): γ₁ = ∂Sᴾ/∂G = +0.074, θ = −42.47 ⇒ drag = −3.137.** Separate
  objects from the §4 Gini channel; neither was reproduced. The §4 inequality block is the
  one part of the paper that does not reproduce at all (`docs/RERUN_NOTES.md`), and recovering
  its specifications is open work.
- **AI → top-10% income share positive and significant; Gini and labour share null.** Not
  re-run. Note that on the committed panel the §4 AI→inequality coefficient is a negligible
  −0.085 (n.s.), opposite in sign to the published +0.005.

## Caveats

- F is one Findex component of four, interpolated between waves. On wave years only, β₃
  collapses to **−0.062** (N=412). This is the binding constraint on the whole exercise.
- G is mostly cross-sectional: `Z_readiness` and `Z_adoption` have *exactly zero*
  within-country variation and are absorbed whole by country fixed effects.
- The vulnerability→exit link runs backwards (ψ₄ = +1.441\*\*\*) on 16 exit events — a
  rare-events model, as previously noted.
- GMM Hansen borderline; the sectoral U21 decomposition is reduced-form (no sector
  productivity). Neither was re-run.
