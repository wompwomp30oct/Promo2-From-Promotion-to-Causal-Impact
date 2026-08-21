"""
Shared utilities: JSON exit-check logging and path constants.

Every phase script writes its exit-check results through log_exit_check()
so eval_logs/ is a single source of truth for "did this step actually pass,
and what number did it produce" -- matching the plan's rule that no README
section may state a conclusion without a corresponding logged artifact.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = REPO_ROOT / "data" / "raw"
DATA_PROCESSED = REPO_ROOT / "data" / "processed"
EVAL_LOGS = REPO_ROOT / "eval_logs"
DOCS = REPO_ROOT / "docs"

TRAIN_CSV = DATA_RAW / "train.csv"
STORE_CSV = DATA_RAW / "store.csv"

# Locked design constants (see docs/MEMORY.md for rationale / review history)
EARLY_BUFFER_WEEKS = 8  # lower bound of the plan's locked 8-10 week range
LATE_BUFFER_WEEKS = 8   # kept as a separate constant (not reused from EARLY_*)
                         # so Phase 1's event-study window justification can
                         # reference either bound independently if they ever
                         # need to diverge.
THIN_CELL_MIN_STORES = 10
USABLE_TREATED_FLOOR = 50  # rough floor before the design itself is questioned
EVENT_WINDOW_WEEKS = tuple(range(-8, 9))
EVENT_REFERENCE_WEEK = -1
MISSING_ADOPTION_DROP_GUARD = 500  # raise (not just warn) above this count --
                                    # SinceWeek/Year should be structurally
                                    # null only for Promo2=0 stores, so a
                                    # count this large signals a merge/parse
                                    # bug, not genuine data sparsity.


def log_exit_check(step_name: str, payload: dict[str, Any]) -> Path:
    """
    Write one exit-check result to eval_logs/<step_name>.json.

    Overwrites on rerun (idempotent) but keeps a timestamp so it's obvious
    when a logged number was last produced.
    """
    EVAL_LOGS.mkdir(parents=True, exist_ok=True)
    record = {
        "step": step_name,
        "logged_at_utc": datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    out_path = EVAL_LOGS / f"{step_name}.json"
    with out_path.open("w") as f:
        json.dump(record, f, indent=2, default=str)
    return out_path


def read_exit_check(step_name: str) -> dict[str, Any]:
    """Read back a previously logged exit-check. Raises if it doesn't exist."""
    path = EVAL_LOGS / f"{step_name}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"No exit-check log for '{step_name}' yet -- run that step first."
        )
    with path.open() as f:
        return json.load(f)
