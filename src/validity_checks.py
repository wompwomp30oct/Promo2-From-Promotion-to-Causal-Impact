"""
Phase 0.5 (estimator validation) + Phase 1 (confound / balance / window checks).

GATED: do not fill in logic here until Phase 0's exit check clears
(usable_staggered_treated >= MIN_STAGGERED_TREATED_FLOOR) on the REAL
Rossmann panel, not the synthetic smoke-test data.

Locked tolerance rule (from the plan, refined):
  - Point estimates from `differences` and Sun-Abraham (linearmodels): both
    are deterministic computations on a fixed tutorial dataset. Use a tight
    relative tolerance (well under 1%) against the published value -- a
    bigger miss means a real setup bug, not acceptable noise.
  - Standard errors: tight IF analytic/closed-form. Loose (~5-10% or
    CI-overlap) ONLY if the tutorial's inference is explicitly documented as
    bootstrap/simulation-based. Default to tight if the docs don't say.
  - This tolerance rule does NOT carry over to the Phase 4 CausalImpact
    case-study check -- VI-based Bayesian structural time series is
    genuinely stochastic, so sign/rough-magnitude is the honest bar there.
"""

# TODO (gated on Phase 0 clearing on real data):
# def validate_differences_on_tutorial() -> dict: ...
# def stress_check_on_rossmann(panel) -> dict: ...
# def check_covariate_support() -> dict: ...
# def validate_fallback_on_tutorial() -> dict: ...
#
# def check_promo_confound(panel) -> dict: ...
# def check_holiday_correlation(panel) -> dict: ...
# def balance_check(panel) -> dict: ...        # SMD (CompetitionDistance) + Cramer's V (StoreType/Assortment)
# def justify_event_study_window(panel) -> dict: ...
