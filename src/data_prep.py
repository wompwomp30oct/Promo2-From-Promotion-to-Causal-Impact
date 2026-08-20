"""
Phase 0 -- Data & Treatment Definition.

Implements, in order:
  1. Load + merge train.csv / store.csv
  2. Missing-adoption-data check (Promo2=1 stores missing SinceWeek/SinceYear)
     -> DROP those stores (treatment-timing field, not an ordinary covariate;
        see docs/MEMORY.md for why drop beats impute here). Raises instead of
        silently proceeding if the dropped count exceeds a guard threshold --
        that would signal a merge/parse bug, not genuine data sparsity.
  3. Compute one adoption date per Promo2=1 store from SinceWeek/SinceYear.
  4. Early-panel buffer  -> excluded_early_thin_pre
  5. Late-panel buffer   -> excluded_late_thin_post
  6. Out-of-window recoding -> recoded_out_of_window (becomes never-treated)
  7. Retain weekly `Promo` as a separate confound column (never dropped).

Produces data/processed/panel.parquet and eval_logs/phase0_step3_counts.json.

Run as a script:  python -m src.data_prep
"""
from __future__ import annotations

import sys
from datetime import date, timedelta

import pandas as pd

from src.utils import (
    DATA_PROCESSED,
    EARLY_BUFFER_WEEKS,
    LATE_BUFFER_WEEKS,
    MISSING_ADOPTION_DROP_GUARD,
    STORE_CSV,
    TRAIN_CSV,
    USABLE_TREATED_FLOOR,
    log_exit_check,
)


class Phase0DataError(RuntimeError):
    """Raised when Phase 0 data checks find something that should stop the
    pipeline rather than be silently logged and passed through."""


def load_raw() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load train.csv and store.csv. Raises a clear error if files are absent."""
    missing = [p for p in (TRAIN_CSV, STORE_CSV) if not p.exists()]
    if missing:
        names = ", ".join(str(p) for p in missing)
        raise FileNotFoundError(
            f"Missing raw data file(s): {names}\n"
            "Download train.csv and store.csv from the Rossmann Store Sales "
            "Kaggle competition and place them in data/raw/ (or run "
            "notebooks/make_synthetic_data.py for a schema-matched smoke test)."
        )
    train = pd.read_csv(TRAIN_CSV, parse_dates=["Date"], low_memory=False)
    store = pd.read_csv(STORE_CSV, low_memory=False)
    return train, store


def check_raw_row_counts(train: pd.DataFrame, store: pd.DataFrame) -> dict:
    """
    Phase 0 Step 2 exit check: row counts should match Kaggle's published
    counts (1,017,209 train rows; 1,115 stores) for the REAL dataset.
    Logged, not enforced -- Kaggle occasionally revises files, and synthetic
    smoke-test data won't match at all, so a mismatch is a flag to
    investigate, not an automatic failure.
    """
    expected_train_rows = 1_017_209
    expected_store_rows = 1_115
    result = {
        "train_rows": int(len(train)),
        "store_rows": int(len(store)),
        "expected_train_rows": expected_train_rows,
        "expected_store_rows": expected_store_rows,
        "train_rows_match": len(train) == expected_train_rows,
        "store_rows_match": len(store) == expected_store_rows,
    }
    log_exit_check("phase0_step2_raw_counts", result)
    return result


def _iso_week_year_to_date(year: float, week: float) -> date | None:
    """
    Convert an ISO (year, week) pair to the Monday of that ISO week.
    Returns None if either value is missing/NaN or if the (year, week)
    pair is not a valid ISO calendar week (e.g. week 53 in a year that
    only has 52) -- treated as a malformed record, not silently coerced.
    """
    if pd.isna(year) or pd.isna(week):
        return None
    try:
        return date.fromisocalendar(int(year), int(week), 1)
    except ValueError:
        return None


def compute_adoption_dates(store: pd.DataFrame) -> pd.DataFrame:
    """
    Add an `adoption_date` column (Python date, or None for Promo2=0 stores
    or malformed ISO week/year values).
    """
    store = store.copy()
    store["adoption_date"] = store.apply(
        lambda r: _iso_week_year_to_date(r.get("Promo2SinceYear"), r.get("Promo2SinceWeek"))
        if r.get("Promo2") == 1
        else None,
        axis=1,
    )
    return store


def apply_missing_adoption_filter(store: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Drop Promo2=1 stores whose adoption_date could not be computed
    (missing or malformed SinceWeek/SinceYear). This is a treatment-timing
    field, not an ordinary covariate -- an imputed date would misassign a
    store to the wrong cohort-time cell for the CS estimator, so we drop
    rather than impute (locked decision, see docs/MEMORY.md).

    Raises Phase0DataError if the dropped count exceeds
    MISSING_ADOPTION_DROP_GUARD: SinceWeek/Year should be structurally null
    only for Promo2=0 stores, so a count this large means a merge/parse bug
    upstream, not the data gap this decision was designed to handle. A
    dropped-store log entry can't compensate for that -- it needs to stop
    the run, not be noted and passed through.
    """
    promo2_stores = store[store["Promo2"] == 1]
    missing_mask = promo2_stores["adoption_date"].isna()
    missing_count = int(missing_mask.sum())
    missing_store_ids = promo2_stores.loc[missing_mask, "Store"].tolist()
    total_promo2 = len(promo2_stores)
    missing_fraction = (missing_count / total_promo2) if total_promo2 else 0.0

    if missing_count > MISSING_ADOPTION_DROP_GUARD:
        raise Phase0DataError(
            f"missing_adoption_dropped={missing_count} exceeds the guard "
            f"threshold of {MISSING_ADOPTION_DROP_GUARD}. SinceWeek/Year "
            "should only be null for Promo2=0 stores -- this count suggests "
            "a merge or parse bug, not genuine data sparsity. Investigate "
            "before rerunning."
        )

    filtered = store[~store["Store"].isin(missing_store_ids)].copy()
    result = {
        "promo2_store_count": total_promo2,
        "missing_adoption_dropped": missing_count,
        "missing_fraction": round(missing_fraction, 4),
        "guard_threshold": MISSING_ADOPTION_DROP_GUARD,
        "dropped_store_ids": missing_store_ids,
    }
    return filtered, result


def apply_boundary_filters(
    store: pd.DataFrame, panel_start: date, panel_end: date
) -> tuple[pd.DataFrame, dict]:
    """
    Apply the early-panel buffer, late-panel buffer, and out-of-window
    recoding. Adds a `treatment_status` column with values:
      - "staggered_treated": usable treated store, adoption inside the
        buffered window
      - "never_treated": Promo2=0 throughout, OR out-of-window recoded
      - "excluded_early_thin_pre": adoption too close to panel start
      - "excluded_late_thin_post": adoption too close to panel end
    """
    store = store.copy()
    early_cutoff = panel_start + timedelta(weeks=EARLY_BUFFER_WEEKS)
    late_cutoff = panel_end - timedelta(weeks=LATE_BUFFER_WEEKS)

    def classify(row) -> str:
        ad = row["adoption_date"]
        if ad is None:
            return "never_treated"
        if ad > panel_end:
            return "never_treated"  # out-of-window recoding
        if ad < early_cutoff:
            return "excluded_early_thin_pre"
        if ad > late_cutoff:
            return "excluded_late_thin_post"
        return "staggered_treated"

    # Track out-of-window recodes separately before folding into never_treated,
    # so the count is visible even though the final label matches never_treated.
    store["_out_of_window"] = store["adoption_date"].apply(
        lambda ad: ad is not None and ad > panel_end
    )
    store["treatment_status"] = store.apply(classify, axis=1)

    counts = store["treatment_status"].value_counts().to_dict()
    result = {
        "panel_start": panel_start.isoformat(),
        "panel_end": panel_end.isoformat(),
        "early_buffer_weeks": EARLY_BUFFER_WEEKS,
        "late_buffer_weeks": LATE_BUFFER_WEEKS,
        "excluded_early_thin_pre": int(counts.get("excluded_early_thin_pre", 0)),
        "excluded_late_thin_post": int(counts.get("excluded_late_thin_post", 0)),
        "recoded_out_of_window": int(store["_out_of_window"].sum()),
        "usable_staggered_treated": int(counts.get("staggered_treated", 0)),
        "never_treated_donor_pool": int(counts.get("never_treated", 0)),
        "usable_treated_below_floor": int(counts.get("staggered_treated", 0))
        < USABLE_TREATED_FLOOR,
        "floor_used": USABLE_TREATED_FLOOR,
    }
    store = store.drop(columns=["_out_of_window"])
    return store, result


def build_panel(train: pd.DataFrame, store: pd.DataFrame) -> pd.DataFrame:
    """Merge daily sales with store-level treatment/covariate info."""
    return train.merge(store, on="Store", how="left", validate="many_to_one")


def run_phase0() -> pd.DataFrame:
    """Execute Phase 0 end-to-end and write all logged artifacts."""
    train, store_raw = load_raw()
    check_raw_row_counts(train, store_raw)

    panel_start = train["Date"].min().date()
    panel_end = train["Date"].max().date()

    store = compute_adoption_dates(store_raw)
    store, missing_result = apply_missing_adoption_filter(store)  # may raise
    store, boundary_result = apply_boundary_filters(store, panel_start, panel_end)

    counts = {
        "missing_adoption_dropped": missing_result["missing_adoption_dropped"],
        "missing_adoption_guard_threshold": missing_result["guard_threshold"],
        "excluded_early_thin_pre": boundary_result["excluded_early_thin_pre"],
        "excluded_late_thin_post": boundary_result["excluded_late_thin_post"],
        "recoded_out_of_window": boundary_result["recoded_out_of_window"],
        "usable_staggered_treated": boundary_result["usable_staggered_treated"],
        "never_treated_donor_pool": boundary_result["never_treated_donor_pool"],
        "usable_treated_below_floor": boundary_result["usable_treated_below_floor"],
        "panel_start": boundary_result["panel_start"],
        "panel_end": boundary_result["panel_end"],
        "early_buffer_weeks": boundary_result["early_buffer_weeks"],
        "late_buffer_weeks": boundary_result["late_buffer_weeks"],
    }
    log_exit_check("phase0_step3_counts", counts)

    if boundary_result["usable_treated_below_floor"]:
        print(
            "WARNING: usable_staggered_treated "
            f"({boundary_result['usable_staggered_treated']}) is below the "
            f"floor of {USABLE_TREATED_FLOOR}. Per the plan, this is a "
            "stop-and-reconsider-the-design signal, not a proceed-silently one.",
            file=sys.stderr,
        )

    # Retain weekly `Promo` as a distinct confound column -- it lives on the
    # daily `train` table already, so it survives the merge untouched.
    panel = build_panel(train, store)
    assert "Promo" in panel.columns, "weekly Promo column dropped during merge"
    assert "treatment_status" in panel.columns

    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    out_path = DATA_PROCESSED / "panel.parquet"
    panel.to_parquet(out_path, index=False)

    log_exit_check(
        "phase0_output",
        {
            "output_path": str(out_path),
            "row_count": int(len(panel)),
            "store_count": int(panel["Store"].nunique()),
            "columns": list(panel.columns),
        },
    )
    return panel


if __name__ == "__main__":
    df = run_phase0()
    print(f"Phase 0 complete. Panel shape: {df.shape}")
    print("See eval_logs/phase0_step3_counts.json for the six logged counts.")
