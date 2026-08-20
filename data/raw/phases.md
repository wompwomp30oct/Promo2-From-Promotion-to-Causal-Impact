# Phases — Promo Pricing Causal Impact

2-week scope, $0 cost. Sequential within a phase; do not proceed past a
step whose exit check fails. This mirrors the locked implementation plan
exactly — nothing here is open for re-litigation.

## Phase 0 — Repo Setup & Data Foundations (Day 1–2) — ✅ COMPLETE
- Load `train.csv` + `store.csv`, merge on `Store`.
- Missing-adoption-data check on `Promo2=1` stores → **drop**, not impute
  (treatment-timing field, not an ordinary covariate). Guard: raise if
  dropped count exceeds 500 (signals a merge/parse bug, not real sparsity).
- Compute one adoption date per `Promo2=1` store from
  `Promo2SinceWeek`/`Promo2SinceYear`.
- Early-panel buffer (8 weeks) and late-panel buffer (8 weeks), symmetric.
- Out-of-window recoding (adoption date after panel end → never-treated).
- Retain weekly `Promo` as a separate confound column — never dropped.
- **Exit check:** six counts logged to `eval_logs/phase0_step3_counts.json`.
  If `usable_staggered_treated` < 50, stop and reconsider the design.
- **Actual result (real Rossmann data):** `missing_adoption_dropped=0`,
  `excluded_early_thin_pre=392`, `excluded_late_thin_post=0`,
  `recoded_out_of_window=0`, `usable_staggered_treated=179`,
  `never_treated_donor_pool=544`. Floor cleared. Early/late asymmetry
  flagged for diagnostic review before trusting at face value (see
  `diagnose_boundary_asymmetry.py`).

## Phase 0.5 — Validate Both the Primary and Fallback Estimator (Day 2–3) — ⏳ NEXT
- Tutorial reproduction (primary): run `differences` against its own
  documented worked example. Tight tolerance (<1% relative) on point
  estimates (deterministic); tight on SEs unless the tutorial's inference
  is documented as bootstrap/simulation-based (then ~5–10%/CI-overlap).
- Structural stress-check on Rossmann's own shape: log every ATT(g,t)
  cell's group size. Thin cells (<10 stores) → leave-that-cohort-out
  re-run → report with/without, without-cohort as primary headline.
- API capability check: does `differences` support time-varying
  covariates? Determines Phase 1's Promo-confound path.
- Fallback validation (Sun–Abraham via `linearmodels`), run
  **unconditionally** regardless of whether the primary passes — this is
  deliberate schedule cost, disclosed as such in the README, never cut
  under time pressure.
- **Exit check:** both validation results logged; thin-cell action applied,
  not deferred; fallback's feature parity (clustered SEs, never-treated
  support) confirmed or logged as a known gap.

## Phase 1 — Validity & Confound Checks (Day 3–4)
- Weekly `Promo` as a time-varying confounder: control if
  `differences` supports it, disclosed threat with stated bias direction
  if not.
- Holiday-timing correlation (`StateHoliday`/`SchoolHoliday` vs. adoption
  timing) — controls decision justified either way.
- Balance check on comparison group: SMD (`CompetitionDistance`,
  threshold 0.1) + Cramér's V (`StoreType`/`Assortment`, threshold 0.1).
  Breach → restrict donor pool to matched subset; otherwise disclose and
  proceed. If restriction fires, **re-run Phase 0.5's thin-cell audit**
  against the restricted pool before Phase 2.
- Event-study window justified against Rossmann's own seasonal structure
  and the filtered cohorts' actual pre/post lengths — not an unexamined
  default.
- **Exit check:** every correlation/balance value logged; every controls
  decision justified in `docs/MEMORY.md`.

## Phase 2 — Main Causal Estimates (Day 5–7)
- Naive baseline: pooled TWFE (store + week FE, single treatment dummy,
  no staggered correction) — the method a working analyst gets wrong.
- Primary estimate: Callaway–Sant'Anna via `differences`, never-treated
  comparison group, clustered SEs, simple ATT as headline, event-study
  aggregation as secondary.
- Cohort-weight audit: log each cohort's contribution to the simple ATT.
  Disproportionate weight → report with/without.
- Collision rule: if the thin-cell rule (Phase 0.5) and the weight audit
  flag different cohorts, report all three variants (full,
  without-thin-cohort, without-high-weight-cohort) rather than picking
  one silently.
- **Exit check:** headline ATT, event-study aggregation, per-cohort
  weights, collision outcome, and the pooled-TWFE comparison all logged
  together.

## Phase 3 — Robustness (Day 8–9)
- Placebo test: non-overlapping offset (well clear of the event-study
  window, avoiding anticipation-effect overlap). Shifted placebo dates
  **re-validated through the same Phase 0 filters** as the real
  analysis — not assumed valid because the real date was.
- Bias-direction derivation for unobserved competitor pricing: two-line
  logical derivation, explicitly labeled unanchored theoretical
  reasoning, not empirically validated.
- Stockout honesty statement: `Open=0` captures closures only, not
  stockouts while open — disclosed as unobserved, never claimed
  controlled-for.
- **Exit check:** placebo coefficient + clustered CI logged; derivation
  and stockout wording checked against what the data actually supports.

## Phase 4 — Case-Study Visual (Day 10, stretch goal)
- One-store `google/tfp-causalimpact` case study, VI inference (not HMC —
  avoids timeout risk on free compute), explicitly labeled "illustrative
  case study, not the primary causal estimate" everywhere it appears.
- **First thing cut if behind schedule.**

## Phase 5 — Write-Up (Day 11–13)
- README, in order: treatment definition, Phase 0 filter counts, Phase 0.5
  dual-estimator validation, comparison-group + balance check, aggregation
  + cohort-weight audit, naive-vs-primary divergence, event-study result,
  Promo confound finding, re-validated placebo result, bias-direction
  derivation, stockout gap statement, case-study visual (if shipped),
  limitations section (consolidated, not scattered).
- **Exit check:** every section traces to a specific logged artifact in
  `eval_logs/`; no section states a conclusion without one.

## Day 14 — Buffer
Absorbs slippage from Phases 1–3, which determine whether the causal claim
actually holds. Do not spend buffer time polishing Phase 4 if Phases 1–3
aren't fully logged.

## Cut line (strict order, do not reorder under schedule pressure)
1. Drop Phase 4 (case-study visual) entirely.
2. Drop the cohort-weight audit's full with/without reporting — keep the
   single headline, note the limitation in prose instead of a second
   number.
3. **Never cut Phase 0.5's fallback validation**, regardless of how far
   behind schedule the project is — that check exists specifically to
   prevent a Day-12 scramble if the primary estimator is unstable on
   Rossmann's shape.

If steps 1–2 aren't enough to recover the schedule, ship a smaller but
fully-validated project (Phase 0 + 0.5 + 1 + naive-vs-primary divergence +
one placebo + limitations section) rather than cut into the validity chain.
