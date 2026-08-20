# PRD — Promo Pricing Causal Impact (Rossmann)

## Problem statement
Most entry-level DA/DS portfolios show a naive before/after or a plain churn
classifier with no baseline, no error analysis, no pre-registered hypothesis.
This project demonstrates causal-inference rigor — pre-committed design,
naive-vs-corrected comparison, validated tooling, documented limitations —
applied to a real business question: **did adopting the Promo2 campaign
cause a change in store sales, and by how much?**

## What gets built
A reproducible pipeline + README that estimates the causal effect of Promo2
adoption on Rossmann store sales, using:
- A **naive baseline** (pooled TWFE) — the method a working analyst would
  actually run and get wrong under staggered treatment timing.
- A **primary causal estimate** (Callaway–Sant'Anna staggered DiD via
  `differences`) that corrects for the Goodman-Bacon bias the naive method
  is exposed to.
- Documented validity checks (parallel trends via event study, placebo test,
  comparison-group balance, confound checks) run and logged *before* the
  headline number is trusted, not after.
- A named limitations section with reasoned (not hand-waved) direction of
  bias for every gap the data can't close.

## Targeted users / audience
- **Primary: hiring managers / recruiters** screening entry-level DA/DS
  candidates for fintech and analytics-adjacent roles — the artifact is
  built to be legible to someone with 5 minutes and general stats literacy,
  not just a fellow causal-inference specialist.
- **Secondary: interviewers** who will probe the causal claim directly —
  every design decision needs a defensible, pre-stated reason, not a
  post-hoc justification invented under questioning.
- **Not built for:** production deployment, real-time serving, or any
  audience needing API access. This is a single reproducible analysis, not
  a service.

## Core features / deliverables
1. `data_prep.py` — Phase 0 data loading, treatment-date computation, four
   boundary filters (missing-data, early-buffer, late-buffer, out-of-window).
2. Estimator validation — primary (`differences`) and fallback
   (Sun–Abraham via `linearmodels`) both validated against known published
   results before being trusted on Rossmann.
3. Validity checks — Promo confound check, holiday-timing correlation,
   comparison-group balance (SMD + Cramér's V), justified event-study
   window.
4. Main estimate — pooled-TWFE naive baseline vs. Callaway–Sant'Anna
   estimate, with a cohort-weight audit and a collision rule if the
   thin-cell and weight audits disagree.
5. Robustness — re-validated placebo test, bias-direction derivation
   (labeled unanchored), stockout honesty statement.
6. Optional stretch — one-store `tfp-causalimpact` illustrative visual,
   explicitly labeled non-primary.
7. README — every section traces to a specific logged artifact in
   `eval_logs/`; no conclusion without a corresponding number.

## Success criteria
- Every locked design decision in `Architecture.md` / `phases.md` is
  reflected in actual code and actual logged output — no gap between what
  the docs claim and what the repo does.
- The naive-vs-corrected divergence is real and explained, not asserted.
- At least one validity check (event-study pre-trend, placebo, or balance
  check) is reported with its real value even if it's not clean — per the
  plan's rule that a marginal or failing check gets disclosed, not hidden.
- Runs end-to-end at $0 cost, entirely on free-tier tools (Kaggle data,
  local/Colab compute, no paid API calls).
- README is legible to a hiring manager in under 10 minutes, with a
  limitations section a specialist would find honest rather than naive.

## Explicitly out of scope
- Deployment, hosting, or a live demo — this is a static repo + README.
- Any dataset requiring payment or a non-free API key.
- Group or calendar ATT(g,t) aggregations (simple + event-study only, per
  locked decision — not computed, not claimed).
- Causal claims about *why* competitor pricing or stockouts behave a
  certain way — those are disclosed as unobserved, not modeled.
