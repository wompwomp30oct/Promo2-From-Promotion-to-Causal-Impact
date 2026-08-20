"""Robustness checks and limitations for the Promo2 causal analysis."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from differences import ATTgt

from src.utils import log_exit_check


def _weekly_store_panel(panel: pd.DataFrame) -> pd.DataFrame:
    df = panel.copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["adoption_date"] = pd.to_datetime(df["adoption_date"], errors="coerce")
    df = df[df["Open"].fillna(1).astype(int) == 1].copy()
    df["week"] = df["Date"].dt.to_period("W-MON")
    df["cohort"] = df["adoption_date"].dt.to_period("W-MON")
    weekly = (
        df.groupby(["Store", "week"], as_index=False)
        .agg(
            Sales=("Sales", "sum"),
            Promo=("Promo", "max"),
            SchoolHoliday=("SchoolHoliday", "max"),
            treatment_status=("treatment_status", "first"),
            cohort=("cohort", "first"),
        )
        .sort_values(["Store", "week"])
        .reset_index(drop=True)
    )
    weekly.loc[weekly["treatment_status"] != "staggered_treated", "cohort"] = np.nan
    return weekly


def placebo_test(panel: pd.DataFrame, placebo_weeks: int = 12) -> dict[str, Any]:
    """Shift the treatment cohort back by a placebo offset and re-estimate on the same panel."""
    weekly = _weekly_store_panel(panel)
    usable = weekly[weekly["treatment_status"].isin(["staggered_treated", "never_treated"])].copy()
    usable["placebo_cohort"] = usable["cohort"].astype("object")
    usable["placebo_cohort"] = usable["placebo_cohort"].where(usable["placebo_cohort"].notna(), np.nan)
    treated = usable[usable["treatment_status"] == "staggered_treated"].copy()
    treated["placebo_cohort"] = treated["cohort"] - pd.DateOffset(weeks=placebo_weeks)
    usable = pd.concat([treated, usable[usable["treatment_status"] == "never_treated"]], ignore_index=True)
    usable = usable.set_index(["Store", "week"])
    model = ATTgt(data=usable[["Sales", "placebo_cohort"]], cohort_column="placebo_cohort", base_period="varying")
    result = model.fit("Sales ~ 1", control_group="never_treated", est_method="reg", progress_bar=False)
    agg = result.aggregate("simple")
    first = agg.iloc[0].to_dict() if not agg.empty else {}
    estimate = first.get("estimate", first.get("effect", np.nan))
    payload = {
        "placebo_weeks": placebo_weeks,
        "estimate": float(estimate) if pd.notna(estimate) else np.nan,
        "summary": agg.to_dict() if agg is not None else None,
    }
    log_exit_check("phase3_placebo_test", payload)
    return payload


def bias_direction_derivation() -> dict[str, Any]:
    """State the directional bias for unobserved competitor pricing as an explicit, labeled hypothesis."""
    payload = {
        "label": "unanchored theoretical reasoning",
        "direction": "If competitor pricing is correlated with adoption and also raises sales pressure outside Promo2, then the observed effect could be biased upward in treated stores relative to the counterfactual.",
        "note": "This is a reasoned direction-of-bias statement, not a measured empirical estimate.",
    }
    log_exit_check("phase3_bias_direction", payload)
    return payload


def stockout_statement() -> dict[str, Any]:
    """State honestly that Open=0 tracks full closures, not stockouts while open."""
    payload = {
        "statement": "Open=0 captures store closures only; it does not observe stockouts while the store remains open. The project therefore does not claim that stockouts were controlled for.",
    }
    log_exit_check("phase3_stockout_statement", payload)
    return payload
