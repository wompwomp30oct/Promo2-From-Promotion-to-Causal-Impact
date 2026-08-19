# Promo Pricing Causal Impact — Rossmann Store Sales

Estimating the causal effect of Promo2 campaign adoption on store sales using
a staggered-adoption difference-in-differences design, with a naive pooled-TWFE
baseline shown alongside it to make explicit what the naive method gets wrong.

**Cost: $0. Scope: 2 weeks.** Full design rationale and review history in
[`docs/MEMORY.md`](docs/MEMORY.md).

## Status

- [x] Phase 0 — data prep + boundary filters (`src/data_prep.py`), smoke-tested
      against synthetic data covering all six classification buckets
- [ ] Phase 0.5 — estimator validation (gated on real data clearing Phase 0's floor)
- [ ] Phase 1 — confound / balance / event-study window checks
- [ ] Phase 2 — main causal estimates
- [ ] Phase 3 — robustness (placebo, bias-direction derivation, stockout caveat)
- [ ] Phase 4 — illustrative case-study visual (stretch, cut first if behind)
- [ ] Phase 5 — write-up

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Getting the data

This environment can't reach Kaggle directly. Download `train.csv` and
`store.csv` from the
[Rossmann Store Sales competition](https://www.kaggle.com/c/rossmann-store-sales/data)
and place both in `data/raw/`.

To smoke-test the pipeline logic before real data is available:

```bash
python3 notebooks/make_synthetic_data.py   # writes schema-matched fake data/raw/*.csv
python3 -m src.data_prep                    # runs Phase 0 end-to-end
```

## Running Phase 0

```bash
python3 -m src.data_prep
```

Writes `data/processed/panel.parquet` and logs six counts to
`eval_logs/phase0_step3_counts.json`: `missing_adoption_dropped`,
`excluded_early_thin_pre`, `excluded_late_thin_post`, `recoded_out_of_window`,
`usable_staggered_treated`, `never_treated_donor_pool`.

If `usable_staggered_treated` comes back below the floor (50), the script
prints a warning rather than proceeding silently — that's a signal to
reconsider the design, not a bug to suppress.

## Repo layout

```
data/raw/            train.csv, store.csv (gitignored — not committed)
data/processed/      panel.parquet (gitignored)
src/                 phase logic — data_prep.py is live; the rest are
                     signature-only stubs gated behind Phase 0.5
notebooks/           make_synthetic_data.py — schema-matched smoke-test data
eval_logs/           one JSON per exit check — the source of truth for every
                     number that ends up in the README write-up
docs/MEMORY.md       decision log across every design-review round
```
# Promo2-From-Promotion-to-Causal-Impact
