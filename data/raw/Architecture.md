# Architecture — Promo Pricing Causal Impact

## Architecture flow

```
train.csv + store.csv (Kaggle, manual download → data/raw/)
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 0 — src/data_prep.py                               │
│  load_raw() → check_raw_row_counts()                     │
│  compute_adoption_dates()  [ISO week/year → date]         │
│  apply_missing_adoption_filter()  [drop, guard >500]      │
│  apply_boundary_filters()  [early/late buffer, OOW recode]│
│  build_panel()  → data/processed/panel.parquet            │
└─────────────────────────────────────────────────────────┘
        │  gate: usable_staggered_treated ≥ 50, else STOP
        ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 0.5 — src/validity_checks.py (estimator validation) │
│  validate_differences_on_tutorial()   [tight tolerance]   │
│  stress_check_on_rossmann(panel)      [thin-cell audit]   │
│  check_covariate_support()            [time-varying?]     │
│  validate_fallback_on_tutorial()      [unconditional]     │
└─────────────────────────────────────────────────────────┘
        │  gate: which estimator wins (primary vs. fallback)
        ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 1 — src/validity_checks.py (confound / balance)     │
│  check_promo_confound(panel)                              │
│  check_holiday_correlation(panel)                          │
│  balance_check(panel)         [SMD + Cramér's V]           │
│  justify_event_study_window(panel)                         │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 2 — src/estimators.py                               │
│  pooled_twfe_baseline(panel)          [naive]              │
│  callaway_santanna_estimate(panel)    [primary]            │
│  cohort_weight_audit() + collision_rule()                  │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 3 — src/robustness.py                                │
│  placebo_test(panel)          [re-validated through Phase 0]│
│  bias_direction_derivation()  [labeled unanchored]          │
│  stockout_statement()                                       │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 4 (stretch) — src/case_study.py                      │
│  one_store_causal_impact()    [VI inference, illustrative]  │
└─────────────────────────────────────────────────────────┘
        │
        ▼
        README.md  (every section ← eval_logs/*.json)
```

Every phase writes its results through `src/utils.py::log_exit_check()` to
`eval_logs/<step_name>.json`. This is the single source of truth the README
is built from — no section may state a conclusion without a corresponding
file in `eval_logs/`.

## File / folder structure

```
promo-causal-impact/
├── data/
│   ├── raw/                     # train.csv, store.csv — gitignored
│   └── processed/                # panel.parquet — gitignored
├── src/
│   ├── utils.py                  # constants, JSON exit-check logger
│   ├── data_prep.py               # Phase 0 — LIVE
│   ├── validity_checks.py         # Phase 0.5 + Phase 1 — gated stub
│   ├── estimators.py              # Phase 2 — gated stub
│   ├── robustness.py              # Phase 3 — gated stub
│   └── case_study.py              # Phase 4 — gated stub
├── notebooks/
│   └── make_synthetic_data.py     # schema-matched smoke-test data generator
├── eval_logs/                     # one JSON per exit check (gitignored data,
│                                   # but logs themselves ARE committed)
├── docs/
│   ├── PRD.md                     # this document set
│   ├── Architecture.md
│   ├── phases.md
│   ├── rules.md
│   └── MEMORY.md                  # decision log across review rounds
├── requirements.txt
├── .gitignore
└── README.md
```

**Why stubs, not empty files, for Phases 0.5–4:** function signatures and
docstrings are committed now so the I/O contract is fixed early, but logic
is gated behind two checkpoints — Phase 0 clearing its floor on real data,
and Phase 0.5 resolving which estimator wins — because writing estimator
logic against `differences` before knowing if it passes validation risks
throwing away real work if the Sun–Abraham fallback triggers instead.

## Tech stack

| Layer | Tool | Why | Cost |
|---|---|---|---|
| Data | Rossmann Store Sales (Kaggle) | Real `Promo2` binary treatment flag, no proxy construction needed | Free |
| Data handling | pandas, pyarrow | Standard; parquet for the processed panel (typed, fast reload) | Free |
| Primary estimator | `differences` (Callaway–Sant'Anna) | Staggered-adoption-robust, avoids Goodman-Bacon bias that plain TWFE has | Free |
| Fallback estimator | `linearmodels` (Sun–Abraham) | Pre-committed contingency if `differences` fails validation | Free |
| Naive baseline | `linearmodels` (pooled TWFE) | The method a working analyst would actually run — the thing being argued against | Free |
| Stats / validity checks | `scipy`, `statsmodels` | SMD, Cramér's V, event-study regression, clustered SEs | Free |
| Illustrative case study | `google/tfp-causalimpact` (official) | Bayesian structural time series, VI inference (not HMC — avoids timeout risk on free compute) | Free |
| Plotting | `matplotlib` | Event-study plot, one-store case-study visual | Free |
| Compute | Local machine / Colab free tier | No paid compute anywhere in the pipeline | Free |
| Version control | Git + GitHub | Standard; `data/raw` and `data/processed` gitignored (large, regeneratable) | Free |

No paid API, no paid compute, no paid dataset — every tool in this stack
has a free tier sufficient for the full pipeline.
