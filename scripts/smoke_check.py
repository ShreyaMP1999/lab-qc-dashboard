"""
Quick project health check for the Lab QC dashboard.

Run with: python scripts/smoke_check.py
"""

import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src import queries


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    sites, assays = queries.get_filter_options()
    require(sites, "No sites found in qc_results.")
    require(assays, "No assays found in qc_results.")

    summary = queries.summary_by_site_assay()
    require(len(summary) == len(sites) * len(assays), "Summary row count does not match site/assay combinations.")
    require(summary["pass_rate_pct"].between(0, 100).all(), "Summary pass rates must be between 0 and 100.")

    trend = queries.daily_trend(sites[0], assays[0], "Low")
    require(not trend.empty, "Daily trend query returned no rows.")
    require({"run_date", "mean_result", "lower_limit", "upper_limit"}.issubset(trend.columns), "Daily trend columns are incomplete.")

    rolling = queries.rolling_out_of_range_rate(sites[0], assays[0])
    require(not rolling.empty, "Rolling pass-rate query returned no rows.")
    require(rolling["rolling_pass_rate"].between(0, 1).all(), "Rolling pass rates must be between 0 and 1.")

    worst = queries.worst_performing_combinations()
    require(not worst.empty, "Worst-performing combinations query returned no rows.")

    print("Smoke check passed.")
    print(f"Sites: {len(sites)} | Assays: {len(assays)} | Summary rows: {len(summary)}")


if __name__ == "__main__":
    main()
