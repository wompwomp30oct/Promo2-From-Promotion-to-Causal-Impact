# Rules — Promo Pricing Causal Impact

## Libraries: use

| Purpose | Use | Not |
|---|---|---|
| Staggered DiD | `differences` (Callaway–Sant'Anna) | Manual TWFE with a pooled treatment dummy — this is the exact naive baseline being argued against, not a substitute estimator |
| Fallback estimator | `linearmodels` (Sun–Abraham, interaction-weighted) | A second unfamiliar package chosen ad hoc mid-project — the fallback is pre-committed and validated in Phase 0.5, not improvised on Day 12 |
| Naive comparison | `linearmodels` pooled TWFE | A no-comparison-group before/after — that's a strawman, not what a working analyst would actually run |
| Bayesian counterfactual (illustrative only) | Official `google/tfp-causalimpact` | Will Fuks' community `tfcausalimpact` fork — same backend, but the official package is the citable one |
| Balance checks | `scipy`/`statsmodels` for SMD (continuous) and Cramér's V (categorical) | Reusing SMD on categorical fields (`StoreType`, `Assortment`) — SMD isn't well-defined there without a per-dummy workaround |
| Data storage | `pyarrow`/parquet for `data/processed/` | Re-parsing raw CSVs on every run — parquet keeps `treatment_status`/`adoption_date` typed correctly across reloads |

## Libraries: avoid
- **Any paid API or paid compute tier** — the $0 constraint is load-bearing
  for the project's own PRD, not a soft preference.
- **HMC inference by default** in `tfp-causalimpact` — use VI (fast
  default); HMC is reserved only for the single headline plot, if time
  allows, because HMC fitting risks timeouts on free compute (Colab/local).
- **Untested statistical packages applied directly to real data** — every
  estimator (primary and fallback) is validated against its own documented
  worked example *before* touching Rossmann. This is not optional caution;
  it's Phase 0.5's entire purpose.

## Error handling
- **Missing-adoption-data guard:** `apply_missing_adoption_filter()` raises
  `Phase0DataError` (not a warning) if the dropped count exceeds 500 —
  `Promo2SinceWeek/Year` should be structurally null only for `Promo2=0`
  stores, so a count this large means a merge/parse bug upstream. A logged
  warning can't compensate for a silently-wrong count; the pipeline must
  stop.
- **Floor check:** if `usable_staggered_treated` < 50 after Phase 0's
  filters, the pipeline prints an explicit warning and does **not**
  proceed silently into Phase 0.5 — per the plan, this is a
  stop-and-reconsider-the-design signal.
- **Every phase writes through `log_exit_check()`** to `eval_logs/`, never
  directly to `README.md` or `docs/MEMORY.md` by hand — the README is
  assembled from logged JSON after the fact, so there is no path for a
  conclusion to appear in the write-up without a corresponding artifact.
- **ISO week/year → date conversion** returns `None` (not a coerced
  guess) for malformed values (e.g. week 53 in a 52-week year) — a
  malformed date is treated as missing, feeding into the same drop-not-impute
  path as a genuinely absent value.
- **Assertions, not silent trust, on merge integrity** — `data_prep.py`
  asserts that `Promo` and `treatment_status` survive the `train`/`store`
  merge before writing `panel.parquet`, since a silently dropped column
  here would invalidate Phase 1's confound check without any visible error.

## Boundaries for AI-assisted work on this repo
- **No logic in `validity_checks.py`, `estimators.py`, `robustness.py`, or
  `case_study.py` until their gating condition clears** — Phase 0's floor
  on real data, then Phase 0.5's estimator resolution. Writing ahead of
  the gate risks producing code built against an estimator that gets
  discarded.
- **No aggregation scheme, comparison group, or tolerance threshold gets
  decided inside a function body.** Every one of these is a locked
  decision recorded in `docs/MEMORY.md` and referenced by name in code —
  if a script needs to make a judgment call not already locked, that's a
  signal to stop and log a decision first, not to pick a default silently.
- **No claim of "controlled for" without a corresponding check.** The
  stockout statement is the concrete example: `Open=0` only captures full
  closures, and the README must say so explicitly rather than imply
  stockouts were handled.
- **No quoting or reproducing text from external sources** (Kaggle
  discussion threads, package documentation, blog posts) in the README —
  paraphrase findings, cite by name/link only.
- **No silent estimator substitution.** If `differences` fails validation
  and the Sun–Abraham fallback triggers, that switch is logged explicitly
  in `docs/MEMORY.md` and called out in the README's methodology section —
  never a quiet swap that changes which comparison-group/SE assumptions
  are actually in effect.
- **Any new dependency added to `requirements.txt` must have a free tier
  sufficient for the full pipeline** — checked before adding, not after
  hitting a paywall mid-run.
