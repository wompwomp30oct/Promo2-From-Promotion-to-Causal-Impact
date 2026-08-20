"""Main estimator logic for the Promo2 causal-impact project."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from linearmodels import PanelOLS

from differences import ATTgt

from src.utils import EVAL_LOGS, log_exit_check


def _weekly_store_panel(panel: pd.DataFrame) -> pd.DataFrame:
    df = panel.copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["adoption_date"] = pd.to_datetime(df["adoption_date"], errors="coerce")
    df = df[df["Open"].fillna(1).astype(int) == 1].copy()
    df["week"] = df["Date"].dt.to_period("W-MON")
    df["adoption_week"] = df["adoption_date"].dt.to_period("W-MON")
    weekly = (
        df.groupby(["Store", "week"], as_index=False)
        .agg(
            Sales=("Sales", "sum"),
            Promo=("Promo", "max"),
            SchoolHoliday=("SchoolHoliday", "max"),
            StateHoliday=("StateHoliday", lambda s: int((s != "0").any() or (s != 0).any())),
            treatment_status=("treatment_status", "first"),
            adoption_week=("adoption_week", "first"),
        )
        .sort_values(["Store", "week"])
        .reset_index(drop=True)
    )
    weekly["cohort"] = weekly["adoption_week"]
    weekly.loc[weekly["treatment_status"] != "staggered_treated", "cohort"] = np.nan
    weekly["is_treated"] = weekly["treatment_status"].eq("staggered_treated").astype(int)
    return weekly


def _safe_estimate_from_agg(agg: pd.DataFrame) -> float | None:
    if agg is None or agg.empty:
        return None
    first = agg.iloc[0].to_dict()
    for key in ("estimate", "effect", "ATT", "att", "coef"):
        if key in first and pd.notna(first[key]):
            return float(first[key])
    return None


def pooled_twfe_baseline(panel: pd.DataFrame) -> dict[str, Any]:
    """Naive baseline: pooled TWFE with a single post-treatment indicator."""
    weekly = _weekly_store_panel(panel)
    usable = weekly[weekly["treatment_status"].isin(["staggered_treated", "never_treated"])].copy()
    usable["treated_post"] = (
        usable["is_treated"].astype(int).to_numpy() * (usable["week"] >= usable["cohort"]).astype(int).to_numpy()
    )
    usable = usable.dropna(subset=["treated_post"])  # keep all valid rows
    usable = usable.set_index(["Store", "week"])
    model = PanelOLS.from_formula(
        "Sales ~ 1 + treated_post + EntityEffects + TimeEffects",
        data=usable,
        entity_effects=True,
        time_effects=True,
    )
    fitted = model.fit(cov_type="clustered", cluster_entity=True)
    payload = {
        "estimate": float(fitted.params.get("treated_post", np.nan)),
        "std_error": float(fitted.std_errors.get("treated_post", np.nan)),
        "pvalue": float(fitted.pvalues.get("treated_post", np.nan)),
        "model": "pooled_twfe_baseline",
    }
    log_exit_check("phase2_naive_twfe", payload)
    return payload


def callaway_santanna_estimate(panel: pd.DataFrame) -> dict[str, Any]:
    """Primary staggered DiD estimate using differences.ATTgt."""
    weekly = _weekly_store_panel(panel)
    usable = weekly[weekly["treatment_status"].isin(["staggered_treated", "never_treated"])].copy()
    usable = usable.set_index(["Store", "week"]).sort_index()
    data = usable[["Sales", "cohort", "Promo", "SchoolHoliday"]].copy()
    model = ATTgt(data=data, cohort_column="cohort", base_period="varying")
    result = model.fit(
        "Sales ~ Promo + SchoolHoliday",
        control_group="never_treated",
        cluster_var="Store",
        est_method="reg",
        progress_bar=False,
    )
    simple = result.aggregate("simple")
    event = result.aggregate("event")
    payload = {
        "simple_ATT_estimate": _safe_estimate_from_agg(simple),
        "simple_ATT_summary": simple.to_dict() if simple is not None else None,
        "event_study_summary": event.to_dict() if event is not None else None,
        "control_group": "never_treated",
        "estimator": "differences.ATTgt",
    }
    log_exit_check("phase2_primary_estimate", payload)
    return payload


def cohort_weight_audit(panel: pd.DataFrame) -> dict[str, Any]:
    """Audit how much each cohort contributes to the headline ATT."""
    weekly = _weekly_store_panel(panel)
    treated = weekly[weekly["treatment_status"] == "staggered_treated"].copy()
    treated = treated.dropna(subset=["cohort"])\
        .groupby("cohort").size()\
        .rename("cohort_size")
    total = treated.sum()
    weights = (treated / total).to_dict() if total else {}
    payload = {
        "cohort_sizes": {str(k): int(v) for k, v in treated.items()},
        "cohort_weights": {str(k): float(v) for k, v in weights.items()},
    }
    log_exit_check("phase2_cohort_weights", payload)
    return payload


def collision_rule(panel: pd.DataFrame, thin_threshold: int = 10) -> dict[str, Any]:
    """Report the collision rule when thin-cell and weight diagnostics disagree."""
    weekly = _weekly_store_panel(panel)
    treated = weekly[weekly["treatment_status"] == "staggered_treated"].copy()
    treated = treated.dropna(subset=["cohort"])
    cohort_counts = treated.groupby("cohort").size().to_dict()
    thin_cohorts = {str(k) for k, v in cohort_counts.items() if v < thin_threshold}
    weight_audit = cohort_weight_audit(panel)
    weighted_cohorts = {str(k) for k, v in weight_audit["cohort_weights"].items() if v > 0.1}
    collision = set(thin_cohorts) & set(weighted_cohorts)
    payload = {
        "thin_cohorts": sorted(thin_cohorts),
        "high_weight_cohorts": sorted(weighted_cohorts),
        "collision": sorted(collision),
        "report_all_variants": bool(collision),
    }
    log_exit_check("phase2_collision_rule", payload)
    return payload
