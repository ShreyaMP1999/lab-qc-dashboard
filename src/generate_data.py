"""
Generates a synthetic multi-site, multi-assay lab QC dataset and loads it into
a SQLite database. Mirrors the shape of real lab QC data: multiple sites
running the same assays over time, with control lot values that should stay
within acceptance limits, and occasional out-of-range flags.

Run with: python src/generate_data.py
Produces: data/lab_qc.db
"""

import os
import sqlite3
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "lab_qc.db")
RANDOM_SEED = 42

SITES = ["Irvine", "Chicago", "Austin", "Raleigh"]
ASSAYS = [
    {"name": "Lyme-OspC", "target_mean": 12.0, "sd": 1.1, "lsl": 9.0, "usl": 15.0},
    {"name": "RPR", "target_mean": 4.5, "sd": 0.5, "lsl": 3.0, "usl": 6.0},
    {"name": "SyphT", "target_mean": 8.0, "sd": 0.8, "lsl": 6.0, "usl": 10.0},
    {"name": "HbA1c-QC", "target_mean": 6.2, "sd": 0.4, "lsl": 5.0, "usl": 7.5},
]
CONTROL_LEVELS = ["Low", "Medium", "High"]

START_DATE = datetime(2025, 6, 1)
N_DAYS = 240  # 8 months of daily QC runs


def generate(seed=RANDOM_SEED):
    rng = np.random.default_rng(seed)
    rows = []
    run_id = 1
    for day_offset in range(N_DAYS):
        run_date = START_DATE + timedelta(days=day_offset)
        for site in SITES:
            for assay in ASSAYS:
                for level in CONTROL_LEVELS:
                    # Slight per-site systematic offset (some sites run a hair high/low)
                    site_bias = {"Irvine": 0.0, "Chicago": 0.05, "Austin": -0.03, "Raleigh": 0.08}[site]
                    level_multiplier = {"Low": 0.7, "Medium": 1.0, "High": 1.3}[level]

                    mean = assay["target_mean"] * level_multiplier
                    value = rng.normal(mean * (1 + site_bias), assay["sd"] * level_multiplier)

                    # Inject occasional drift/outlier events to make the data realistic
                    if rng.random() < 0.015:
                        value += rng.choice([-1, 1]) * assay["sd"] * 4

                    lsl = assay["lsl"] * level_multiplier
                    usl = assay["usl"] * level_multiplier
                    in_range = lsl <= value <= usl

                    rows.append(
                        {
                            "run_id": run_id,
                            "run_date": run_date.strftime("%Y-%m-%d"),
                            "site": site,
                            "assay": assay["name"],
                            "control_level": level,
                            "result_value": round(float(value), 3),
                            "lower_limit": round(lsl, 3),
                            "upper_limit": round(usl, 3),
                            "in_range": int(in_range),
                        }
                    )
                    run_id += 1

    return pd.DataFrame(rows)


def main():
    df = generate()

    conn = sqlite3.connect(DB_PATH)
    df.to_sql("qc_results", conn, if_exists="replace", index=False)

    # A couple of indexes, since this is meant to demonstrate real query patterns
    conn.execute("CREATE INDEX IF NOT EXISTS idx_site_assay ON qc_results(site, assay)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_run_date ON qc_results(run_date)")
    conn.commit()
    conn.close()

    print(f"Generated {len(df):,} QC result rows across {len(SITES)} sites and {len(ASSAYS)} assays.")
    print(f"Saved to {DB_PATH}")
    print(f"Out-of-range rate: {(1 - df['in_range'].mean()) * 100:.2f}%")


if __name__ == "__main__":
    main()
