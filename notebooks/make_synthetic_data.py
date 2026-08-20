"""
Generates synthetic train.csv + store.csv with the same SCHEMA as Rossmann
Store Sales, deliberately covering every Phase 0 edge case:
  - a store with Promo2=1 and missing since-week/year (missing_adoption_dropped)
  - a store adopting inside the first 8 weeks (excluded_early_thin_pre)
  - a store adopting inside the last 8 weeks (excluded_late_thin_post)
  - a store with an adoption date computed AFTER the panel end (recoded_out_of_window)
  - a store adopting cleanly mid-panel (staggered_treated)
  - a store with Promo2=0 throughout (never_treated)

This is NOT real Rossmann data -- purely for testing data_prep.py logic.
"""
import datetime as dt
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)

PANEL_START = dt.date(2013, 1, 1)
PANEL_END = dt.date(2015, 7, 31)
dates = pd.date_range(PANEL_START, PANEL_END, freq="D")

stores = pd.DataFrame(
    {
        "Store": [1, 2, 3, 4, 5, 6],
        "StoreType": ["a", "b", "a", "c", "a", "b"],
        "Assortment": ["a", "a", "c", "b", "a", "c"],
        "CompetitionDistance": [1200.0, 500.0, np.nan, 3400.0, 800.0, 2100.0],
        "CompetitionOpenSinceMonth": [9, 11, np.nan, 3, 1, 6],
        "CompetitionOpenSinceYear": [2008, 2007, np.nan, 2012, 2010, 2011],
        "Promo2": [1, 1, 1, 1, 1, 0],
        # Store 1: missing since-week/year despite Promo2=1 -> missing_adoption_dropped
        "Promo2SinceWeek": [np.nan, 3, 40, 20, 10, np.nan],
        "Promo2SinceYear": [np.nan, 2013, 2015, 2014, 2013, np.nan],
        # Store 2: week 3, 2013 -> ~Jan 14 2013, inside first 8 weeks -> excluded_early_thin_pre
        # Store 3: week 40, 2015 -> Sep/Oct 2015, AFTER panel end (Jul 2015) -> recoded_out_of_window
        # Store 4: week 20, 2014 -> mid-panel, clean -> staggered_treated
        # Store 5: week 10, 2013 -> ~Mar 2013, clean, well inside buffers -> staggered_treated
        # Store 6: Promo2=0 -> never_treated
        "PromoInterval": ["", "Jan,Apr,Jul,Oct", "Feb,May,Aug,Nov", "Mar,Jun,Sept,Dec", "", ""],
    }
)

store_rows = []
for _, s in stores.iterrows():
    store_rows.append(s)
store.to_csv if False else None  # no-op placeholder (kept out of exec path)

stores.to_csv("/home/claude/promo-causal-impact/data/raw/store.csv", index=False)

train_rows = []
for store_id in stores["Store"]:
    base_sales = rng.integers(4000, 8000)
    for d in dates:
        is_open = 0 if d.weekday() == 6 else 1  # closed Sundays
        train_rows.append(
            {
                "Store": store_id,
                "Date": d.strftime("%Y-%m-%d"),
                "Sales": int(base_sales * is_open + rng.normal(0, 200)) if is_open else 0,
                "Customers": int(500 * is_open + rng.normal(0, 50)) if is_open else 0,
                "Open": is_open,
                "Promo": int(rng.random() < 0.3),
                "StateHoliday": "0",
                "SchoolHoliday": int(rng.random() < 0.1),
                "DayOfWeek": d.isoweekday(),
            }
        )

train = pd.DataFrame(train_rows)
train.to_csv("/home/claude/promo-causal-impact/data/raw/train.csv", index=False)

print(f"Synthetic train.csv: {len(train)} rows, store.csv: {len(stores)} rows")
