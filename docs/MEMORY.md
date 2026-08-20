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

## Phase 0.5 — tolerance rule resolved, logic not yet run
- Point estimates: tight tolerance (<1% relative) against tutorial values —
  both `differences` and Sun-Abraham are deterministic on a fixed dataset.
- Standard errors: tight if analytic, loose (~5-10%/CI-overlap) only if the
  tutorial's inference is documented as bootstrap/simulation-based. Default
  to tight if undocumented.
- This tolerance rule does NOT apply to the Phase 4 CausalImpact case-study
  check (VI is genuinely stochastic — sign/magnitude check only there).

## Build sequencing — resolved
- Structure/stubs for all phases built now. Logic gated at two checkpoints:
  after Phase 0 clears its floor on REAL data, and after Phase 0.5 resolves
  which estimator (primary vs. fallback) is in play. Phases 1-3 do not need
  gating between each other once Phase 0.5 clears.

## Open — waiting on user
- Real train.csv / store.csv not yet available (Kaggle not reachable from
  the build sandbox — requires manual download + upload).
- Phase 0 exit-check counts on REAL data not yet known. Floor check
  (usable_staggered_treated >= 50) must be evaluated before Phase 0.5 begins.
