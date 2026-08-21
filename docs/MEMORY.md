# Decision Log

## Phase 0 — resolved
- **Missing Promo2SinceWeek/Year (Promo2==1 stores): DROP, not impute.**
  Rationale: this is the treatment-timing variable feeding the CS estimator's
  cohort-time cells directly, not an ordinary covariate. An imputed date
  silently misassigns cohorts; a "flag" in the write-up doesn't neutralize
  that, since the imputed value still gets used in estimation either way.
  Guard added: if the dropped count exceeds 500 (Promo2SinceWeek/Year should
  be structurally null only for Promo2==0 stores), the pipeline raises
  instead of proceeding — a large count signals a merge/parse bug, not a
  genuine data gap this decision was designed for.
- **Buffer width: 8 weeks, both ends, symmetric.** Lower bound of the locked
  8-10 week range. Named constant (`EARLY_BUFFER_WEEKS`, `LATE_BUFFER_WEEKS`
  in `data_prep.py`) so Phase 1's event-study window justification can
  reference it directly rather than re-deriving it.
- Phase 0 logic smoke-tested against synthetic data covering all six
  buckets (missing / early / late / out-of-window / staggered-treated /
  never-treated) — all six confirmed correct against planted cases before
  being trusted on real data.

## Phase 0.5 — validation decisions resolved
- Point estimates: tight tolerance (<1% relative) against tutorial values —
  both `differences` and Sun-Abraham are deterministic on a fixed dataset.
- Standard errors: tight if analytic, loose (~5-10%/CI-overlap) only if the
  tutorial's inference is documented as bootstrap/simulation-based. Default
  to tight if undocumented.
- Primary fixture: committed `data/fixtures/mpdta.csv`, converted from the
  authors' `mpdta.rda` at
  `https://raw.githubusercontent.com/bcallaway11/did/master/data/mpdta.rda`.
  The locked specification is `differences` 0.3.0, never-treated controls,
  doubly robust estimation (`est_method="dr"`), and simple aggregation with
  `outcome ~ 1`. The verified Python target is ATT=-0.039951 and analytic
  SE=0.012034 at 1% tolerance. The R `did` reference for the same fixture is
  approximately ATT=-0.04 and SE=0.0119; it is retained as a cross-language
  reference, not substituted for the installed Python target. In
  `differences` 0.3.0, `boot_iterations=0` is the default and the result
  reports an analytic SE, so the loose bootstrap tolerance is not applicable
  to this validation.
- Rossmann stress audit: event time is limited to -8 through +8 weeks,
  reference week -1, and cell size means distinct treated stores. Any thin
  cohort is rerun through the validated primary estimator, with the
  without-cohort estimate reported as primary.
- Fallback: `linearmodels.PanelOLS` with explicit cohort-by-event-time terms,
  never-treated stores retained in the fixture, entity-clustered SEs, and all
  32 configured interaction coefficients reported. This is a fallback
  validation, not a silent replacement for the primary estimator.
- Time-varying covariates are capability-checked in Phase 0.5 only; Promo and
  holiday controls remain a Phase 1 decision.
- This tolerance rule does NOT apply to the Phase 4 CausalImpact case-study
  check (VI is genuinely stochastic — sign/magnitude check only there).

## Build sequencing — resolved
- Structure/stubs for all phases built now. Logic gated at two checkpoints:
  after Phase 0 clears its floor on REAL data, and after Phase 0.5 resolves
  which estimator (primary vs. fallback) is in play. Phases 1-3 do not need
  gating between each other once Phase 0.5 clears.

## Open
- Phase 0.5 real-data stress reruns must be regenerated when the primary
  `est_method` changes; the current artifact must use the locked `dr` method.
